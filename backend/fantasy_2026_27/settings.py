"""Team settings (name, abbreviation, logo) and per-person notification preferences.

Rules:
- Name: trimmed, control characters stripped, 1–50 characters. Duplicates allowed.
- Color: "#rrggbb". Defaults to a color picked from a hash of the owner's username; the
  owner can change it. With no logo uploaded, the team's icon is a solid block of this color.
- Abbreviation: 1–4 letters or numbers, stored uppercase. Duplicates allowed.
- New teams default to the owner's Discord display name and the first 4 letters/numbers of it.
- Logo: PNG / JPEG / GIF / WebP (checked by file signature, not the declared type), ≤ 512 KB,
  stored in Postgres (Railway containers have no persistent disk) and served from
  GET /teams/{team_id}/logo. No SVG (can carry scripts).
- Notifications: per person (not per team), on/off per category, all off by default.
  In-website only (no Discord DMs, no email), sent right away (no digests).
"""
import colorsys
import hashlib
import re
import unicodedata
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response

from backend.auth import read_session_cookie
from backend.db import get_db

router = APIRouter()

NAME_MAX = 50
ABBR_MAX = 4
LOGO_MAX_BYTES = 512 * 1024
LOGO_TYPES = [  # (signature check, content type)
    (lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"), "image/png"),
    (lambda b: b.startswith(b"\xff\xd8\xff"), "image/jpeg"),
    (lambda b: b[:6] in (b"GIF87a", b"GIF89a"), "image/gif"),
    (lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP", "image/webp"),
]
# User's list (2026-09-28). Everything starts off.
NOTIFICATION_DEFAULTS = {
    "injuries": False,        # a player of yours changes injury status
    "ir_reminders": False,    # your Out player can go on IR / your IR player is back
    "trade_offers": False,    # offers to you: received, accepted, rejected
    "league_trades": False,   # any trade completed in the league
    "claims": False,          # your adds / waiver claims succeeded or failed
    "weekly_recap": False,    # weekly recap: other teams' activity + results; also end of regular season and playoffs
    "draft_reminders": False, # draft starting, your pick is up
}


def clean_name(raw: str) -> str:
    name = "".join(ch for ch in (raw or "") if unicodedata.category(ch) != "Cc").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Team name can't be empty")
    if len(name) > NAME_MAX:
        raise HTTPException(status_code=400, detail=f"Team name must be {NAME_MAX} characters or fewer")
    return name


def clean_abbreviation(raw: str) -> str:
    abbr = (raw or "").strip().upper()
    if not (1 <= len(abbr) <= ABBR_MAX) or not all(ch.isalnum() for ch in abbr):
        raise HTTPException(status_code=400, detail=f"Abbreviation must be 1–{ABBR_MAX} letters or numbers")
    return abbr


def default_color(username: str) -> str:
    """Stable color from a hash of the username: hash → hue; saturation/lightness fixed
    so every default reads well on the dark theme."""
    h = int(hashlib.md5((username or "").lower().encode()).hexdigest(), 16)
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, 0.55, 0.65)
    return f"#{round(r * 255):02x}{round(g * 255):02x}{round(b * 255):02x}"


def clean_color(raw: str) -> str:
    color = (raw or "").strip().lower()
    if not re.fullmatch(r"#[0-9a-f]{6}", color):
        raise HTTPException(status_code=400, detail="Color must look like #1a2b3c")
    return color


def default_abbreviation(name: str) -> str:
    return "".join(ch for ch in (name or "") if ch.isalnum())[:ABBR_MAX].upper() or "TEAM"


def _viewer(request: Request) -> dict:
    user = read_session_cookie(request)
    if not user:
        raise HTTPException(status_code=401, detail="Log in first")
    return user


def _team_for_edit(cur, request: Request, team_id: str) -> dict:
    """The team, if the viewer owns it (or is an admin)."""
    user = _viewer(request)
    cur.execute("SELECT * FROM fantasy_teams WHERE id = %s", (team_id,))
    team = cur.fetchone()
    if not team:
        raise HTTPException(status_code=404, detail="No such team")
    if team["owner_user_id"] != user.get("discord_id") and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not your team")
    return team


def logo_url(team: dict) -> Optional[str]:
    if not team.get("logo_updated"):
        return None
    return f"/fantasy/2026_27/teams/{team['id']}/logo?v={int(team['logo_updated'].timestamp())}"


def public_settings(team: dict) -> dict:
    return {"id": team["id"], "name": team["name"], "abbreviation": team["abbreviation"],
            "color": team["color"], "logo_url": logo_url(team)}


@router.put("/teams/{team_id}/settings")
async def save_settings(team_id: str, request: Request):
    """Body: {"name": "...", "abbreviation": "...", "color": "#rrggbb"} — any subset."""
    body = await request.json()
    conn = get_db()
    try:
        with conn.cursor() as cur:
            team = _team_for_edit(cur, request, team_id)
            name = clean_name(body["name"]) if "name" in body else team["name"]
            abbr = clean_abbreviation(body["abbreviation"]) if "abbreviation" in body else team["abbreviation"]
            color = clean_color(body["color"]) if "color" in body else team["color"]
            cur.execute("UPDATE fantasy_teams SET name = %s, abbreviation = %s, color = %s WHERE id = %s RETURNING *",
                        (name, abbr, color, team_id))
            team = cur.fetchone()
        conn.commit()
    finally:
        conn.close()
    return public_settings(team)


@router.put("/teams/{team_id}/logo")
async def upload_logo(team_id: str, request: Request):
    """Raw image bytes as the request body (no multipart)."""
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="No image sent")
    if len(data) > LOGO_MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"Logo must be {LOGO_MAX_BYTES // 1024} KB or smaller")
    ctype = next((t for check, t in LOGO_TYPES if check(data)), None)
    if not ctype:
        raise HTTPException(status_code=415, detail="Logo must be a PNG, JPEG, GIF, or WebP image")
    conn = get_db()
    try:
        with conn.cursor() as cur:
            _team_for_edit(cur, request, team_id)
            cur.execute("""
                UPDATE fantasy_teams SET logo = %s, logo_type = %s, logo_updated = now() WHERE id = %s RETURNING *
            """, (data, ctype, team_id))
            team = cur.fetchone()
        conn.commit()
    finally:
        conn.close()
    return public_settings(team)


