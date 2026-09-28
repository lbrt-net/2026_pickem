import asyncio
from datetime import date
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Request

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


@router.post("/admin/schedule/history")
async def load_history(request: Request, body: dict = Body(...)):
    """One-time load of a finished season from local files
    (scripts/load_historical_schedules.py). Body: {"season": "2024-25", "games": [...]}."""
    require_admin(request)
    if not isinstance(body.get("season"), str) or not isinstance(body.get("games"), list):
        raise HTTPException(status_code=400, detail="need season (str) and games (list)")
    return await asyncio.to_thread(schedule.sync, f"history {body['season']}", None, body)


BOX_COLS = ("game_id", "player_id", "season", "player_name", "team", "position", "starter", "dnp_reason", "minutes",
            "fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb", "ast", "stl", "blk", "tov", "pf", "pts", "plus_minus")
MISC_COLS = ("blkd", "pfd")  # optional; only updated when the posted rows include them


@router.post("/admin/boxscores")
async def load_boxscores(request: Request, body: dict = Body(...)):
    """Upsert player box score rows (scripts/load_historical_boxscores.py posts
    them in chunks). Body: {"rows": [{game_id, player_id, season, ...}]}."""
    require_admin(request)
    rows = body.get("rows")
    if not isinstance(rows, list):
        raise HTTPException(status_code=400, detail="need rows (list)")

    def upsert():
        from psycopg2.extras import execute_values
        misc = [c for c in MISC_COLS if any(c in r for r in rows)]
        cols = BOX_COLS + tuple(misc)
        values = [tuple(r.get(c) for c in cols) for r in rows]
        conn = get_db()
        try:
            with conn.cursor() as cur:
                execute_values(cur, f"""
                    INSERT INTO nba_player_games ({', '.join(cols)}) VALUES %s
                    ON CONFLICT (game_id, player_id) DO UPDATE SET
                    {', '.join(f'{c} = EXCLUDED.{c}' for c in cols[2:])}, loaded_at = now()
                """, values, page_size=1000)
            conn.commit()
        finally:
            conn.close()
        return {"ok": True, "rows": len(values), "games": len({r.get("game_id") for r in rows})}

    return await asyncio.to_thread(upsert)
