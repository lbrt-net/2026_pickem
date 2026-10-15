"""Upload a season's shot charts (SVGs drawn by nba-pipeline models/shot_chart_batch.py) to the site.

    python3 scripts/upload_shot_charts.py --season 2025-26 --dir ../nba-pipeline/data/processed/2025_26/shot_charts
    python3 scripts/upload_shot_charts.py --season 2025-26 --dir ... --base http://localhost:8001

Loads INTERNAL_API_KEY from .env (same as stat_guide.py). Replaces the season's whole set: POST /nba/admin/shot-charts.
"""
import argparse
import json
import os
import pathlib
import urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("--season", required=True)
ap.add_argument("--dir", required=True, help="folder of <player_id>.svg files")
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

charts = [{"player_id": f.stem, "svg": f.read_text()} for f in sorted(pathlib.Path(a.dir).glob("*.svg"))]
body = json.dumps({"season": a.season, "charts": charts}).encode()
print(f"{len(charts)} charts, {len(body) // 1024 // 1024} MB -> {a.base}/nba/admin/shot-charts")
req = urllib.request.Request(f"{a.base}/nba/admin/shot-charts", data=body, method="POST",
                             headers={"Content-Type": "application/json", "X-Internal-Key": key, "User-Agent": "Mozilla/5.0"})
try:
    import certifi, ssl
    ctx = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    ctx = None
with urllib.request.urlopen(req, timeout=300, context=ctx) as r:
    print(r.status, r.read().decode()[:200])
