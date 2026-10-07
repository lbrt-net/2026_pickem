"""TEAM scoring draft 2 on 2025-26 (vs draft 1). Per game:
  hold under 100 +15, under 95 +10 more, under 90 +10 more
  +5 per violation forced (opponent's shot clock + 8 sec + 5 sec that day)
  +10 each: 20+ turnovers forced; opp fast-break pts 6 or fewer; opp paint pts 32 or fewer; DREB − opp OREB 30+
Weekly score = best game of the fantasy week."""
import json, sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem")
from backend.fantasy_2026_27.weeks import build_weeks, week_for  # noqa: E402

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
D = pd.read_parquet(S + "team_games2.parquet")
g = D[D.season == "2025-26"].copy()
v = json.load(open(f"{R}team_violations/2025-26.json"))
ids = D.drop_duplicates("TEAM_ID").set_index("TEAM_ID").TEAM_ABBREVIATION
vf = pd.DataFrame([(ids.get(dict(zip(x["headers"], r))["TEAM_ID"]), pd.to_datetime(day),
                    sum(dict(zip(x["headers"], r))[k] for k in ("SHOT_CLOCK", "EIGHT_SEC", "FIVE_SEC"))) for day, x in v.items() for r in x["rows"]],
                  columns=["team", "date", "viol"])
pair = g[["GAME_ID", "TEAM_ABBREVIATION"]].merge(g[["GAME_ID", "TEAM_ABBREVIATION", "GAME_DATE"]], on="GAME_ID", suffixes=("", "_opp"))
pair = pair[pair.TEAM_ABBREVIATION != pair.TEAM_ABBREVIATION_opp].merge(vf, left_on=["TEAM_ABBREVIATION_opp", "GAME_DATE"], right_on=["team", "date"], how="left")
g = g.merge(pair[["GAME_ID", "TEAM_ABBREVIATION", "viol"]], on=["GAME_ID", "TEAM_ABBREVIATION"], how="left")
g["viol"] = g.viol.fillna(0)
B = {"20+ turnovers forced": g.OPP_TOV >= 20, "Fast-break pts held to 6 or fewer": g.OPP_PTS_FB <= 6,
     "Paint pts held to 32 or fewer": g.OPP_PTS_PAINT <= 32, "Rebounding: DREB − opp OREB 30+": g.DREB_MARGIN >= 30}
g["held"] = 15 * (g.OPP_PTS < 100) + 10 * (g.OPP_PTS < 95) + 10 * (g.OPP_PTS < 90)
g["viol_pts"] = 5 * g.viol
g["bonus"] = sum(10 * b.astype(int) for b in B.values())
for k, b in B.items():
    g[k] = b.astype(int)
g["score2"] = g.held + g.viol_pts + g.bonus
g["score1"] = 5 * sum((g.OPP_PTS < L).astype(int) for L in (120, 115, 110, 105, 100, 95, 90)) + g.OPP_TOV + 2 * g.viol
weeks = build_weeks(set(g.GAME_DATE.dt.date), [])
g["week"] = [(w["week"] if (w := week_for(weeks, x)) else None) for x in g.GAME_DATE.dt.date]
g = g.dropna(subset=["week"])
wk = g.groupby(["TEAM_ABBREVIATION", "week"]).agg(best2=("score2", "max"), best1=("score1", "max"), n=("score2", "size")).reset_index()
dr = (g.DEF_RATING * g.POSS).groupby(g.TEAM_ABBREVIATION).sum() / g.POSS.groupby(g.TEAM_ABBREVIATION).sum()
t = wk.groupby("TEAM_ABBREVIATION").agg(week2=("best2", "mean"), sd2=("best2", "std"), zero2=("best2", lambda s: float((s == 0).mean())),
                                         big2=("best2", lambda s: float((s >= 30).mean())), top2=("best2", "max"), week1=("best1", "mean"), sd1=("best1", "std"))
t["dr"] = dr
t["u100"] = g.groupby("TEAM_ABBREVIATION").OPP_PTS.apply(lambda s: float((s < 100).mean()))
t["viol"] = g.groupby("TEAM_ABBREVIATION").viol.mean()
for k in B:
    t[k] = g.groupby("TEAM_ABBREVIATION")[k].mean()
t = t.sort_values("week2", ascending=False)
pd.set_option("display.width", 240)
print(t.round(2).to_string())
print(f"\nleague weekly: draft 2 {wk.best2.mean():.1f} ± {wk.best2.std():.1f} (zero weeks {100 * (wk.best2 == 0).mean():.0f}%, 30+ weeks {100 * (wk.best2 >= 30).mean():.0f}%) | "
      f"draft 1 {wk.best1.mean():.1f} ± {wk.best1.std():.1f}")
print(f"corr with defense: draft 2 {np.corrcoef(t.week2, -t.dr)[0, 1]:.2f}, draft 1 {np.corrcoef(t.week1, -t.dr)[0, 1]:.2f}")
print(f"violations forced per game: league {g.viol.mean():.2f}, top {t.viol.idxmax()} {t.viol.max():.2f}")
# a big week: example
ex = g.sort_values("score2", ascending=False).head(5)[["GAME_DATE", "MATCHUP", "OPP_PTS", "viol", "OPP_TOV", "OPP_PTS_FB", "OPP_PTS_PAINT", "DREB_MARGIN", "score2"]]
print(ex.to_string(index=False))
json.dump(dict(teams=t.reset_index().to_dict("records"), league_week2=float(wk.best2.mean()), league_sd2=float(wk.best2.std()),
               zero=float((wk.best2 == 0).mean()), big=float((wk.best2 >= 30).mean()), league_week1=float(wk.best1.mean()), league_sd1=float(wk.best1.std()),
               corr2=float(np.corrcoef(t.week2, -t.dr)[0, 1]), corr1=float(np.corrcoef(t.week1, -t.dr)[0, 1]), viol_league=float(g.viol.mean()),
               examples=ex.assign(GAME_DATE=ex.GAME_DATE.dt.strftime("%b %d")).to_dict("records"), bonuses=list(B)),
          open(S + "team_draft2.json", "w"), default=float)
