"""TEAM draft 2 groundwork: for each candidate cutoff, on '22–'25 team-games (and '26):
how often a game hits it, best vs worst defense's rate, chance a team hits it at least once in a 3-game week,
whether teams' hit rates follow defense (−defensive rating) and repeat next season."""
import json
import numpy as np
import pandas as pd

R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
D = pd.read_parquet(S + "team_games.parquet")
opp = []
for s in ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]:
    rs = json.load(open(f"{R}team_logs_opponent/{s}.json"))["resultSets"][0]
    o = pd.DataFrame(rs["rowSet"], columns=rs["headers"])[["TEAM_ID", "GAME_ID", "OPP_OREB", "OPP_DREB"]]
    opp.append(o)
D = D.merge(pd.concat(opp), on=["TEAM_ID", "GAME_ID"], how="left")
D["DREB_MARGIN"] = D.DREB - D.OPP_OREB  # defensive rebounds minus the opponent's offensive rebounds
CUT = [("Opponent under 100", lambda d: d.OPP_PTS < 100), ("Opponent under 95", lambda d: d.OPP_PTS < 95), ("Opponent under 90", lambda d: d.OPP_PTS < 90),
       ("Opponent under 85", lambda d: d.OPP_PTS < 85),
       ("18+ turnovers forced", lambda d: d.OPP_TOV >= 18), ("20+ turnovers forced", lambda d: d.OPP_TOV >= 20), ("22+ turnovers forced", lambda d: d.OPP_TOV >= 22),
       ("Opp fast-break pts 8 or fewer", lambda d: d.OPP_PTS_FB <= 8), ("Opp fast-break pts 6 or fewer", lambda d: d.OPP_PTS_FB <= 6),
       ("Opp fast-break pts 4 or fewer", lambda d: d.OPP_PTS_FB <= 4),
       ("Opp paint pts 36 or fewer", lambda d: d.OPP_PTS_PAINT <= 36), ("Opp paint pts 32 or fewer", lambda d: d.OPP_PTS_PAINT <= 32),
       ("Opp paint pts 28 or fewer", lambda d: d.OPP_PTS_PAINT <= 28),
       ("Opp offensive rebounds 6 or fewer", lambda d: d.OPP_OREB <= 6), ("Opp offensive rebounds 4 or fewer", lambda d: d.OPP_OREB <= 4),
       ("Def. rebound margin 30+", lambda d: d.DREB_MARGIN >= 30), ("Def. rebound margin 35+", lambda d: d.DREB_MARGIN >= 35)]
ss = D.groupby(["season", "TEAM_ABBREVIATION"]).apply(lambda g: (g.DEF_RATING * g.POSS).sum() / g.POSS.sum(), include_groups=False).rename("dr")
rows = []
for lab, fn in CUT:
    D["hit"] = fn(D).astype(float)
    t = D.groupby(["season", "TEAM_ABBREVIATION"]).hit.mean().rename("rate").to_frame().join(ss)
    dev = t[t.index.get_level_values(0) < "2025-26"]
    corr = float(np.corrcoef(dev.rate, -dev.dr)[0, 1])
    w = t.rate.unstack(0)
    yoy = float(np.nanmean([w[[a, b]].dropna().corr().iloc[0, 1] for a, b in zip(w.columns[:-2], w.columns[1:-1])]))
    s26 = t.loc["2025-26"].sort_values("dr")
    best5, worst5 = s26.head(5).rate.mean(), s26.tail(5).rate.mean()
    league = float(D[D.season < "2025-26"].hit.mean())
    rows.append(dict(cut=lab, league=league, week=1 - (1 - league) ** 3, best5=float(best5), worst5=float(worst5),
                     best5_week=1 - (1 - best5) ** 3, corr=corr, yoy=yoy, top=s26.rate.idxmax(), top_rate=float(s26.rate.max())))
T = pd.DataFrame(rows)
pd.set_option("display.width", 220)
print(T.round(2).to_string(index=False))
T.to_csv(S + "team_cutoffs.csv", index=False)
D.to_parquet(S + "team_games2.parquet")
