"""League-wide, one-request-per-season pulls for the projection study:
  bios   — LeagueDashPlayerBioStats (age, height, weight, draft year/round/number), 2019-20 → 2025-26
  zones  — LeagueDashPlayerShotLocations, By Zone, regular season, 2020-21 → 2025-26
  player_advanced / team_advanced — LeagueDashPlayerStats / LeagueDashTeamStats, Advanced, Totals
           (on-court POSS, PACE, USG_PCT), 2020-21 → 2025-26
  game_logs — PlayerGameLogs, every player-game incl. BLKA (own shots blocked) and PFD, 2020-21 → 2025-26
  player_scoring — LeagueDashPlayerStats, Scoring (assisted share of 2PM / 3PM), 2020-21 → 2025-26

    python3 scripts/pull_league_seasons.py

Saves the raw JSON response per season under nba-pipeline/data/raw/{bios,shot_locations}/<season>.json
(shot locations have a two-row header, so parse from the raw JSON). Skips files already on disk.
stats.nba.com rules: 5s between requests, backoff 30→60→120s, never alongside another stats.nba.com script.
'26 (2025-26) is pulled for validation only — never fit on it.
"""
import json
import time
from pathlib import Path

from nba_api.stats.endpoints import (leaguedashplayerbiostats, leaguedashplayershotlocations, leaguedashplayerstats,
                                     leaguedashteamstats, playergamelogs)

RAW = Path.home() / "PycharmProjects" / "nba-pipeline" / "data" / "raw"
DELAY = 5
BACKOFF = [30, 60, 120, 120, 120]
JOBS = [("bios", s) for s in ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]] + \
       [("shot_locations", s) for s in ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]] + \
       [(k, s) for k in ("player_advanced", "team_advanced")
        for s in ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]] + \
       [("game_logs", s) for s in ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]] + \
       [("player_scoring", s) for s in ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]]


def request(kind: str, season: str) -> dict:
    if kind == "game_logs":  # every player-game in the season, incl. BLKA (own shots blocked) and PFD
        return playergamelogs.PlayerGameLogs(
            season_nullable=season, season_type_nullable="Regular Season", timeout=120).get_dict()
    if kind == "player_advanced":  # POSS, PACE, USG_PCT, MIN per player (on-court possessions)
        return leaguedashplayerstats.LeagueDashPlayerStats(
            season=season, season_type_all_star="Regular Season", measure_type_detailed_defense="Advanced",
            per_mode_detailed="Totals", timeout=60).get_dict()
    if kind == "player_scoring":  # PCT_AST_2PM / PCT_AST_3PM: share of a player's makes that were assisted
        return leaguedashplayerstats.LeagueDashPlayerStats(
            season=season, season_type_all_star="Regular Season", measure_type_detailed_defense="Scoring",
            per_mode_detailed="Totals", timeout=60).get_dict()
    if kind == "team_advanced":  # PACE, POSS per team
        return leaguedashteamstats.LeagueDashTeamStats(
            season=season, season_type_all_star="Regular Season", measure_type_detailed_defense="Advanced",
            per_mode_detailed="Totals", timeout=60).get_dict()
    if kind == "bios":
        return leaguedashplayerbiostats.LeagueDashPlayerBioStats(
            season=season, season_type_all_star="Regular Season", timeout=60).get_dict()
    return leaguedashplayershotlocations.LeagueDashPlayerShotLocations(
        season=season, season_type_all_star="Regular Season", distance_range="By Zone",
        per_mode_detailed="Totals", timeout=60).get_dict()


def main():
    for kind, season in JOBS:
        f = RAW / kind / f"{season}.json"
        if f.exists():
            print(f"{kind} {season}: on disk")
            continue
        for wait in BACKOFF + [None]:
            try:
                data = request(kind, season)
                break
            except Exception as e:
                if wait is None:
                    raise
                print(f"  {kind} {season}: {type(e).__name__}: {e} — retry in {wait}s")
                time.sleep(wait)
        rs = data["resultSets"]
        n = len((rs[0] if isinstance(rs, list) else rs)["rowSet"])
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(data))
        print(f"{kind} {season}: {n} players")
        time.sleep(DELAY)


if __name__ == "__main__":
    main()
