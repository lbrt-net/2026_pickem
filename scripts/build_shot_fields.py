"""Build the player page's shot chart fields and load them into the site (nba_shot_fields).

    python3 scripts/build_shot_fields.py --post                                # every pool player, 2026-27 (the page shows only this)
    python3 scripts/build_shot_fields.py --season 2025-26 --player 1628378     # check the method on an old season, print only

The nightly job (backend/nba/nightly.py) builds 2026-27 on the server from the stored play-by-play; this script is
for checking the method locally on the pipeline's pulls. Method = nba-pipeline/analysis/shot_chart.py (TEAMMATE_EFFECT.md "Shot charts"), cell for cell:
- where: his shots smoothed at 1.5 ft, twos and threes separately with the kernel mass that falls across the line
  corrected, a 1.2-ft finish blur; the layers are the levels holding 95 / 80 / 60 / 40 / 20% of his shots.
- how well: his points per shot minus the league's from the same spot (both 4 ft, twos / threes apart), shrunk toward
  even where he has few shots nearby (n / (n + 6)), faded outside the area holding 90% of his shots, 1.2-ft finish blur.
Stored every 0.5 ft: lvl (0 = outside the 95% area, 1..5) and d = points vs league x100 where lvl > 0.

Runs locally (numpy / pandas; system python3) on the play-by-play pulls in nba_api_tests / nba-pipeline. Meant to
join the nightly job once it exists. Loads INTERNAL_API_KEY from .env. Re-running is safe (upsert).
"""
import argparse, json, os, subprocess, sys, time
from pathlib import Path

import numpy as np
import requests

PIPE = Path("/Users/allan/PycharmProjects/nba-pipeline")
# The page shows this season only. 2026-27 play-by-play lands here once the nightly pull exists; older seasons stay
# runnable for checking the method (--season 2025-26 --player ...) but are never posted.
PBP = {"2026-27": "/Users/allan/PycharmProjects/nba_api_tests/data/playbyplayv3/2026_27_regular_season/*.parquet",
       "2025-26": "/Users/allan/PycharmProjects/nba_api_tests/data/playbyplayv3/2025_26_regular_season/*.parquet"}
LIVE = "2026-27"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.nba import shot_fields  # noqa: E402  (the one copy of the method; the nightly job uses it too)


def load_env():
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def pool_ids(base):
    rows = json.loads(subprocess.run(["curl", "-s", f"{base}/fantasy/2026_27/players?scenario=live"], capture_output=True, text=True).stdout)
    return {p["id"] for p in rows if p.get("in_pool") and p["id"].isdigit()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", action="append")
    ap.add_argument("--player", action="append")
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--base", default="https://lbrt.net")
    a = ap.parse_args()
    load_env()
    key = os.environ.get("INTERNAL_API_KEY", "")
    if a.post and not key:
        sys.exit("INTERNAL_API_KEY missing (.env)")
    sys.path.insert(0, str(PIPE / "process"))
    import possession_rules as pr
    ids = set(a.player) if a.player else pool_ids(a.base)
    if a.post and any(s != LIVE for s in (a.season or [LIVE])):
        sys.exit("the page shows 2026-27 only: post that season, check older ones without --post")
    for season in a.season or [LIVE]:
        t0 = time.time()
        pbp = pr.load(PBP[season]); pbp = pbp[pbp.game_id.str.startswith("002")]
        shots = pbp[pbp.action_type.isin(["Made Shot", "Missed Shot"])].copy()
        shots["pts"] = np.where(shots.action_type == "Made Shot", shots.shot_value, 0); shots["three"] = shots.shot_value == 3
        if "shot_distance" in shots:
            shots = shots[shots.shot_distance.fillna(0) <= shot_fields.HEAVE_FT]
        rows_ = [{"player_id": str(r.person_id), "x": r.x_legacy, "y": r.y_legacy, "three": bool(r.three), "pts": r.pts}
                 for r in shots.itertuples()]
        print(f"{season}: {len(rows_)} league shots loaded in {time.time() - t0:.0f}s", flush=True)
        fields = shot_fields.build_all(rows_)
        rows = [{"player_id": pid, "season": season, "data": f} for pid, f in fields.items() if pid in ids]
        for i in range(0, len(rows), 25) if a.post else []:
            requests.post(f"{a.base}/nba/admin/shot-fields", json={"rows": rows[i:i + 25]}, headers={"X-Internal-Key": key},
                          timeout=120).raise_for_status()
        if rows and not a.post:
            r = rows[0]["data"]; print("sample", rows[0]["player_id"], r["n"], "shots,", sum(c != "0" for c in r["lvl"]), "lit cells")
        print(f"{season}: done in {time.time() - t0:.0f}s", flush=True)
