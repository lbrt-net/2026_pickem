import asyncio
from datetime import date
from typing import Optional

from fastapi import APIRouter, Body, Request

from backend.auth import require_admin
from backend.db import get_db

from . import schedule

router = APIRouter()


@router.get("/schedule")
async def get_schedule(season: str = "2026-27", start: Optional[date] = None, end: Optional[date] = None,
                       team: Optional[str] = None, include_missing: bool = False):
    """Games for a season, optionally within [start, end] and/or for one team (tricode)."""
    where, args = ["season = %s"], [season]
    if start:
        where.append("game_date >= %s"); args.append(start)
    if end:
        where.append("game_date <= %s"); args.append(end)
    if team:
        where.append("(home_team = %s OR away_team = %s)"); args += [team.upper(), team.upper()]
    if not include_missing:
        where.append("missing_since IS NULL")
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM nba_games WHERE {' AND '.join(where)} ORDER BY game_date, tipoff_utc NULLS LAST, game_id", args)
            return cur.fetchall()
    finally:
        conn.close()


@router.get("/admin/schedule/status")
async def schedule_status(request: Request):
    """Recent sync runs, recent changes, and game counts by status."""
    require_admin(request)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM nba_sync_runs WHERE kind = 'schedule' ORDER BY id DESC LIMIT 20")
            runs = cur.fetchall()
            cur.execute("SELECT * FROM nba_game_changes WHERE kind <> 'added' ORDER BY id DESC LIMIT 100")
            changes = cur.fetchall()
            cur.execute("""
                SELECT season, game_type, status, (missing_since IS NOT NULL) AS missing,
                       count(*) AS games, count(*) FILTER (WHERE time_tbd) AS time_tbd,
                       count(*) FILTER (WHERE home_team IS NULL OR away_team IS NULL) AS teams_tbd
                FROM nba_games GROUP BY 1, 2, 3, 4 ORDER BY 1, 2, 3, 4
            """)
            counts = cur.fetchall()
    finally:
        conn.close()
    return {"runs": runs, "changes": changes, "counts": counts}


@router.post("/admin/schedule/sync")
async def sync_now(request: Request):
    """Fetch the NBA feed from the server and sync right now."""
    require_admin(request)
    return await asyncio.to_thread(schedule.sync, "manual")


@router.post("/admin/schedule/ingest")
async def ingest(request: Request, payload: dict = Body(...)):
    """Fallback when the server can't reach the NBA feed: a machine that can
    (scripts/pull_nba_schedule.py) fetches it and posts the raw JSON here."""
    require_admin(request)
    return await asyncio.to_thread(schedule.sync, "ingest", payload)
