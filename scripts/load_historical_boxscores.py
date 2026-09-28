"""One-time load of finished seasons' player box scores into the site, from
parquet already pulled in the sister repos (nothing is fetched from the NBA).

    python3 scripts/load_historical_boxscores.py            # coverage report only
    python3 scripts/load_historical_boxscores.py --post     # also POST to lbrt.net (chunked)
    python3 scripts/load_historical_boxscores.py --post --season 2025-26 --base http://localhost:8000

Sources (all boxscoretraditionalv3, full game):
  nba-pipeline data/box_scores/trad_box_scores_YYYY_YY.parquet (pull_box_score_traditional.py output),
  falling back to data/raw/box_scores_traditional/ for seasons it hasn't been run on

The report lists final games in the schedule that have no box score in any source —
that list (and only that list) is what still needs pulling from the NBA.
Needs pandas + pyarrow locally. Loads INTERNAL_API_KEY from .env. Re-running is safe (upsert).
"""
import argparse
import math
import os
import sys
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
PIPELINE_BOX = PROJECTS / "nba-pipeline" / "data" / "raw" / "box_scores_traditional"
PIPELINE_BOX_CURRENT = PROJECTS / "nba-pipeline" / "data" / "box_scores"
PIPELINE_SCHED = PROJECTS / "nba-pipeline" / "data" / "raw" / "schedules"
API_TESTS_BOX = PROJECTS / "nba_api_tests" / "data" / "boxscore" / "traditional"
SEASONS = ["2022-23", "2023-24", "2024-25", "2025-26"]
CHUNK = 5000
STATS = ["fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb", "ast", "stl", "blk", "tov", "pf", "pts", "plus_minus"]
API_TESTS_RENAME = {
    "gameId": "game_id", "personId": "player_id", "teamTricode": "team_tricode",
    "fieldGoalsMade": "fgm", "fieldGoalsAttempted": "fga", "threePointersMade": "fg3m", "threePointersAttempted": "fg3a",
    "freeThrowsMade": "ftm", "freeThrowsAttempted": "fta", "reboundsOffensive": "oreb", "reboundsDefensive": "dreb",
    "assists": "ast", "steals": "stl", "blocks": "blk", "turnovers": "tov", "foulsPersonal": "pf", "points": "pts",
    "plusMinusPoints": "plus_minus",
}


def minutes(v) -> float:
    """'29:54' / 'PT29M54.00S' / number → decimal minutes."""
    if v is None or (isinstance(v, float) and math.isnan(v)) or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v)
    if s.startswith("PT"):
        m, _, sec = s[2:].rstrip("S").partition("M")
        return round(float(m or 0) + float(sec or 0) / 60, 2)
    m, _, sec = s.partition(":")
    return round(float(m or 0) + float(sec or 0) / 60, 2)


def to_rows(df: pd.DataFrame, season: str) -> list[dict]:
    rows = []
    for r in df.to_dict("records"):
        pos = (r.get("position") or "").strip() or None
        dnp = (r.get("comment") or "").strip() or None
        rows.append({
            "game_id": str(r["game_id"]),
            "player_id": str(int(r["player_id"])),
            "season": season,
            "player_name": r["player_name"],
            "team": r["team_tricode"],
            "position": pos,
            "starter": pos is not None,
            "dnp_reason": dnp,
            "minutes": minutes(r.get("minutes")),
            **{k: int(r[k]) if not pd.isna(r[k]) else 0 for k in STATS},
        })
    return rows


def load_season(season: str) -> pd.DataFrame:
    """nba-pipeline's box score file for the season: the incremental puller's output
    (data/box_scores/) when it exists, else the older raw pull."""
    tag = season.replace("-", "_")
    for folder in (PIPELINE_BOX_CURRENT, PIPELINE_BOX):
        f = folder / f"trad_box_scores_{tag}.parquet"
        if f.exists():
            return pd.read_parquet(f).drop_duplicates(subset=["game_id", "player_id"], keep="last")
    raise FileNotFoundError(f"no box scores for {season}")


def report(season: str, df: pd.DataFrame) -> None:
    tag = season.replace("-", "_")
    games = set(df["game_id"].astype(str))
    print(f"\n{season}: {len(df)} player rows, {len(games)} games")
    sched_file = PIPELINE_SCHED / f"schedule_{tag}.parquet"
    if sched_file.exists():
        s = pd.read_parquet(sched_file)
        final = s[(s["game_status"] == 3) & (s["game_id"].str[2].isin(["2", "4", "5", "6"]))]
        missing = final[~final["game_id"].isin(games)].sort_values("game_id")
        print(f"  final games in schedule: {len(final)}   missing box scores: {len(missing)}")
        for r in missing.to_dict("records")[:60]:
            print(f"    {r['game_id']} {r['game_date']} {r['away_team_tricode']}@{r['home_team_tricode']}")
        if len(missing) > 60:
            print(f"    … {len(missing) - 60} more")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--season", choices=SEASONS)
    ap.add_argument("--base", default="https://lbrt.net")
    args = ap.parse_args()
    key = os.environ.get("INTERNAL_API_KEY", "")
    if args.post and not key:
        sys.exit("INTERNAL_API_KEY missing (.env)")

    for season in [args.season] if args.season else SEASONS:
        df = load_season(season)
        report(season, df)
        if not args.post:
            continue
        rows = to_rows(df, season)
        for i in range(0, len(rows), CHUNK):
            r = requests.post(f"{args.base}/nba/admin/boxscores", json={"rows": rows[i:i + CHUNK]},
                              headers={"X-Internal-Key": key}, timeout=300)
            print(f"  POST rows {i}–{i + len(rows[i:i + CHUNK])}: {r.status_code} {r.text[:200]}")
            if r.status_code != 200:
                sys.exit("stopping on error")


if __name__ == "__main__":
    main()
