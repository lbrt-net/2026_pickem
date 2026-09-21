from datetime import datetime, timezone, timedelta

from backend.config import CENTRAL
from backend.db import get_db


def game_time_to_lock_time(game_time_str: str) -> str:
    """
    Given a game time string in Central Time (e.g. "2026-04-19T13:00"),
    returns an ISO UTC string 1 hour before tip-off.
    """
    naive = datetime.fromisoformat(game_time_str)
    central_dt = naive.replace(tzinfo=CENTRAL)
    lock_dt = central_dt - timedelta(hours=1)
    return lock_dt.astimezone(timezone.utc).isoformat()


def init_schema() -> None:
    conn = get_db()
    try:
        with conn.cursor() as cur:
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
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stat_guide (
                    id         INTEGER PRIMARY KEY DEFAULT 1,
                    data       TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT NOT NULL DEFAULT ''
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
