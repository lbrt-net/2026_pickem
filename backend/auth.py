import re
import time
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


# Logged-in devices (account menu → Devices): every login is a row in `sessions` (device, how, when, last active);
# the cookie carries its id ("sid"). Logging a device out marks its row ended → that cookie stops working on its next
# request. Checks are cached for a minute so pages don't hit the database on every call; "last active" is written at
# most every 5 minutes. Cookies from before this (no sid) still work until they expire, but aren't listed.
_SID_CACHE: dict = {}       # sid -> (alive, checked_at)
_SEEN: dict = {}            # sid -> last time we wrote last_seen
SID_CHECK_S, SEEN_EVERY_S = 60, 300


def start_session(user: dict, request: Request, method: str) -> str:
    """A new login on this device: its sessions row and the cookie value that points at it."""
    import secrets
    sid = secrets.token_urlsafe(16)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO sessions (sid, discord_id, method, user_agent) VALUES (%s, %s, %s, %s)",
                        (sid, user["discord_id"], method, (request.headers.get("user-agent") or "")[:400]))
        conn.commit()
    finally:
        conn.close()
    _SID_CACHE[sid] = (True, time.time())
    return make_session_cookie({**user, "sid": sid})


def _sid_alive(sid: str) -> bool:
    now = time.time()
    hit = _SID_CACHE.get(sid)
    if hit and now - hit[1] < SID_CHECK_S:
        alive = hit[0]
    else:
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT ended_at IS NULL AS alive FROM sessions WHERE sid = %s", (sid,))
                row = cur.fetchone()
                alive = bool(row and row["alive"])
                if alive and now - _SEEN.get(sid, 0) > SEEN_EVERY_S:
                    cur.execute("UPDATE sessions SET last_seen = now() WHERE sid = %s", (sid,))
                    _SEEN[sid] = now
            conn.commit()
        finally:
            conn.close()
        if len(_SID_CACHE) > 5000:
            _SID_CACHE.clear()
        _SID_CACHE[sid] = (alive, now)
    return alive


def read_session_cookie(request: Request) -> Optional[dict]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        data = signer.loads(token, max_age=COOKIE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    if data.get("sid") and not _sid_alive(data["sid"]):
        return None  # this device was logged out
    return data


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
            # `username` = Discord display name (shown on the site, not unique).
            # `handle` = the real Discord username (unique) — used in URLs.
            # NULL until the person logs in again after this column was added.
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS handle TEXT")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_handle ON users (handle) WHERE handle IS NOT NULL")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    sid        TEXT PRIMARY KEY,
                    discord_id TEXT NOT NULL REFERENCES users(discord_id),
                    method     TEXT NOT NULL,                 -- discord / phone
                    user_agent TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    last_seen  TIMESTAMPTZ NOT NULL DEFAULT now(),
                    ended_at   TIMESTAMPTZ
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS sessions_user ON sessions (discord_id)")
            # What the page itself saw (an iPad in desktop mode claims to be a Mac; Firefox / Chrome on iOS claim to be
            # Safari) — set by POST /auth/sessions/device, preferred over guessing from the user agent.
            cur.execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS device_hint TEXT")
            # Every handle a person has had, so links using an old one still resolve.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_handle_history (
                    handle     TEXT PRIMARY KEY,
                    discord_id TEXT NOT NULL REFERENCES users(discord_id),
                    last_seen  TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
        conn.commit()
    finally:
        conn.close()


def upsert_user(discord_id: str, username: str, avatar_url: Optional[str], handle: Optional[str] = None) -> dict:
    env_admin = discord_id in ADMIN_DISCORD_IDS
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT is_admin FROM users WHERE discord_id = %s", (discord_id,))
            row = cur.fetchone()
            is_admin = env_admin or (row["is_admin"] if row else False)
            if handle:
                # Discord handles can be released and re-taken: whoever logs in with
                # it now owns it; a stale holder loses it until their next login.
                cur.execute("UPDATE users SET handle = NULL WHERE handle = %s AND discord_id <> %s", (handle, discord_id))
            cur.execute("""
                INSERT INTO users (discord_id, username, avatar_url, is_admin, handle)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT(discord_id) DO UPDATE SET
                    username   = EXCLUDED.username,
                    avatar_url = EXCLUDED.avatar_url,
                    is_admin   = EXCLUDED.is_admin,
                    handle     = COALESCE(EXCLUDED.handle, users.handle)
            """, (discord_id, username, avatar_url, is_admin, handle))
            if handle:
                cur.execute("""
                    INSERT INTO user_handle_history (handle, discord_id) VALUES (%s, %s)
                    ON CONFLICT (handle) DO UPDATE SET discord_id = EXCLUDED.discord_id, last_seen = now()
                """, (handle, discord_id))
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
    username   = d.get("global_name") or d.get("username")  # display name
    handle     = (d.get("username") or "").lower() or None     # real, unique Discord username
    avatar_url = (
        f"https://cdn.discordapp.com/avatars/{discord_id}/{d['avatar']}.png"
        if d.get("avatar") else None
    )

    user = upsert_user(discord_id, username, avatar_url, handle)

    if user.get("is_banned"):
        return RedirectResponse("/?banned=1", status_code=302)

    response = RedirectResponse(_safe_next(state), status_code=302)
    response.set_cookie(
        key=COOKIE_NAME,
        value=start_session(user, request, "discord"),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=True,
    )
    return response


