"""Phone login: type /login in Discord, tap the button, you're logged in on that device.

1. Discord sends the /login command here (POST /discord/interactions, signed — checked against DISCORD_PUBLIC_KEY).
2. We reply with a message only that person sees: a "Log in to lbrt.net" button holding a one-time link
   (10 minutes, one use). A button, not a pasted link: Discord pre-opens pasted links for previews, which would
   spend a one-time link.
3. The link opens a small page ("Log in as allan?"); the link is only spent when they press its button (a POST), so
   link scanners that only look (GET) can't burn it. Then the same session cookie as Discord login.

Setup (once): DISCORD_PUBLIC_KEY in the environment; the Developer Portal's Interactions Endpoint URL set to
https://lbrt.net/discord/interactions; the app added to the server (applications.commands); then
POST /admin/discord/commands (admin) registers /login.
"""
import html
import os
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from .auth import make_session_cookie, require_admin, upsert_user
from .config import CLIENT_ID, CLIENT_SECRET, COOKIE_MAX_AGE, COOKIE_NAME
from .db import get_db

router = APIRouter()
PUBLIC_KEY = os.environ.get("DISCORD_PUBLIC_KEY", "")
LINK_MINUTES = 10
SITE = os.environ.get("SITE_URL", "https://lbrt.net")
LANDING = "/fantasy/2026_27"
COMMANDS = [{"name": "login", "description": "Log in to lbrt.net on this device", "type": 1,
             "integration_types": [0, 1], "contexts": [0, 1, 2]}]


def init_schema() -> None:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS login_links (
                    token      TEXT PRIMARY KEY,
                    discord_id TEXT NOT NULL REFERENCES users(discord_id),
                    expires_at TIMESTAMPTZ NOT NULL,
                    used_at    TIMESTAMPTZ
                )
            """)
            cur.execute("DELETE FROM login_links WHERE expires_at < now() - interval '1 day'")
        conn.commit()
    finally:
        conn.close()


def verify(signature: str, timestamp: str, body: bytes, public_key: str = None) -> bool:
    """Discord signs every interaction (Ed25519 over timestamp + body); anything that doesn't verify is refused."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    key = public_key if public_key is not None else PUBLIC_KEY
    if not (key and signature and timestamp):
        return False
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(key)).verify(bytes.fromhex(signature), timestamp.encode() + body)
        return True
    except (InvalidSignature, ValueError):
        return False


def new_link(discord_id: str) -> str:
    token = secrets.token_urlsafe(24)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO login_links (token, discord_id, expires_at) VALUES (%s, %s, %s)",
                        (token, discord_id, datetime.now(timezone.utc) + timedelta(minutes=LINK_MINUTES)))
        conn.commit()
    finally:
        conn.close()
    return token


def _live_link(cur, token: str):
    cur.execute("""SELECT l.*, u.username, u.is_banned FROM login_links l JOIN users u ON u.discord_id = l.discord_id
                   WHERE l.token = %s AND l.used_at IS NULL AND l.expires_at > now()""", (token,))
    return cur.fetchone()


def spend_link(token: str):
    """The user for a live link, marking it used; None if it's unknown, used or expired."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            row = _live_link(cur, token)
            if not row:
                return None
            cur.execute("UPDATE login_links SET used_at = now() WHERE token = %s AND used_at IS NULL", (token,))
            if cur.rowcount != 1:
                return None
            cur.execute("SELECT * FROM users WHERE discord_id = %s", (row["discord_id"],))
            user = dict(cur.fetchone())
        conn.commit()
        return user
    finally:
        conn.close()


@router.post("/discord/interactions")
async def interactions(request: Request):
    body = await request.body()
    if not verify(request.headers.get("X-Signature-Ed25519", ""), request.headers.get("X-Signature-Timestamp", ""), body):
        raise HTTPException(status_code=401, detail="bad signature")
    data = await request.json()
    if data.get("type") == 1:  # Discord checking the endpoint
        return JSONResponse({"type": 1})
    if data.get("type") == 2 and (data.get("data") or {}).get("name") == "login":
        u = (data.get("member") or {}).get("user") or data.get("user") or {}
        avatar = f'https://cdn.discordapp.com/avatars/{u["id"]}/{u["avatar"]}.png' if u.get("avatar") else None
        user = upsert_user(u["id"], u.get("global_name") or u.get("username"), avatar, (u.get("username") or "").lower() or None)
        if user.get("is_banned"):
            return JSONResponse({"type": 4, "data": {"flags": 64, "content": "This account can't log in."}})
        token = new_link(user["discord_id"])
        return JSONResponse({"type": 4, "data": {
            "flags": 64,  # only they see it
            "content": f"Log in on this device — the button works once, for {LINK_MINUTES} minutes.",
            "components": [{"type": 1, "components": [{"type": 2, "style": 5, "label": "Log in to lbrt.net",
                                                        "url": f"{SITE}/auth/link?t={token}"}]}]}})
    return JSONResponse({"type": 4, "data": {"flags": 64, "content": "Unknown command."}})


PAGE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Log in · LBRT</title><style>
body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#0f1117;color:#e6edf3;font:16px system-ui,sans-serif}}
.b{{width:100%;max-width:360px;padding:28px 24px;display:flex;flex-direction:column;gap:18px;text-align:center}}
h1{{margin:0;font-size:22px}}button{{height:48px;border:0;border-radius:10px;background:#ff6a1f;color:#0b0b0b;font:700 16px system-ui,sans-serif}}
a{{color:#e6edf3}}</style></head><body><div class="b">{body}</div></body></html>"""


@router.get("/auth/link")
def link_page(t: str = ""):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            row = _live_link(cur, t)
    finally:
        conn.close()
    if not row or row["is_banned"]:
        return HTMLResponse(PAGE.format(body='<h1>This link has expired</h1><p>Type <b>/login</b> in Discord for a new one.</p>'), status_code=410)
    return HTMLResponse(PAGE.format(body=f'<h1>Log in as {html.escape(row["username"])}?</h1>'
                                         f'<form method="post" action="/auth/link"><input type="hidden" name="t" value="{html.escape(t)}">'
                                         f'<button type="submit" style="width:100%">Log in</button></form>'))


@router.post("/auth/link")
def link_login(t: str = Form("")):
    user = spend_link(t)
    if not user or user.get("is_banned"):
        return HTMLResponse(PAGE.format(body='<h1>This link has expired</h1><p>Type <b>/login</b> in Discord for a new one.</p>'), status_code=410)
    response = RedirectResponse(LANDING, status_code=303)
    response.set_cookie(key=COOKIE_NAME, value=make_session_cookie(user), max_age=COOKIE_MAX_AGE,
                        httponly=True, samesite="lax", secure=True)
    return response


@router.post("/admin/discord/commands")
async def register_commands(request: Request):
    """Admin: register /login with Discord (the app's own client credentials; no bot token needed)."""
    require_admin(request)
    async with httpx.AsyncClient() as client:
        tok = await client.post("https://discord.com/api/v10/oauth2/token", auth=(CLIENT_ID, CLIENT_SECRET),
                                data={"grant_type": "client_credentials", "scope": "applications.commands.update"})
        if tok.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Discord token: {tok.text}")
        r = await client.put(f"https://discord.com/api/v10/applications/{CLIENT_ID}/commands",
                             headers={"Authorization": f'Bearer {tok.json()["access_token"]}'}, json=COMMANDS)
    if r.status_code >= 300:
        raise HTTPException(status_code=502, detail=f"Discord commands: {r.text}")
    return {"ok": True, "commands": [c["name"] for c in r.json()]}
