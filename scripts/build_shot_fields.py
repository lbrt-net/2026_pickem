"""Build the player page's shot chart fields and load them into the site (nba_shot_fields).

    python3 scripts/build_shot_fields.py --post                                # every pool player, 2026-27 (the page shows only this)
    python3 scripts/build_shot_fields.py --season 2025-26 --player 1628378     # check the method on an old season, print only

Method = nba-pipeline/analysis/shot_chart.py (TEAMMATE_EFFECT.md "Shot charts"), cell for cell:
- where: his shots smoothed at 1.5 ft, twos and threes separately with the kernel mass that falls across the line
  corrected, a 1.2-ft finish blur; the layers are the levels holding 95 / 80 / 60 / 40 / 20% of his shots.
- how well: his points per shot minus the league's from the same spot (both 4 ft, twos / threes apart), shrunk toward
  even where he has few shots nearby (n / (n + 6)), faded outside the area holding 90% of his shots, 1.2-ft finish blur.
Stored every 0.5 ft: lvl (0 = outside the 95% area, 1..5) and d = points vs league x100 where lvl > 0.

Runs locally (numpy / pandas; system python3) on the play-by-play pulls in nba_api_tests / nba-pipeline. Meant to
join the nightly job once it exists. Loads INTERNAL_API_KEY from .env. Re-running is safe (upsert).
"""
import argparse, json, math, os, subprocess, sys, time
from pathlib import Path

import numpy as np
import requests

PIPE = Path("/Users/allan/PycharmProjects/nba-pipeline")
# The page shows this season only. 2026-27 play-by-play lands here once the nightly pull exists; older seasons stay
# runnable for checking the method (--season 2025-26 --player ...) but are never posted.
PBP = {"2026-27": "/Users/allan/PycharmProjects/nba_api_tests/data/playbyplayv3/2026_27_regular_season/*.parquet",
       "2025-26": "/Users/allan/PycharmProjects/nba_api_tests/data/playbyplayv3/2025_26_regular_season/*.parquet"}
LIVE = "2026-27"
MIN_SHOTS = 50          # fewer than this in a season: no chart (the layers would be a few dots)
STEP = 5                # stored cell = 0.5 ft
X0, X1, Y0, Y1 = -250, 250, -52, 420
NX, NY = X1 - X0, Y1 - Y0
S_WHERE, S_HOW = 15, 40
gy, gx = np.mgrid[Y0:Y1, X0:X1]
IS3 = (np.abs(gx) >= 220) | (np.hypot(gx, gy) >= 237.5)
EDGE = np.clip(np.minimum.reduce([gx - X0, X1 - 1 - gx, gy - Y0, Y1 - 1 - gy]) / 20.0, 0, 1)
EDGE = EDGE * EDGE * (3 - 2 * EDGE)


def load_env():
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def grid(x, y, w=None):
    g = np.zeros((NY, NX))
    np.add.at(g, ((y - Y0).clip(0, NY - 1).astype(int), (x - X0).clip(0, NX - 1).astype(int)), 1 if w is None else w)
    return g


def blur(g, s):
    k = np.exp(-0.5 * (np.arange(-3 * s, 3 * s + 1) / s) ** 2); k /= k.sum()
    g = np.apply_along_axis(lambda r: np.convolve(r, k, "same"), 1, g)
    return np.apply_along_axis(lambda c: np.convolve(c, k, "same"), 0, g)


DEN = {s: (blur(IS3.astype(float), s), blur((~IS3).astype(float), s)) for s in (S_WHERE, S_HOW)}


def kde(df, s, w=None):
    out = np.zeros((NY, NX))
    for m, part, den in ((IS3, df[df.three], DEN[s][0]), (~IS3, df[~df.three], DEN[s][1])):
        num = blur(grid(part.x_legacy.values, part.y_legacy.values, None if w is None else part[w].values), s)
        out[m] = (num / np.maximum(den, 1e-9))[m]
    return out


