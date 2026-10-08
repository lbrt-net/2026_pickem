"""TEAM projections for 2026-27 under draft 3 (A and B), the TEAM version of PROJ AVG / PROJ MAX:
  per-game projection = league average + carry-over × (team's '26 average − league average), carry-over measured on
  '23→'24 and '24→'25 (game level)
  weekly best: simulate the best of n games by drawing the team's own '26 games, shifted to the projected average;
  n = the team's games in each 2026-27 fantasy week (real schedule, NBA Cup games filled — same as players)
  PROJ MAX (TEAM) = average over the season's weeks
Then value over replacement at 4 / 8 / 10 / 12 teams, next to the player slots (DRAFT_GUIDE.md)."""
import json, sys
import numpy as np
import pandas as pd
import psycopg2, psycopg2.extras
sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem")
from backend.fantasy_2026_27.weeks import season_weeks  # noqa: E402
from backend.fantasy_2026_27.projections import team_games  # noqa: E402

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
G = pd.read_parquet(S + "team_weeks.parquet")
rng = np.random.default_rng(27)
conn = psycopg2.connect("dbname=pickem_local")
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
weeks = season_weeks(cur, "2026-27")
TG = team_games(cur, "2026-27", weeks)
DG = json.load(open(S + "draft_guide.json"))
out = {}
for v in ("A", "B"):
    m = G.groupby(["season", "TEAM_ABBREVIATION"])[v].mean().unstack(0)
    c = float(np.mean([np.polyfit(m[a] - m[a].mean(), m[b] - m[b].mean(), 1)[0] for a, b in (("2022-23", "2023-24"), ("2023-24", "2024-25"))]))
    lg = m["2025-26"].mean()
    rows = []
    for t in m.index:
        games = G[(G.season == "2025-26") & (G.TEAM_ABBREVIATION == t)][v].to_numpy()
        proj = lg + c * (m.loc[t, "2025-26"] - lg)
        shifted = games - games.mean() + proj
        curve = {}
        for n in range(1, 11):
            curve[n] = float(rng.choice(shifted, size=(20000, n)).max(axis=1).mean())
        wk = [curve[min(TG[t].get(w["week"], 0), 10)] if TG[t].get(w["week"], 0) else 0.0 for w in weeks]
        rows.append(dict(team=t, proj_avg=float(proj), proj_max=float(np.mean(wk)), curve=curve, avg26=float(m.loc[t, "2025-26"])))
    R = pd.DataFrame(rows).sort_values("proj_max", ascending=False).reset_index(drop=True)
    vor = {}
    for N in (4, 8, 10, 12):
        vor[N] = dict(avg=float(R.proj_max.head(N).mean() - R.proj_max.iloc[N]), best=float(R.proj_max.iloc[0] - R.proj_max.iloc[N]), repl=float(R.proj_max.iloc[N]))
    out[v] = dict(carry=c, teams=R.drop(columns=["curve"]).to_dict("records"), curves={r.team: r.curve for r in R.itertuples()}, vor=vor)
    print(f"\n{v}: carry-over {c:.2f}; 2026-27 TEAM PROJ MAX top: " + ", ".join(f"{r.team} {r.proj_max:.1f}" for r in R.head(6).itertuples())
          + " … bottom: " + ", ".join(f"{r.team} {r.proj_max:.1f}" for r in R.tail(3).itertuples()))
    for N in (4, 8, 10, 12):
        pl = DG[f"gfc|{N}"]["by_slot"]
        print(f"   {N} teams: TEAM avg starter +{vor[N]['avg']:.1f}, best +{vor[N]['best']:.1f} (repl {vor[N]['repl']:.1f})   | players G/F/C avg starter +{pl['G']['avg_vor']:.1f} / +{pl['F']['avg_vor']:.1f} / +{pl['C']['avg_vor']:.1f}, best C +{pl['C']['best_vor']:.1f}")
json.dump(out, open(S + "team_proj.json", "w"))
