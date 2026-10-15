"""Each veteran's projected 2026-27 per-game stat line (the same pipeline.project run27.py uses), for the player page's
wheel before games. Writes nba-pipeline/data/raw/projection_lines_2026_27.csv; leaves projections_2026_27.csv alone and
checks its fp against it (they must match — same model, same inputs).
    .venv/bin/python scripts/projection_study/lines27.py [--post [--base URL]]   (--post loads them: POST /admin/pool/lines)"""
import contextlib, io, runpy
import pandas as pd
import sys; sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import HERE
S = str(HERE) + "/"
R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
with contextlib.redirect_stdout(io.StringIO()):
    P = runpy.run_path(S + "pipeline.py", run_name="lib")
r27 = pd.read_csv(R + "rosters/2026-27.csv")
cur = pd.read_csv(R + "projections_2026_27.csv", index_col="pid")
KEYS = ["pts", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb", "ast", "stl", "blk", "tov", "blkd", "mpg", "fp"]
rows, drift = [], []
for x in r27.itertuples():
    p = int(x.PLAYER_ID)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            g = P["project"](p, "2026-27")
    except Exception:
        g = None
    if not g:
        continue
    rows.append({"pid": p, **{k: round(float(g[k]), 3) for k in KEYS}})
    if p in cur.index and pd.notna(cur.loc[p, "fp"]) and abs(cur.loc[p, "fp"] - g["fp"]) > 0.05:
        drift.append((x.PLAYER, round(cur.loc[p, "fp"], 2), round(g["fp"], 2)))
pd.DataFrame(rows).to_csv(R + "projection_lines_2026_27.csv", index=False)
print(f"{len(rows)} lines written; fp drift vs projections_2026_27.csv: {len(drift)}", drift[:10])

if "--post" in sys.argv:
    import os, requests
    from pathlib import Path
    env = Path(__file__).resolve().parents[2] / ".env"
    key = next((l.split("=", 1)[1].strip().strip('"') for l in env.read_text().splitlines() if l.startswith("INTERNAL_API_KEY=")), "")
    base = sys.argv[sys.argv.index("--base") + 1] if "--base" in sys.argv else "https://lbrt.net"
    lines = {str(r["pid"]): {k: r[k] for k in KEYS} for r in rows}
    r = requests.post(f"{base}/fantasy/2026_27/admin/pool/lines", json={"season": "2026-27", "lines": lines},
                      headers={"X-Internal-Key": key}, timeout=120)
    print(r.status_code, r.text[:200])
