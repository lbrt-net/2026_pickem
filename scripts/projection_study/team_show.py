"""Per-team season averages ('26) for every TEAM candidate category, incl. hustle when pulled. → team_show.json"""
import json
import numpy as np
import pandas as pd

R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
D = pd.read_parquet(S + "team_games.parquet")


def hustle(season):
    try:
        h = json.load(open(f"{R}team_hustle/{season}.json"))
    except FileNotFoundError:
        return None
    rows = []
    for day, v in h.items():
        for r in v["rows"]:
            rows.append(dict(zip(v["headers"], r), date=pd.to_datetime(day)))
    if not rows:
        return None
    h = pd.DataFrame(rows)
    ids = D.drop_duplicates("TEAM_ID").set_index("TEAM_ID").TEAM_ABBREVIATION
    h["TEAM_ABBREVIATION"] = h.TEAM_ID.map(ids)
    return h


CATS = [("Opponent points", "OPP_PTS", "lower"), ("Held under 100 (share of games)", "U100", "higher"), ("Held under 105", "U105", "higher"), ("Held under 110", "U110", "higher"),
        ("Steals", "STL", "higher"), ("Blocks", "BLK", "higher"), ("Turnovers forced", "OPP_TOV", "higher"),
        ("Opponent paint points", "OPP_PTS_PAINT", "lower"), ("Opponent fast-break points", "OPP_PTS_FB", "lower"),
        ("Opponent second-chance points", "OPP_PTS_2ND_CHANCE", "lower"), ("Opponent eFG%", "OPP_EFG_PCT", "lower"),
        ("Opponent 3P%", "OPP_FG3_PCT", "lower"), ("Defensive rebound %", "DREB_PCT", "higher")]
HCATS = [("Deflections", "DEFLECTIONS", "higher"), ("Charges drawn", "CHARGES_DRAWN", "higher"), ("Contested shots", "CONTESTED_SHOTS", "higher"),
         ("Loose balls recovered", "LOOSE_BALLS_RECOVERED", "higher"), ("Box outs (defensive)", "DEF_BOXOUTS", "higher")]


def season_table(season):
    d = D[D.season == season].copy()
    d["U100"], d["U105"], d["U110"] = (d.OPP_PTS < 100).astype(float), (d.OPP_PTS < 105).astype(float), (d.OPP_PTS < 110).astype(float)
    t = d.groupby("TEAM_ABBREVIATION").agg(dr=("DEF_RATING", "mean"), n=("GAME_ID", "size"), **{c: (c, "mean") for _, c, _ in CATS})
    h = hustle(season)
    cats = list(CATS)
    if h is not None:
        ht = h.groupby("TEAM_ABBREVIATION")[[c for _, c, _ in HCATS if c in h.columns]].mean()
        t = t.join(ht)
        cats += [x for x in HCATS if x[1] in h.columns]
    return t, cats


t, cats = season_table("2025-26")
# DEF_RATING per team-season from per-game logs is a game average; use possession-weighted for the ranking
d = D[D.season == "2025-26"]
drw = (d.DEF_RATING * d.POSS).groupby(d.TEAM_ABBREVIATION).sum() / d.POSS.groupby(d.TEAM_ABBREVIATION).sum()
t["dr"] = drw
out = dict(cats=[[a, b, c] for a, b, c in cats], teams=t.reset_index().to_dict("records"),
           corr={c: float(np.corrcoef(-t.dr, t[c] * (1 if s == "higher" else -1))[0, 1]) for _, c, s in cats},
           league={c: float(t[c].mean()) for _, c, _ in cats})
# shot clock violations forced, '25 (play-by-play): the offending team's "Shot Clock Turnover" credited to its opponent
pbp = pd.read_parquet(R + "play_by_play/pbp_2024_25.parquet", columns=["game_id", "person_id", "sub_type"])
sc = pbp[pbp.sub_type == "Shot Clock Turnover"].groupby(["game_id", "person_id"]).size().rename("n").reset_index()
g25 = D[D.season == "2024-25"][["GAME_ID", "TEAM_ID", "TEAM_ABBREVIATION"]]
pairs = g25.merge(g25, on="GAME_ID", suffixes=("", "_opp"))
pairs = pairs[pairs.TEAM_ID != pairs.TEAM_ID_opp]
pairs = pairs.merge(sc, left_on=["GAME_ID", "TEAM_ID_opp"], right_on=["game_id", "person_id"], how="left").fillna({"n": 0})
scf = pairs.groupby("TEAM_ABBREVIATION").n.mean()
d25 = D[D.season == "2024-25"]
dr25 = (d25.DEF_RATING * d25.POSS).groupby(d25.TEAM_ABBREVIATION).sum() / d25.POSS.groupby(d25.TEAM_ABBREVIATION).sum()
out["shot_clock_25"] = [{"team": k, "scv": float(v), "dr": float(dr25[k]), "tov": float(d25[d25.TEAM_ABBREVIATION == k].OPP_TOV.mean())} for k, v in scf.items()]
out["shot_clock_25_corr"] = float(np.corrcoef(-dr25.reindex(scf.index), scf)[0, 1])
json.dump(out, open(S + "team_show.json", "w"), default=float)
print("shot clock forced '25 top:", scf.sort_values(ascending=False).head(5).round(2).to_dict(), "corr w/ defense", round(out["shot_clock_25_corr"], 2))
top = t.sort_values("dr").head(5)
print("best defenses '26:", list(top.index), [round(x, 1) for x in top.dr])
print({k: round(v, 2) for k, v in out["corr"].items()})
