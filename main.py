import os
import sqlite3
import httpx
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CLIENT_ID     = os.environ["DISCORD_CLIENT_ID"]
CLIENT_SECRET = os.environ["DISCORD_CLIENT_SECRET"]
REDIRECT_URI  = os.environ["DISCORD_REDIRECT_URI"]
SECRET_KEY    = os.environ.get("SECRET_KEY", "change-me-in-prod")
DATABASE_PATH = os.environ.get("DATABASE_PATH", "pickem.db")

ADMIN_DISCORD_IDS: set[str] = set(
    x.strip()
    for x in os.environ.get("ADMIN_DISCORD_IDS", "").split(",")
    if x.strip()
)

signer = URLSafeTimedSerializer(SECRET_KEY)

DISCORD_AUTH_URL  = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_API_URL   = "https://discord.com/api/users/@me"

COOKIE_NAME = "session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 14  # 14 days

# ---------------------------------------------------------------------------
# Session helpers  (itsdangerous signed cookie, no middleware needed)
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            discord_id  TEXT PRIMARY KEY,
            username    TEXT NOT NULL,
            avatar_url  TEXT,
            is_admin    INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS matchups (
            id                  TEXT PRIMARY KEY,
            label               TEXT NOT NULL,
            team_a              TEXT NOT NULL,
            team_b              TEXT NOT NULL,
            seed_a              INTEGER,
            seed_b              INTEGER,
            conference          TEXT,
            round               INTEGER,
            stat_label          TEXT,
            lock_time           TEXT,
            winner_result       TEXT,
            games_result        INTEGER,
            stat_leader_result  TEXT
        );

        CREATE TABLE IF NOT EXISTS picks (
            user_id      TEXT NOT NULL,
            matchup_id   TEXT NOT NULL,
            winner       TEXT NOT NULL,
            games        INTEGER NOT NULL,
            stat_leader  TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            PRIMARY KEY (user_id, matchup_id),
            FOREIGN KEY (user_id)    REFERENCES users(discord_id),
            FOREIGN KEY (matchup_id) REFERENCES matchups(id)
        );

        CREATE TABLE IF NOT EXISTS scores (
            user_id TEXT PRIMARY KEY,
            correct INTEGER NOT NULL DEFAULT 0,
            total   INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(discord_id)
        );
        """)


def upsert_user(discord_id: str, username: str, avatar_url: Optional[str]) -> dict:
    is_admin = 1 if discord_id in ADMIN_DISCORD_IDS else 0
    with get_db() as conn:
        conn.execute("""
            INSERT INTO users (discord_id, username, avatar_url, is_admin)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(discord_id) DO UPDATE SET
                username   = excluded.username,
                avatar_url = excluded.avatar_url,
                is_admin   = excluded.is_admin
        """, (discord_id, username, avatar_url, is_admin))
    return {
        "discord_id": discord_id,
        "username":   username,
        "avatar_url": avatar_url,
        "is_admin":   bool(is_admin),
    }

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

# ---------------------------------------------------------------------------
# Existing routes (kept, callback upgraded to set cookie)
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <html><body style="font-family:sans-serif;padding:2rem">
      <h1>Pickem</h1>
      <a href="/auth/login">
        <button style="padding:.75rem 1.5rem;font-size:1rem;background:#5865F2;color:white;border:none;border-radius:6px;cursor:pointer">
          Login with Discord
        </button>
      </a>
    </body></html>
    """


@app.get("/auth/login")
async def login():
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
        return HTMLResponse(
            f"<h2>OAuth error: {error or 'no code returned'}</h2>",
            status_code=400,
        )

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
        secure=True,   # drop to False if testing over plain HTTP locally
    )
    return response


@app.get("/auth/logout")
async def logout():
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------

@app.get("/me")
async def me(request: Request):
    return current_user(request)


# ---------------------------------------------------------------------------
# Picks
# ---------------------------------------------------------------------------

class PickPayload(BaseModel):
    matchup_id:  str
    winner:      str
    games:       int
    stat_leader: str


