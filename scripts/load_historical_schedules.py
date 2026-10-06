"""One-time load of finished NBA seasons' schedules into the site, from parquet
files already pulled in the sister repos (nothing is fetched from the NBA).

    python3 scripts/load_historical_schedules.py            # summarize + gap report only
    python3 scripts/load_historical_schedules.py --post     # also POST to lbrt.net
    python3 scripts/load_historical_schedules.py --post --season 2024-25 --base http://localhost:8000

Sources (per season):
  2021-22 → 2025-26 — nba-pipeline/data/raw/schedules/schedule_YYYY_YY.parquet (times + scores)
  2025-26 — same file, re-pulled in full on 2026-09-27

Needs pandas + pyarrow (local only; not a server dependency). Loads INTERNAL_API_KEY from .env.
Re-running is safe: games are upserted by game_id.
"""
import argparse
import os
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import requests

_env = Path(__file__).parent.parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if "=" in _line and not _line.lstrip().startswith("#"):
            k, v = _line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

PROJECTS = Path.home() / "PycharmProjects"
PIPELINE = PROJECTS / "nba-pipeline" / "data" / "raw" / "schedules"
API_TESTS = PROJECTS / "nba_api_tests" / "data" / "schedule"
SEASONS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
STATUS = {1: "scheduled", 2: "live", 3: "final"}
REGULAR_SEASON_GAMES = 1230


def _clean(v):
    return None if pd.isna(v) else v


def from_pipeline(path: Path) -> dict:
    """nba-pipeline format → {game_id: row}. Has tip times and scores."""
    out = {}
    for r in pd.read_parquet(path).to_dict("records"):
        status = STATUS.get(r["game_status"], "scheduled")
        text = (_clean(r.get("game_status_text")) or "").strip()
        tip = _clean(r.get("game_time_utc"))
        out[r["game_id"]] = {
            "game_id": r["game_id"],
            "game_date": r["game_date"],
            "tipoff_utc": None if text.upper() == "TBD" or tip is None else tip.isoformat(),
            "status": status,
            "status_text": text,
            "home_team": _clean(r.get("home_team_tricode")),
            "away_team": _clean(r.get("away_team_tricode")),
            "home_score": int(r["home_score"]) if status == "final" else None,
            "away_score": int(r["away_score"]) if status == "final" else None,
            "label": None,
        }
    return out


def from_api_tests(path: Path) -> dict:
    """nba_api_tests format → {game_id: row}. No tip times or scores."""
    out = {}
    for r in pd.read_parquet(path).to_dict("records"):
        out[r["game_id"]] = {
            "game_id": r["game_id"],
            "game_date": r["game_date"],
            "tipoff_utc": None,
            "status": STATUS.get(r["game_status"], "scheduled"),
            "status_text": (_clean(r.get("game_status_text")) or "").strip(),
            "home_team": _clean(r.get("home_tricode")),
            "away_team": _clean(r.get("away_tricode")),
            "home_score": None,
            "away_score": None,
            "label": _clean(r.get("series_text")),
        }
    return out


def load_season(season: str) -> list[dict]:
    """Every season comes from nba-pipeline's scoreboardv3 pull (2025-26 was re-pulled
    in full on 2026-09-27 so it matches the others)."""
    tag = season.replace("-", "_")
    return list(from_pipeline(PIPELINE / f"schedule_{tag}.parquet").values())


def report(season: str, games: list[dict]) -> None:
    types = Counter(g["game_id"][2:3] for g in games)
    reg = [g for g in games if g["game_id"][2:3] == "2"]
    past_unfinished = [g for g in games if g["status"] != "final"]
    no_time = sum(1 for g in games if not g["tipoff_utc"])
    print(f"\n{season}: {len(games)} games, {min(g['game_date'] for g in games)} → {max(g['game_date'] for g in games)}")
    print(f"  by type (2 regular, 3 all-star, 4 playoffs, 5 play-in, 6 cup final): {dict(sorted(types.items()))}")
    print(f"  regular season: {len(reg)}/{REGULAR_SEASON_GAMES}" + ("" if len(reg) == REGULAR_SEASON_GAMES else "  <-- GAPS"))
    if not types.get("5"):
        print("  play-in: none in source files  <-- GAP")
    print(f"  no tip time: {no_time}   not final: {len(past_unfinished)}")
    for g in sorted(past_unfinished, key=lambda g: g["game_id"]):
        print(f"    {g['game_id']} {g['game_date']} {g['away_team']}@{g['home_team']} status={g['status']} '{g['status_text']}'")
    if len(reg) != REGULAR_SEASON_GAMES:
        by_date = Counter(g["game_date"] for g in reg)
        dates = pd.date_range(min(by_date), max(by_date)).strftime("%Y-%m-%d")
        empty = [d for d in dates if d not in by_date]
        print(f"  dates with no regular-season games ({len(empty)}; includes normal off days like All-Star break):")
        print("    " + ", ".join(empty))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--season", choices=SEASONS, help="only this season (default: all)")
    ap.add_argument("--base", default="https://lbrt.net")
    args = ap.parse_args()

    key = os.environ.get("INTERNAL_API_KEY", "")
    if args.post and not key:
        sys.exit("INTERNAL_API_KEY missing (.env)")

    for season in [args.season] if args.season else SEASONS:
        games = load_season(season)
        report(season, games)
        if args.post:
            r = requests.post(f"{args.base}/nba/admin/schedule/history", json={"season": season, "games": games},
                              headers={"X-Internal-Key": key}, timeout=300)
            print(f"  POST → {r.status_code} {r.text[:300]}")


if __name__ == "__main__":
    main()
