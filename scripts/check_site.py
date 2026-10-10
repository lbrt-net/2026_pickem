"""After a deploy (or any time): is the live site answering, fast, with sane data?

    python3 scripts/check_site.py            # https://lbrt.net, both leagues
    python3 scripts/check_site.py --base http://localhost:8000

1. Every main page's data answers, and quickly (the draft room under 1 s — last season's 25 s lag can't sneak back).
2. The check-up (GET /admin/health): projections and history built for the current scoring rules, pool and rosters
   sane, box scores keeping up, no stuck waivers.
Exits non-zero if anything fails. Reads INTERNAL_API_KEY from .env for the check-up.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PAGES = [  # (path, slowest acceptable seconds)
    ("/draft", 1.0), ("/players", 3.0), ("/nba-teams", 2.0), ("/teams", 2.0), ("/results", 3.0),
    ("/transactions", 2.0), ("/players/actual?window=season", 4.0), ("/players/board?view=proj", 3.0),
    ("/scoring", 1.0), ("/league/settings", 1.0), ("/league/members", 1.0),
]


def key():
    if os.environ.get("INTERNAL_API_KEY"):
        return os.environ["INTERNAL_API_KEY"]
    env = Path(__file__).resolve().parent.parent / ".env"
    for line in env.read_text().splitlines() if env.exists() else []:
        if line.startswith("INTERNAL_API_KEY="):
            return line.split("=", 1)[1].strip()
    return ""


def get(base, path, headers=None):
    req = urllib.request.Request(base + path, headers={"User-Agent": "Mozilla/5.0", **(headers or {})})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            return r.status, body, time.time() - t
    except urllib.error.HTTPError as e:
        return e.code, e.read(), time.time() - t
    except Exception as e:  # noqa: BLE001 — a dead site is a failed check, not a crash
        return 0, str(e).encode(), time.time() - t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://lbrt.net")
    args = ap.parse_args()
    api = args.base.rstrip("/") + "/fantasy/2026_27"
    failed = 0
    for scenario in ("live", "replay"):
        print(f"\n== {scenario}")
        for path, limit in PAGES:
            sep = "&" if "?" in path else "?"
            status, body, secs = get(api, f"{path}{sep}scenario={scenario}")
            is_json = body[:1] in (b"{", b"[")
            ok = status == 200 and is_json and secs <= limit
            failed += not ok
            why = "" if ok else (f"HTTP {status}" if status != 200 else "not data (page served instead?)" if not is_json else f"slow (limit {limit}s)")
            print(f"  {'OK' if ok else '!!'}  {path:<32} {secs:5.2f}s  {why}")
        status, body, _ = get(api, f"/admin/health?scenario={scenario}", {"X-Internal-Key": key()})
        if status != 200 or body[:1] != b"{":
            print(f"  !!  check-up unavailable (HTTP {status})")
            failed += 1
            continue
        for c in json.loads(body)["checks"]:
            failed += not c["ok"]
            print(f"  {'OK' if c['ok'] else '!!'}  {c['check']}" + (f" — {c['detail']}" if c["detail"] and not c["ok"] else ""))
    print("\nall good" if not failed else f"\n{failed} problem(s)")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
