import asyncio
from datetime import date
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Request

from backend.auth import require_admin
from backend.db import get_db

from . import injuries, schedule

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


@router.get("/injuries")
async def get_injuries(player_id: Optional[str] = None):
    """Who's injured right now (present state only; ESPN feed, synced every 30 minutes). A player not listed is
    healthy. ?player_id= → just that player ([] if healthy). Rows: {player_id (null if unmatched), name, team,
    status (Out / Day-To-Day / ...), short (OUT / GTD), injury, return_date, comment, reported_at, synced_at}."""
    def run():
        conn = get_db()
        try:
            with conn.cursor() as cur:
                return injuries.current(cur, player_id)
        finally:
            conn.close()
    return await asyncio.to_thread(run)


@router.post("/admin/injuries/sync")
async def sync_injuries(request: Request):
    require_admin(request)
    return await asyncio.to_thread(injuries.sync, "manual")


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


TEAM_STAT_COLS = ("game_id", "team", "season", "game_date", "opp_pts_fb", "opp_pts_paint", "opp_tov", "dreb", "opp_dreb", "shot_clock_forced")


@router.post("/admin/team-games")
async def load_team_games(request: Request, body: dict = Body(...)):
    """Upsert team defensive lines per game (scripts/load_team_clutch.py). Body: {"rows": [{game_id, team, season,
    game_date, opp_pts_fb, opp_pts_paint, opp_tov, dreb, opp_dreb, shot_clock_forced}]}."""
    require_admin(request)
    rows = body.get("rows")
    if not isinstance(rows, list):
        raise HTTPException(status_code=400, detail="need rows (list)")

    def upsert():
        from psycopg2.extras import execute_values
        conn = get_db()
        try:
            with conn.cursor() as cur:
                execute_values(cur, f"""
                    INSERT INTO nba_team_game_stats ({', '.join(TEAM_STAT_COLS)}) VALUES %s
                    ON CONFLICT (game_id, team) DO UPDATE SET
                    {', '.join(f'{c} = EXCLUDED.{c}' for c in TEAM_STAT_COLS[2:])}, loaded_at = now()
                """, [tuple(r.get(c) for c in TEAM_STAT_COLS) for r in rows], page_size=1000)
            conn.commit()
        finally:
            conn.close()
        return {"ok": True, "rows": len(rows)}

    return await asyncio.to_thread(upsert)


@router.post("/admin/clutch")
async def load_clutch(request: Request, body: dict = Body(...)):
    """Set clutch-time points per player-game. Body: {"season": "2025-26", "reset": true, "rows": [{player_id,
    game_date: "YYYY-MM-DD", pts}]}. A player plays at most once a day, so (player, date) finds the game. reset=true
    first sets every played game of the season to 0 (loaded, no clutch points) — send it with the first chunk."""
    require_admin(request)
    season, rows = body.get("season"), body.get("rows")
    if not isinstance(season, str) or not isinstance(rows, list):
        raise HTTPException(status_code=400, detail="need season (str) and rows (list)")

    def apply():
        from psycopg2.extras import execute_values
        conn = get_db()
        try:
            with conn.cursor() as cur:
                if body.get("reset"):
                    cur.execute("UPDATE nba_player_games SET clutch_pts = 0 WHERE season = %s AND minutes > 0", (season,))
                execute_values(cur, """
                    UPDATE nba_player_games pg SET clutch_pts = v.pts
                    FROM (VALUES %s) AS v(player_id, game_date, pts), nba_games g
                    WHERE g.game_id = pg.game_id AND pg.player_id = v.player_id AND g.game_date = v.game_date::date
                """, [(str(r["player_id"]), r["game_date"], int(r["pts"])) for r in rows], page_size=1000)
                n = cur.rowcount
            conn.commit()
        finally:
            conn.close()
        return {"ok": True, "rows": len(rows), "updated": n}

    return await asyncio.to_thread(apply)
