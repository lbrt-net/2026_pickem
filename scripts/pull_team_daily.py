"""Team stats per team-game, pulled one game date at a time (each team plays at most once a day, so a date's row is
that game; match it to the opponent from the schedule), for TEAM_SCORING.md:
  hustle     — LeagueHustleStatsTeam: deflections, charges drawn, contested shots, loose balls, box outs
  violations — LeagueDashTeamStats MeasureType=Violations: shot clock, 8 / 5 second, travel, offensive foul,
               offensive 3 seconds, backcourt, ... (a team's violations FORCED = its opponent's that day)
About 165 game dates a season, two requests each.

    python3 scripts/pull_team_daily.py                       # 2025-26, 2024-25, 2023-24, 2022-23
    python3 scripts/pull_team_daily.py --season 2025-26

Saves nba-pipeline data/raw/team_hustle/<season>.json and team_violations/<season>.json ({date: rows}); resumes.
stats.nba.com rules: 5s between requests, backoff 30→60→120s, never alongside another stats.nba.com script.
"""
import argparse
import json
import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import leaguehustlestatsteam
from nba_api.stats.library.http import NBAStatsHTTP

RAW = Path.home() / "PycharmProjects" / "nba-pipeline" / "data" / "raw"
OUT = {"hustle": RAW / "team_hustle", "violations": RAW / "team_violations"}
SEASONS = ["2025-26", "2024-25", "2023-24", "2022-23"]
DELAY = 5
BACKOFF = [30, 60, 120, 120, 120]


def dates(season: str) -> list[str]:
    s = pd.read_parquet(RAW / "schedules" / f"schedule_{season.replace('-', '_')}.parquet")
    s = s[(s.game_id.str[2] == "2") & (s.game_status == 3)]
    return sorted(pd.to_datetime(s.game_date).dt.strftime("%m/%d/%Y").unique(), key=lambda d: (d[6:], d[:5]))


def request(kind: str, season: str, day: str) -> dict:
    if kind == "hustle":
        return leaguehustlestatsteam.LeagueHustleStatsTeam(season=season, season_type_all_star="Regular Season", per_mode_time="Totals",
                                                          date_from_nullable=day, date_to_nullable=day, timeout=60).get_dict()
    import json as _json  # Violations isn't wrapped by nba_api; same endpoint as the team stats pages
    return _json.loads(NBAStatsHTTP().send_api_request(endpoint="leaguedashteamstats", timeout=60, parameters={
        "Season": season, "SeasonType": "Regular Season", "MeasureType": "Violations", "PerMode": "Totals", "LeagueID": "00",
        "LastNGames": 0, "Month": 0, "OpponentTeamID": 0, "PaceAdjust": "N", "Period": 0, "PlusMinus": "N", "Rank": "N",
        "DateFrom": day, "DateTo": day}).get_response())


def fetch(kind: str, season: str, day: str) -> dict:
    for wait in BACKOFF + [None]:
        try:
            return request(kind, season, day)
        except Exception as e:
            if wait is None:
                raise
            print(f"    {day}: {type(e).__name__}: {e} — retry in {wait}s", flush=True)
            time.sleep(wait)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", choices=SEASONS)
    args = ap.parse_args()
    for season in [args.season] if args.season else SEASONS:
        for kind in ("violations", "hustle"):
            OUT[kind].mkdir(parents=True, exist_ok=True)
            f = OUT[kind] / f"{season}.json"
            have = json.loads(f.read_text()) if f.exists() else {}
            todo = [d for d in dates(season) if d not in have]
            print(f"{season} {kind}: {len(have)} dates on disk, {len(todo)} to pull", flush=True)
            for i, day in enumerate(todo):
                rs = fetch(kind, season, day)["resultSets"][0]
                have[day] = {"headers": rs["headers"], "rows": rs["rowSet"]}
                if i % 10 == 0 or i == len(todo) - 1:
                    f.write_text(json.dumps(have))
                    print(f"  {season} {kind} {day}: {len(rs['rowSet'])} teams ({i + 1}/{len(todo)})", flush=True)
                time.sleep(DELAY)
            f.write_text(json.dumps(have))


if __name__ == "__main__":
    main()
