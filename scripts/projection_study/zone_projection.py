"""Shot-zone share + zone FG% projection.

Zones: RA, Paint (non-RA), Mid, Corner3 (L+R), Other3 (above the break + backcourt).
Share:  FGA- and recency-weighted 3-season mean + damped linear trend (lam), clipped, renormalized.
FG%:    recency-weighted makes/attempts over 3 seasons, shrunk toward the league zone % with strength k_z.
Tuning: project '25 from '22–'24 (grid search). Test: same recipe projects '26 from '23–'25, scored once.
Eligible: 100+ FGA in each of the 3 input seasons; scored where the target season has 200+ FGA.
"""
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path.home() / "PycharmProjects" / "nba-pipeline" / "data" / "raw" / "shot_locations"
ZMAP = {"Restricted Area": "RA", "In The Paint (Non-RA)": "Paint", "Mid-Range": "Mid", "Left Corner 3": "Corner3",
        "Right Corner 3": "Corner3", "Above the Break 3": "Other3", "Backcourt": "Other3"}
ZONES = ["RA", "Paint", "Mid", "Corner3", "Other3"]
VAL = {"RA": 2, "Paint": 2, "Mid": 2, "Corner3": 3, "Other3": 3}
SIX = {201942: "DeRozan", 202696: "Vučević", 1626167: "Turner", 1628969: "Bridges", 1628389: "Adebayo", 203999: "Jokić"}


def load(season: str) -> pd.DataFrame:
    rs = json.load(open(RAW / f"{season}.json"))["resultSets"]
    cat, cols = rs["headers"]
    skip, names = cat["columnsToSkip"], cat["columnNames"]
    out = []
    for r in rs["rowSet"]:
        for i, zn in enumerate(names):
            if zn in ZMAP:
                fgm, fga = r[skip + 3 * i], r[skip + 3 * i + 1]
                out.append((r[0], r[1], ZMAP[zn], fgm or 0, fga or 0))
    d = pd.DataFrame(out, columns=["pid", "name", "zone", "fgm", "fga"]).groupby(["pid", "name", "zone"]).sum().reset_index()
    d["season"] = season
    return d


