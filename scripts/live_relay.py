"""Backup live pull, run on the commissioner's machine (2026-10-22: the NBA's live feed started refusing our Railway
server). Leave it running on game nights:

    python3 scripts/live_relay.py              # steps in only when the site's own pull is failing
    python3 scripts/live_relay.py --always     # push every live game every 30 s regardless

Every 30 seconds it asks the site (GET /nba/admin/live-health). If the site's last live pull failed (or it's been
quiet for 2+ minutes while games are on), it downloads each live game's box score and play-by-play itself and hands
them to the site (POST /nba/admin/live-push), which loads them with its usual parser. Healthy site = it does nothing.
Reads INTERNAL_API_KEY from .env. Ctrl-C to stop.
"""
import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

SITE = "https://lbrt.net"
FEEDS = ["https://cdn.nba.com/static/json/liveData", "https://nba-prod-us-east-1-mediaops-stats.s3.amazonaws.com/NBA/liveData"]
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
           "Accept": "application/json", "Referer": "https://www.nba.com/", "Origin": "https://www.nba.com"}


def key() -> str:
    env = Path(__file__).resolve().parents[1] / ".env"
    for line in env.read_text().splitlines():
        if line.startswith("INTERNAL_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    sys.exit("INTERNAL_API_KEY missing from .env")


def feed(path: str):
    for base in FEEDS:
        try:
            r = requests.get(f"{base}/{path}", headers=HEADERS, timeout=20)
            if r.ok:
                return r.json()
        except (requests.RequestException, ValueError):
            pass
    return None


def site_failing(h: dict) -> bool:
    if h.get("failing_since"):
        return True
    ok = h.get("last_ok")
    if h.get("games_on") and ok:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(ok)).total_seconds() > 120
    return bool(h.get("games_on")) and not ok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--always", action="store_true", help="push every live game whether or not the site is failing")
    ap.add_argument("--site", default=SITE)
    a = ap.parse_args()
    hdr = {"X-Internal-Key": key()}
    print(f"live relay → {a.site} ({'always' if a.always else 'only when the site fails'}); Ctrl-C to stop", flush=True)
    while True:
        try:
            h = requests.get(f"{a.site}/nba/admin/live-health", headers=hdr, timeout=30).json()
            games = h.get("games_on") or []
            if games and (a.always or site_failing(h)):
                for gid in games:
                    box = feed(f"boxscore/boxscore_{gid}.json")
                    if not box:
                        print(f"{datetime.now():%H:%M:%S} {gid}: no box score yet", flush=True)
                        continue
                    pbp = feed(f"playbyplay/playbyplay_{gid}.json")
                    r = requests.post(f"{a.site}/nba/admin/live-push", headers=hdr, json={"game_id": gid, "box": box, "pbp": pbp}, timeout=60)
                    print(f"{datetime.now():%H:%M:%S} pushed {gid}: {r.status_code} {r.text[:120]}", flush=True)
            else:
                print(f"{datetime.now():%H:%M:%S} site healthy ({len(games)} game(s) on) — standing by", flush=True)
        except Exception as e:  # noqa: BLE001 — keep relaying through hiccups
            print(f"{datetime.now():%H:%M:%S} error: {e}", flush=True)
        time.sleep(30)


if __name__ == "__main__":
    main()
