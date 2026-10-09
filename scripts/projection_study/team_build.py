"""2026-27 TEAM projections under the build's TEAM rules (common.TEAM; TEAM_SCORING.md has the study behind them).

1. Score every '23–'26 team-game with the app's scorer (scoring.points on a team line), week score per the rules'
   week mode (best game / sum) on the study weeks.
2. Per-game projection from the 2026-27 ROSTER (commissioner's choice, 2026-10-08: it tied the old carryover model in
   testing and makes more sense): roster defense = each player's 2025-26 defensive rating (vs league, 300+ minutes),
   weighted by his projected 2026-27 minutes (projected minutes a game × expected games, availability.py); players with
   no rating (rookies, too few minutes) get the average of players in that spot. Per-game score = league mean + slope ×
   roster defense; slope fit on '23→'24 and '24→'25 (actual minutes). ('26 is never fit on.)
3. Weekly curve: the league's 2025-26 game-to-game swing (every team's games around its own average, pooled) around
   the projected mean, best-of-n (or sum-of-n) for n = 1..10 games,
   simulated — expected / floor (25th pct) / ceiling (90th pct), same shape as the players' curves.
4. PROJ MAX / MAX low / MAX high: the curve on the 2026-27 schedule (each week's game count), averaged over the season.

Writes
  nba-pipeline data/raw/team_proj_week_2026_27.json  — team → {e, p25, p90, avg}
  WORK/team_pool_2026_27.json                        — rows for POST /fantasy/2026_27/admin/team-pool/load
"""
import json
import sys

import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import INPUTS, R, TEAM, W, scoring  # noqa: E402
from backend.fantasy_2026_27.weeks import build_weeks, season_weeks, week_for  # noqa: E402
from backend.fantasy_2026_27.projections import team_games  # noqa: E402

NMAX, DRAWS = 10, 20000
D = pd.read_parquet(INPUTS + "team_full.parquet")
VF = pd.read_parquet(INPUTS + "team_viol_forced.parquet")[["GAME_ID", "TEAM_ABBREVIATION", "SHOT_CLOCK"]]
D = D.merge(VF, on=["GAME_ID", "TEAM_ABBREVIATION"], how="left")


def team_line(r) -> dict:
    """A '23–'26 team-game → the app's team stat line (scoring.team_line + the defensive stats)."""
    x = {"shot_clock_forced": r.SHOT_CLOCK, "fb_pts_allowed": r.OPP_PTS_FB, "paint_pts_allowed": r.OPP_PTS_PAINT,
         "tov_forced": r.OPP_TOV, "dreb_margin": r.DREB - r.OPP_DREB}
    return scoring.team_line(r.PTS, r.OPP_PTS, {k: v for k, v in x.items() if pd.notna(v)})  # not recorded → 0, as in the app


out = []
for s, g in D.groupby("season"):
    weeks = build_weeks(set(g.GAME_DATE.dt.date), [])
    out.append(g.assign(week=[(w["week"] if (w := week_for(weeks, x)) else None) for x in g.GAME_DATE.dt.date]).dropna(subset=["week"]))
G = pd.concat(out)
G["score"] = [scoring.points(TEAM, team_line(r)) for r in G.itertuples()]
agg = np.max if TEAM["week"] == "best_game" else np.sum

m = G.groupby(["season", "TEAM_ABBREVIATION"]).score.mean().unstack(0)
lg = m["2025-26"].mean()


# ---- roster defense ----
def J(kind, s):
    rs = json.load(open(f"{R}{kind}/{s}.json"))["resultSets"]
    rs = rs[0] if isinstance(rs, list) else rs
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"])


