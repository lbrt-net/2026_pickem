import json as _json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from backend.auth import current_user, resolve_user, url_name
from backend.db import get_db

from .models import PickPayload
from .scoring import ROUND_MULTIPLIERS, _pick_series_pts

router = APIRouter()


@router.post("/picks")
async def submit_pick(payload: PickPayload, request: Request):
    user = current_user(request)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT lock_time, team_a, team_b FROM matchups WHERE id = %s",
                (payload.matchup_id,)
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Matchup not found")

            # Block picks on TBD matchups
            if not row["team_a"] or not row["team_b"]:
                raise HTTPException(status_code=403, detail="Teams not yet determined")

            if row["lock_time"]:
                lock_dt = datetime.fromisoformat(row["lock_time"])
                if lock_dt.tzinfo is None:
                    lock_dt = lock_dt.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) >= lock_dt:
                    raise HTTPException(status_code=403, detail="Matchup is locked")

            cur.execute("""
                INSERT INTO picks (user_id, matchup_id, winner, games, stat_leader, submitted_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT(user_id, matchup_id) DO UPDATE SET
                    winner       = EXCLUDED.winner,
                    games        = EXCLUDED.games,
                    stat_leader  = EXCLUDED.stat_leader,
                    submitted_at = EXCLUDED.submitted_at
            """, (
                user["discord_id"],
                payload.matchup_id,
                payload.winner,
                payload.games,
                payload.stat_leader,
                datetime.now(timezone.utc).isoformat(),
            ))
        conn.commit()
    finally:
        conn.close()

    return {"ok": True}


@router.get("/picks/user/{username}")
async def user_picks_by_username(username: str):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            row = resolve_user(cur, username)
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            uid = row["discord_id"]

            now = datetime.now(timezone.utc).isoformat()
            cur.execute("""
                SELECT p.matchup_id, p.winner, p.games, p.stat_leader,
                       (m.lock_time IS NOT NULL AND m.lock_time <= %s) AS locked
                FROM picks p
                JOIN matchups m ON m.id = p.matchup_id
                WHERE p.user_id = %s
            """, (now, uid))
            rows = cur.fetchall()
    finally:
        conn.close()

    picks = []
    status = {}
    for r in rows:
        locked = bool(r["locked"])
        status[r["matchup_id"]] = {
            "has_winner": bool(r["winner"]),
            "has_games": r["games"] is not None,
            "has_stat_leader": bool(r["stat_leader"]),
        }
        picks.append({
            "matchup_id": r["matchup_id"],
            "winner": r["winner"] if locked else None,
            "games": r["games"] if locked else None,
            "stat_leader": r["stat_leader"] if locked else None,
        })

    # `handle` is the canonical URL name — the page redirects if it was reached by an old one.
    return {"username": row["username"], "handle": url_name(row), "picks": picks, "status": status}


