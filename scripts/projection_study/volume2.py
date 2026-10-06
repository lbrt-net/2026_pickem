"""Possessions per game from NBA.com advanced stats.

poss/G = MPG x pace / 48
  pace: his '26 team's '25 team PACE (team = his first '26 game's team — the opening roster, known preseason).
        Compared with: his own recency-weighted on-court PACE.
  MPG:  recency-weighted '23–'25 MPG (weights GP * r^t), then pulled toward the group mean:
        proj = mean + beta * (weighted - mean). r and beta tuned on 60% of players, scored on 40%, 20 splits.
NBA advanced 'MIN' is per game; season minutes = MIN * GP. POSS is a season total.
Players: the 210 from the zone study.
"""
import contextlib
import io
import json
import runpy
from collections import Counter

import numpy as np
import pandas as pd

with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path("/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/zone_trend5.py",
                        run_name="lib")
pids, SIX = ns["pids"], ns["SIX"]
R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"


def tab(kind, s):
    rs = json.load(open(f"{R}{kind}/{s}.json"))["resultSets"][0]
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"])


IN = ["2022-23", "2023-24", "2024-25"]
P = {s: tab("player_advanced", s).set_index("PLAYER_ID") for s in IN + ["2025-26"]}
T25 = tab("team_advanced", "2024-25")
abbr = pd.read_csv(f"{R}rosters/2025-26.csv").drop_duplicates("TeamID").set_index("TeamID").TEAM.to_dict()
pace25 = {abbr[r.TEAM_ID]: r.PACE for r in T25.itertuples()}
opening = pd.read_csv(f"{R}rosters/opening_2025_26_from_box.csv").set_index("player_id").team26


def g(s, c):
    return np.array([P[s][c].get(p, 0.0) for p in pids], float)


gp = np.stack([g(s, "GP") for s in IN], 1)
mpg = np.stack([g(s, "MIN") for s in IN], 1)
pace_own = np.stack([g(s, "PACE") for s in IN], 1)
a_gp, a_mpg, a_poss, a_pace = g("2025-26", "GP"), g("2025-26", "MIN"), g("2025-26", "POSS"), g("2025-26", "PACE")
a_pg = a_poss / a_gp
team26 = [opening.get(p) for p in pids]
pace_team = np.array([pace25.get(t, np.nan) for t in team26])
names = [P["2025-26"].PLAYER_NAME.get(p, str(p)) for p in pids]


def wmpg(r):
    w = gp * r ** np.arange(3.0)
    return (mpg * w).sum(1) / w.sum(1)


def own_pace(r):
    w = gp * mpg * r ** np.arange(3.0)
    return (pace_own * w).sum(1) / w.sum(1)


mae = lambda p, a, rows: np.abs(p[rows] - a[rows]).mean()  # noqa: E731
RS, BS = [1, 2, 3, 5, 8, 1000], [1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.6]
rng = np.random.default_rng(26)
out = {k: [] for k in ["mpg_raw", "mpg_pulled", "pace_team", "pace_own", "poss_last", "poss"]}
picks = Counter()
for _ in range(20):
    perm = rng.permutation(len(pids))
    T, V = perm[: int(0.6 * len(pids))], perm[int(0.6 * len(pids)):]
    r0 = min(RS, key=lambda r: mae(wmpg(r), a_mpg, T))
    best = min(((r, b) for r in RS for b in BS),
               key=lambda x: mae(wmpg(x[0]).mean() + x[1] * (wmpg(x[0]) - wmpg(x[0])[T].mean()), a_mpg, T))
    picks[best] += 1
    m = wmpg(best[0])
    m_pull = m[T].mean() + best[1] * (m - m[T].mean())
    rp = min(RS, key=lambda r: mae(own_pace(r), a_pace, T))
    out["mpg_raw"].append(mae(wmpg(r0), a_mpg, V))
    out["mpg_pulled"].append(mae(m_pull, a_mpg, V))
    out["pace_team"].append(mae(pace_team, a_pace, V))
    out["pace_own"].append(mae(own_pace(rp), a_pace, V))
    out["poss_last"].append(mae(mpg[:, -1] * pace_own[:, -1] / 48, a_pg, V))
    out["poss"].append(mae(m_pull * pace_team / 48, a_pg, V))

(r, b), _ = picks.most_common(1)[0]
m = wmpg(r)
m_pull = m.mean() + b * (m - m.mean())
proj_pg = m_pull * pace_team / 48
print(f"{len(pids)} players, '23–'25 → '26, held-out 40%, mean of 20 splits.  Tuned MPG: recency r={r}, keep {b:.0%} of distance from mean "
      f"(mean ≈ {m.mean():.1f}).  Picks: {picks.most_common(3)}\n")
print(f"  minutes/G   typical {np.median(a_mpg):5.1f}   error: recency only {np.mean(out['mpg_raw']):.2f}  → with pull {np.mean(out['mpg_pulled']):.2f}")
print(f"  pace        typical {np.median(a_pace):5.1f}   error: his '26 team's '25 pace {np.mean(out['pace_team']):.2f}  vs his own history {np.mean(out['pace_own']):.2f}")
print(f"  poss/G      typical {np.median(a_pg):5.1f}   error: model {np.mean(out['poss']):.2f}   vs same as '25 {np.mean(out['poss_last']):.2f}")
e = proj_pg - a_pg
print(f"  poss/G bias {e.mean():+.2f};  within ±4: {np.mean(np.abs(e) <= 4):.0%},  within ±8: {np.mean(np.abs(e) <= 8):.0%}")

print("\nThe six — '26 projected → actual:")
for p, n in SIX.items():
    if p in pids:
        i = pids.index(p)
        print(f"  {n:<9} team {team26[i]}  MPG {m_pull[i]:4.1f}→{a_mpg[i]:4.1f}   pace {pace_team[i]:5.1f}→{a_pace[i]:5.1f}   poss/G {proj_pg[i]:4.1f}→{a_pg[i]:4.1f}")
o = np.argsort(-np.abs(e))[:8]
print("\nBiggest poss/G misses:")
for i in o:
    print(f"  {names[i]:<24} {team26[i]}  MPG {m_pull[i]:4.1f}→{a_mpg[i]:4.1f}   poss/G {proj_pg[i]:4.1f}→{a_pg[i]:4.1f}")
