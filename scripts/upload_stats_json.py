"""Post a stats page's JSON to the site (nightly refresh): POST /nba/admin/stats-json.

    python3 scripts/upload_stats_json.py --name shot-value --season 2026-27 --file ../nba-pipeline/analysis/out/site_shot_value.json
    python3 scripts/upload_stats_json.py --name playmaking --season 2026-27 --file ... [--base http://localhost:8001]

Loads INTERNAL_API_KEY from .env. The route serves this copy over the static file shipped with the app.
"""
import argparse
import json
import os
import pathlib
import urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True, choices=["shot-value", "playmaking", "rebounding", "lineups"])
ap.add_argument("--season", required=True); ap.add_argument("--file", required=True)
ap.add_argument("--base", default="https://lbrt.net")
a = ap.parse_args()

env = pathlib.Path(__file__).resolve().parent.parent / ".env"
key = os.environ.get("INTERNAL_API_KEY")
if not key and env.exists():
    for line in env.read_text().splitlines():
        if line.startswith("INTERNAL_API_KEY="):
            key = line.split("=", 1)[1].strip().strip('"')
if not key:
    raise SystemExit("INTERNAL_API_KEY not set and not in .env")
import math
def clean(v):
    """NaN / Infinity aren't JSON: Postgres JSONB rejects them (HTTP 500). Send them as null."""
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, dict):
        return {k: clean(x) for k, x in v.items()}
    if isinstance(v, list):
        return [clean(x) for x in v]
    return v
data = clean(json.load(open(a.file)))
body = json.dumps({"name": a.name, "season": a.season, "data": data}, allow_nan=False).encode()
req = urllib.request.Request(f"{a.base}/nba/admin/stats-json", data=body, method="POST",
                             headers={"Content-Type": "application/json", "X-Internal-Key": key, "User-Agent": "Mozilla/5.0"})
try:
    import certifi, ssl
    ctx = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    ctx = None
with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
    print(r.status, r.read().decode()[:200])
