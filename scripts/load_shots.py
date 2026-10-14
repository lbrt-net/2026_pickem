"""Load shot locations (every field goal attempt) into the site's nba_shots table, for the player page's shot chart.

    python3 scripts/load_shots.py --season 2025-26                 # pull only, print counts
    python3 scripts/load_shots.py --post                           # '23–'26, POST to lbrt.net
    python3 scripts/load_shots.py --post --season 2025-26 --team CLE --base http://localhost:8000

One ShotChartDetail call per team-season (player_id 0 = everyone on that team), so 30 × 4 = 120 calls for '23–'26.
Uses nba_api (system python3 has it) with a pause between calls. Loads INTERNAL_API_KEY from .env. Re-running is
safe (upsert on game + event).
"""
import argparse, os, sys, time
from pathlib import Path

import requests

SEASONS = ["2022-23", "2023-24", "2024-25", "2025-26"]
CHUNK = 5000


def load_env():
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def pull(team_id: int, season: str) -> list:
    from nba_api.stats.endpoints import ShotChartDetail
    for attempt in range(6):
        try:
            df = ShotChartDetail(team_id=team_id, player_id=0, season_nullable=season,
                                 season_type_all_star="Regular Season", context_measure_simple="FGA",
                                 timeout=90).get_data_frames()[0]
            return df
        except Exception as e:
            print(f"  retry {attempt + 1}: {e}", flush=True)
            time.sleep([30, 60, 120, 120, 120, 120][attempt])
    raise RuntimeError(f"gave up on team {team_id} {season}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", action="append")
    ap.add_argument("--team", action="append", help="tricode(s); default all 30")
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--base", default="https://lbrt.net")
    a = ap.parse_args()
    load_env()
    key = os.environ.get("INTERNAL_API_KEY", "")
    if a.post and not key:
        sys.exit("INTERNAL_API_KEY missing (.env)")
    from nba_api.stats.static import teams
    tri = {t["id"]: t["abbreviation"] for t in teams.get_teams()}
    wanted = [i for i, ab in tri.items() if not a.team or ab in a.team]
    for season in a.season or SEASONS:
        total = 0
        for tid in wanted:
            df = pull(tid, season)
            rows = [[r.GAME_ID, int(r.GAME_EVENT_ID), season, str(r.PLAYER_ID), tri.get(r.TEAM_ID), int(r.LOC_X), int(r.LOC_Y),
                     bool(r.SHOT_MADE_FLAG)] for r in df.itertuples()]
            total += len(rows)
            print(f"{season} {tri[tid]}: {len(rows)} shots", flush=True)
            if a.post:
                for i in range(0, len(rows), CHUNK):
                    r = requests.post(f"{a.base}/nba/admin/shots", json={"rows": rows[i:i + CHUNK]},
                                      headers={"X-Internal-Key": key}, timeout=120)
                    r.raise_for_status()
            time.sleep(2)
        print(f"{season}: {total} shots", flush=True)