ALL = pd.concat(load(s) for s in ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"])
W = ALL.pivot_table(index=["pid", "season"], columns="zone", values=["fgm", "fga"], fill_value=0)


def frame(seasons):
    """per player: arrays [n_season, zone] of fga, fgm for players with 100+ FGA in every input season."""
    keep = None
    fga, fgm = [], []
    for s in seasons:
        x = W.xs(s, level="season")
        ok = set(x.index[x["fga"].sum(axis=1) >= 100])
        keep = ok if keep is None else keep & ok
    keep = sorted(keep)
    for s in seasons:
        x = W.xs(s, level="season").loc[keep]
        fga.append(x["fga"][ZONES].to_numpy(float))
        fgm.append(x["fgm"][ZONES].to_numpy(float))
    return keep, np.stack(fga, 1), np.stack(fgm, 1)  # [player, season, zone]


def project(seasons, r, lam, k):
    pids, fga, fgm = frame(seasons)
    t = np.array([-2.0, -1.0, 0.0])
    rw = r ** (t + 2)  # recency weights 1, r, r^2
    tot = fga.sum(2)  # [p, s]
    share = fga / tot[:, :, None]
    w = tot * rw  # [p, s]
    wn = w / w.sum(1, keepdims=True)
    tbar = (wn * t).sum(1)  # [p]
    lvl = (wn[:, :, None] * share).sum(1)  # [p, z]
    dt = t[None, :] - tbar[:, None]
    slope = (wn[:, :, None] * dt[:, :, None] * (share - lvl[:, None, :])).sum(1) / (wn * dt ** 2).sum(1)[:, None]
    proj_share = np.clip(lvl + lam * slope * (1 - tbar)[:, None], 0, None)
    proj_share /= proj_share.sum(1, keepdims=True)
    mu = fgm.sum((0, 1)) / fga.sum((0, 1))  # league zone % over the input seasons (eligible players)
    m = (fgm * rw[None, :, None]).sum(1)
    a = (fga * rw[None, :, None]).sum(1)
    proj_pct = (m + k * mu) / (a + k)
    return pids, proj_share, proj_pct, (fga, fgm)


def actual(pids, season):
    x = W.xs(season, level="season").reindex(pids)
    fga, fgm = x["fga"][ZONES].to_numpy(float), x["fgm"][ZONES].to_numpy(float)
    return fga, fgm


def score(pids, ps, pp, season):
    fga, fgm = actual(pids, season)
    tot = np.nan_to_num(fga.sum(1))
    ok = tot >= 200
    ps, pp, fga, fgm, tot = ps[ok], pp[ok], fga[ok], fgm[ok], tot[ok]
    sh = fga / tot[:, None]
    share_err = (np.abs(ps - sh).sum(1) / 2 * tot).sum() / tot.sum()  # share of shots in the wrong zone
    pct_err, floor = {}, {}
    for j, z in enumerate(ZONES):
        n = fga[:, j]
        has = n > 0
        act = fgm[has, j] / n[has]
        pct_err[z] = (np.abs(pp[has, j] - act) * n[has]).sum() / n[has].sum()
        floor[z] = (np.sqrt(pp[has, j] * (1 - pp[has, j]) / n[has]) * np.sqrt(2 / np.pi) * n[has]).sum() / n[has].sum()
    vals = np.array([VAL[z] for z in ZONES])
    pps_p = (ps * pp * vals).sum(1)
    pps_a = (fgm * vals).sum(1) / tot
    pps_err = (np.abs(pps_p - pps_a) * tot).sum() / tot.sum()
    return dict(n=int(ok.sum()), share_err=share_err, pct=pct_err, floor=floor, pps_err=pps_err)


def baseline(seasons, target, kind):
    pids, fga, fgm = frame(seasons)
    if kind == "last season":
        a, m = fga[:, -1], fgm[:, -1]
    else:  # plain 3-yr pooled
        a, m = fga.sum(1), fgm.sum(1)
    ps = a / a.sum(1, keepdims=True)
    mu = fgm.sum((0, 1)) / fga.sum((0, 1))
    pp = np.where(a > 0, m / np.where(a > 0, a, 1), mu)
    return score(pids, ps, pp, target)


TUNE_IN, TUNE_OUT = ["2021-22", "2022-23", "2023-24"], "2024-25"
TEST_IN, TEST_OUT = ["2022-23", "2023-24", "2024-25"], "2025-26"

# share: tune r, lam on share error; FG%: tune r_pct and k per zone on that zone's error
best_share = min(((r, lam) for r in [1, 1.5, 2, 3] for lam in [0, 0.25, 0.5, 0.75, 1]),
                 key=lambda p: score(*project(TUNE_IN, p[0], p[1], np.zeros(5))[:3], TUNE_OUT)["share_err"])
best_k, best_rp = np.zeros(5), 1.0
best_tot = None
for rp in [1, 1.5, 2]:
    ks = []
    for j, z in enumerate(ZONES):
        def err(kz):
            k = np.full(5, 100.0)
            k[j] = kz
            return score(*project(TUNE_IN, rp, 0, k)[:3], TUNE_OUT)["pct"][z]
        ks.append(min([0, 10, 25, 50, 100, 200, 400, 800, 1600], key=err))
    k = np.array(ks, float)
    s = score(*project(TUNE_IN, rp, 0, k)[:3], TUNE_OUT)
    tot = sum(s["pct"].values())
    if best_tot is None or tot < best_tot:
        best_tot, best_rp, best_k = tot, rp, k
r_s, lam = best_share
print(f"TUNED on '22–'24 → '25:  share recency r={r_s}, trend damping lam={lam};  FG% recency r={best_rp}, "
      f"shrink k = " + ", ".join(f"{z} {int(k)}" for z, k in zip(ZONES, best_k)))


def show(label, s):
    print(f"  {label:<14} n={s['n']:>3}  shots in wrong zone {100 * s['share_err']:4.1f}%   "
          + "  ".join(f"{z} {100 * s['pct'][z]:4.1f}" for z in ZONES) + f"   pts/FGA err {s['pps_err']:.3f}")


for name, ins, out in [("TUNE  '22–'24 → '25", TUNE_IN, TUNE_OUT), ("TEST  '23–'25 → '26", TEST_IN, TEST_OUT)]:
    print(f"\n{name}   (FG% columns = attempt-weighted mean abs error, pp)")
    pids, ps, _, _ = project(ins, r_s, lam, best_k)
    _, _, pp, _ = project(ins, best_rp, 0, best_k)
    s = score(pids, ps, pp, out)
    show("model", s)
    show("last season", baseline(ins, out, "last season"))
    show("3-yr average", baseline(ins, out, "3yr"))
    print(f"  {'noise floor':<14} (error even with the true %, from shot count alone)          "
          + "  ".join(f"{z} {100 * s['floor'][z]:4.1f}" for z in ZONES))

# the six, test window
pids, ps, _, _ = project(TEST_IN, r_s, lam, best_k)
_, _, pp, _ = project(TEST_IN, best_rp, 0, best_k)
fga, fgm = actual(pids, TEST_OUT)
print("\nThe six — projected '26 vs actual '26 (share of FGA % | FG %)")
for pid, n in SIX.items():
    if pid not in pids:
        print(f"  {n}: not eligible")
        continue
    i = pids.index(pid)
    a = fga[i]
    if np.isnan(a).all() or np.nansum(a) == 0:
        print(f"  {n}: no '26 shots")
        continue
    print(f"  {n}  ('26 FGA {int(np.nansum(a))})")
    for j, z in enumerate(ZONES):
        act_pct = f"{100 * fgm[i, j] / a[j]:5.1f}" if a[j] > 0 else "   — "
        print(f"     {z:<8} share {100 * ps[i, j]:5.1f} → {100 * a[j] / np.nansum(a):5.1f}    "
              f"FG% {100 * pp[i, j]:5.1f} → {act_pct}  ({int(a[j])} att)")
