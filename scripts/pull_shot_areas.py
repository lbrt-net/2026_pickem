"""Shot zones + assisted share per player-season (PlayerDashboardByShootingSplits,
ShotAreaPlayerDashboard table), for the projection study. One request per player-season.

    python3 scripts/pull_shot_areas.py

Saves one parquet per player-season under nba-pipeline/data/raw/shot_area/<season>/<player_id>.parquet
and skips files already on disk. stats.nba.com rules: 5s between requests, backoff 30→60→120s,
never alongside another stats.nba.com script.
"""
import time
from pathlib import Path

from nba_api.stats.endpoints import playerdashboardbyshootingsplits

OUT = Path.home() / "PycharmProjects" / "nba-pipeline" / "data" / "raw" / "shot_area"
SEASONS = ["2022-23", "2023-24", "2024-25"]  # '23–'25; '26 is the validation season, never pulled here
PLAYERS = {
    "201942": "DeMar DeRozan", "202696": "Nikola Vučević", "1626167": "Myles Turner",
    "1628969": "Mikal Bridges", "1628389": "Bam Adebayo", "203999": "Nikola Jokić",
}
DELAY = 5
BACKOFF = [30, 60, 120, 120, 120]


def fetch(pid: str, season: str):
    for wait in BACKOFF + [None]:
        try:
            r = playerdashboardbyshootingsplits.PlayerDashboardByShootingSplits(
                player_id=pid, season=season, season_type_playoffs="Regular Season",
                per_mode_detailed="Totals", timeout=60)
            return r.shot_area_player_dashboard.get_data_frame()
        except Exception as e:
            if wait is None:
                raise
            print(f"    {type(e).__name__}: {e} — retry in {wait}s")
            time.sleep(wait)


def main():
    for season in SEASONS:
        for pid, name in PLAYERS.items():
            f = OUT / season / f"{pid}.parquet"
            if f.exists():
                print(f"{season} {name}: on disk")
                continue
            df = fetch(pid, season)
            df.insert(0, "PLAYER_ID", pid)
            df.insert(1, "SEASON", season)
            f.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(f)
            print(f"{season} {name}: {len(df)} zones")
            time.sleep(DELAY)


if __name__ == "__main__":
    main()
