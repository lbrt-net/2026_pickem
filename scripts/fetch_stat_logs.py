"""
fetch_stat_logs.py — Fetch per-game stat logs from the NBA API and POST to the pickem app.
Uses nba_api library (same as stat_guide.py), filtered by date per game.

Usage:
    python3 scripts/fetch_stat_logs.py
    python3 scripts/fetch_stat_logs.py --matchup w5
    python3 scripts/fetch_stat_logs.py --date-to 05/04/2026
"""

import argparse
import difflib
import json
import os
import time
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import requests

_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

from nba_api.stats.endpoints import (
    LeagueDashPlayerStats,
    LeagueHustleStatsPlayer,
    LeagueDashPlayerPtShot,
)

SEASON = "2025-26"
BASE_URL = "https://pickem.lbrt.net"
OUT_DIR = Path(__file__).parent / "stat_logs"

# ---------------------------------------------------------------------------
# Matchup config — update each round
# ---------------------------------------------------------------------------

MATCHUPS = {
    "f1": {
        "team_a": "San Antonio", "team_b": "New York", "fetch": "trad", "col": "FGM_MINUS_FGMISS",
        "derived": ("FGM_MINUS_FGMISS", lambda df: df["FGM"] - (df["FGA"] - df["FGM"])),
        "tiebreak": "FGA",
    },
}

TEAM_ABBR_MAP = {
    "Detroit":       "DET",
    "Cleveland":     "CLE",
    "Philadelphia":  "PHI",
    "New York":      "NYK",
    "Oklahoma City": "OKC",
    "LA Lakers":     "LAL",
    "San Antonio":   "SAS",
    "Minnesota":     "MIN",
    "Houston":       "HOU",
    "Denver":        "DEN",
    "Boston":        "BOS",
    "Toronto":       "TOR",
    "Orlando":       "ORL",
    "Atlanta":       "ATL",
    "Portland":      "POR",
    "Phoenix":       "PHX",
}

# ---------------------------------------------------------------------------
# Per-game fetchers — same as stat_guide but with date_from/date_to
# ---------------------------------------------------------------------------

def _date_param(game_date: str) -> str:
    y, m, d = game_date.split("-")
    return f"{m}/{d}/{y}"


def fetch_trad(game_date: str) -> "pd.DataFrame":
    dp = _date_param(game_date)
    r = LeagueDashPlayerStats(
        measure_type_detailed_defense="Base",
        per_mode_detailed="Totals",
        season=SEASON, season_type_all_star="Playoffs",
        date_from_nullable=dp, date_to_nullable=dp,
        timeout=60,
    )
    time.sleep(0.7)
    return r.get_data_frames()[0]


def fetch_misc(game_date: str) -> "pd.DataFrame":
    dp = _date_param(game_date)
    r = LeagueDashPlayerStats(
        measure_type_detailed_defense="Misc",
        per_mode_detailed="Totals",
        season=SEASON, season_type_all_star="Playoffs",
        date_from_nullable=dp, date_to_nullable=dp,
        timeout=60,
    )
    time.sleep(0.7)
    return r.get_data_frames()[0]


def fetch_hustle(game_date: str) -> "pd.DataFrame":
    dp = _date_param(game_date)
    for attempt in range(3):
        try:
            r = LeagueHustleStatsPlayer(
                per_mode_time="Totals",
                season=SEASON, season_type_all_star="Playoffs",
                date_from_nullable=dp, date_to_nullable=dp,
                timeout=60,
            )
            time.sleep(0.7)
            return r.get_data_frames()[0]
        except Exception as e:
            if attempt == 2:
                raise
            print(f"  retry {attempt+1}: {e}")
            time.sleep(3)


def fetch_open3(game_date: str) -> "pd.DataFrame":
    import pandas as pd
    dp = _date_param(game_date)
    dfs = []
    for dist in ("4-6 Feet - Open", "6+ Feet - Wide Open"):
        r = LeagueDashPlayerPtShot(
            per_mode_simple="Totals",
            season=SEASON, season_type_all_star="Playoffs",
            close_def_dist_range_nullable=dist,
            shot_dist_range_nullable=">=10.0",
            date_from_nullable=dp, date_to_nullable=dp,
            period_nullable=0, timeout=60,
        )
        df = r.get_data_frames()[0][["PLAYER_ID", "PLAYER_NAME", "PLAYER_LAST_TEAM_ABBREVIATION", "FG3M"]]
        df = df.rename(columns={"PLAYER_LAST_TEAM_ABBREVIATION": "TEAM_ABBREVIATION"})
        dfs.append(df)
        time.sleep(0.7)
    return pd.concat(dfs).groupby(
        ["PLAYER_ID", "PLAYER_NAME", "TEAM_ABBREVIATION"], as_index=False
    )["FG3M"].sum()


FETCHERS = {"trad": fetch_trad, "misc": fetch_misc, "hustle": fetch_hustle, "open3": fetch_open3}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def deaccent(name: str) -> str:
    return unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode().lower()


