"""Player clutch stats per player-game (LeagueDashPlayerClutch: last 5 minutes of the 4th / OT, score within 5 — the
NBA's definition), for the clutch-points category (SCORING_SCALE.md). No per-game mode, so it's pulled one game date at
a time (a player plays at most once a day): about 165 requests a season.

    python3 scripts/pull_player_clutch.py                     # 2025-26, 2024-25, 2023-24, 2022-23
    python3 scripts/pull_player_clutch.py --season 2025-26

Saves nba-pipeline data/raw/player_clutch/<season>.json ({date: {headers, rows}}); resumes where it left off.
stats.nba.com rules: 5s between requests, backoff 30→60→120s, never alongside another stats.nba.com script.
"""
import argparse
import json
import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerclutch

RAW = Path.home() / "PycharmProjects" / "nba-pipeline" / "data" / "raw"
OUT = RAW / "player_clutch"
SEASONS = ["2025-26", "2024-25", "2023-24", "2022-23"]
DELAY = 5
BACKOFF = [30, 60, 120, 120, 120]


def dates(season: str) -> list[str]:
    s = pd.read_parquet(RAW / "schedules" / f"schedule_{season.replace('-', '_')}.parquet")
    s = s[(s.game_id.str[2] == "2") & (s.game_status == 3)]
    return sorted(pd.to_datetime(s.game_date).dt.strftime("%m/%d/%Y").unique(), key=lambda d: (d[6:], d[:5]))


def fetch(season: str, day: str) -> dict:
    for wait in BACKOFF + [None]:
        try:
            return leaguedashplayerclutch.LeagueDashPlayerClutch(
                season=season, season_type_all_star="Regular Season", per_mode_detailed="Totals",
                clutch_time="Last 5 Minutes", ahead_behind="Ahead or Behind", point_diff=5,
                date_from_nullable=day, date_to_nullable=day, timeout=60).get_dict()
        except Exception as e:
            if wait is None:
                raise
            print(f"    {day}: {type(e).__name__}: {e} — retry in {wait}s", flush=True)
            time.sleep(wait)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", choices=SEASONS)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for season in [args.season] if args.season else SEASONS:
        f = OUT / f"{season}.json"
        have = json.loads(f.read_text()) if f.exists() else {}
        todo = [d for d in dates(season) if d not in have]
        print(f"{season}: {len(have)} dates on disk, {len(todo)} to pull", flush=True)
        for i, day in enumerate(todo):
            rs = fetch(season, day)["resultSets"][0]
            have[day] = {"headers": rs["headers"], "rows": rs["rowSet"]}
            if i % 10 == 0 or i == len(todo) - 1:
                f.write_text(json.dumps(have))
                print(f"  {season} {day}: {len(rs['rowSet'])} players ({i + 1}/{len(todo)})", flush=True)
            time.sleep(DELAY)
        f.write_text(json.dumps(have))


if __name__ == "__main__":
    main()
