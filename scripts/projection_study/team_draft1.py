"""TEAM scoring, draft 1, on 2025-26: per game +5 for each line the opponent finishes under (120/115/110/105/100/95/90),
+1 per turnover forced, (+2 per violation forced once pulled). Weekly score = best game of the fantasy week."""
import json, sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem")
from backend.fantasy_2026_27.weeks import build_weeks, week_for  # noqa: E402

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
LINES = [120, 115, 110, 105, 100, 95, 90]
D = pd.read_parquet(S + "team_games.parquet")


def violations_forced(season):
    """opponent's shot clock + 8 sec + 5 sec that day (team_violations/<season>.json), by (team, date)"""
    try:
        v = json.load(open(f"{R}team_violations/{season}.json"))
    except FileNotFoundError:
        return None
    ids = D.drop_duplicates("TEAM_ID").set_index("TEAM_ID").TEAM_ABBREVIATION
    rows = []
    for day, x in v.items():
        for r in x["rows"]:
            d = dict(zip(x["headers"], r))
            rows.append((ids.get(d["TEAM_ID"]), pd.to_datetime(day), d["SHOT_CLOCK"] + d["EIGHT_SEC"] + d["FIVE_SEC"]))
    return pd.DataFrame(rows, columns=["team", "date", "viol"])


def score(season):
    g = D[D.season == season].copy()
    g["lines"] = sum((g.OPP_PTS < L).astype(int) for L in LINES)
    g["pts_allowed"] = 5 * g.lines
    g["tov"] = g.OPP_TOV.astype(float)
    vf = violations_forced(season)
    if vf is not None and len(vf):
        # my violations forced = the opponent's violations on that date
        opp = g[["GAME_ID", "TEAM_ABBREVIATION"]].merge(g[["GAME_ID", "TEAM_ABBREVIATION", "GAME_DATE"]], on="GAME_ID", suffixes=("", "_opp"))
        opp = opp[opp.TEAM_ABBREVIATION != opp.TEAM_ABBREVIATION_opp].merge(vf, left_on=["TEAM_ABBREVIATION_opp", "GAME_DATE"], right_on=["team", "date"], how="left")
        g = g.merge(opp[["GAME_ID", "TEAM_ABBREVIATION", "viol"]], on=["GAME_ID", "TEAM_ABBREVIATION"], how="left")
        g["viol_pts"] = 2 * g.viol
    else:
        g["viol"], g["viol_pts"] = np.nan, 0.0
    g["score"] = g.pts_allowed + g.tov + g.viol_pts.fillna(0)
    weeks = build_weeks(set(g.GAME_DATE.dt.date), [])
    g["week"] = [(w["week"] if (w := week_for(weeks, x)) else None) for x in g.GAME_DATE.dt.date]
    return g, weeks


g, weeks = score("2025-26")
gw = g.dropna(subset=["week"])
wk = gw.groupby(["TEAM_ABBREVIATION", "week"]).score.max().rename("best").reset_index()
dr = (g.DEF_RATING * g.POSS).groupby(g.TEAM_ABBREVIATION).sum() / g.POSS.groupby(g.TEAM_ABBREVIATION).sum()
t = g.groupby("TEAM_ABBREVIATION").agg(game=("score", "mean"), opp_pts=("OPP_PTS", "mean"), tov=("tov", "mean"), viol=("viol", "mean"),
                                        **{f"u{L}": ("OPP_PTS", lambda s, L=L: float((s < L).mean())) for L in (100, 105, 110)})
t["week_best"] = wk.groupby("TEAM_ABBREVIATION").best.mean()
t["dr"] = dr
t = t.sort_values("week_best", ascending=False)
pd.set_option("display.width", 200)
print(t.round(2).to_string())
print("\nleague: game", round(g.score.mean(), 1), "week best", round(wk.best.mean(), 1), " corr(week best, -def rating)", round(np.corrcoef(t.week_best, -t.dr)[0, 1], 2))
json.dump(dict(teams=t.reset_index().to_dict("records"), league_game=float(g.score.mean()), league_week=float(wk.best.mean()),
               has_viol=bool(g.viol.notna().any())), open(S + "team_draft1.json", "w"), default=float)
