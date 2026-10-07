"""TEAM_SCORING.md — evaluate candidate defensive stats on '22–'26 team-games (TeamGameLogs + player box scores).
For each candidate (sign-flipped so higher = better defense):
  separation : SD of team season averages (true, after removing game noise) vs SD of single games
  defense    : corr of team season average with -DEF_RATING (higher = better defense)
  offense    : corr with OFF_RATING  (want ~0: it's defense, not a good team)
  margin     : corr with point margin per game (season)
  carry-over : corr of a team's season average with its next season's
Dev seasons '22–'25 for the season-level numbers; '26 shown alongside."""
import json
import numpy as np
import pandas as pd
import psycopg2

R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
SEAS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]


def J(kind, s):
    rs = json.load(open(f"{R}{kind}/{s}.json"))["resultSets"]
    rs = rs[0] if isinstance(rs, list) else rs
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"])


frames = []
for s in SEAS:
    b = J("team_logs_base", s)[["TEAM_ID", "TEAM_ABBREVIATION", "GAME_ID", "GAME_DATE", "MATCHUP", "WL", "PTS", "PLUS_MINUS", "STL", "BLK", "DREB", "OREB", "TOV"]]
    a = J("team_logs_advanced", s)[["TEAM_ID", "GAME_ID", "DEF_RATING", "OFF_RATING", "PACE", "POSS", "DREB_PCT"]]
    m = J("team_logs_misc", s)[["TEAM_ID", "GAME_ID", "OPP_PTS_PAINT", "OPP_PTS_FB", "OPP_PTS_2ND_CHANCE", "OPP_PTS_OFF_TOV"]]
    f = J("team_logs_four_factors", s)[["TEAM_ID", "GAME_ID", "OPP_EFG_PCT", "OPP_FTA_RATE", "OPP_TOV_PCT", "OPP_OREB_PCT"]]
    o = J("team_logs_opponent", s)
    o = o[["TEAM_ID", "GAME_ID"] + [c for c in o.columns if c.startswith("OPP_") and c in ("OPP_PTS", "OPP_FG_PCT", "OPP_FG3_PCT", "OPP_FG3A", "OPP_TOV", "OPP_FTA")]]
    d = b.merge(a, on=["TEAM_ID", "GAME_ID"]).merge(m, on=["TEAM_ID", "GAME_ID"]).merge(f, on=["TEAM_ID", "GAME_ID"]).merge(o, on=["TEAM_ID", "GAME_ID"])
    d["season"] = s
    frames.append(d)
D = pd.concat(frames, ignore_index=True)
D["GAME_DATE"] = pd.to_datetime(D.GAME_DATE)
# top opposing scorer (player box scores in the app DB, '23–'26)
conn = psycopg2.connect("dbname=pickem_local")
top = pd.read_sql("SELECT game_id, team, max(pts) AS top FROM nba_player_games WHERE minutes > 0 GROUP BY 1, 2", conn)
abbr = D[["GAME_ID", "TEAM_ABBREVIATION"]].rename(columns={"GAME_ID": "game_id", "TEAM_ABBREVIATION": "team"})
opp = D[["GAME_ID", "TEAM_ABBREVIATION"]].merge(D[["GAME_ID", "TEAM_ABBREVIATION"]], on="GAME_ID", suffixes=("", "_opp"))
opp = opp[opp.TEAM_ABBREVIATION != opp.TEAM_ABBREVIATION_opp]
opp = opp.merge(top, left_on=["GAME_ID", "TEAM_ABBREVIATION_opp"], right_on=["game_id", "team"], how="left")
D = D.merge(opp[["GAME_ID", "TEAM_ABBREVIATION", "top"]].rename(columns={"top": "OPP_TOP"}), on=["GAME_ID", "TEAM_ABBREVIATION"], how="left")
D.to_parquet(S + "team_games.parquet")

