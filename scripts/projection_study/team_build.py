"""2026-27 TEAM projections under the build's TEAM rules (common.TEAM; TEAM_SCORING.md has the study behind them).

1. Score every '23–'26 team-game with the app's scorer (scoring.points on a team line), week score per the rules'
   week mode (best game / sum) on the study weeks.
2. Per-game projection = league mean + carryover × (team's '26 mean − league mean); carryover = how much of a team's
   per-game level repeated '23→'24 and '24→'25.
3. Weekly curve: the team's '26 games shifted to the projected mean, best-of-n (or sum-of-n) for n = 1..10 games,
   simulated — expected / floor (25th pct) / ceiling (90th pct), same shape as the players' curves.
4. PROJ MAX / MAX low / MAX high: the curve on the 2026-27 schedule (each week's game count), averaged over the season.

Same numbers as team_draft4.py for the draft 6 rules (same draws). Writes
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
carry = float(np.mean([np.polyfit(m[a] - m[a].mean(), m[b] - m[b].mean(), 1)[0] for a, b in (("2022-23", "2023-24"), ("2023-24", "2024-25"))]))
lg = m["2025-26"].mean()

cur = psycopg2.connect("dbname=pickem_local").cursor(cursor_factory=psycopg2.extras.RealDictCursor)
weeks27 = season_weeks(cur, "2026-27")
TG = team_games(cur, "2026-27", weeks27)
rng = np.random.default_rng(27)
curves, pool = {}, []
for team in m.index:
    games = G[(G.season == "2025-26") & (G.TEAM_ABBREVIATION == team)].score.to_numpy()
    pm = lg + carry * (m.loc[team, "2025-26"] - lg)
    sh = games - games.mean() + pm
    sims = {n: agg(rng.choice(sh, size=(DRAWS, n)), axis=1) for n in range(1, NMAX + 1)}
    c = {"e": [round(float(sims[n].mean()), 2) for n in range(1, NMAX + 1)],
         "p25": [round(float(np.percentile(sims[n], 25)), 2) for n in range(1, NMAX + 1)],
         "p90": [round(float(np.percentile(sims[n], 90)), 2) for n in range(1, NMAX + 1)],
         "avg": round(float(pm), 2)}
    curves[team] = c
    ns = [min(TG[team].get(w["week"], 0), NMAX) for w in weeks27]
    on = lambda k: float(np.mean([c[k][n - 1] if n else 0.0 for n in ns]))  # noqa: E731
    pool.append({"team": team, "proj_avg": round(float(pm), 2), "proj_max": round(on("e"), 2),
                 "max_low": round(on("p25"), 2), "max_high": round(on("p90"), 2)})

json.dump(curves, open(R + "team_proj_week_2026_27.json", "w"))
json.dump(pool, open(W + "team_pool_2026_27.json", "w"))
top = sorted(pool, key=lambda r: -r["proj_max"])
print(f"TEAM: {len(G)} team-games scored, carryover {carry:.2f}; PROJ MAX top", [(r["team"], r["proj_max"]) for r in top[:4]],
      "bottom", [(r["team"], r["proj_max"]) for r in top[-2:]])