@router.get("/picks/user/{username}/status")
async def user_picks_status(username: str):
    """Pick completion flags (no pick content) for all matchups — public."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            row = resolve_user(cur, username)
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            uid = row["discord_id"]

            cur.execute("""
                SELECT matchup_id,
                       winner IS NOT NULL AND winner != '' AS has_winner,
                       games IS NOT NULL AS has_games,
                       stat_leader IS NOT NULL AND stat_leader != '' AS has_stat_leader
                FROM picks
                WHERE user_id = %s
            """, (uid,))
            rows = cur.fetchall()
    finally:
        conn.close()

    return {
        "status": {
            r["matchup_id"]: {
                "has_winner": bool(r["has_winner"]),
                "has_games": bool(r["has_games"]),
                "has_stat_leader": bool(r["has_stat_leader"]),
            }
            for r in rows
        }
    }


@router.get("/picks/me")
async def my_picks(request: Request):
    user = current_user(request)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM picks WHERE user_id = %s",
                (user["discord_id"],)
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return {
        "username": user["username"],
        "handle": url_name(user),
        "is_admin": user.get("is_admin", False),
        "picks": [
            {
                "matchup_id":  row["matchup_id"],
                "winner":      row["winner"],
                "games":       row["games"],
                "stat_leader": row["stat_leader"],
            }
            for row in rows
        ],
    }


@router.get("/stats")
async def stats():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users WHERE NOT is_banned AND NOT is_hidden")
            count = cur.fetchone()[0]
        return {"user_count": count}
    finally:
        conn.close()


@router.get("/scores")
async def leaderboard():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.discord_id, u.username, u.handle, u.avatar_url, COALESCE(s.points, 0) AS points,
                       p.winner, p.games, p.stat_leader,
                       m.winner_result, m.games_result, m.stat_leader_result, m.round
                FROM users u
                LEFT JOIN scores s ON s.user_id = u.discord_id
                LEFT JOIN picks p ON p.user_id = u.discord_id
                LEFT JOIN matchups m ON m.id = p.matchup_id AND m.winner_result IS NOT NULL
                WHERE NOT u.is_hidden
                ORDER BY COALESCE(s.points, 0) DESC, u.username
            """)
            rows = cur.fetchall()
    finally:
        conn.close()

    users = {}
    for row in rows:
        uname = row["discord_id"]  # keyed by id: display names aren't unique
        if uname not in users:
            users[uname] = {
                "username": row["username"],
                "handle": url_name(row),
                "avatar_url": row["avatar_url"],
                "points": row["points"],
                "r1": 0, "r2": 0, "r3": 0, "r4": 0,
            }
        if row["winner_result"]:
            rnd = row["round"] or 1
            pts = _pick_series_pts(
                row["winner"], row["games"], row["stat_leader"],
                row["winner_result"], row["games_result"], row["stat_leader_result"],
            ) * ROUND_MULTIPLIERS.get(rnd, 1)
            users[uname][f"r{rnd}"] = users[uname].get(f"r{rnd}", 0) + pts

    return sorted(users.values(), key=lambda x: (-x["points"], x["username"]))


@router.get("/matchups")
async def public_matchups():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM matchups ORDER BY round, id")
            rows = cur.fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


@router.get("/matchups/aggregate")
async def matchups_aggregate():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    p.matchup_id,
                    p.winner,
                    p.games,
                    p.stat_leader,
                    u.username,
                    u.avatar_url
                FROM picks p
                JOIN users u ON u.discord_id = p.user_id
                JOIN matchups m ON m.id = p.matchup_id
                WHERE m.lock_time IS NOT NULL
                  AND m.lock_time <= %s
            """, (datetime.now(timezone.utc).isoformat(),))
            rows = cur.fetchall()
    finally:
        conn.close()

    result = {}
    for row in rows:
        mid = row["matchup_id"]
        if mid not in result:
            result[mid] = {"picks": [], "stat_picks": {}}

        # Full pick entry for avatar placement / points distribution
        if row["winner"]:
            result[mid]["picks"].append({
                "username":   row["username"],
                "avatar_url": row["avatar_url"],
                "winner":     row["winner"],
                "games":      row["games"],
                "stat_leader": row["stat_leader"],
            })

        # Stat leader picks (case-insensitive key for consistency with scoring)
        if row["stat_leader"]:
            key = row["stat_leader"].strip()
            sp = result[mid]["stat_picks"]
            if key not in sp:
                sp[key] = []
            sp[key].append({
                "username":   row["username"],
                "avatar_url": row["avatar_url"],
            })

    return result


@router.get("/rosters")
async def get_rosters():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT team_name, players FROM rosters")
            rows = cur.fetchall()
    finally:
        conn.close()
    return {row["team_name"]: _json.loads(row["players"]) for row in rows}


@router.get("/stat-guide")
async def get_stat_guide():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT data FROM stat_guide WHERE id = 1")
            row = cur.fetchone()
            return _json.loads(row["data"]) if row else []
    finally:
        conn.close()