RSEAS = ["2022-23", "2023-24", "2024-25", "2025-26"]
ADV = pd.concat(J("player_advanced", s).assign(season=s) for s in RSEAS)
ADV["amin"] = ADV.MIN * ADV.GP                      # MIN there is per game
RATED = {s: ADV[(ADV.season == s) & (ADV.amin >= 300)].set_index("PLAYER_ID") for s in RSEAS}
LGD = {s: float(np.average(r.DEF_RATING, weights=r.amin)) for s, r in RATED.items()}
LOGS = pd.concat(J("game_logs", s).assign(season=s) for s in RSEAS[1:3])
MINS = LOGS.groupby(["season", "TEAM_ABBREVIATION", "PLAYER_ID"]).MIN.sum().reset_index()
# players with no prior-season rating: what they actually defended at (vs league), minutes-weighted, '24 and '25
cur_rel = {(s, p): float(r.DEF_RATING) - LGD[s] for s in RSEAS for p, r in RATED[s].iterrows()}
unr = MINS[[p not in RATED[RSEAS[RSEAS.index(s) - 1]].index for s, p in zip(MINS.season, MINS.PLAYER_ID)]]
unr = unr.assign(d=[cur_rel.get((s, p), np.nan) for s, p in zip(unr.season, unr.PLAYER_ID)]).dropna(subset=["d"])
NO_RATING = float(np.average(unr.d, weights=unr.MIN))


def roster_def(prev_season, pids, w):
    r = RATED[prev_season]
    d = [float(r.DEF_RATING[p]) - LGD[prev_season] if p in r.index else NO_RATING for p in pids]
    return float(np.average(d, weights=w))


fit = []
for s in RSEAS[1:3]:
    prev = RSEAS[RSEAS.index(s) - 1]
    for t, g in MINS[MINS.season == s].groupby("TEAM_ABBREVIATION"):
        fit.append((roster_def(prev, g.PLAYER_ID, g.MIN.to_numpy()), m.loc[t, s] - m[s].mean()))
SLOPE = float(np.polyfit([a for a, _ in fit], [b for _, b in fit], 1)[0])

r27 = pd.read_csv(R + "rosters/2026-27.csv")
p27 = pd.read_csv(R + "projections_2026_27.csv").set_index("pid")
av = json.load(open(R + "availability_2026_27.json"))["players"]
RD = {}
for t, g in r27.groupby("TEAM"):
    w = np.array([float(p27.mpg.get(p, 0) or 0) * av.get(str(p), {}).get("games", 60) for p in g.PLAYER_ID])
    w = np.nan_to_num(w)
    if w.sum() > 0:
        RD[t] = roster_def("2025-26", g.PLAYER_ID, w)

cur = psycopg2.connect("dbname=pickem_local").cursor(cursor_factory=psycopg2.extras.RealDictCursor)
weeks27 = season_weeks(cur, "2026-27")
TG = team_games(cur, "2026-27", weeks27)
rng = np.random.default_rng(27)
# every team's 2025-26 games around its own average, pooled: the league's game-to-game swing (a roster that changed
# shouldn't carry last season's swing)
g26 = G[G.season == "2025-26"]
SWING = (g26.score - g26.groupby("TEAM_ABBREVIATION").score.transform("mean")).to_numpy()
curves, pool = {}, []
for team in m.index:
    pm = lg + SLOPE * RD[team]
    sh = SWING + pm                                   # league-average game-to-game swing around the roster's level
    sims = {n: agg(rng.choice(sh, size=(DRAWS, n)), axis=1) for n in range(1, NMAX + 1)}
    c = {"e": [round(float(sims[n].mean()), 2) for n in range(1, NMAX + 1)],
         "p25": [round(float(np.percentile(sims[n], 25)), 2) for n in range(1, NMAX + 1)],
         "p90": [round(float(np.percentile(sims[n], 90)), 2) for n in range(1, NMAX + 1)],
         "avg": round(float(pm), 2)}
    curves[team] = c
    ns = [min(TG[team].get(w["week"], 0), NMAX) for w in weeks27]
    on = lambda k: float(np.mean([c[k][n - 1] if n else 0.0 for n in ns]))  # noqa: E731
    pool.append({"team": team, "proj_avg": round(float(pm), 2), "proj_max": round(on("e"), 2), "roster_def": round(RD[team], 2),
                 "max_low": round(on("p25"), 2), "max_high": round(on("p90"), 2)})

json.dump(curves, open(R + "team_proj_week_2026_27.json", "w"))
json.dump(pool, open(W + "team_pool_2026_27.json", "w"))
top = sorted(pool, key=lambda r: -r["proj_max"])
print(f"TEAM: {len(G)} team-games scored; roster defense slope {SLOPE:.2f} pts/game per point of rating, unrated players {NO_RATING:+.1f}; PROJ MAX top", [(r["team"], r["proj_max"]) for r in top[:4]],
      "bottom", [(r["team"], r["proj_max"]) for r in top[-2:]])
