"""Site-wide admin: user moderation. Not scoped to any pickem year or product area."""

from fastapi import APIRouter, HTTPException, Request

from .auth import require_admin
from .config import ADMIN_DISCORD_IDS
from .db import get_db

router = APIRouter(prefix="/admin")


@router.get("/users")
async def admin_list_users(request: Request):
    require_admin(request)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # NOTE: joins pickem_2026's `scores` table for display convenience.
            # Once a second scored product area exists, this needs to decide
            # which season/module's points to show here.
            cur.execute("""
                SELECT u.discord_id, u.username, u.avatar_url,
                       u.is_admin, u.is_hidden, u.is_banned,
                       COALESCE(s.points, 0) AS points
                FROM users u
                LEFT JOIN scores s ON s.user_id = u.discord_id
                ORDER BY points DESC, u.username
            """)
            rows = [
                {**dict(r), "is_owner": r["discord_id"] in ADMIN_DISCORD_IDS}
                for r in cur.fetchall()
            ]
    finally:
        conn.close()
    return rows


def _toggle_user_flag(discord_id: str, field: str, request: Request):
    require_admin(request)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE users SET {field} = NOT {field} WHERE discord_id = %s RETURNING {field}",
                (discord_id,)
            )
            row = cur.fetchone()
        conn.commit()
    finally:
        conn.close()
    return {field: row[field]}


@router.post("/users/{discord_id}/admin")
async def admin_toggle_admin(discord_id: str, request: Request):
    if discord_id in ADMIN_DISCORD_IDS:
        raise HTTPException(status_code=403, detail="Owner status is controlled by server config only")
    return _toggle_user_flag(discord_id, "is_admin", request)


@router.post("/users/{discord_id}/hidden")
async def admin_toggle_hidden(discord_id: str, request: Request):
    return _toggle_user_flag(discord_id, "is_hidden", request)


@router.post("/users/{discord_id}/ban")
async def admin_toggle_ban(discord_id: str, request: Request):
    if discord_id in ADMIN_DISCORD_IDS:
        raise HTTPException(status_code=403, detail="Cannot ban a site owner")
    return _toggle_user_flag(discord_id, "is_banned", request)
