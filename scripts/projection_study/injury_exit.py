"""How often a played game is cut short (2026-10-26: Jaren Jackson Jr. 10 min, Markkanen 6 min, both left hurt and
counted as "played" for 1+ Game %). Box scores only (disp_games). A player counts on a team from his first to his last
game for it that season, with 10+ games and a median of 20+ minutes there.
Short game = under 40% of his median minutes. Exit = a short game followed by missing his team's next game.
Reports per season: short / exit share of played games, the short game's points vs his average, and the chance he plays
each of the next 3 team games after a short game vs after a normal one.
Run: .venv/bin/python scripts/projection_study/injury_exit.py
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
    if len(d) < 10 or d.MIN.median() < 20:
        continue
    med, avg_fp = d.MIN.median(), d.fp.mean()
    by_game = d.set_index("GAME_ID")
    games = [g for dt, g in teamg[(season, team)] if d.date.min() <= dt <= d.date.max()]
    for i, g in enumerate(games):
        if g not in by_game.index:
            continue
        r = by_game.loc[g]
        nxt = [games[i + j] in by_game.index if i + j < len(games) else None for j in (1, 2, 3)]
        rows.append((season, pid, r.PLAYER_NAME, r.MIN < 0.4 * med, r.fp / avg_fp if avg_fp > 0 else None, *nxt))
t = pd.DataFrame(rows, columns=["season", "pid", "name", "short", "fp_ratio", "next1", "next2", "next3"])
t["exit"] = t.short & (t.next1 == False)  # noqa: E712
print("played games, share short / exit, short game's points vs his average")
print(t.groupby("season").agg(games=("short", "size"), short=("short", "mean"), exit=("exit", "mean")).round(4).to_string())
print("\nshort game points ÷ his average:", round(t[t.short].fp_ratio.median(), 2), "(median)", round(t[t.short].fp_ratio.mean(), 2), "(mean)")
print("exit game points ÷ his average:", round(t[t.exit].fp_ratio.median(), 2), "(median)")
for lab, part in (("after a short game", t[t.short]), ("after a normal game", t[~t.short]), ("after an exit", t[t.exit])):
    print(f"\nplays next 1 / 2 / 3 {lab}: n={len(part)}",
          [round(part[c].dropna().astype(float).mean(), 3) for c in ("next1", "next2", "next3")])
