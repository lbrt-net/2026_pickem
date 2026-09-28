from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from .config import (
    CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SECRET_KEY,
    DISCORD_AUTH_URL, DISCORD_TOKEN_URL, DISCORD_API_URL,
    COOKIE_NAME, COOKIE_MAX_AGE, INTERNAL_API_KEY, ADMIN_DISCORD_IDS,
)
from .db import get_db

signer = URLSafeTimedSerializer(SECRET_KEY)

router = APIRouter()


def make_session_cookie(data: dict) -> str:
    return signer.dumps(data)


def read_session_cookie(request: Request) -> Optional[dict]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        return signer.loads(token, max_age=COOKIE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def current_user(request: Request) -> dict:
    user = read_session_cookie(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_admin(request: Request) -> dict:
    key = request.headers.get("X-Internal-Key")
    if key and INTERNAL_API_KEY and key == INTERNAL_API_KEY:
        return {"is_admin": True, "internal": True}
    user = current_user(request)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def init_schema() -> None:
    """users — the one table shared across every pickem year and product area."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    discord_id  TEXT PRIMARY KEY,
                    username    TEXT NOT NULL,
                    avatar_url  TEXT,
                    is_admin    BOOLEAN NOT NULL DEFAULT FALSE
                )
            """)
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN NOT NULL DEFAULT FALSE")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_banned BOOLEAN NOT NULL DEFAULT FALSE")
        conn.commit()
    finally:
        conn.close()


def upsert_user(discord_id: str, username: str, avatar_url: Optional[str]) -> dict:
    env_admin = discord_id in ADMIN_DISCORD_IDS
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT is_admin FROM users WHERE discord_id = %s", (discord_id,))
            row = cur.fetchone()
            is_admin = env_admin or (row["is_admin"] if row else False)
            cur.execute("""
                INSERT INTO users (discord_id, username, avatar_url, is_admin)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT(discord_id) DO UPDATE SET
                    username   = EXCLUDED.username,
                    avatar_url = EXCLUDED.avatar_url,
                    is_admin   = EXCLUDED.is_admin
            """, (discord_id, username, avatar_url, is_admin))
            cur.execute("SELECT * FROM users WHERE discord_id = %s", (discord_id,))
            full = cur.fetchone()
        conn.commit()
    finally:
        conn.close()
    return dict(full)


def _safe_next(next_path: Optional[str]) -> str:
    """Only same-site relative paths, to avoid an open redirect."""
    if next_path and next_path.startswith("/") and not next_path.startswith("//") and "\\" not in next_path:
        return next_path
    return "/"


def _discord_redirect(next_path: Optional[str]) -> RedirectResponse:
    params = urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
        "state": _safe_next(next_path),
    })
    return RedirectResponse(f"{DISCORD_AUTH_URL}?{params}")


@router.get("/auth/login")
async def login(next: Optional[str] = None):
    return _discord_redirect(next)


@router.get("/auth/discord")
async def auth_discord(next: Optional[str] = None):
    return _discord_redirect(next)


@router.get("/auth/callback")
async def callback(request: Request, code: str = None, error: str = None, state: str = None):
    if error or not code:
        return HTMLResponse(f"<h2>OAuth error: {error or 'no code returned'}</h2>", status_code=400)

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            DISCORD_TOKEN_URL,
            data={
                "client_id":     CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type":    "authorization_code",
                "code":          code,
                "redirect_uri":  REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        user_resp = await client.get(
            DISCORD_API_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_resp.raise_for_status()
        d = user_resp.json()

    discord_id = d["id"]
    username   = d.get("global_name") or d.get("username")
    avatar_url = (
        f"https://cdn.discordapp.com/avatars/{discord_id}/{d['avatar']}.png"
        if d.get("avatar") else None
    )

    user = upsert_user(discord_id, username, avatar_url)

    if user.get("is_banned"):
        return RedirectResponse("/?banned=1", status_code=302)

    response = RedirectResponse(_safe_next(state), status_code=302)
    response.set_cookie(
        key=COOKIE_NAME,
        value=make_session_cookie(user),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=True,
    )
    return response


@router.get("/auth/logout")
async def logout():
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


@router.get("/me")
async def me(request: Request):
    return current_user(request)
