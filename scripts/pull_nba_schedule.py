"""Fetch the NBA full-season schedule feed from this machine and hand it to the
site — the fallback for when the server itself can't reach cdn.nba.com.

    python3 scripts/pull_nba_schedule.py                 # fetch + summarize only
    python3 scripts/pull_nba_schedule.py --post          # fetch + POST to lbrt.net
    python3 scripts/pull_nba_schedule.py --post --base http://localhost:8000

Loads INTERNAL_API_KEY from .env. Same feed and headers as nba_api_tests/update_schedule.py.
"""
import argparse
import os
import sys
import time
from collections import Counter
from pathlib import Path

import requests

_env = Path(__file__).parent.parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if "=" in _line and not _line.lstrip().startswith("#"):
            k, v = _line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

FEED_URL = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"
FEED_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.nba.com/",
}
RETRY_WAITS = [30, 60, 120, 120]


def fetch():
    for i, wait in enumerate([0] + RETRY_WAITS):
        if wait:
            print(f"  retry {i}/{len(RETRY_WAITS)} in {wait}s")
            time.sleep(wait)
        try:
            r = requests.get(FEED_URL, headers=FEED_HEADERS, timeout=30)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            print(f"  fetch failed: {e}")
    sys.exit("giving up")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--base", default="https://lbrt.net")
    args = ap.parse_args()

    data = fetch()
    sched = data["leagueSchedule"]
    games = [g for d in sched["gameDates"] for g in d["games"]]
    types = Counter(g["gameId"][2:3] for g in games)
    tbd_time = sum(1 for g in games if (g.get("gameStatusText") or "").strip().upper() == "TBD")
    tbd_team = sum(1 for g in games if not (g.get("homeTeam") or {}).get("teamId") or not (g.get("awayTeam") or {}).get("teamId"))
    dates = sorted(g["gameDateEst"][:10] for g in games if g.get("gameDateEst"))
    print(f"season {sched.get('seasonYear')}: {len(games)} games, {dates[0] if dates else '?'} → {dates[-1] if dates else '?'}")
    print(f"  by type (1 pre, 2 reg, 3 ASG, 4 playoffs, 5 play-in, 6 cup final): {dict(types)}")
    print(f"  time TBD: {tbd_time}   team TBD: {tbd_team}")

    if args.post:
        key = os.environ.get("INTERNAL_API_KEY", "")
        if not key:
            sys.exit("INTERNAL_API_KEY missing (.env)")
        r = requests.post(f"{args.base}/nba/admin/schedule/ingest", json=data,
                          headers={"X-Internal-Key": key}, timeout=120)
        print(r.status_code, r.text[:500])


if __name__ == "__main__":
    main()
