"""
fetch_stat_logs.py — Auto-fetch per-game stat logs from the NBA API and
POST them to the pickem app.

Usage:
    python3 scripts/fetch_stat_logs.py --cookie "session=..."
    python3 scripts/fetch_stat_logs.py --matchup w3 --cookie "session=..."
    python3 scripts/fetch_stat_logs.py --matchup w3   # print curl only, no upload
    python3 scripts/fetch_stat_logs.py --base-url http://localhost:8000 --cookie "session=..."
"""

import argparse
import difflib
import json
import time
import unicodedata
from datetime import date, timedelta
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

# Pickem team name → NBA API TEAM_NAME (for leaguegamelog team-level lookup)
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

# Pickem team name → NBA API TEAM_ABBREVIATION (for box score team filtering)
TEAM_ABBR_MAP = {
    "Detroit":       "DET",
    "Orlando":       "ORL",
    "Cleveland":     "CLE",
    "Toronto":       "TOR",
    "New York":      "NYK",
    "Atlanta":       "ATL",
    "Boston":        "BOS",
    "Philadelphia":  "PHI",
    "Oklahoma City": "OKC",
    "Phoenix":       "PHX",
    "LA Lakers":     "LAL",
    "Houston":       "HOU",
    "Denver":        "DEN",
    "Minnesota":     "MIN",
    "San Antonio":   "SAS",
    "Portland":      "POR",
}

# stat key → how to fetch from NBA API
#   source: "traditional" | "hustle" | "misc" | "ptdash"
#   field: key inside player statistics dict (for box score sources)
#   computed: expression string (for traditional only)
STAT_CONFIG = {
    "pf":             {"source": "traditional", "field": "foulsPersonal"},
    "screen_assists": {"source": "hustle",      "field": "screenAssists"},
    "pts_fb":         {"source": "misc",        "field": "pointsFastBreak"},
    "plus_minus":     {"source": "traditional", "field": "plusMinusPoints"},
    "missed_3s":      {"source": "traditional", "computed": "threePointersAttempted - threePointersMade"},
    "drives":         {"source": "ptdash"},   # no per-game box score endpoint; uses date-based fallback
    "pts":            {"source": "traditional", "field": "points"},
    "stl":            {"source": "traditional", "field": "steals"},
}

# Box score endpoint → (url_endpoint, top_key)
BOX_SCORE_ENDPOINTS = {
    "traditional": ("boxscoretraditionalv3", "boxScoreTraditional"),
    "hustle":      ("boxscorehustlev2",      "boxScoreHustle"),
    "misc":        ("boxscoremiscv3",        "boxScoreMisc"),
}

# Update this when your session cookie expires (copy from browser DevTools → Application → Cookies)
SESSION_COOKIE = "session=.eJxljcsOwiAUBf-FtSlQnu3PkCuXKklLCY9ujP8uie7czpzMeRGM1Z8FXUSyksUYpoSU3CjDZsY1uZFeQ0lwhKHDfg-lDQYXNCiul33QZ2u5rpR6TNOvBjlP_jzod1fpX5dqFtiCFpAb5ELNQlsxbygRrGabsFNOj3EUqwM8YiJrKz28P2TKNWo.aeFgqg.Q6EaOWWHRSHKsAZWk831z-Ikfzc"

NBA_BASE = "https://stats.nba.com/stats"
OUT_DIR = Path(__file__).parent / "stat_logs"

NBA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.nba.com/",
    "Accept": "application/json",
}