# candidates: (label, column or function, sign: +1 = more is better defense)
C = {
    "Opponent points (fewer)": (lambda d: d.OPP_PTS, -1),
    "Held under 100 (+10)": (lambda d: 10.0 * (d.OPP_PTS < 100), 1),
    "Held under 110 (+5)": (lambda d: 5.0 * (d.OPP_PTS < 110), 1),
    "Both tiers (<100: +15, <110: +5)": (lambda d: 10.0 * (d.OPP_PTS < 100) + 5.0 * (d.OPP_PTS < 110), 1),
    "Defensive rating (pts/100 poss, lower)": (lambda d: d.DEF_RATING, -1),
    "Team steals": (lambda d: d.STL, 1),
    "Team blocks": (lambda d: d.BLK, 1),
    "Steals + blocks": (lambda d: d.STL + d.BLK, 1),
    "Opponent turnovers forced": (lambda d: d.OPP_TOV, 1),
    "Opponent turnover % forced": (lambda d: d.OPP_TOV_PCT, 1),
    "Defensive rebounds": (lambda d: d.DREB, 1),
    "Defensive rebound %": (lambda d: d.DREB_PCT, 1),
    "Opponent paint points (fewer)": (lambda d: d.OPP_PTS_PAINT, -1),
    "Opp paint under 40 (bonus)": (lambda d: 1.0 * (d.OPP_PTS_PAINT < 40), 1),
    "Opponent fast-break points (fewer)": (lambda d: d.OPP_PTS_FB, -1),
    "Opponent second-chance points (fewer)": (lambda d: d.OPP_PTS_2ND_CHANCE, -1),
    "Opponent points off turnovers (fewer)": (lambda d: d.OPP_PTS_OFF_TOV, -1),
    "Opponent eFG% (lower)": (lambda d: d.OPP_EFG_PCT, -1),
    "Opponent 3P% (lower)": (lambda d: d.OPP_FG3_PCT, -1),
    "Opponent 3PA (fewer)": (lambda d: d.OPP_FG3A, -1),
    "Opponent FT rate (lower)": (lambda d: d.OPP_FTA_RATE, -1),
    "No opponent scores 30 (bonus)": (lambda d: 1.0 * (d.OPP_TOP < 30), 1),
    "Point margin (reference — out)": (lambda d: d.PLUS_MINUS, 1),
}
ss = D.groupby(["season", "TEAM_ABBREVIATION"]).agg(dr=("DEF_RATING", "mean"), orr=("OFF_RATING", "mean"), mg=("PLUS_MINUS", "mean"), n=("GAME_ID", "size"))
rows = []
for lab, (fn, sign) in C.items():
    d = D.assign(v=sign * fn(D).astype(float))
    if d.v.isna().all():
        continue
    dd = d.dropna(subset=["v"])
    t = dd.groupby(["season", "TEAM_ABBREVIATION"]).v.agg(["mean", "var", "size"])
    dev = t[t.index.get_level_values(0) < "2025-26"]
    noise = dev["var"].mean() / dev["size"].mean()
    true_sd = float(np.sqrt(max(dev["mean"].groupby(level=0).var().mean() - noise, 0)))
    game_sd = float(np.sqrt(dev["var"].mean()))
    x = t.join(ss)
    xd = x[x.index.get_level_values(0) < "2025-26"]
    cd = float(np.corrcoef(xd["mean"], -xd.dr)[0, 1])
    co = float(np.corrcoef(xd["mean"], xd.orr)[0, 1])
    cm = float(np.corrcoef(xd["mean"], xd.mg)[0, 1])
    w = t["mean"].unstack(0)
    pairs = [(a, b) for a, b in zip(SEAS[:-1], SEAS[1:]) if a in w and b in w]
    yoy = float(np.nanmean([w[[a, b]].dropna().corr().iloc[0, 1] for a, b in pairs[:-1]]))
    yoy26 = float(w[[pairs[-1][0], pairs[-1][1]]].dropna().corr().iloc[0, 1])
    # weekly (3 games): share of a team's 3-game total that is real team difference
    wk_rel = true_sd ** 2 / (true_sd ** 2 + game_sd ** 2 / 3)
    rows.append(dict(cand=lab, mean=float(sign * dev["mean"].mean()), true_sd=true_sd, game_sd=game_sd, sep=true_sd / game_sd, wk_rel=wk_rel,
                     defense=cd, offense=co, margin=cm, yoy=yoy, yoy26=yoy26))
T = pd.DataFrame(rows)
T.to_csv(S + "team_eval.csv", index=False)
pd.set_option("display.width", 220)
print(T.round(2).to_string(index=False))
