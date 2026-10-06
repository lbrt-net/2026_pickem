"""Slot balance: G / F / C / FLX / TEAM, using '26 real weekly scores (Mon–Sun weeks, regular season).
Player weekly score = best single game that week (FP, user scoring minus BLKD); value = mean over weeks he played.
TEAM weekly score = sum of point margins that week; value = mean over weeks.
Position = most frequent box-score starting position '23–'26 (the app's rule); none → FLX-only.
Allocation for N teams: top N at G, F, C; FLX = next N best players of any position; TEAM = top N teams.
Replacement = best player/team left over for that slot.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem/scripts")
sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem")
from load_historical_boxscores import minutes  # noqa: E402
from backend.fantasy_2026_27.logic import player_points  # noqa: E402

D = "/Users/allan/PycharmProjects/nba-pipeline/data/"
SEASON_FILES = [D + "raw/box_scores_traditional/trad_box_scores_2022_23.parquet",
                D + "raw/box_scores_traditional/trad_box_scores_2023_24.parquet",
                D + "raw/box_scores_traditional/trad_box_scores_2024_25.parquet",
                D + "box_scores/trad_box_scores_2025_26.parquet"]
pos = pd.concat(pd.read_parquet(f, columns=["player_id", "position"]) for f in SEASON_FILES)
pos = pos[pos.position.fillna("").str.strip() != ""]
pos["player_id"] = pos.player_id.astype(int)
POS = pos.groupby("player_id").position.agg(lambda s: s.value_counts().index[0])

sched = pd.read_parquet(D + "raw/schedules/schedule_2025_26.parquet")
sched = sched[sched.game_id.astype(str).str[2] == "2"]
gdate = pd.to_datetime(sched.set_index("game_id").game_date)
week = (gdate - pd.to_timedelta(gdate.dt.weekday, unit="D")).dt.date  # Monday of the week

b = pd.read_parquet(SEASON_FILES[-1])
b = b[b.game_id.astype(str).str[2] == "2"].copy()
b["m"] = b["minutes"].map(minutes)
b = b[b.m > 0]
b["player_id"] = b.player_id.astype(int)
b["fp"] = [player_points(r) for r in b[["pts", "fga", "fgm", "fg3m", "fta", "ftm", "oreb", "dreb", "ast", "stl", "blk", "tov"]].to_dict("records")]
b["week"] = b.game_id.map(week)
wk = b.groupby(["player_id", "week"]).fp.max().reset_index()
pv = wk.groupby("player_id").agg(val=("fp", "mean"), weeks=("fp", "size"))
pv = pv[pv.weeks >= 10]  # enough weeks to be a real draftable player
pv["name"] = b.groupby("player_id").player_name.last()
pv["pos"] = POS.reindex(pv.index).fillna("—")

t = sched[["game_id", "home_team_tricode", "away_team_tricode", "home_score", "away_score"]].copy()
t["week"] = t.game_id.map(week)
rows = [(r.home_team_tricode, r.week, r.home_score - r.away_score) for r in t.itertuples()] + \
       [(r.away_team_tricode, r.week, r.away_score - r.home_score) for r in t.itertuples()]
tm = pd.DataFrame(rows, columns=["team", "week", "margin"]).groupby(["team", "week"]).margin.sum().groupby("team").mean().sort_values(ascending=False)

print(f"'26: {len(pv)} players with 10+ weeks. Position counts: {pv.pos.value_counts().to_dict()}")
print(f"Average weekly best game, top player at each position: " + ", ".join(
    f"{p} {pv[pv.pos == p].val.max():.1f} ({pv[pv.pos == p].val.idxmax() and pv.loc[pv[pv.pos == p].val.idxmax(), 'name']})" for p in ["G", "F", "C"]))
print(f"TEAM weekly margin total: best {tm.index[0]} {tm.iloc[0]:+.1f}, median {tm.median():+.1f}, worst {tm.index[-1]} {tm.iloc[-1]:+.1f}\n")

for N in [4, 8, 10, 12]:
    taken = set()
    out = {}
    for p in ["G", "F", "C"]:
        s = pv[pv.pos == p].sort_values("val", ascending=False)
        st = s.head(N)
        taken |= set(st.index)
        out[p] = (st.val, s.val.iloc[N] if len(s) > N else np.nan)
    rest = pv.drop(index=list(taken)).sort_values("val", ascending=False)
    out["FLX"] = (rest.val.head(N), rest.val.iloc[N])
    out["TEAM"] = (tm.head(N), tm.iloc[N] if len(tm) > N else np.nan)
    print(f"N = {N} teams        {'avg starter':>12}{'best':>8}{'worst st.':>10}{'replace':>9}{'avg − repl':>12}{'spread best−worst':>19}")
    for k, (st, rep) in out.items():
        print(f"   {k:<5}{'':12}{st.mean():12.1f}{st.max():8.1f}{st.min():10.1f}{rep:9.1f}{st.mean() - rep:12.1f}{st.max() - st.min():19.1f}")
    print()

print("'26 top 50 by weekly value, with position:")
top = pv.sort_values("val", ascending=False).head(50)
print("  " + "  ".join(f"{i + 1}.{n.split()[-1]}({p}) {v:.1f}" for i, (n, p, v) in enumerate(zip(top.name, top.pos, top.val))))
print(f"  positions in top 50: {top.pos.value_counts().to_dict()}")
