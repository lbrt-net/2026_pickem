import json as _json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from backend.auth import require_admin
from backend.db import get_db

from .models import (
    AdminPickItem, MatchupPayload, ResultPayload, RosterPayload,
    StatGuidePayload, StatLogPayload, WinsPayload,
)
from .schema import game_time_to_lock_time
from .scoring import _recalculate_scores_for_matchup

router = APIRouter(prefix="/admin")


@router.post("/picks/{user_id}")
async def admin_submit_picks(user_id: str, picks: list[AdminPickItem], request: Request):
    require_admin(request)
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    try:
        with conn.cursor() as cur:
            for p in picks:
                cur.execute("""
                    INSERT INTO picks (user_id, matchup_id, winner, games, stat_leader, submitted_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT(user_id, matchup_id) DO UPDATE SET
                        winner       = EXCLUDED.winner,
                        games        = EXCLUDED.games,
                        stat_leader  = EXCLUDED.stat_leader,
                        submitted_at = EXCLUDED.submitted_at
                """, (user_id, p.matchup_id, p.winner, p.games, p.stat_leader, now))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True, "submitted": len(picks)}


@router.post("/matchups/{matchup_id}/wins")
async def update_wins(matchup_id: str, payload: WinsPayload, request: Request):
    require_admin(request)

    if payload.wins_a < 0 or payload.wins_b < 0:
        raise HTTPException(status_code=400, detail="Wins cannot be negative")
    if payload.wins_a > 4 or payload.wins_b > 4:
        raise HTTPException(status_code=400, detail="Max 4 wins per team")
    if payload.wins_a == 4 and payload.wins_b == 4:
        raise HTTPException(status_code=400, detail="Both teams cannot have 4 wins")

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT team_a, team_b FROM matchups WHERE id = %s",
                (matchup_id,)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Matchup not found")

            cur.execute(
                "UPDATE matchups SET wins_a = %s, wins_b = %s WHERE id = %s",
                (payload.wins_a, payload.wins_b, matchup_id)
            )
        conn.commit()
    finally:
        conn.close()

    return {"ok": True}


@router.post("/matchups/{matchup_id}/result")
async def set_result(matchup_id: str, payload: ResultPayload, request: Request):
    require_admin(request)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE matchups
                SET winner_result      = %s,
                    games_result       = %s,
                    stat_leader_result = %s
                WHERE id = %s
            """, (payload.winner, payload.games, payload.stat_leader, matchup_id))

            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Matchup not found")

            # Auto-advance winner (with seed) to dependent next-round matchups
            cur.execute("SELECT team_a, team_b, seed_a, seed_b FROM matchups WHERE id = %s", (matchup_id,))
            m = cur.fetchone()
            winner_seed = m["seed_a"] if payload.winner == m["team_a"] else (m["seed_b"] if payload.winner == m["team_b"] else None)

            cur.execute(
                "UPDATE matchups SET team_a = %s, seed_a = %s WHERE source_matchup_a = %s AND (team_a IS NULL OR team_a = '')",
                (payload.winner, winner_seed, matchup_id)
            )
            cur.execute(
                "UPDATE matchups SET team_b = %s, seed_b = %s WHERE source_matchup_b = %s AND (team_b IS NULL OR team_b = '')",
                (payload.winner, winner_seed, matchup_id)
            )

            _recalculate_scores_for_matchup(cur, matchup_id)
        conn.commit()
    finally:
        conn.close()

    return {"ok": True, "matchup_id": matchup_id}


@router.delete("/matchups/{matchup_id}/result")
async def clear_result(matchup_id: str, request: Request):
    require_admin(request)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE matchups
                SET winner_result      = NULL,
                    games_result       = NULL,
                    stat_leader_result = NULL
                WHERE id = %s
            """, (matchup_id,))

            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Matchup not found")

            # Recalculate scores — this matchup no longer contributes points
            _recalculate_scores_for_matchup(cur, matchup_id)
        conn.commit()
    finally:
        conn.close()

    return {"ok": True, "matchup_id": matchup_id}


@router.post("/matchups/{matchup_id}/stat-log")
async def set_stat_log(matchup_id: str, payload: StatLogPayload, request: Request):
    require_admin(request)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE matchups SET stat_game_log = %s WHERE id = %s",
                (_json.dumps(payload.log), matchup_id)
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Matchup not found")
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


@router.post("/stat-guide")
async def set_stat_guide(payload: StatGuidePayload, request: Request):
    require_admin(request)
    data = _json.dumps(payload.matchups)
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO stat_guide (id, data, updated_at) VALUES (1, %s, %s)
                ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data, updated_at = EXCLUDED.updated_at
            """, (data, now))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True, "updated_at": now}


@router.post("/matchups")
async def upsert_matchup(payload: MatchupPayload, request: Request):
    require_admin(request)

    # Auto-calculate lock_time from game_time (1 hour before, Central)
    lock_time = None
    if payload.game_time:
        lock_time = game_time_to_lock_time(payload.game_time)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO matchups (id, label, team_a, team_b, seed_a, seed_b,
                                    conference, round, stat_label, game_time, lock_time,
                                    home_net_rating_a, home_net_rating_b,
                                    source_matchup_a, source_matchup_b)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(id) DO UPDATE SET
                    label           = EXCLUDED.label,
                    team_a          = EXCLUDED.team_a,
                    team_b          = EXCLUDED.team_b,
                    seed_a          = EXCLUDED.seed_a,
                    seed_b          = EXCLUDED.seed_b,
                    conference      = EXCLUDED.conference,
                    round           = EXCLUDED.round,
                    stat_label      = EXCLUDED.stat_label,
                    game_time       = EXCLUDED.game_time,
                    lock_time       = EXCLUDED.lock_time,
                    home_net_rating_a = EXCLUDED.home_net_rating_a,
                    home_net_rating_b = EXCLUDED.home_net_rating_b,
                    source_matchup_a = EXCLUDED.source_matchup_a,
                    source_matchup_b = EXCLUDED.source_matchup_b
            """, (
                payload.id, payload.label, payload.team_a, payload.team_b,
                payload.seed_a, payload.seed_b, payload.conference,
                payload.round, payload.stat_label, payload.game_time, lock_time,
                payload.home_net_rating_a, payload.home_net_rating_b,
                payload.source_matchup_a, payload.source_matchup_b,
            ))
        conn.commit()
    finally:
        conn.close()

    return {"ok": True, "lock_time": lock_time}


@router.get("/matchups")
async def list_matchups(request: Request):
    require_admin(request)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM matchups ORDER BY round, id")
            rows = cur.fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


@router.post("/rosters")
async def upsert_roster(payload: RosterPayload, request: Request):
    require_admin(request)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO rosters (team_name, players)
                VALUES (%s, %s)
                ON CONFLICT(team_name) DO UPDATE SET players = EXCLUDED.players
            """, (payload.team_name, _json.dumps(payload.players)))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}
