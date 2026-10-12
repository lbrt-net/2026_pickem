"""Chance a player plays his team's next game, given how many of its games in a row he has just missed (2026-10-11).
Feeds Roster's 1+ Game %. Box scores only (disp_games, played = MIN > 0); a player counts on a team from his first to
his last game for it that season, and needs 10+ games there. Fit on '22–'25, '26 shown as the check.
Run: .venv/bin/python scripts/projection_study/miss_streak.py
"""
import sys

import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import W  # noqa: E402

G = pd.read_parquet(W + "disp_games.parquet")
G["date"] = pd.to_datetime(G["date"])
teamg = {k: sorted(set(zip(d.date, d.GAME_ID))) for k, d in G.groupby(["season", "TEAM_ABBREVIATION"])}
rows = []
for (season, team, pid), d in G[G.MIN > 0].groupby(["season", "TEAM_ABBREVIATION", "PLAYER_ID"]):
    if len(d) < 10:
        continue
    played = set(d.GAME_ID)
    games = [g for dt, g in teamg[(season, team)] if d.date.min() <= dt <= d.date.max()]
    streak = 0
    for g in games:
        rows.append((season, min(streak, 6), g in played))
        streak = 0 if g in played else streak + 1
t = pd.DataFrame(rows, columns=["season", "streak", "played"])
for label, part in (("fit '22–'25", t[t.season < "2025-26"]), ("check '26", t[t.season == "2025-26"])):
    print(label)
    print(part.groupby("streak").played.agg(["mean", "size"]).round(3).to_string())
