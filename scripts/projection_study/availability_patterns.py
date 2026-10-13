"""Two kinds of missing time, per player (commissioner, 2026-10-12): scattered misses (sits 1–2 games here and there —
rest, load management, nagging; Kawhi) vs stretch misses (healthy = plays everything, then gone 3+ games in a row;
LaMelo). Embiid = both. Box scores '22–'26 (disp_games, played = MIN > 0); a player's span with a team runs from his
first to his last game for it that season. Scattered rate = games missed in runs of 1–2 ÷ games in his span outside
long runs; stretch share = games missed in runs of 3+ ÷ span games. Pooled over seasons, recent seasons weighted more.
Run: .venv/bin/python scripts/projection_study/availability_patterns.py
"""
import sys

import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import W  # noqa: E402

G = pd.read_parquet(W + "disp_games.parquet")
G["date"] = pd.to_datetime(G["date"])
SEASON_W = {"2021-22": 0.5, "2022-23": 0.7, "2023-24": 0.85, "2024-25": 1.0, "2025-26": 1.0}
team_games = {k: sorted(set(zip(d.date, d.GAME_ID))) for k, d in G.groupby(["season", "TEAM_ABBREVIATION"])}
rows = []
for (season, team, pid), d in G[G.MIN > 0].groupby(["season", "TEAM_ABBREVIATION", "PLAYER_ID"]):
    if len(d) < 5:
        continue
    played = set(d.GAME_ID)
    span = [g for dt, g in team_games[(season, team)] if d.date.min() <= dt <= d.date.max()]
    runs, cur = [], 0
    for g in span:
        if g in played:
            if cur:
                runs.append(cur)
            cur = 0
        else:
            cur += 1
    short = sum(r for r in runs if r <= 2)
    long_ = sum(r for r in runs if r >= 3)
    rows.append({"pid": pid, "name": d.PLAYER_NAME.iloc[0], "season": season, "span": len(span), "played": len(played),
                 "short": short, "long": long_, "long_runs": sum(1 for r in runs if r >= 3), "fp": d.fp.mean(),
                 "w": SEASON_W.get(season, 0.5)})
t = pd.DataFrame(rows)
t["active"] = t.span - t.long
agg = t.assign(ws=t.short * t.w, wa=t.active * t.w, wl=t.long * t.w, wsp=t.span * t.w, wr=t.long_runs * t.w, wn=t.w).groupby(["pid", "name"]).agg(
    short=("ws", "sum"), active=("wa", "sum"), long=("wl", "sum"), span=("wsp", "sum"), runs=("wr", "sum"), seasons=("wn", "sum"), fp=("fp", "mean"))
agg["scattered"] = (agg.short / agg.active).round(3)       # chance he sits a given game while otherwise healthy
agg["stretch"] = (agg.long / agg.span).round(3)            # share of his games lost to 3+ game absences
agg["stretch_runs_per_season"] = (agg.runs / agg.seasons).round(2)
top = agg[agg.span >= 60].sort_values("fp", ascending=False).head(100)
print("checks:")
for n in ("Kawhi Leonard", "LaMelo Ball", "Joel Embiid"):
    r = agg.reset_index().query("name == @n")
    print(" ", n, r[["scattered", "stretch", "stretch_runs_per_season"]].to_dict("records"))
print("\ntop-100 by FP/G — most scattered:")
print(top.sort_values("scattered", ascending=False).head(10)[["scattered", "stretch", "stretch_runs_per_season"]].to_string())
print("\ntop-100 — most stretch:")
print(top.sort_values("stretch", ascending=False).head(10)[["scattered", "stretch", "stretch_runs_per_season"]].to_string())
print("\ntop-100 medians:", top[["scattered", "stretch"]].median().round(3).to_dict())
agg.reset_index().to_csv(W + "availability_patterns.csv", index=False)
