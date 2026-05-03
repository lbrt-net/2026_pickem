import json as _json
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

INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "")

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
    key = request.headers.get("X-Internal-Key")
    if key and INTERNAL_API_KEY and key == INTERNAL_API_KEY:
        return {"is_admin": True, "internal": True}
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
            # Migrate: add wins tracking columns
            cur.execute("ALTER TABLE matchups ADD COLUMN IF NOT EXISTS wins_a INTEGER NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE matchups ADD COLUMN IF NOT EXISTS wins_b INTEGER NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE matchups ADD COLUMN IF NOT EXISTS stat_game_log TEXT")
            # Migrate: rename home_net_rating → home_net_rating_a (if old column exists)
            cur.execute("""
                DO $$
                BEGIN
                  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='matchups' AND column_name='home_net_rating')
                  AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='matchups' AND column_name='home_net_rating_a')
                  THEN ALTER TABLE matchups RENAME COLUMN home_net_rating TO home_net_rating_a;
                  END IF;
                END$$
            """)
            cur.execute("ALTER TABLE matchups ADD COLUMN IF NOT EXISTS home_net_rating_a FLOAT")
            cur.execute("ALTER TABLE matchups ADD COLUMN IF NOT EXISTS home_net_rating_b FLOAT")

            cur.execute("""
                ALTER TABLE matchups ADD COLUMN IF NOT EXISTS game_time TEXT
            """)
            cur.execute("ALTER TABLE matchups ADD COLUMN IF NOT EXISTS source_matchup_a TEXT")
            cur.execute("ALTER TABLE matchups ADD COLUMN IF NOT EXISTS source_matchup_b TEXT")
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
                    points  INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(discord_id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS rosters (
                    team_name TEXT PRIMARY KEY,
                    players   TEXT NOT NULL DEFAULT '[]'
                )
            """)
            # Migrate: add points column if old schema, drop old columns
            cur.execute("ALTER TABLE scores ADD COLUMN IF NOT EXISTS points INTEGER NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE scores DROP COLUMN IF EXISTS correct")
            cur.execute("ALTER TABLE scores DROP COLUMN IF EXISTS total")
            # Seed all matchups on first deploy
            cur.execute("SELECT COUNT(*) FROM matchups")
            if cur.fetchone()["count"] == 0:
                TBD = "2026-07-31T00:00"  # placeholder lock for future rounds
                matchup_seed = [
                    # id,  label,                  team_a,          team_b,         sa,   sb,  conf,    rnd,  game_time,               stat_label
                    # East R1 — home team on top, ordered 1/4/3/2 by home seed
                    ("e1", "East 1 vs 8",           "Detroit",       None,           1, None, "East",  1, "2026-04-19T18:30", "Plus/Minus"),
                    ("e4", "East 4 vs 5",           "Cleveland",     "Toronto",      4,    5, "East",  1, "2026-04-18T13:00", "Screen Assists"),
                    ("e3", "East 3 vs 6",           "New York",      "Atlanta",      3,    6, "East",  1, "2026-04-18T18:00", "Fast Break Points"),
                    ("e2", "East 2 vs 7",           "Boston",        "Philadelphia", 2,    7, "East",  1, "2026-04-19T13:00", "Plus/Minus"),
                    # West R1
                    ("w1", "West 1 vs 8",           "Oklahoma City", None,           1, None, "West",  1, "2026-04-19T15:30", None),
                    ("w4", "West 4 vs 5",           "LA Lakers",     "Houston",      4,    5, "West",  1, "2026-04-18T20:30", "Drives"),
                    ("w3", "West 3 vs 6",           "Denver",        "Minnesota",    3,    6, "West",  1, "2026-04-18T15:30", "Points"),
                    ("w2", "West 2 vs 7",           "San Antonio",   "Portland",     2,    7, "West",  1, "2026-04-19T21:00", "Steals"),
                    # East R2
                    ("e5", "East R2 — Game A",      None,            None,        None, None, "East",  2, TBD, None),
                    ("e6", "East R2 — Game B",      None,            None,        None, None, "East",  2, TBD, None),
                    # West R2
                    ("w5", "West R2 — Game A",      None,            None,        None, None, "West",  2, TBD, None),
                    ("w6", "West R2 — Game B",      None,            None,        None, None, "West",  2, TBD, None),
                    # Conf Finals
                    ("e7", "East Conference Finals", None,           None,        None, None, "East",  3, TBD, None),
                    ("w7", "West Conference Finals", None,           None,        None, None, "West",  3, TBD, None),
                    # NBA Finals
                    ("f1", "NBA Finals",             None,           None,        None, None, "Finals",4, TBD, None),
                ]
                for (mid, label, ta, tb, sa, sb, conf, rnd, gt, sl) in matchup_seed:
                    cur.execute("""
                        INSERT INTO matchups (id, label, team_a, team_b, seed_a, seed_b,
                                             conference, round, game_time, lock_time, stat_label)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT(id) DO NOTHING
                    """, (mid, label, ta, tb, sa, sb, conf, rnd, gt, game_time_to_lock_time(gt), sl))

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

    response = RedirectResponse(f"/picks/{user['username']}", status_code=302)
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


@app.get("/picks/user/{username}")
async def user_picks_by_username(username: str):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT discord_id FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            uid = row["discord_id"]

            # Only return picks for locked matchups
            cur.execute("""
                SELECT p.matchup_id, p.winner, p.games, p.stat_leader
                FROM picks p
                JOIN matchups m ON m.id = p.matchup_id
                WHERE p.user_id = %s
                  AND m.lock_time IS NOT NULL
                  AND m.lock_time <= %s
            """, (uid, datetime.now(timezone.utc).isoformat()))
            rows = cur.fetchall()
    finally:
        conn.close()

    return {
        "username": username,
        "picks": [
            {
                "matchup_id": r["matchup_id"],
                "winner": r["winner"],
                "games": r["games"],
                "stat_leader": r["stat_leader"],
            }
            for r in rows
        ],
    }


@app.get("/picks/user/{username}/status")
async def user_picks_status(username: str):
    """Pick completion flags (no pick content) for all matchups — public."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT discord_id FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
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

def _pick_series_pts(winner, games, stat_leader, winner_result, games_result, stat_leader_result):
    pts = 0
    correct = winner and winner == winner_result
    if correct:
        pts += 2
    if games is not None and games_result is not None:
        dist = abs(games - games_result)
        if dist == 0: pts += 2
        elif dist == 1: pts += 1
    if stat_leader and stat_leader_result:
        leaders = [n.strip().lower() for n in stat_leader_result.split(",")]
        if stat_leader.strip().lower() in leaders:
            pts += 1
    return min(pts, 5)

@app.get("/leaderboard")
async def leaderboard():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.username, u.avatar_url, COALESCE(s.points, 0) AS points,
                       p.winner, p.games, p.stat_leader,
                       m.winner_result, m.games_result, m.stat_leader_result, m.round
                FROM users u
                LEFT JOIN scores s ON s.user_id = u.discord_id
                LEFT JOIN picks p ON p.user_id = u.discord_id
                LEFT JOIN matchups m ON m.id = p.matchup_id AND m.winner_result IS NOT NULL
                ORDER BY COALESCE(s.points, 0) DESC, u.username
            """)
            rows = cur.fetchall()
    finally:
        conn.close()

    users = {}
    for row in rows:
        uname = row["username"]
        if uname not in users:
            users[uname] = {
                "username": uname,
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


# ── Admin ─────────────────────────────────────────────────────────────────────

class ResultPayload(BaseModel):
    winner:      str
    games:       int
    stat_leader: str


ROUND_MULTIPLIERS = {1: 1, 2: 4, 3: 8, 4: 16}

def _recalculate_scores_for_matchup(cur, matchup_id: str) -> None:
    cur.execute(
        "SELECT DISTINCT user_id FROM picks WHERE matchup_id = %s",
        (matchup_id,)
    )
    affected = cur.fetchall()

    for row in affected:
        uid = row["user_id"]

        # Recalculate total points across ALL scored matchups for this user
        cur.execute("""
            SELECT
                p.winner, p.games, p.stat_leader,
                m.winner_result, m.games_result, m.stat_leader_result, m.round
            FROM picks p
            JOIN matchups m ON m.id = p.matchup_id
            WHERE p.user_id = %s
              AND m.winner_result IS NOT NULL
        """, (uid,))
        all_picks = cur.fetchall()

        total_points = 0
        for pick in all_picks:
            pts = 0
            winner_correct = pick["winner"] and pick["winner"] == pick["winner_result"]

            # Correct winner: 2 pts
            if winner_correct:
                pts += 2

            # Games scoring: treat the full series as a continuum
            # OKC4-OKC5-OKC6-OKC7-PHX7-PHX6-PHX5-PHX4
            # Distance = same winner: abs(diff). Different winner: (pg-4) + (rg-4) + 1
            if pick["games"] is not None and pick["games_result"] is not None:
                dist = abs(pick["games"] - pick["games_result"])
                if dist == 0:
                    pts += 2
                elif dist == 1:
                    pts += 1

            # Correct stat leader: 1 pt
            if pick["stat_leader"] and pick["stat_leader_result"]:
                result_names = [n.strip().lower() for n in pick["stat_leader_result"].split(",")]
                if pick["stat_leader"].strip().lower() in result_names:
                    pts += 1
            # Cap at 5, apply round multiplier
            mult = ROUND_MULTIPLIERS.get(pick["round"] or 1, 1)
            total_points += min(pts, 5) * mult

        cur.execute("""
            INSERT INTO scores (user_id, points)
            VALUES (%s, %s)
            ON CONFLICT(user_id) DO UPDATE SET points = EXCLUDED.points
        """, (uid, total_points))


class WinsPayload(BaseModel):
    wins_a: int
    wins_b: int

@app.post("/admin/matchups/{matchup_id}/wins")
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


@app.delete("/admin/matchups/{matchup_id}/result")
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


class StatLogPayload(BaseModel):
    log: dict  # { "1": [{"name": "OG Anunoby", "value": 8}, ...], "2": [...] }
 
@app.post("/admin/matchups/{matchup_id}/stat-log")
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
    home_net_rating_a: Optional[float] = None
    home_net_rating_b: Optional[float] = None
    source_matchup_a: Optional[str] = None
    source_matchup_b: Optional[str] = None


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


@app.get("/matchups/aggregate")
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
 

# ── Rosters ───────────────────────────────────────────────────────────────────

@app.get("/rosters")
async def get_rosters():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT team_name, players FROM rosters")
            rows = cur.fetchall()
    finally:
        conn.close()
    return {row["team_name"]: _json.loads(row["players"]) for row in rows}


class RosterPayload(BaseModel):
    team_name: str
    players:   list[str]

@app.post("/admin/rosters")
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




STATIC_DIR = os.path.join(os.path.dirname(__file__), "frontend", "dist")

if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react(full_path: str):
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))