COMMON_DASH_PARAMS = {
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
    return unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode().lower()


def nba_get(endpoint: str, params: dict) -> dict:
    time.sleep(0.6)
    url = f"{NBA_BASE}/{endpoint}"
    r = requests.get(url, headers=NBA_HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def parse_result_set(data: dict, index: int = 0) -> tuple[list[str], list[list]]:
    rs = data["resultSets"][index]
    return rs["headers"], rs["rowSet"]


# ---------------------------------------------------------------------------
# Roster fetching + name matching
# ---------------------------------------------------------------------------

def fetch_rosters(base_url: str) -> dict[str, list[str]]:
    r = requests.get(f"{base_url}/rosters", timeout=10)
    r.raise_for_status()
    return r.json()  # {team_name: [players]}


def match_name(api_name: str, roster_names: list[str], matchup_id: str) -> str | None:
    norm_api = deaccent(api_name)
    norm_roster = [deaccent(n) for n in roster_names]
    matches = difflib.get_close_matches(norm_api, norm_roster, n=1, cutoff=0.7)
    if not matches:
        print(f"  [WARN] {matchup_id}: no roster match for '{api_name}'")
        return None
    return roster_names[norm_roster.index(matches[0])]


# ---------------------------------------------------------------------------
# Game log: fetch all playoff games once, keyed by game_id
# ---------------------------------------------------------------------------

def fetch_all_playoff_games(date_to: str | None = None) -> dict[str, dict]:
    """
    Fetch the full leaguegamelog for the 2025-26 playoffs once.
    Returns {game_id: {"date": str, "teams": set[abbr]}}.
    """
    label = f" through {date_to}" if date_to else ""
    print(f"Fetching all playoff games from NBA API (one call){label}...")
    params = {
        "PlayerOrTeam": "T",
        "Season": "2025-26",
        "SeasonType": "Playoffs",
        "LeagueID": "00",
        "Sorter": "DATE",
        "Direction": "ASC",
    }
    if date_to:
        params["DateTo"] = date_to
    data = nba_get("leaguegamelog", params)
    headers, rows = parse_result_set(data)
    idx = {h: i for i, h in enumerate(headers)}

    games: dict[str, dict] = {}
    for row in rows:
        game_id = row[idx["GAME_ID"]]
        if game_id not in games:
            games[game_id] = {"date": row[idx["GAME_DATE"]], "teams": set()}
        games[game_id]["teams"].add(row[idx["TEAM_ABBREVIATION"]])

    print(f"  Found {len(games)} games across all playoff matchups.")
    return games


def get_series_games(team_a_abbr: str, team_b_abbr: str, all_games: dict[str, dict]) -> list[tuple[str, str]]:
    """
    Return [(date, game_id), ...] sorted by date for the given series.
    """
    pair = {team_a_abbr, team_b_abbr}
    return sorted(
        [(g["date"], gid) for gid, g in all_games.items() if g["teams"] == pair],
        key=lambda x: x[0],
    )


# ---------------------------------------------------------------------------
# Stat fetching per game
# ---------------------------------------------------------------------------

def fetch_stat_boxscore(stat_key: str, game_id: str, team_abbrs: list[str]) -> list[dict]:
    """
    Fetch per-player stat from a box score endpoint using game_id.
    Returns [{"_api_name": name, "value": N}, ...].
    """
    cfg = STAT_CONFIG[stat_key]
    source = cfg["source"]
    url_endpoint, top_key = BOX_SCORE_ENDPOINTS[source]

    params = {"gameId": game_id, "leagueId": "00"}
    # hustle v2 uses different param casing
    if source == "hustle":
        params = {"GameID": game_id}

    data = nba_get(url_endpoint, params)
    box = data[top_key]

    results = []
    for team_key in ("homeTeam", "awayTeam"):
        team = box[team_key]
        if team["teamTricode"] not in team_abbrs:
            continue
        for p in team["players"]:
            full_name = f"{p['firstName']} {p['familyName']}"
            stats = p["statistics"]
            if "computed" in cfg:
                # e.g. "threePointersAttempted - threePointersMade"
                a_key, b_key = [s.strip() for s in cfg["computed"].split("-")]
                value = stats[a_key] - stats[b_key]
            else:
                value = stats[cfg["field"]]
            results.append({"_api_name": full_name, "value": value})

    return results


def fetch_stat_ptdash(game_date: str, team_abbrs: list[str]) -> list[dict]:
    """
    Fetch player-level drives for a single game date.
    Uses PlayerOrTeam=Player (full word, not 'P') which is what the NBA API expects.
    """
    y, m, d = game_date.split("-")
    date_param = f"{m}/{d}/{y}"
    data = nba_get("leaguedashptstats", {
        "LastNGames": 0,
        "Month": 0,
        "OpponentTeamID": 0,
        "PerMode": "Totals",
        "PlayerOrTeam": "Player",
        "PtMeasureType": "Drives",
        "Season": "2025-26",
        "SeasonType": "Playoffs",
        "College": "",
        "Conference": "",
        "Country": "",
        "DateFrom": date_param,
        "DateTo": date_param,
        "Division": "",
        "DraftPick": "",
        "DraftYear": "",
        "GameScope": "",
        "Height": "",
        "LeagueID": "00",
        "Location": "",
        "Outcome": "",
        "PORound": "",
        "PlayerExperience": "",
        "PlayerPosition": "",
        "SeasonSegment": "",
        "StarterBench": "",
        "TeamID": "",
        "VsConference": "",
        "VsDivision": "",
        "Weight": "",
    })
    headers, rows = parse_result_set(data)
    idx = {h: i for i, h in enumerate(headers)}

    results = []
    for row in rows:
        if row[idx["TEAM_ABBREVIATION"]] not in team_abbrs:
            continue
        results.append({
            "_api_name": row[idx["PLAYER_NAME"]],
            "value": row[idx["DRIVES"]],
        })
    return results


# ---------------------------------------------------------------------------
# Main logic per matchup
# ---------------------------------------------------------------------------

def process_matchup(matchup_id: str, cfg: dict, rosters: dict, all_games: dict) -> dict:
    team_a = cfg["team_a"]
    team_b = cfg["team_b"]
    stat = cfg["stat"]
    a_abbr = TEAM_ABBR_MAP[team_a]
    b_abbr = TEAM_ABBR_MAP[team_b]

    print(f"\n=== {matchup_id}: {team_a} vs {team_b} — stat={stat} ===")

    roster_a = rosters.get(team_a, [])
    roster_b = rosters.get(team_b, [])
    all_roster = roster_a + roster_b
    if not all_roster:
        print(f"  [WARN] No roster entries found for {team_a} or {team_b}")

    series_games = get_series_games(a_abbr, b_abbr, all_games)
    if not series_games:
        print(f"  [WARN] No playoff games found for {team_a} vs {team_b}")
        return {}

    print(f"  Found {len(series_games)} game(s): {[g[0] for g in series_games]}")

    stat_cfg = STAT_CONFIG[stat]
    stat_log = {}

    for game_num, (game_date, game_id) in enumerate(series_games, start=1):
        print(f"  Game {game_num} ({game_date}, id={game_id})...")

        if stat_cfg["source"] == "ptdash":
            raw = fetch_stat_ptdash(game_date, [a_abbr, b_abbr])
        else:
            raw = fetch_stat_boxscore(stat, game_id, [a_abbr, b_abbr])

        game_entries = []
        for entry in raw:
            api_name = entry["_api_name"]
            roster_name = match_name(api_name, all_roster, matchup_id) if all_roster else api_name
            if roster_name is None:
                roster_name = api_name
            game_entries.append({"name": roster_name, "value": entry["value"]})

        game_entries.sort(key=lambda x: x["value"], reverse=True)
        stat_log[str(game_num)] = game_entries
        print(f"    {len(game_entries)} players, top: {game_entries[0] if game_entries else 'none'}")

    return stat_log


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def upload_stat_log(matchup_id: str, stat_log: dict, cookie: str, base_url: str) -> None:
    url = f"{base_url}/admin/matchups/{matchup_id}/stat-log"
    headers = {"Content-Type": "application/json", "Cookie": cookie}
    r = requests.post(url, json={"log": stat_log}, headers=headers, timeout=10)
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
    parser.add_argument("--cookie", default=SESSION_COOKIE, help='Session cookie string, e.g. "session=..."')
    parser.add_argument("--base-url", default="https://pickem.lbrt.net",
                        help="API base URL (default: https://pickem.lbrt.net)")
    yesterday = (date.today() - timedelta(days=1)).strftime("%m/%d/%Y")
    parser.add_argument("--date-to", default=yesterday,
                        help="Only include games on or before this date (MM/DD/YYYY, default: yesterday)")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Fetching rosters from {base_url}...")
    try:
        rosters = fetch_rosters(base_url)
        print(f"  Got rosters for: {list(rosters.keys())}")
    except Exception as e:
        print(f"  [WARN] Could not fetch rosters: {e}. Name matching will use API names.")
        rosters = {}

    try:
        all_games = fetch_all_playoff_games(args.date_to)
    except Exception as e:
        print(f"  [ERROR] Could not fetch playoff game log: {e}")
        return

    matchup_ids = [args.matchup] if args.matchup else list(MATCHUPS.keys())

    for mid in matchup_ids:
        if mid not in MATCHUPS:
            print(f"Unknown matchup: {mid}")
            continue

        try:
            stat_log = process_matchup(mid, MATCHUPS[mid], rosters, all_games)
        except Exception as e:
            print(f"  [ERROR] {mid}: {e}")
            continue

        if not stat_log:
            continue

        out_path = OUT_DIR / f"{mid}.json"
        with open(out_path, "w") as f:
            json.dump(stat_log, f, indent=2)
        print(f"  Saved → {out_path}")

        if args.cookie:
            upload_stat_log(mid, stat_log, args.cookie, base_url)
        else:
            print(f"\n  curl -s -X POST {base_url}/admin/matchups/{mid}/stat-log \\")
            print(f'    -H "Content-Type: application/json" \\')
            print(f'    -H "Cookie: YOUR_SESSION_COOKIE" \\')
            print(f'    -d \'{{"log": $(cat scripts/stat_logs/{mid}.json)}}\'')

    print("\nDone.")
    print("\nSmoke test:")
    print(f'  python3 scripts/fetch_stat_logs.py --matchup e1 --cookie "session=<value>"')


if __name__ == "__main__":
    main()
