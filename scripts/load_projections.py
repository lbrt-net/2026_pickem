"""Load the 2026-27 draft pool and projections into the site, once, before the season.

    python3 scripts/load_projections.py                                      # summary only
    python3 scripts/load_projections.py --post                               # POST to lbrt.net
    python3 scripts/load_projections.py --post --base http://localhost:8001  # local

Sources (built offline by scripts/projection_study/, rules in PROJECTIONS.md and DISPERSION.md):
  nba-pipeline data/raw/projections_2026_27.csv — every 2026-27 roster player: PROJ AVG (veterans and rookies),
      position, team, flags; blank PROJ AVG = no projection (still draftable)
  nba-pipeline data/raw/proj_week_2026_27.json — weekly-best curve per player (pmax27.py): expected best /
      floor / ceiling for 1..10 games in a fantasy week
The server applies each curve to the 2026-27 schedule when it loads (PROJ MAX + per-week projection) and
stores the result. Re-running replaces this season's "roster" rows; detected and manual rows are kept.
Loads INTERNAL_API_KEY from .env.
"""
import argparse
import json
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

RAW = Path.home() / "PycharmProjects" / "nba-pipeline" / "data" / "raw"
SEASON = "2026-27"


def rows() -> list[dict]:
    b = pd.read_csv(RAW / "projections_2026_27.csv")
    curves = json.loads((RAW / "proj_week_2026_27.json").read_text())
    out = []
    for r in b.to_dict("records"):
        pid = str(int(r["pid"]))
        fp = r.get("fp")
        has = fp is not None and not (isinstance(fp, float) and math.isnan(fp))
        out.append({"player_id": pid, "name": r["name"], "nba_team": r.get("team") if isinstance(r.get("team"), str) else None,
                    "position": r.get("pos") if isinstance(r.get("pos"), str) else None,
                    "proj_avg": round(float(fp), 2) if has else None,
                    "flags": r.get("flags") if isinstance(r.get("flags"), str) else None,
                    "proj_week": curves.get(pid) if has else None})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--base", default="https://lbrt.net")
    args = ap.parse_args()
    rs = rows()
    print(f"{len(rs)} players; PROJ AVG for {sum(r['proj_avg'] is not None for r in rs)}, curves for {sum(r['proj_week'] is not None for r in rs)}")
    if not args.post:
        return
    key = os.environ.get("INTERNAL_API_KEY", "")
    if not key:
        sys.exit("INTERNAL_API_KEY missing (.env)")
    r = requests.post(f"{args.base}/fantasy/2026_27/admin/pool/load", json={"season": SEASON, "source": "roster", "replace": True, "rows": rs},
                      headers={"X-Internal-Key": key}, timeout=300)
    print(r.status_code, r.text[:400])


if __name__ == "__main__":
    main()
