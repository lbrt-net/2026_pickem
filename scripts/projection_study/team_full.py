"""One row per team-game '23–'26: box score, opponent, misc, four factors, hustle (by date), violations forced (opponent's
own violations that day). Then each candidate's job fit:
  bread and butter — pays most games, follows defense, repeats next season
  swingy cutoffs   — how often, best vs worst defenses
→ team_full.parquet, team_candidates.csv"""
import json
import numpy as np
import pandas as pd

R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
SEAS = ["2022-23", "2023-24", "2024-25", "2025-26"]
D = pd.read_parquet(S + "team_games2.parquet")
D = D[D.season.isin(SEAS)].copy()
ids = D.drop_duplicates("TEAM_ID").set_index("TEAM_ID").TEAM_ABBREVIATION


def by_date(kind, season):
    v = json.load(open(f"{R}{kind}/{season}.json"))
    rows = []
    for day, x in v.items():
        for r in x["rows"]:
            d = dict(zip(x["headers"], r))
            d["TEAM_ABBREVIATION"], d["GAME_DATE"] = ids.get(d["TEAM_ID"]), pd.to_datetime(day)
            rows.append(d)
    return pd.DataFrame(rows)


H, V = [], []
for s in SEAS:
    h = by_date("team_hustle", s)
    H.append(h[["TEAM_ABBREVIATION", "GAME_DATE", "DEFLECTIONS", "CHARGES_DRAWN", "CONTESTED_SHOTS", "DEF_LOOSE_BALLS_RECOVERED", "DEF_BOXOUTS"]])
    v = by_date("team_violations", s)
    v["VIOL_OWN"] = v.SHOT_CLOCK + v.EIGHT_SEC + v.FIVE_SEC
    v["SC_OWN"] = v.SHOT_CLOCK
    V.append(v[["TEAM_ABBREVIATION", "GAME_DATE", "VIOL_OWN", "SC_OWN", "OFF_FOUL", "TRAVEL"]])
H, V = pd.concat(H), pd.concat(V)
D = D.merge(H, on=["TEAM_ABBREVIATION", "GAME_DATE"], how="left")
pair = D[["GAME_ID", "TEAM_ABBREVIATION"]].merge(D[["GAME_ID", "TEAM_ABBREVIATION", "GAME_DATE"]], on="GAME_ID", suffixes=("", "_opp"))
pair = pair[pair.TEAM_ABBREVIATION != pair.TEAM_ABBREVIATION_opp].merge(V, left_on=["TEAM_ABBREVIATION_opp", "GAME_DATE"], right_on=["TEAM_ABBREVIATION", "GAME_DATE"],
                                                                        how="left", suffixes=("", "_v"))
pair = pair.rename(columns={"VIOL_OWN": "VIOL_FORCED", "SC_OWN": "SC_FORCED", "OFF_FOUL": "OFF_FOUL_FORCED", "TRAVEL": "TRAVEL_FORCED"})
D = D.merge(pair[["GAME_ID", "TEAM_ABBREVIATION", "VIOL_FORCED", "SC_FORCED", "OFF_FOUL_FORCED", "TRAVEL_FORCED"]], on=["GAME_ID", "TEAM_ABBREVIATION"], how="left")
D.to_parquet(S + "team_full.parquet")
print(D.shape, "missing hustle", D.DEFLECTIONS.isna().mean().round(3), "missing viol", D.VIOL_FORCED.isna().mean().round(3))

dr = D.groupby(["season", "TEAM_ABBREVIATION"]).apply(lambda g: (g.DEF_RATING * g.POSS).sum() / g.POSS.sum(), include_groups=False).rename("dr")
COUNTS = {  # steady, per-game counts (bread-and-butter candidates); sign +1 = more is better defense
    "Turnovers forced": ("OPP_TOV", 1), "Deflections": ("DEFLECTIONS", 1), "Contested shots": ("CONTESTED_SHOTS", 1),
    "Charges drawn": ("CHARGES_DRAWN", 1), "Loose balls recovered (def)": ("DEF_LOOSE_BALLS_RECOVERED", 1), "Box outs (def)": ("DEF_BOXOUTS", 1),
    "Violations forced": ("VIOL_FORCED", 1), "Offensive fouls forced": ("OFF_FOUL_FORCED", 1), "Steals": ("STL", 1), "Blocks": ("BLK", 1),
    "Points allowed": ("OPP_PTS", -1)}
rows = []
for lab, (c, sgn) in COUNTS.items():
    t = D.groupby(["season", "TEAM_ABBREVIATION"])[c].mean().rename("m").to_frame().join(dr)
    corr = float(np.mean([np.corrcoef(sgn * q.m, -q.dr)[0, 1] for _, q in t.groupby(level=0)]))
    w = t.m.unstack(0)
    yoy = float(np.nanmean([w[[a, b]].dropna().corr().iloc[0, 1] for a, b in zip(w.columns[:-1], w.columns[1:])]))
    zero = float((D[c] == 0).mean()) if sgn > 0 else np.nan
    s26 = t.loc["2025-26"]
    rows.append(dict(cand=lab, per_game=float(D[c].mean()), game_sd=float(D[c].std()), zero_games=zero, team_lo=float(s26.m.min()), team_hi=float(s26.m.max()),
                     best_team=s26.m.idxmax() if sgn > 0 else s26.m.idxmin(), follows_defense=corr, repeats=yoy))
T = pd.DataFrame(rows)
pd.set_option("display.width", 220)
print(T.round(2).to_string(index=False))
T.to_csv(S + "team_candidates.csv", index=False)
