import os
import httpx
import psycopg2
import psycopg2.extras
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from pydantic import BaseModel

CLIENT_ID     = os.environ["DISCORD_CLIENT_ID"]
CLIENT_SECRET = os.environ["DISCORD_CLIENT_SECRET"]
REDIRECT_URI  = os.environ["DISCORD_REDIRECT_URI"]
SECRET_KEY    = os.environ.get("SECRET_KEY", "change-me-in-prod")
DATABASE_URL  = os.environ["DATABASE_URL"]

ADMIN_DISCORD_IDS: set[str] = set(
    x.strip()
    for x in os.environ.get("ADMIN_DISCORD_IDS", "").split(",")
    if x.strip()
)

CENTRAL = ZoneInfo("America/Chicago")

signer = URLSafeTimedSerializer(SECRET_KEY)

DISCORD_AUTH_URL  = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_API_URL   = "https://discord.com/api/users/@me"

COOKIE_NAME    = "session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 14


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
    user = current_user(request)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn


def game_time_to_lock_time(game_time_str: str) -> str:
    """
    Given a game time string in Central Time (e.g. "2026-04-19T13:00"),
    returns an ISO UTC string 1 hour before tip-off.
    """
    naive = datetime.fromisoformat(game_time_str)
    central_dt = naive.replace(tzinfo=CENTRAL)
    lock_dt = central_dt - timedelta(hours=1)
    return lock_dt.astimezone(timezone.utc).isoformat()


def init_db() -> None:
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
            cur.execute("""
                CREATE TABLE IF NOT EXISTS matchups (
                    id                  TEXT PRIMARY KEY,
                    label               TEXT NOT NULL,
                    team_a              TEXT,
                    team_b              TEXT,
                    seed_a              INTEGER,
                    seed_b              INTEGER,
                    conference          TEXT,
                    round               INTEGER,
                    stat_label          TEXT,
                    game_time           TEXT,
                    lock_time           TEXT,
                    winner_result       TEXT,
                    games_result        INTEGER,
                    stat_leader_result  TEXT
                )
            """)
            # Migrate: add game_time column if it doesn't exist yet
            cur.execute("""
                ALTER TABLE matchups ADD COLUMN IF NOT EXISTS game_time TEXT
            """)
            # Migrate: make team_a / team_b nullable if they were NOT NULL
            cur.execute("""
                ALTER TABLE matchups ALTER COLUMN team_a DROP NOT NULL
            """)
            cur.execute("""
                ALTER TABLE matchups ALTER COLUMN team_b DROP NOT NULL
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS picks (
                    user_id      TEXT NOT NULL,
                    matchup_id   TEXT NOT NULL,
                    winner       TEXT,
                    games        INTEGER,
                    stat_leader  TEXT,
                    submitted_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, matchup_id),
                    FOREIGN KEY (user_id)    REFERENCES users(discord_id),
                    FOREIGN KEY (matchup_id) REFERENCES matchups(id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scores (
                    user_id TEXT PRIMARY KEY,
                    correct INTEGER NOT NULL DEFAULT 0,
                    total   INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(discord_id)
                )
            """)
        conn.commit()
    finally:
        conn.close()


def upsert_user(discord_id: str, username: str, avatar_url: Optional[str]) -> dict:
    is_admin = discord_id in ADMIN_DISCORD_IDS
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (discord_id, username, avatar_url, is_admin)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT(discord_id) DO UPDATE SET
                    username   = EXCLUDED.username,
                    avatar_url = EXCLUDED.avatar_url,
                    is_admin   = EXCLUDED.is_admin
            """, (discord_id, username, avatar_url, is_admin))
        conn.commit()
    finally:
        conn.close()
    return {
        "discord_id": discord_id,
        "username":   username,
        "avatar_url": avatar_url,
        "is_admin":   is_admin,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.get("/auth/login")
async def login():
    params = (
        f"client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify"
    )
    return RedirectResponse(f"{DISCORD_AUTH_URL}?{params}")


@app.get("/auth/discord")
async def auth_discord():
    params = (
        f"client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify"
    )
    return RedirectResponse(f"{DISCORD_AUTH_URL}?{params}")


@app.get("/auth/callback")
async def callback(request: Request, code: str = None, error: str = None):
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

    response = RedirectResponse("/", status_code=302)
    response.set_cookie(
        key=COOKIE_NAME,
        value=make_session_cookie(user),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=True,
    )
    return response


@app.get("/auth/logout")
async def logout():
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


@app.get("/me")
async def me(request: Request):
    return current_user(request)


# ── Picks ─────────────────────────────────────────────────────────────────────

class PickPayload(BaseModel):
    matchup_id:  str
    winner:      Optional[str] = None
    games:       Optional[int] = None
    stat_leader: Optional[str] = None


@app.post("/picks")
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


@app.get("/picks/me")
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


# ── Leaderboard ───────────────────────────────────────────────────────────────

@app.get("/leaderboard")
async def leaderboard():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.username, u.avatar_url, s.correct, s.total
                FROM scores s
                JOIN users u ON u.discord_id = s.user_id
                ORDER BY s.correct DESC, s.total DESC
            """)
            rows = cur.fetchall()
    finally:
        conn.close()

    return [dict(r) for r in rows]


