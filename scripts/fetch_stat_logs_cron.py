"""
fetch_stat_logs_cron.py — Railway cron version of fetch_stat_logs.py.

Runs all 8 matchups, uploads via X-Internal-Key header, no file writing.
Schedule: 0 10 * * * (10am UTC = ~5am CT)

Required env vars:
    BASE_URL          e.g. https://pickem.lbrt.net
    INTERNAL_API_KEY  shared secret configured in Railway
"""

import difflib
import json
import os
import time
import unicodedata
from datetime import date, timedelta

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL        = os.environ["BASE_URL"].rstrip("/")
INTERNAL_API_KEY = os.environ["INTERNAL_API_KEY"]

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

STAT_CONFIG = {
    "pf":             {"source": "traditional", "field": "foulsPersonal"},
    "screen_assists": {"source": "hustle",      "field": "screenAssists"},
    "pts_fb":         {"source": "misc",        "field": "pointsFastBreak"},
    "plus_minus":     {"source": "traditional", "field": "plusMinusPoints"},
    "missed_3s":      {"source": "traditional", "computed": "threePointersAttempted - threePointersMade"},
    "drives":         {"source": "ptdash"},
    "pts":            {"source": "traditional", "field": "points"},
    "stl":            {"source": "traditional", "field": "steals"},
}

BOX_SCORE_ENDPOINTS = {
    "traditional": ("boxscoretraditionalv3", "boxScoreTraditional"),
    "hustle":      ("boxscorehustlev2",      "boxScoreHustle"),
    "misc":        ("boxscoremiscv3",        "boxScoreMisc"),
}

NBA_BASE = "https://stats.nba.com/stats"

NBA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.nba.com/",
    "Accept": "application/json",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def deaccent(name: str) -> str:
    return unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode().lower()


