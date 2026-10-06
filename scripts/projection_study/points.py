"""Points per game = FG points (zone model) + FTM.
  FTA/75: '23–'25, possession-weighted with recency r (tuned on 60%), NBA POSS as the denominator.
  FT%:    '23–'25 attempt-weighted, k=25 toward league FT%, no pull at 200+ FTA.
  poss/G: MPG ('25, keep 70% of distance from 26.9) x own pace / 48.
Scored on '26 for the 210 zone-study players (held-out 40%, 20 splits for FTA/75; points scored on all 210).
"""
import contextlib
import io
import json
import runpy
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem/scripts")
from load_historical_boxscores import minutes  # noqa: E402

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
with contextlib.redirect_stdout(io.StringIO()):
    z = runpy.run_path(S + "zone_trend5.py", run_name="lib")
    v2 = runpy.run_path(S + "volume2.py", run_name="lib")
pids, SIX, ZONES, VAL = z["pids"], z["SIX"], z["ZONES"], z["VAL"]
vals = np.array([VAL[k] for k in ZONES], float)

# zone points per FGA (settled model)
share = z["proj_share"](5, 0)
a3, m3 = z["fga5"][:, -3:].sum(1), z["fgm5"][:, -3:].sum(1)
mu = m3.sum(0) / a3.sum(0)
k = np.where(a3 >= 200, 0.0, 25.0)
pps = (share * (m3 + k * mu) / (a3 + k) * vals).sum(1)

R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
BOX = {"2022-23": R + "box_scores_traditional/trad_box_scores_2022_23.parquet",
       "2023-24": R + "box_scores_traditional/trad_box_scores_2023_24.parquet",
       "2024-25": R + "box_scores_traditional/trad_box_scores_2024_25.parquet",
       "2025-26": "/Users/allan/PycharmProjects/nba-pipeline/data/box_scores/trad_box_scores_2025_26.parquet"}


def tot(s):
    d = pd.read_parquet(BOX[s])
    d = d[d.game_id.astype(str).str[2] == "2"].copy()
    d["player_id"] = d.player_id.astype(int)
    d["m"] = d["minutes"].map(minutes)
    d = d[d.m > 0]
    return d.groupby("player_id")[["fga", "fgm", "fg3m", "fta", "ftm", "pts"]].sum().join(d.groupby("player_id").game_id.nunique().rename("gp"))


def adv(s):
    rs = json.load(open(f"{R}player_advanced/{s}.json"))["resultSets"][0]
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"]).set_index("PLAYER_ID")


IN = ["2022-23", "2023-24", "2024-25"]
B = {s: tot(s) for s in IN + ["2025-26"]}
A = {s: adv(s) for s in IN + ["2025-26"]}
col = lambda s, c, src: np.array([src[s][c].get(p, 0.0) for p in pids], float)  # noqa: E731
fta = np.stack([col(s, "fta", B) for s in IN], 1)
ftm = np.stack([col(s, "ftm", B) for s in IN], 1)
poss = np.stack([col(s, "POSS", A) for s in IN], 1)
a_fta, a_ftm, a_pts, a_gp, a_poss = (col("2025-26", c, B) for c in ["fta", "ftm", "pts", "gp"]) + (col("2025-26", "POSS", A),) \
    if False else (col("2025-26", "fta", B), col("2025-26", "ftm", B), col("2025-26", "pts", B), col("2025-26", "gp", B), col("2025-26", "POSS", A))
act_fta75 = 75 * a_fta / a_poss


def fta75(r):
    w = r ** np.arange(3.0)
    return 75 * (fta * w).sum(1) / (poss * w).sum(1)


mae = lambda p, a, rows: np.abs(p[rows] - a[rows]).mean()  # noqa: E731
RS = [1, 2, 3, 5, 8, 1000]
rng = np.random.default_rng(26)
picks, err, err_last = [], [], []
for _ in range(20):
    perm = rng.permutation(len(pids))
    T, V = perm[: int(0.6 * len(pids))], perm[int(0.6 * len(pids)):]
    r = min(RS, key=lambda x: mae(fta75(x), act_fta75, T))
    picks.append(r)
    err.append(mae(fta75(r), act_fta75, V))
    err_last.append(mae(fta75(1000), act_fta75, V))
r_ft = max(set(picks), key=picks.count)
ft75 = fta75(r_ft)

fta3, ftm3 = fta.sum(1), ftm.sum(1)
mu_ft = ftm3.sum() / fta3.sum()
kf = np.where(fta3 >= 200, 0.0, 25.0)
ftp = (ftm3 + kf * mu_ft) / np.where(fta3 + kf > 0, fta3 + kf, 1)
has = a_fta > 0
ft_err = (np.abs(ftp[has] - a_ftm[has] / a_fta[has]) * a_fta[has]).sum() / a_fta[has].sum()

# poss/G from the settled volume model
m = v2["wmpg"](1000)
mpg = m.mean() + 0.70 * (m - m.mean())
own_pace = v2["own_pace"](3)
poss_g = mpg * own_pace / 48
fga75 = v2["proj"](2)["fga75"] if "proj" in v2 else None
# FGA/75 from NBA POSS (recency r=2)
fga = np.stack([col(s, "fga", B) for s in IN], 1)
w = 2.0 ** np.arange(3)
fga75 = 75 * (fga * w).sum(1) / (poss * w).sum(1)

proj_fgpts = poss_g / 75 * fga75 * pps
proj_ftm = poss_g / 75 * ft75 * ftp
proj_pts = proj_fgpts + proj_ftm
act_ppg = a_pts / a_gp
names = [A["2025-26"].PLAYER_NAME.get(p, str(p)) for p in pids]

print(f"{len(pids)} players, '23–'25 → '26\n")
print(f"  FTA per 75:  typical {np.median(act_fta75):.2f}   tuned recency r={r_ft}   error {np.mean(err):.2f} (held-out)   same as '25 {np.mean(err_last):.2f}")
print(f"  FT%:         attempt-weighted error {100 * ft_err:.2f} pp  (league {100 * mu_ft:.1f}%)")
e = proj_pts - act_ppg
last = (B["2024-25"].pts.reindex(pids).to_numpy() / B["2024-25"].gp.reindex(pids).to_numpy())
print(f"\n  POINTS PER GAME: typical {np.median(act_ppg):.1f}   error {np.abs(e).mean():.2f}  (median {np.median(np.abs(e)):.2f})   "
      f"bias {e.mean():+.2f}   | same as '25: {np.abs(last - act_ppg).mean():.2f}")
print(f"  within ±2: {np.mean(np.abs(e) <= 2):.0%}   within ±4: {np.mean(np.abs(e) <= 4):.0%}")
print(f"  FT share of points: projected {np.median(proj_ftm / proj_pts):.0%}")

print("\nThe six (PTS/G projected → actual; FTA/75, FT%):")
for p, n in SIX.items():
    if p in pids:
        i = pids.index(p)
        print(f"  {n:<9} {proj_pts[i]:5.1f} → {act_ppg[i]:5.1f}    FTA/75 {ft75[i]:4.1f}→{act_fta75[i]:4.1f}   FT% {100 * ftp[i]:4.1f}→{100 * a_ftm[i] / max(a_fta[i], 1):4.1f}")
print("\nTop 12 projected:")
for i in np.argsort(-proj_pts)[:12]:
    print(f"  {names[i]:<26} {proj_pts[i]:5.1f} → {act_ppg[i]:5.1f}")