def soft(field, level):
    x = np.clip(np.log(np.maximum(field, 1e-15) / level) / np.log(3) + 0.5, 0, 1)
    return x * x * (3 - 2 * x)


def fields(sh, l_pps):
    p_raw = kde(sh, S_WHERE); p_d = p_raw / p_raw.sum()
    p_att, p_pts = kde(sh, S_HOW), kde(sh, S_HOW, "pts")
    n_how = p_att * 2 * math.pi * S_HOW ** 2
    delta = (p_pts / np.maximum(p_att, 1e-9) - l_pps) * (n_how / (n_how + 6))
    flat = np.sort(p_d.ravel())[::-1]
    delta = blur(delta * soft(p_d, float(flat[np.searchsorted(np.cumsum(flat), 0.90)])) * EDGE, 12)
    dens = blur(p_d * EDGE, 12)
    dflat = np.sort(dens.ravel())[::-1]; dcum = np.cumsum(dflat) / dflat.sum()
    hdr = [float(dflat[np.searchsorted(dcum, q)]) for q in (0.95, 0.80, 0.60, 0.40, 0.20)]
    d5, f5 = dens[::STEP, ::STEP], delta[::STEP, ::STEP]
    lvl = sum((d5 >= h).astype(int) for h in hdr)
    return {"x0": X0, "y0": Y0, "step": STEP, "nx": NX // STEP, "ny": NY // STEP, "n": int(len(sh)),
            "lvl": "".join(map(str, lvl.ravel())), "d": [int(round(v * 100)) for v in f5[lvl > 0]]}


def pool_ids(base):
    rows = json.loads(subprocess.run(["curl", "-s", f"{base}/fantasy/2026_27/players?scenario=live"], capture_output=True, text=True).stdout)
    return {p["id"] for p in rows if p.get("in_pool") and p["id"].isdigit()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", action="append")
    ap.add_argument("--player", action="append")
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--base", default="https://lbrt.net")
    a = ap.parse_args()
    load_env()
    key = os.environ.get("INTERNAL_API_KEY", "")
    if a.post and not key:
        sys.exit("INTERNAL_API_KEY missing (.env)")
    sys.path.insert(0, str(PIPE / "process"))
    import possession_rules as pr
    ids = set(a.player) if a.player else pool_ids(a.base)
    if a.post and any(s != LIVE for s in (a.season or [LIVE])):
        sys.exit("the page shows 2026-27 only: post that season, check older ones without --post")
    for season in a.season or [LIVE]:
        t0 = time.time()
        pbp = pr.load(PBP[season]); pbp = pbp[pbp.game_id.str.startswith("002")]
        shots = pbp[pbp.action_type.isin(["Made Shot", "Missed Shot"])].copy()
        shots["pts"] = np.where(shots.action_type == "Made Shot", shots.shot_value, 0); shots["three"] = shots.shot_value == 3
        l_pps = kde(shots, S_HOW, "pts") / np.maximum(kde(shots, S_HOW), 1e-9)  # the league's points per shot, every spot
        print(f"{season}: {len(shots)} league shots loaded in {time.time() - t0:.0f}s", flush=True)
        rows = []
        for pid, sh in shots.groupby("person_id"):
            if str(pid) not in ids or len(sh) < MIN_SHOTS:
                continue
            rows.append({"player_id": str(pid), "season": season, "data": fields(sh, l_pps)})
            if a.post and len(rows) >= 25:
                requests.post(f"{a.base}/nba/admin/shot-fields", json={"rows": rows}, headers={"X-Internal-Key": key}, timeout=120).raise_for_status()
                rows = []
        if a.post and rows:
            requests.post(f"{a.base}/nba/admin/shot-fields", json={"rows": rows}, headers={"X-Internal-Key": key}, timeout=120).raise_for_status()
        if not a.post and rows:
            r = rows[0]["data"]; print("sample", rows[0]["player_id"], r["n"], "shots,", sum(c != "0" for c in r["lvl"]), "lit cells,", len(r["d"]), "values")
        print(f"{season}: done in {time.time() - t0:.0f}s", flush=True)