@app.post("/picks")
async def submit_pick(payload: PickPayload, request: Request):
    user = current_user(request)

    with get_db() as conn:
        row = conn.execute(
            "SELECT lock_time FROM matchups WHERE id = ?",
            (payload.matchup_id,)
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Matchup not found")

        if row["lock_time"]:
            lock_dt = datetime.fromisoformat(row["lock_time"])
            if lock_dt.tzinfo is None:
                lock_dt = lock_dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) >= lock_dt:
                raise HTTPException(status_code=403, detail="Matchup is locked")

        conn.execute("""
            INSERT INTO picks (user_id, matchup_id, winner, games, stat_leader, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, matchup_id) DO UPDATE SET
                winner       = excluded.winner,
                games        = excluded.games,
                stat_leader  = excluded.stat_leader,
                submitted_at = excluded.submitted_at
        """, (
            user["discord_id"],
            payload.matchup_id,
            payload.winner,
            payload.games,
            payload.stat_leader,
            datetime.now(timezone.utc).isoformat(),
        ))

    return {"ok": True}


@app.get("/picks/me")
async def my_picks(request: Request):
    user = current_user(request)

    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM picks WHERE user_id = ?",
            (user["discord_id"],)
        ).fetchall()

    return {
        row["matchup_id"]: {
            "winner":       row["winner"],
            "games":        row["games"],
            "stat_leader":  row["stat_leader"],
            "submitted_at": row["submitted_at"],
        }
        for row in rows
    }


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

@app.get("/leaderboard")
async def leaderboard():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT u.username, u.avatar_url, s.correct, s.total
            FROM scores s
            JOIN users u ON u.discord_id = s.user_id
            ORDER BY s.correct DESC, s.total DESC
        """).fetchall()

    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

class ResultPayload(BaseModel):
    winner:      str
    games:       int
    stat_leader: str


def _recalculate_scores_for_matchup(conn: sqlite3.Connection, matchup_id: str) -> None:
    affected = conn.execute(
        "SELECT DISTINCT user_id FROM picks WHERE matchup_id = ?",
        (matchup_id,)
    ).fetchall()

    for row in affected:
        uid = row["user_id"]
        agg = conn.execute("""
            SELECT
                SUM(
                    CASE WHEN p.winner      = m.winner_result      THEN 1 ELSE 0 END +
                    CASE WHEN p.games       = m.games_result        THEN 1 ELSE 0 END +
                    CASE WHEN p.stat_leader = m.stat_leader_result  THEN 1 ELSE 0 END
                ) AS correct,
                COUNT(*) * 3 AS total
            FROM picks p
            JOIN matchups m ON m.id = p.matchup_id
            WHERE p.user_id = ?
              AND m.winner_result      IS NOT NULL
              AND m.games_result       IS NOT NULL
              AND m.stat_leader_result IS NOT NULL
        """, (uid,)).fetchone()

        conn.execute("""
            INSERT INTO scores (user_id, correct, total)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                correct = excluded.correct,
                total   = excluded.total
        """, (uid, agg["correct"] or 0, agg["total"] or 0))


@app.post("/admin/matchups/{matchup_id}/result")
async def set_result(matchup_id: str, payload: ResultPayload, request: Request):
    require_admin(request)

    with get_db() as conn:
        cur = conn.execute("""
            UPDATE matchups
            SET winner_result      = ?,
                games_result       = ?,
                stat_leader_result = ?
            WHERE id = ?
        """, (payload.winner, payload.games, payload.stat_leader, matchup_id))

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Matchup not found")

        _recalculate_scores_for_matchup(conn, matchup_id)

    return {"ok": True, "matchup_id": matchup_id}


class MatchupPayload(BaseModel):
    id:         str
    label:      str
    team_a:     str
    team_b:     str
    seed_a:     Optional[int] = None
    seed_b:     Optional[int] = None
    conference: Optional[str] = None
    round:      Optional[int] = None
    stat_label: Optional[str] = None
    lock_time:  Optional[str] = None


@app.post("/admin/matchups")
async def upsert_matchup(payload: MatchupPayload, request: Request):
    require_admin(request)

    with get_db() as conn:
        conn.execute("""
            INSERT INTO matchups (id, label, team_a, team_b, seed_a, seed_b,
                                  conference, round, stat_label, lock_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                label      = excluded.label,
                team_a     = excluded.team_a,
                team_b     = excluded.team_b,
                seed_a     = excluded.seed_a,
                seed_b     = excluded.seed_b,
                conference = excluded.conference,
                round      = excluded.round,
                stat_label = excluded.stat_label,
                lock_time  = excluded.lock_time
        """, (
            payload.id, payload.label, payload.team_a, payload.team_b,
            payload.seed_a, payload.seed_b, payload.conference,
            payload.round, payload.stat_label, payload.lock_time,
        ))

    return {"ok": True}


@app.get("/admin/matchups")
async def list_matchups(request: Request):
    require_admin(request)
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM matchups ORDER BY round, id").fetchall()
    return [dict(r) for r in rows]