# ── Admin ─────────────────────────────────────────────────────────────────────

class ResultPayload(BaseModel):
    winner:      str
    games:       int
    stat_leader: str


def _recalculate_scores_for_matchup(cur, matchup_id: str) -> None:
    cur.execute(
        "SELECT DISTINCT user_id FROM picks WHERE matchup_id = %s",
        (matchup_id,)
    )
    affected = cur.fetchall()

    for row in affected:
        uid = row["user_id"]
        cur.execute("""
            SELECT
                SUM(
                    CASE WHEN p.winner      = m.winner_result      THEN 1 ELSE 0 END +
                    CASE WHEN p.games       = m.games_result        THEN 1 ELSE 0 END +
                    CASE WHEN p.stat_leader = m.stat_leader_result  THEN 1 ELSE 0 END
                ) AS correct,
                COUNT(*) * 3 AS total
            FROM picks p
            JOIN matchups m ON m.id = p.matchup_id
            WHERE p.user_id = %s
              AND m.winner_result      IS NOT NULL
              AND m.games_result       IS NOT NULL
              AND m.stat_leader_result IS NOT NULL
        """, (uid,))
        agg = cur.fetchone()

        cur.execute("""
            INSERT INTO scores (user_id, correct, total)
            VALUES (%s, %s, %s)
            ON CONFLICT(user_id) DO UPDATE SET
                correct = EXCLUDED.correct,
                total   = EXCLUDED.total
        """, (uid, agg["correct"] or 0, agg["total"] or 0))


@app.post("/admin/matchups/{matchup_id}/result")
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

            _recalculate_scores_for_matchup(cur, matchup_id)
        conn.commit()
    finally:
        conn.close()

    return {"ok": True, "matchup_id": matchup_id}


class MatchupPayload(BaseModel):
    id:         str
    label:      str
    team_a:     Optional[str] = None   # NULL = TBD, unclickable in frontend
    team_b:     Optional[str] = None
    seed_a:     Optional[int] = None
    seed_b:     Optional[int] = None
    conference: Optional[str] = None
    round:      Optional[int] = None
    stat_label: Optional[str] = None
    game_time:  Optional[str] = None   # Central Time, e.g. "2026-04-19T13:00"


@app.post("/admin/matchups")
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
                                      conference, round, stat_label, game_time, lock_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(id) DO UPDATE SET
                    label      = EXCLUDED.label,
                    team_a     = EXCLUDED.team_a,
                    team_b     = EXCLUDED.team_b,
                    seed_a     = EXCLUDED.seed_a,
                    seed_b     = EXCLUDED.seed_b,
                    conference = EXCLUDED.conference,
                    round      = EXCLUDED.round,
                    stat_label = EXCLUDED.stat_label,
                    game_time  = EXCLUDED.game_time,
                    lock_time  = EXCLUDED.lock_time
            """, (
                payload.id, payload.label, payload.team_a, payload.team_b,
                payload.seed_a, payload.seed_b, payload.conference,
                payload.round, payload.stat_label, payload.game_time, lock_time,
            ))
        conn.commit()
    finally:
        conn.close()

    return {"ok": True, "lock_time": lock_time}


@app.get("/admin/matchups")
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


# ── Public matchups (for frontend to render picks UI) ─────────────────────────

@app.get("/matchups")
async def public_matchups():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM matchups ORDER BY round, id")
            rows = cur.fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


# ── Serve React frontend — must be LAST ───────────────────────────────────────

STATIC_DIR = os.path.join(os.path.dirname(__file__), "frontend", "dist")

if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react(full_path: str):
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))