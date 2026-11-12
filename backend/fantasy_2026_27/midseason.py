"""Mid-Season Report on the site (2026-11-12, commissioner): admin only, at /reports/midseason.

Built by scripts/midseason_report/run.py (the report's own pipeline, pulling from this server's public API) after
the nightly job, and on boot if there's no copy yet. Saved in fantasy_recaps as kind 'midseason'. It covers every
week that has started, through week 9; the copy built once week 9 is final is frozen and never rebuilt.
"""
import json
import logging
import os
import subprocess
import sys
import tempfile

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from psycopg2.extras import Json

from backend.auth import require_admin
from backend.db import get_db

log = logging.getLogger(__name__)
router = APIRouter()
RUN = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                   "scripts", "midseason_report", "run.py")
TIME_CAP = 1800  # seconds; a stuck pull fails the build instead of hanging (it normally takes under a minute)


def _saved(cur):
    cur.execute("SELECT data, built_at FROM fantasy_recaps WHERE scenario = 'live' AND kind = 'midseason' AND week = 0")
    return cur.fetchone()


def build(force: bool = False) -> dict:
    """Run the pipeline and save the page, unless the frozen (week 9 final) copy already exists."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            row = _saved(cur)
        if row and row["data"].get("final") and not force:
            return {"skipped": "frozen", "weeks": row["data"].get("weeks")}
        base = os.environ.get("MIDSEASON_BASE") or f"http://127.0.0.1:{os.environ.get('PORT', '8000')}"
        with tempfile.TemporaryDirectory(prefix="midseason-") as work:
            out = os.path.join(work, "midseason.html")
            r = subprocess.run([sys.executable, RUN, "--base", base, "--out", out, "--work", os.path.join(work, "w")],
                               capture_output=True, text=True, timeout=TIME_CAP)
            if r.returncode:
                raise RuntimeError(f"midseason build failed: {r.stderr[-1500:]}")
            meta = json.loads(r.stdout.strip().splitlines()[-1])
            html = open(out).read()
        data = {"html": html, "weeks": meta["weeks"], "final": meta["final"]}
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO fantasy_recaps (scenario, kind, week, data) VALUES ('live', 'midseason', 0, %s)
                           ON CONFLICT (scenario, kind, week) DO UPDATE SET data = EXCLUDED.data, built_at = now()""",
                        (Json(data),))
        conn.commit()
        return {"weeks": meta["weeks"], "final": meta["final"], "kb": len(html) // 1024}
    finally:
        conn.close()


def build_if_missing() -> dict:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            row = _saved(cur)
    finally:
        conn.close()
    return {"skipped": "exists"} if row else build()


@router.get("/reports/midseason", response_class=HTMLResponse)
def page(request: Request):
    try:
        require_admin(request)
    except HTTPException:
        return HTMLResponse("Not found", status_code=404)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            row = _saved(cur)
    finally:
        conn.close()
    if not row:
        return HTMLResponse("Mid-Season Report: not built yet (it builds a few minutes after a deploy).", status_code=503)
    return HTMLResponse(row["data"]["html"], headers={"Cache-Control": "no-store"})


@router.post("/reports/midseason/build")
def rebuild(request: Request, force: bool = False):
    require_admin(request)
    return build(force=force)
