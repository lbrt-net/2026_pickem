"""Team rosters (CommonTeamRoster), one request per team per season — what projections need at draft time,
before any games exist. 2026-27 = current rosters; 2025-26 = that season's roster as the NBA lists it now.

    python3 scripts/pull_team_rosters.py            # both seasons
    python3 scripts/pull_team_rosters.py 2026-27    # just one

Saves nba-pipeline/data/raw/rosters/<season>.csv (one row per player: team, player_id, position, height,
weight, birth date, age, experience). Re-pulls every time — rosters change daily in the offseason.
stats.nba.com rules: 5s between requests, backoff 30→60→120s, never alongside another stats.nba.com script.
"""
import sys
import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import commonteamroster
from nba_api.stats.static import teams

OUT = Path.home() / "PycharmProjects" / "nba-pipeline" / "data" / "raw" / "rosters"
DELAY = 5
BACKOFF = [30, 60, 120, 120, 120]


def fetch(team_id: int, season: str) -> pd.DataFrame:
    for wait in BACKOFF + [None]:
        try:
            return commonteamroster.CommonTeamRoster(team_id=team_id, season=season, timeout=60).common_team_roster.get_data_frame()
        except Exception as e:
            if wait is None:
                raise
            print(f"    {type(e).__name__}: {e} — retry in {wait}s", flush=True)
            time.sleep(wait)


def main():
    seasons = sys.argv[1:] or ["2026-27", "2025-26"]
    OUT.mkdir(parents=True, exist_ok=True)
    for season in seasons:
        frames = []
        for t in sorted(teams.get_teams(), key=lambda x: x["abbreviation"]):
            df = fetch(t["id"], season)
            df.insert(0, "TEAM", t["abbreviation"])
            frames.append(df)
            print(f"{season} {t['abbreviation']}: {len(df)} players", flush=True)
            time.sleep(DELAY)
        pd.concat(frames).to_csv(OUT / f"{season}.csv", index=False)
        print(f"saved {OUT / f'{season}.csv'}", flush=True)


if __name__ == "__main__":
    main()
