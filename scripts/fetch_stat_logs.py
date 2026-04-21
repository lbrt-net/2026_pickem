"""
fetch_stat_logs.py — Auto-fetch per-game stat logs from the NBA API and
POST them to the local pickem app.

Usage:
    python3 scripts/fetch_stat_logs.py
    python3 scripts/fetch_stat_logs.py --upload --cookie "session=..."
    python3 scripts/fetch_stat_logs.py --matchup w3   # single matchup
"""

import argparse
import difflib
import json
import os
import time
import unicodedata
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MATCHUPS = {
    "e1": {"team_a": "Detroit",       "team_b": "Orlando",      "stat": "pf"},
    "e4": {"team_a": "Cleveland",     "team_b": "Toronto",      "stat": "screen_assists"},
    "e3": {"team_a": "New York",      "team_b": "Atlanta",      "stat": "pts_fb"},
    "e2": {"team_a": "Boston",        "team_b": "Philadelphia", "stat": "plus_minus"},
    "w1": {"team_a": "Oklahoma City", "team_b": "Phoenix",      "stat": "missed_3s"},
    "w4": {"team_a": "LA Lakers",     "team_b": "Houston",      "stat": "drives"},
    "w3": {"team_a": "Denver",        "team_b": "Minnesota",    "stat": "pts"},
    "w2": {"team_a": "San Antonio",   "team_b": "Portland",     "stat": "stl"},
}

# Pickem team name → NBA API TEAM_NAME (for game log lookup)
TEAM_MAP = {
    "Detroit":       "Detroit Pistons",
    "Orlando":       "Orlando Magic",
    "Cleveland":     "Cleveland Cavaliers",
    "Toronto":       "Toronto Raptors",
    "New York":      "New York Knicks",
    "Atlanta":       "Atlanta Hawks",
    "Boston":        "Boston Celtics",
    "Philadelphia":  "Philadelphia 76ers",
    "Oklahoma City": "Oklahoma City Thunder",
    "Phoenix":       "Phoenix Suns",
    "LA Lakers":     "Los Angeles Lakers",
    "Houston":       "Houston Rockets",
    "Denver":        "Denver Nuggets",
    "Minnesota":     "Minnesota Timberwolves",
    "San Antonio":   "San Antonio Spurs",
    "Portland":      "Portland Trail Blazers",
}

# stat key → how to fetch from NBA API
STAT_CONFIG = {
    "pf":             {"endpoint": "leaguedashplayerstats", "measure": "Base",    "column": "PF"},
    "screen_assists": {"endpoint": "leaguedashplayerstats", "measure": "Hustle",  "column": "SCREEN_ASSISTS"},
    "pts_fb":         {"endpoint": "leaguedashplayerstats", "measure": "Scoring", "column": "PTS_FB"},
    "plus_minus":     {"endpoint": "leaguedashplayerstats", "measure": "Base",    "column": "PLUS_MINUS"},
    "missed_3s":      {"endpoint": "leaguedashplayerstats", "measure": "Base",    "column": None,  "computed": "FG3A-FG3M"},
    "drives":         {"endpoint": "leaguedashptstats",     "measure": None,      "column": "DRIVES", "pt_measure": "Drives"},
    "pts":            {"endpoint": "leaguedashplayerstats", "measure": "Base",    "column": "PTS"},
    "stl":            {"endpoint": "leaguedashplayerstats", "measure": "Base",    "column": "STL"},
}

NBA_BASE = "https://stats.nba.com/stats"
LOCAL_BASE = "http://localhost:8000"
OUT_DIR = Path(__file__).parent / "stat_logs"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.nba.com/",
    "Accept": "application/json",
}

