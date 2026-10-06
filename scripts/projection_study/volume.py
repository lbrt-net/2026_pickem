"""Volume in real numbers: FGA/G = FGA per 75 poss x poss per minute x minutes per game / 75.

Possessions (box-score estimate): game poss = mean over both teams of FGA + 0.44*FTA - OREB + TOV;
player poss = sum over his games of minutes * game_poss / (team minutes / 5).
Inputs '23–'25, target '26. Players = the 210 from the zone study.
Each component: recency weight r^t (t = 0,1,2 for '23,'24,'25), r tuned on 60% of players, scored on 40%, 20 splits.
poss/min also tried as "his '26 team's '25 pace" (team trait, roster known preseason).
"""
import contextlib
import io
import runpy
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem/scripts")
from load_historical_boxscores import minutes  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path("/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/zone_trend5.py",
                        run_name="lib")
pids, SIX = ns["pids"], ns["SIX"]

RAWB = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/box_scores_traditional/trad_box_scores_{}.parquet"
FILES = {"'23": RAWB.format("2022_23"), "'24": RAWB.format("2023_24"), "'25": RAWB.format("2024_25"),
         "'26": "/Users/allan/PycharmProjects/nba-pipeline/data/box_scores/trad_box_scores_2025_26.parquet"}


def season(f):
    d = pd.read_parquet(f)
    d = d[d.game_id.astype(str).str[2] == "2"].copy()
    d["player_id"] = d.player_id.astype(int)
    d["m"] = d["minutes"].map(minutes)
    tm = d.groupby(["game_id", "team_tricode"]).agg(fga=("fga", "sum"), fta=("fta", "sum"), oreb=("oreb", "sum"),
                                                    tov=("tov", "sum"), tmin=("m", "sum")).reset_index()
    tm["poss"] = tm.fga + 0.44 * tm.fta - tm.oreb + tm.tov
    gm = tm.groupby("game_id").agg(gposs=("poss", "mean"), glen=("tmin", "mean")).reset_index()  # glen = 5 * game minutes
    tm = tm.merge(gm, on="game_id")
    team_pace = tm.groupby("team_tricode").apply(lambda x: x.gposs.sum() / (x.glen / 5).sum(), include_groups=False)
    d = d[d.m > 0].merge(gm, on="game_id")
    d["poss"] = d.m * d.gposs / (d.glen / 5)
    p = d.groupby("player_id").agg(gp=("game_id", "nunique"), min=("m", "sum"), poss=("poss", "sum"), fga=("fga", "sum"),
                                   name=("player_name", "last"))
    main = d.groupby(["player_id", "team_tricode"]).m.sum().reset_index().sort_values("m").groupby("player_id").last().team_tricode
    return p, team_pace, main


S = {s: season(f) for s, f in FILES.items()}
IN = ["'23", "'24", "'25"]


def col(s, c):
    return np.array([S[s][0][c].get(p, 0) for p in pids], float)


gp, mn, poss, fga = (np.stack([col(s, c) for s in IN], 1) for c in ["gp", "min", "poss", "fga"])
a_gp, a_mn, a_poss, a_fga = (col("'26", c) for c in ["gp", "min", "poss", "fga"])
act = dict(fga75=75 * a_fga / a_poss, ppm=a_poss / a_mn, mpg=a_mn / a_gp)
act_fgag = a_fga / a_gp
team26 = [S["'26"][2].get(p) for p in pids]
pace25_of_26team = np.array([S["'25"][1].get(t, np.nan) for t in team26])


def proj(r):
    w = r ** np.arange(3.0)
    return dict(fga75=75 * (fga * w).sum(1) / (poss * w).sum(1),
                ppm=(poss * w).sum(1) / (mn * w).sum(1),
                mpg=(mn * w).sum(1) / (gp * w).sum(1))


R = [1, 2, 3, 5, 8, 1000]
PJ = {r: proj(r) for r in R}
mae = lambda p, a, rows: np.abs(p[rows] - a[rows]).mean()  # noqa: E731
rng = np.random.default_rng(26)
picks = {c: [] for c in act}
v = {c: [] for c in act}
v_last = {c: [] for c in act}
v_pace_team = []
v_fgag, v_fgag_old, v_fgag_parts = [], [], {c: [] for c in act}
for _ in range(20):
    perm = rng.permutation(len(pids))
    T, V = perm[: int(0.6 * len(pids))], perm[int(0.6 * len(pids)):]
    best = {c: min(R, key=lambda r: mae(PJ[r][c], act[c], T)) for c in act}
    for c in act:
        picks[c].append(best[c])
        v[c].append(mae(PJ[best[c]][c], act[c], V))
        v_last[c].append(mae(PJ[1000][c], act[c], V))
    v_pace_team.append(mae(pace25_of_26team, act["ppm"], V))
    p = {c: PJ[best[c]][c] for c in act}
    fg = p["fga75"] * p["ppm"] * p["mpg"] / 75
    v_fgag.append(mae(fg, act_fgag, V))
    for c in act:  # error left if this component were exactly right
        q = dict(p, **{c: act[c]})
        v_fgag_parts[c].append(mae(q["fga75"] * q["ppm"] * q["mpg"] / 75, act_fgag, V))
    old = (fga / gp * 5.0 ** np.arange(3) * gp).sum(1) / (5.0 ** np.arange(3) * gp).sum(1)
    v_fgag_old.append(mae(old, act_fgag, V))

UNIT = dict(fga75="FGA per 75", ppm="poss per minute", mpg="minutes per game")
print(f"{len(pids)} players, '23–'25 → '26, held-out 40%, mean of 20 splits\n")
print(f"  {'component':<18}{'typical value':>15}{'tuned r':>10}{'error':>9}{'same as 25':>12}")
for c in act:
    r = max(set(picks[c]), key=picks[c].count)
    print(f"  {UNIT[c]:<18}{np.median(act[c]):15.2f}{r:>10}{np.mean(v[c]):9.3f}{np.mean(v_last[c]):12.3f}")
print(f"  {'poss/min = his 26 team':<18}{'':>15}{'':>10}{np.mean(v_pace_team):9.3f}   ← '25 pace of his '26 team")
print(f"\nFGA per game: error {np.mean(v_fgag):.2f}  (old direct FGA/G placeholder {np.mean(v_fgag_old):.2f})")
for c in act:
    print(f"  if {UNIT[c]} were exactly right: {np.mean(v_fgag_parts[c]):.2f}")

pj = {c: PJ[max(set(picks[c]), key=picks[c].count)][c] for c in act}
print("\nThe six (proj → actual '26):")
for p_, n in SIX.items():
    if p_ in pids:
        i = pids.index(p_)
        print(f"  {n:<9} FGA/75 {pj['fga75'][i]:5.1f}→{act['fga75'][i]:5.1f}   poss/min {pj['ppm'][i]:.3f}→{act['ppm'][i]:.3f}"
              f"   MPG {pj['mpg'][i]:4.1f}→{act['mpg'][i]:4.1f}   FGA/G {pj['fga75'][i] * pj['ppm'][i] * pj['mpg'][i] / 75:4.1f}→{act_fgag[i]:4.1f}")