def nba_get(endpoint: str, params: dict) -> dict:
    time.sleep(0.6)
    r = requests.get(f"{NBA_BASE}/{endpoint}", headers=NBA_HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def parse_result_set(data: dict, index: int = 0) -> tuple[list[str], list[list]]:
    rs = data["resultSets"][index]
    return rs["headers"], rs["rowSet"]


def fetch_rosters() -> dict[str, list[str]]:
    r = requests.get(f"{BASE_URL}/rosters", timeout=10)
    r.raise_for_status()
    return r.json()


def match_name(api_name: str, roster_names: list[str], matchup_id: str) -> str | None:
    norm_api = deaccent(api_name)
    norm_roster = [deaccent(n) for n in roster_names]
    matches = difflib.get_close_matches(norm_api, norm_roster, n=1, cutoff=0.7)
    if not matches:
        print(f"  [WARN] {matchup_id}: no roster match for '{api_name}'")
        return None
    return roster_names[norm_roster.index(matches[0])]


def fetch_all_playoff_games(date_to: str) -> dict[str, dict]:
    y, m, d = date_to.split("-")
    date_param = f"{m}/{d}/{y}"
    print(f"Fetching all playoff games through {date_to}...")
    params = {
        "PlayerOrTeam": "T",
        "Season": "2025-26",
        "SeasonType": "Playoffs",
        "LeagueID": "00",
        "Sorter": "DATE",
        "Direction": "ASC",
        "DateTo": date_param,
    }
    data = nba_get("leaguegamelog", params)
    headers, rows = parse_result_set(data)
    idx = {h: i for i, h in enumerate(headers)}

    games: dict[str, dict] = {}
    for row in rows:
        game_id = row[idx["GAME_ID"]]
        if game_id not in games:
            games[game_id] = {"date": row[idx["GAME_DATE"]], "teams": set()}
        games[game_id]["teams"].add(row[idx["TEAM_ABBREVIATION"]])

    print(f"  Found {len(games)} games.")
    return games


def get_series_games(a_abbr: str, b_abbr: str, all_games: dict) -> list[tuple[str, str]]:
    pair = {a_abbr, b_abbr}
    return sorted(
        [(g["date"], gid) for gid, g in all_games.items() if g["teams"] == pair],
        key=lambda x: x[0],
    )


def fetch_stat_boxscore(stat_key: str, game_id: str, team_abbrs: list[str]) -> list[dict]:
    cfg = STAT_CONFIG[stat_key]
    source = cfg["source"]
    url_endpoint, top_key = BOX_SCORE_ENDPOINTS[source]
    params = {"gameId": game_id, "leagueId": "00"}
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
                a_key, b_key = [s.strip() for s in cfg["computed"].split("-")]
                value = stats[a_key] - stats[b_key]
            else:
                value = stats[cfg["field"]]
            results.append({"_api_name": full_name, "value": value})
    return results


def fetch_stat_ptdash(game_date: str, team_abbrs: list[str]) -> list[dict]:
    y, m, d = game_date.split("-")
    date_param = f"{m}/{d}/{y}"
    data = nba_get("leaguedashptstats", {
        "LastNGames": 0, "Month": 0, "OpponentTeamID": 0, "PerMode": "Totals",
        "PlayerOrTeam": "Player", "PtMeasureType": "Drives", "Season": "2025-26",
        "SeasonType": "Playoffs", "College": "", "Conference": "", "Country": "",
        "DateFrom": date_param, "DateTo": date_param, "Division": "", "DraftPick": "",
        "DraftYear": "", "GameScope": "", "Height": "", "LeagueID": "00",
        "Location": "", "Outcome": "", "PORound": "", "PlayerExperience": "",
        "PlayerPosition": "", "SeasonSegment": "", "StarterBench": "", "TeamID": "",
        "VsConference": "", "VsDivision": "", "Weight": "",
    })
    headers, rows = parse_result_set(data)
    idx = {h: i for i, h in enumerate(headers)}
    return [
        {"_api_name": row[idx["PLAYER_NAME"]], "value": row[idx["DRIVES"]]}
        for row in rows if row[idx["TEAM_ABBREVIATION"]] in team_abbrs
    ]


def process_matchup(matchup_id: str, cfg: dict, rosters: dict, all_games: dict) -> dict:
    team_a, team_b, stat = cfg["team_a"], cfg["team_b"], cfg["stat"]
    a_abbr, b_abbr = TEAM_ABBR_MAP[team_a], TEAM_ABBR_MAP[team_b]
    print(f"\n=== {matchup_id}: {team_a} vs {team_b} — stat={stat} ===")

    all_roster = rosters.get(team_a, []) + rosters.get(team_b, [])
    series_games = get_series_games(a_abbr, b_abbr, all_games)
    if not series_games:
        print(f"  [WARN] No playoff games found for {team_a} vs {team_b}")
        return {}

    print(f"  Found {len(series_games)} game(s): {[g[0] for g in series_games]}")
    stat_log = {}
    for game_num, (game_date, game_id) in enumerate(series_games, start=1):
        print(f"  Game {game_num} ({game_date}, id={game_id})...")
        if STAT_CONFIG[stat]["source"] == "ptdash":
            raw = fetch_stat_ptdash(game_date, [a_abbr, b_abbr])
        else:
            raw = fetch_stat_boxscore(stat, game_id, [a_abbr, b_abbr])

        game_entries = []
        for entry in raw:
            roster_name = match_name(entry["_api_name"], all_roster, matchup_id) if all_roster else entry["_api_name"]
            game_entries.append({"name": roster_name or entry["_api_name"], "value": entry["value"]})
        game_entries.sort(key=lambda x: x["value"], reverse=True)
        stat_log[str(game_num)] = game_entries
        print(f"    {len(game_entries)} players, top: {game_entries[0] if game_entries else 'none'}")

    return stat_log


def upload_stat_log(matchup_id: str, stat_log: dict) -> None:
    url = f"{BASE_URL}/admin/matchups/{matchup_id}/stat-log"
    r = requests.post(url, json={"log": stat_log},
                      headers={"Content-Type": "application/json", "X-Internal-Key": INTERNAL_API_KEY},
                      timeout=10)
    if r.ok:
        print(f"  Uploaded {matchup_id}: {r.status_code}")
    else:
        print(f"  FAILED {matchup_id}: {r.status_code} {r.text}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"fetch_stat_logs_cron — date_to={yesterday}, base_url={BASE_URL}")

    try:
        rosters = fetch_rosters()
        print(f"  Got rosters for: {list(rosters.keys())}")
    except Exception as e:
        print(f"  [WARN] Could not fetch rosters: {e}. Name matching will use API names.")
        rosters = {}

    try:
        all_games = fetch_all_playoff_games(yesterday)
    except Exception as e:
        print(f"  [ERROR] Could not fetch playoff game log: {e}")
        return

    for mid, cfg in MATCHUPS.items():
        try:
            stat_log = process_matchup(mid, cfg, rosters, all_games)
        except Exception as e:
            print(f"  [ERROR] {mid}: {e}")
            continue
        if stat_log:
            upload_stat_log(mid, stat_log)

    print("\nDone.")


if __name__ == "__main__":
    main()
