"""Log in on your phone: from a computer where you're logged in, your account menu → "Log in on your phone" shows a
QR code of a one-time link (10 minutes, one use). The phone's camera opens it: a small page ("Log in as allan?")
whose button spends the link (a POST, so link previews / scanners that only look can't burn it) and sets the same
session cookie as Discord login. No Discord setup needed.
"""
import html
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .auth import read_session_cookie, require_admin, start_session
from .config import COOKIE_MAX_AGE, COOKIE_NAME
from .db import get_db

router = APIRouter()
LINK_MINUTES = 10
SITE = os.environ.get("SITE_URL", "https://lbrt.net")
LANDING = "/fantasy/2026_27"

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


def new_link(discord_id: str, minutes: int = LINK_MINUTES) -> str:
    token = secrets.token_urlsafe(24)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO login_links (token, discord_id, expires_at) VALUES (%s, %s, %s)",
                        (token, discord_id, datetime.now(timezone.utc) + timedelta(minutes=minutes)))
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


@router.post("/auth/phone-link")
def phone_link(request: Request):
    """A one-time login link for the person logged in here, to open on another device (shown as a QR code)."""
    user = read_session_cookie(request)
    if not user:
        raise HTTPException(status_code=401, detail="Log in first")
    token = new_link(user["discord_id"])
    return {"url": f"{SITE}/auth/link?t={token}", "minutes": LINK_MINUTES}


@router.post("/admin/users/{discord_id}/login-link")
def commish_link(discord_id: str, request: Request, hours: float = 12):
    """Commissioner (2026-10-17): a one-time login link for a member who can't get into Discord (on his phone, forgot
    his password). Whoever opens it is logged in as him — one use, up to 24 hours, same confirm page as the phone
    link, so link previews can't spend it. Banned members can't get one."""
    require_admin(request)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT username, is_banned FROM users WHERE discord_id = %s", (discord_id,))
            u = cur.fetchone()
    finally:
        conn.close()
    if not u:
        raise HTTPException(status_code=404, detail="No such member (they have to have logged in once)")
    if u["is_banned"]:
        raise HTTPException(status_code=403, detail="That member is banned")
    minutes = int(max(1, min(24 * 60, hours * 60)))
    token = new_link(discord_id, minutes)
    return {"url": f"{SITE}/auth/link?t={token}", "for": u["username"], "minutes": minutes}


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
        return HTMLResponse(PAGE.format(body='<h1>This link has expired</h1><p>Ask for a new one (or open <b>Log in on your phone</b> on your computer).</p>'), status_code=410)
    return HTMLResponse(PAGE.format(body=f'<h1>Log in as {html.escape(row["username"])}?</h1>'
                                         f'<form method="post" action="/auth/link"><input type="hidden" name="t" value="{html.escape(t)}">'
                                         f'<button type="submit" style="width:100%">Log in</button></form>'))


@router.post("/auth/link")
def link_login(request: Request, t: str = Form("")):
    user = spend_link(t)
    if not user or user.get("is_banned"):
        return HTMLResponse(PAGE.format(body='<h1>This link has expired</h1><p>Ask for a new one (or open <b>Log in on your phone</b> on your computer).</p>'), status_code=410)
    response = RedirectResponse(LANDING, status_code=303)
    response.set_cookie(key=COOKIE_NAME, value=start_session(user, request, "phone"), max_age=COOKIE_MAX_AGE,
                        httponly=True, samesite="lax", secure=True)
    return response