def device_label(ua: str) -> str:
    """'iPhone · Safari' from a browser's user agent (good enough to tell your devices apart)."""
    ua = ua or ""
    device = ("iPhone" if "iPhone" in ua else "iPad" if "iPad" in ua else "Android" if "Android" in ua else
              "Mac" if "Macintosh" in ua else "Windows" if "Windows" in ua else "Linux" if "Linux" in ua else "Device")
    browser = ("Edge" if ("Edg/" in ua or "EdgiOS" in ua or "EdgA" in ua) else "Discord" if "Discord" in ua else
               "Firefox" if ("Firefox" in ua or "FxiOS" in ua) else "Opera" if ("OPR/" in ua or "OPT/" in ua) else
               "Samsung Internet" if "SamsungBrowser" in ua else "Chrome" if ("Chrome" in ua or "CriOS" in ua) else
               "Safari" if "Safari" in ua else "Browser")
    return f"{device} · {browser}"


HINT_OK = re.compile(r"^[A-Za-z][A-Za-z ]{1,20} · [A-Za-z][A-Za-z ]{1,20}$")


@router.get("/auth/sessions")
def list_sessions(request: Request):
    """Your logged-in devices, most recently active first; `current` = this one."""
    user = current_user(request)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""SELECT sid, method, user_agent, device_hint, created_at, last_seen FROM sessions
                           WHERE discord_id = %s AND ended_at IS NULL ORDER BY last_seen DESC""", (user["discord_id"],))
            rows = cur.fetchall()
    finally:
        conn.close()
    return [{"id": r["sid"], "device": r["device_hint"] or device_label(r["user_agent"]), "method": r["method"],
             "created_at": r["created_at"].isoformat(), "last_seen": r["last_seen"].isoformat(),
             "current": r["sid"] == user.get("sid")} for r in rows]


@router.post("/auth/sessions/device")
async def set_device(request: Request):
    """This page says what device it's on ('iPad · Firefox'); kept on this login's record for the Devices list."""
    user = current_user(request)
    hint = str((await request.json() or {}).get("device", ""))[:44]
    if user.get("sid") and HINT_OK.match(hint):
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE sessions SET device_hint = %s WHERE sid = %s AND discord_id = %s", (hint, user["sid"], user["discord_id"]))
            conn.commit()
        finally:
            conn.close()
    return {"ok": True}


@router.post("/auth/sessions/{sid}/end")
def end_session(sid: str, request: Request):
    """Log one of your devices out."""
    user = current_user(request)
    _end(user["discord_id"], "sid = %s", (sid,))
    return list_sessions(request) if sid != user.get("sid") else []


@router.post("/auth/sessions/end-others")
def end_other_sessions(request: Request):
    """Log out every device but this one."""
    user = current_user(request)
    _end(user["discord_id"], "sid <> %s", (user.get("sid") or "",))
    return list_sessions(request)


def _end(discord_id: str, where: str, args: tuple) -> None:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE sessions SET ended_at = now() WHERE discord_id = %s AND ended_at IS NULL AND {where} RETURNING sid",
                        (discord_id, *args))
            for r in cur.fetchall():
                _SID_CACHE[r["sid"]] = (False, time.time())
        conn.commit()
    finally:
        conn.close()


@router.get("/auth/logout")
async def logout(request: Request):
    user = read_session_cookie(request)
    if user and user.get("sid"):
        _end(user["discord_id"], "sid = %s", (user["sid"],))
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


@router.get("/me")
async def me(request: Request):
    return current_user(request)


def url_name(row: dict) -> str:
    """What goes in a user's URL: their Discord handle, or (until they log in
    again and we learn it) their display name."""
    return row.get("handle") or row["username"]


def resolve_user(cur, name: str) -> Optional[dict]:
    """URL name → user row. Checks the current handle, then old handles, then
    (for people who haven't logged in since handles were added) the display name."""
    cur.execute("SELECT * FROM users WHERE handle = %s", (name.lower(),))
    row = cur.fetchone()
    if row:
        return row
    cur.execute("""
        SELECT u.* FROM user_handle_history h JOIN users u ON u.discord_id = h.discord_id WHERE h.handle = %s
    """, (name.lower(),))
    row = cur.fetchone()
    if row:
        return row
    cur.execute("SELECT * FROM users WHERE handle IS NULL AND username = %s ORDER BY discord_id LIMIT 1", (name,))
    return cur.fetchone()