COMMON_PARAMS = {
    "Season": "2025-26",
    "SeasonType": "Playoffs",
    "LeagueID": "00",
    "PerMode": "Totals",
    "PlusMinus": "N",
    "PaceAdjust": "N",
    "Rank": "N",
    "LastNGames": 0,
    "Month": 0,
    "OpponentTeamID": 0,
    "Period": 0,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def deaccent(name: str) -> str:
    """Normalize name: strip diacritics, lowercase."""
    return unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode().lower()


def nba_get(endpoint: str, params: dict) -> dict:
    """GET from stats.nba.com with a small delay to avoid rate-limiting."""
    time.sleep(0.6)
    url = f"{NBA_BASE}/{endpoint}"
    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def parse_result_set(data: dict, index: int = 0) -> tuple[list[str], list[list]]:
    rs = data["resultSets"][index]
    return rs["headers"], rs["rowSet"]


# ---------------------------------------------------------------------------
# Roster fetching + name matching
# ---------------------------------------------------------------------------

def fetch_rosters() -> dict[str, list[str]]:
    """Return {pickem_team_name: [player_name, ...]} from the local API."""
    r = requests.get(f"{LOCAL_BASE}/rosters", timeout=10)
    r.raise_for_status()
    data = r.json()
    # API returns list of {team, name} objects
    rosters: dict[str, list[str]] = {}
    for entry in data:
        team = entry.get("team", "")
        name = entry.get("name", "")
        rosters.setdefault(team, []).append(name)
    return rosters


def match_name(api_name: str, roster_names: list[str], matchup_id: str) -> str | None:
    """Fuzzy-match an API player name to a roster name. Returns original roster name."""
    norm_api = deaccent(api_name)
    norm_roster = [deaccent(n) for n in roster_names]
    matches = difflib.get_close_matches(norm_api, norm_roster, n=1, cutoff=0.7)
    if not matches:
        print(f"  [WARN] {matchup_id}: no roster match for '{api_name}' (normalized: '{norm_api}')")
        return None
    idx = norm_roster.index(matches[0])
    return roster_names[idx]


# ---------------------------------------------------------------------------
# Game log: find game dates for a matchup
# ---------------------------------------------------------------------------

def fetch_playoff_game_dates(team_a_full: str, team_b_full: str) -> list[str]:
    """
    Return sorted list of dates (YYYY-MM-DD) where team_a and team_b both played.
    Uses leaguegamelog (team-level) to find head-to-head playoff games.
    """
    data = nba_get("leaguegamelog", {
        "PlayerOrTeam": "T",
        "Season": "2025-26",
        "SeasonType": "Playoffs",
        "LeagueID": "00",
        "Sorter": "DATE",
        "Direction": "ASC",
    })
    headers, rows = parse_result_set(data)
    idx = {h: i for i, h in enumerate(headers)}

    # Build {date: set_of_team_names}
    date_teams: dict[str, set] = {}
    for row in rows:
        date = row[idx["GAME_DATE"]]
        team = row[idx["TEAM_NAME"]]
        date_teams.setdefault(date, set()).add(team)

    # Find dates where both teams appear (same game)
    dates = sorted(
        d for d, teams in date_teams.items()
        if team_a_full in teams and team_b_full in teams
    )
    return dates


# ---------------------------------------------------------------------------
# Stat fetching per game date
# ---------------------------------------------------------------------------

def fetch_stat_for_date(stat_key: str, date: str, team_names_full: list[str]) -> list[dict]:
    """
    Fetch per-player stat for a given game date, filtered to the two teams.
    Returns [{"name": roster_name, "value": N}, ...] sorted descending.
    (name matching happens later)
    """
    cfg = STAT_CONFIG[stat_key]
    endpoint = cfg["endpoint"]

    params = {
        **COMMON_PARAMS,
        "DateFrom": date,
        "DateTo": date,
    }

    if endpoint == "leaguedashplayerstats":
        params["MeasureType"] = cfg["measure"]
    elif endpoint == "leaguedashptstats":
        params["PtMeasureType"] = cfg["pt_measure"]

    data = nba_get(endpoint, params)
    headers, rows = parse_result_set(data)
    idx = {h: i for i, h in enumerate(headers)}

    results = []
    for row in rows:
        team = row[idx["TEAM_NAME"]] if "TEAM_NAME" in idx else row[idx.get("TEAM_ABBREVIATION", 0)]
        # Filter to the two teams in this matchup
        if team not in team_names_full:
            continue

        player_name = row[idx["PLAYER_NAME"]]

        if cfg.get("computed") == "FG3A-FG3M":
            value = row[idx["FG3A"]] - row[idx["FG3M"]]
        else:
            value = row[idx[cfg["column"]]]

        results.append({"_api_name": player_name, "value": value})

    return results


# ---------------------------------------------------------------------------
# Main logic per matchup
# ---------------------------------------------------------------------------

def process_matchup(matchup_id: str, cfg: dict, rosters: dict) -> dict:
    """
    Fetch game-by-game stat log for one matchup.
    Returns {game_number_str: [{"name": roster_name, "value": N}, ...]}
    """
    team_a = cfg["team_a"]
    team_b = cfg["team_b"]
    stat = cfg["stat"]

    team_a_full = TEAM_MAP[team_a]
    team_b_full = TEAM_MAP[team_b]

    print(f"\n=== {matchup_id}: {team_a} vs {team_b} — stat={stat} ===")

    # Roster names for both teams combined
    roster_a = rosters.get(team_a, [])
    roster_b = rosters.get(team_b, [])
    all_roster = roster_a + roster_b
    if not all_roster:
        print(f"  [WARN] No roster entries found for {team_a} or {team_b}")

    # Find game dates
    dates = fetch_playoff_game_dates(team_a_full, team_b_full)
    if not dates:
        print(f"  [WARN] No playoff games found between {team_a_full} and {team_b_full}")
        return {}

    print(f"  Found {len(dates)} game(s): {dates}")

    stat_log = {}
    for game_num, date in enumerate(dates, start=1):
        print(f"  Game {game_num} ({date})...")
        raw = fetch_stat_for_date(stat, date, [team_a_full, team_b_full])

        # Name matching
        game_entries = []
        for entry in raw:
            api_name = entry["_api_name"]
            roster_name = match_name(api_name, all_roster, matchup_id) if all_roster else api_name
            if roster_name is None:
                roster_name = api_name  # fall back to API name with warning already printed
            game_entries.append({"name": roster_name, "value": entry["value"]})

        # Sort descending by value
        game_entries.sort(key=lambda x: x["value"], reverse=True)
        stat_log[str(game_num)] = game_entries
        print(f"    {len(game_entries)} players, top: {game_entries[0] if game_entries else 'none'}")

    return stat_log


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def upload_stat_log(matchup_id: str, stat_log: dict, cookie: str) -> None:
    url = f"{LOCAL_BASE}/admin/matchups/{matchup_id}/stat-log"
    headers = {"Content-Type": "application/json", "Cookie": cookie}
    r = requests.post(url, json=stat_log, headers=headers, timeout=10)
    if r.ok:
        print(f"  Uploaded {matchup_id}: {r.status_code}")
    else:
        print(f"  FAILED {matchup_id}: {r.status_code} {r.text}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fetch NBA playoff stat logs")
    parser.add_argument("--matchup", help="Only process this matchup ID (e.g. w3)")
    parser.add_argument("--upload", action="store_true", help="POST results to local API")
    parser.add_argument("--cookie", default="", help='Session cookie string, e.g. "session=..."')
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Fetch rosters once
    print("Fetching rosters from local API...")
    try:
        rosters = fetch_rosters()
        print(f"  Got rosters for: {list(rosters.keys())}")
    except Exception as e:
        print(f"  [WARN] Could not fetch rosters: {e}. Name matching will use API names.")
        rosters = {}

    matchup_ids = [args.matchup] if args.matchup else list(MATCHUPS.keys())

    for mid in matchup_ids:
        if mid not in MATCHUPS:
            print(f"Unknown matchup: {mid}")
            continue

        try:
            stat_log = process_matchup(mid, MATCHUPS[mid], rosters)
        except Exception as e:
            print(f"  [ERROR] {mid}: {e}")
            continue

        if not stat_log:
            continue

        # Save to file
        out_path = OUT_DIR / f"{mid}.json"
        with open(out_path, "w") as f:
            json.dump(stat_log, f, indent=2)
        print(f"  Saved → {out_path}")

        # Print curl command
        print(f"\n  curl -s -X POST http://localhost:8000/admin/matchups/{mid}/stat-log \\")
        print(f'    -H "Content-Type: application/json" \\')
        print(f'    -H "Cookie: YOUR_SESSION_COOKIE" \\')
        print(f"    -d @scripts/stat_logs/{mid}.json")

        # Optionally upload
        if args.upload:
            if not args.cookie:
                print("  [WARN] --upload requires --cookie")
            else:
                upload_stat_log(mid, stat_log, args.cookie)

    print("\nDone.")


if __name__ == "__main__":
    main()