@router.delete("/teams/{team_id}/logo")
async def remove_logo(team_id: str, request: Request):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            _team_for_edit(cur, request, team_id)
            cur.execute("""
                UPDATE fantasy_teams SET logo = NULL, logo_type = NULL, logo_updated = NULL WHERE id = %s RETURNING *
            """, (team_id,))
            team = cur.fetchone()
        conn.commit()
    finally:
        conn.close()
    return public_settings(team)


@router.get("/teams/{team_id}/logo")
async def get_logo(team_id: str):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT logo, logo_type FROM fantasy_teams WHERE id = %s", (team_id,))
            row = cur.fetchone()
    finally:
        conn.close()
    if not row or not row["logo"]:
        raise HTTPException(status_code=404, detail="No logo")
    # URL carries ?v=<updated>, so it can be cached hard; nosniff keeps browsers to the checked type.
    return Response(content=bytes(row["logo"]), media_type=row["logo_type"],
                    headers={"Cache-Control": "public, max-age=31536000, immutable", "X-Content-Type-Options": "nosniff"})


@router.get("/notifications/settings")
async def get_notification_settings(request: Request):
    user = _viewer(request)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT category, enabled FROM fantasy_notification_prefs WHERE discord_id = %s",
                        (user["discord_id"],))
            saved = {r["category"]: r["enabled"] for r in cur.fetchall()}
    finally:
        conn.close()
    return {c: saved.get(c, d) for c, d in NOTIFICATION_DEFAULTS.items()}


@router.put("/notifications/settings")
async def save_notification_settings(request: Request):
    """Body: {"injuries": true, "trades": false, ...} — any subset of the categories."""
    user = _viewer(request)
    body = await request.json()
    unknown = [k for k in body if k not in NOTIFICATION_DEFAULTS]
    if unknown or not all(isinstance(v, bool) for v in body.values()):
        raise HTTPException(status_code=400, detail=f"Categories are {list(NOTIFICATION_DEFAULTS)}, values true/false")
    conn = get_db()
    try:
        with conn.cursor() as cur:
            for category, enabled in body.items():
                cur.execute("""
                    INSERT INTO fantasy_notification_prefs (discord_id, category, enabled) VALUES (%s, %s, %s)
                    ON CONFLICT (discord_id, category) DO UPDATE SET enabled = EXCLUDED.enabled
                """, (user["discord_id"], category, enabled))
        conn.commit()
    finally:
        conn.close()
    return await get_notification_settings(request)