def match_name(api_name: str, roster_names: list[str], matchup_id: str) -> str:
    norm_api = deaccent(api_name)
    norm_roster = [deaccent(n) for n in roster_names]
    matches = difflib.get_close_matches(norm_api, norm_roster, n=1, cutoff=0.7)
    if not matches:
        print(f"  [WARN] {matchup_id}: no roster match for '{api_name}'")
        return api_name
    return roster_names[norm_roster.index(matches[0])]


def fetch_rosters(base_url: str) -> dict[str, list[str]]:
    r = requests.get(f"{base_url}/rosters", timeout=10)
    r.raise_for_status()
    return r.json()


def fetch_all_playoff_games(date_to: str | None = None) -> dict[str, dict]:
    from nba_api.stats.endpoints import LeagueGameLog
    label = f" through {date_to}" if date_to else ""
    print(f"Fetching playoff game log{label}...")
    kw = {}
    if date_to:
        kw["date_to_nullable"] = date_to
    r = LeagueGameLog(
        player_or_team_abbreviation="T",
        season=SEASON, season_type_all_star="Playoffs",
        timeout=60, **kw,
    )
    time.sleep(0.7)
    df = r.get_data_frames()[0]
    games: dict[str, dict] = {}
    for _, row in df.iterrows():
        gid = row["GAME_ID"]
        if gid not in games:
            games[gid] = {"date": row["GAME_DATE"], "teams": set()}
        games[gid]["teams"].add(row["TEAM_ABBREVIATION"])
    print(f"  Found {len(games)} games.")
    return games


def get_series_games(a_abbr: str, b_abbr: str, all_games: dict) -> list[tuple[str, str]]:
    pair = {a_abbr, b_abbr}
    return sorted(
        [(g["date"], gid) for gid, g in all_games.items() if g["teams"] == pair],
        key=lambda x: x[0],
    )


# ---------------------------------------------------------------------------
# Per-matchup processing
# ---------------------------------------------------------------------------

def process_matchup(matchup_id: str, cfg: dict, rosters: dict, all_games: dict) -> dict:
    team_a, team_b = cfg["team_a"], cfg["team_b"]
    a_abbr, b_abbr = TEAM_ABBR_MAP[team_a], TEAM_ABBR_MAP[team_b]
    fetch_fn = FETCHERS[cfg["fetch"]]
    col = cfg["col"]

    print(f"\n=== {matchup_id}: {team_a} vs {team_b} — {col} ===")

    all_roster = rosters.get(team_a, []) + rosters.get(team_b, [])
    series_games = get_series_games(a_abbr, b_abbr, all_games)
    if not series_games:
        print(f"  [WARN] No games found.")
        return {}

    print(f"  {len(series_games)} game(s): {[g[0] for g in series_games]}")

    stat_log = {}
    for game_num, (game_date, game_id) in enumerate(series_games, start=1):
        print(f"  Game {game_num} ({game_date})...")
        df = fetch_fn(game_date)
        if "derived" in cfg:
            dcol, dfn = cfg["derived"]
            df[dcol] = dfn(df)
        df = df[df["TEAM_ABBREVIATION"].isin([a_abbr, b_abbr])]
        tiebreak = cfg.get("tiebreak")
        sort_cols = [col, tiebreak] if tiebreak else [col]
        df = df.sort_values(sort_cols, ascending=False)
        entries = []
        for _, row in df.iterrows():
            name = match_name(row["PLAYER_NAME"], all_roster, matchup_id) if all_roster else row["PLAYER_NAME"]
            entry = {"name": name, "value": float(row[col] or 0)}
            if tiebreak:
                entry["tb"] = float(row[tiebreak] or 0)
            entries.append(entry)
        entries.sort(key=lambda x: x["value"], reverse=True)
        stat_log[str(game_num)] = entries
        print(f"    {len(entries)} players, top: {entries[0] if entries else 'none'}")

    return stat_log


# ---------------------------------------------------------------------------
# Upload + entry point
# ---------------------------------------------------------------------------

def upload_stat_log(matchup_id: str, stat_log: dict, base_url: str) -> None:
    api_key = os.environ.get("INTERNAL_API_KEY", "")
    r = requests.post(
        f"{base_url}/pickem/2026/admin/matchups/{matchup_id}/stat-log",
        json={"log": stat_log},
        headers={"Content-Type": "application/json", "X-Internal-Key": api_key},
        timeout=10,
    )
    print(f"  {'OK' if r.ok else 'FAILED'} {matchup_id}: {r.status_code}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matchup", help="Only process this matchup (e.g. w5)")
    parser.add_argument("--base-url", default=BASE_URL)
    yesterday = (date.today() - timedelta(days=1)).strftime("%m/%d/%Y")
    parser.add_argument("--date-to", default=yesterday,
                        help="Include games through this date (MM/DD/YYYY, default: yesterday)")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Fetching rosters from {base_url}...")
    try:
        rosters = fetch_rosters(base_url)
        print(f"  Teams: {list(rosters.keys())}")
    except Exception as e:
        print(f"  [WARN] Could not fetch rosters: {e}")
        rosters = {}

    all_games = fetch_all_playoff_games(args.date_to)

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
        upload_stat_log(mid, stat_log, base_url)

    print("\nDone.")


if __name__ == "__main__":
    main()
