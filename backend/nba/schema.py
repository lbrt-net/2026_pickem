from psycopg2.extras import Json

from backend.db import get_db


def init_schema() -> None:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # One row per NBA game id, ever. Rows are never deleted: a game that
            # disappears from the NBA feed gets missing_since set instead.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS nba_games (
                    game_id       TEXT PRIMARY KEY,
                    season        TEXT NOT NULL,          -- '2026-27'
                    game_type     TEXT NOT NULL,          -- preseason / regular / allstar / playoffs / playin / cup_final
                    game_date     DATE,                   -- US Eastern calendar date
                    tipoff_utc    TIMESTAMPTZ,            -- NULL while the tip time is TBD
                    time_tbd      BOOLEAN NOT NULL DEFAULT FALSE,
                    status        TEXT NOT NULL,          -- scheduled / live / final / postponed / cancelled
                    status_text   TEXT,
                    home_team     TEXT,                   -- tricode; NULL while TBD (e.g. NBA Cup knockouts)
                    away_team     TEXT,
                    home_score    INTEGER,
                    away_score    INTEGER,
                    label         TEXT,                   -- "Emirates NBA Cup", series text, ...
                    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
                    last_seen_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                    missing_since TIMESTAMPTZ
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS nba_games_season_date ON nba_games (season, game_date)")

            # Every sync attempt, successful or not.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS nba_feed_log (   -- can this server reach the NBA's live feed? (2026-10-22, Feed Log page)
                    id      SERIAL PRIMARY KEY,
                    at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                    kind    TEXT NOT NULL,      -- probe (every 10 min) / pull (a live pull's scoreboard)
                    source  TEXT NOT NULL,      -- cdn / backup
                    status  INTEGER,            -- HTTP status; NULL = no answer
                    ms      INTEGER,
                    error   TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS nba_sync_runs (
                    id          SERIAL PRIMARY KEY,
                    kind        TEXT NOT NULL,            -- 'schedule'
                    trigger     TEXT NOT NULL,            -- daily / startup / manual / ingest
                    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                    finished_at TIMESTAMPTZ,
                    ok          BOOLEAN,
                    games_seen  INTEGER,
                    added       INTEGER,
                    changed     INTEGER,
                    removed     INTEGER,
                    restored    INTEGER,
                    error       TEXT
                )
            """)

            # Audit trail of what moved: date/time changes, TBD teams filled in,
            # postponements, games vanishing and coming back.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS nba_game_changes (
                    id         SERIAL PRIMARY KEY,
                    run_id     INTEGER REFERENCES nba_sync_runs(id),
                    game_id    TEXT NOT NULL,
                    changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    kind       TEXT NOT NULL,             -- added / changed / removed / restored
                    field      TEXT,
                    old_value  TEXT,
                    new_value  TEXT
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS nba_game_changes_game ON nba_game_changes (game_id)")

            # Traditional box score, full game, one row per player per game
            # (DNPs included, with dnp_reason). Loaded once per game; see ROADMAP "Box scores".
            cur.execute("""
                CREATE TABLE IF NOT EXISTS nba_player_games (
                    game_id     TEXT NOT NULL,
                    player_id   TEXT NOT NULL,
                    season      TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    team        TEXT NOT NULL,
                    position    TEXT,                     -- G/F/C, only listed for starters
                    starter     BOOLEAN NOT NULL,
                    dnp_reason  TEXT,                     -- "DNP - Coach's Decision", injury, ...
                    minutes     FLOAT NOT NULL DEFAULT 0, -- decimal
                    fgm INTEGER NOT NULL DEFAULT 0, fga INTEGER NOT NULL DEFAULT 0,
                    fg3m INTEGER NOT NULL DEFAULT 0, fg3a INTEGER NOT NULL DEFAULT 0,
                    ftm INTEGER NOT NULL DEFAULT 0, fta INTEGER NOT NULL DEFAULT 0,
                    oreb INTEGER NOT NULL DEFAULT 0, dreb INTEGER NOT NULL DEFAULT 0,
                    ast INTEGER NOT NULL DEFAULT 0, stl INTEGER NOT NULL DEFAULT 0,
                    blk INTEGER NOT NULL DEFAULT 0, tov INTEGER NOT NULL DEFAULT 0,
                    pf INTEGER NOT NULL DEFAULT 0, pts INTEGER NOT NULL DEFAULT 0,
                    plus_minus INTEGER NOT NULL DEFAULT 0,
                    loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
                    PRIMARY KEY (game_id, player_id)
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS nba_player_games_player ON nba_player_games (player_id, season)")
            # Misc box score (boxscoremiscv3). NULL = not loaded yet for that game.
            cur.execute("ALTER TABLE nba_player_games ADD COLUMN IF NOT EXISTS blkd INTEGER")  # own shots blocked
            cur.execute("ALTER TABLE nba_player_games ADD COLUMN IF NOT EXISTS pfd INTEGER")   # fouls drawn
            cur.execute("CREATE INDEX IF NOT EXISTS nba_player_games_season ON nba_player_games (season)")
            # Clutch-time points (NBA definition: 4th / OT, <= 5:00 left, score within 5) per player-game, from
            # LeagueDashPlayerClutch by game day. NULL = not loaded for that season; 0 = loaded, none scored.
            cur.execute("ALTER TABLE nba_player_games ADD COLUMN IF NOT EXISTS clutch_pts INTEGER")
            # The nightly job's record of each game it loaded (nightly.py): last pull, whether the feed passed its checks,
            # how many player lines a re-pull changed (NBA stat corrections), and what was wrong if it failed.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS nba_game_loads (
                    game_id     TEXT PRIMARY KEY,
                    last_pulled TIMESTAMPTZ NOT NULL,
                    ok          BOOLEAN NOT NULL,
                    attempts    INTEGER NOT NULL DEFAULT 1,
                    changed     INTEGER NOT NULL DEFAULT 0,
                    problems    JSONB
                )
            """)
            # Each game's field goal attempts, pulled out of its play-by-play when the game loads (live final + nightly):
            # shots = [[player_id, x, y, three (0/1), pts], ...] (tenths of a foot, hoop at 0,0; heaves left out). The raw
            # play-by-play itself isn't kept (commissioner, 2026-10-14: ~370 KB a game); the raw box score is.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS nba_game_shots (
                    game_id   TEXT PRIMARY KEY,
                    season    TEXT NOT NULL,
                    shots     JSONB NOT NULL,
                    loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS nba_game_shots_season ON nba_game_shots (season)")
            cur.execute("SELECT to_regclass('nba_live_raw') AS t")
            if cur.fetchone()["t"]:  # once: shots out of any stored play-by-play, then the raw play-by-play goes
                from .shot_fields import shots_rows
                cur.execute("""SELECT r.game_id, g.season, r.payload FROM nba_live_raw r JOIN nba_games g ON g.game_id = r.game_id
                               WHERE r.kind = 'playbyplay'""")
                for r in cur.fetchall():
                    cur.execute("""INSERT INTO nba_game_shots (game_id, season, shots) VALUES (%s, %s, %s)
                                   ON CONFLICT (game_id) DO NOTHING""", (r["game_id"], r["season"], Json(shots_rows(r["payload"]))))
                cur.execute("DELETE FROM nba_live_raw WHERE kind = 'playbyplay'")
            cur.execute("DROP TABLE IF EXISTS nba_shots")  # raw shot locations (2026-10-14, never loaded): replaced by the fields
            # Shot chart fields (the player page's Extras LED board), one row per player-season, computed offline by
            # scripts/build_shot_fields.py with nba-pipeline/analysis/shot_chart.py's method. data: x0 / y0 / step / nx / ny
            # (cells of 0.5 ft, tenths of a foot, hoop at 0,0), lvl = one digit per cell (0 = outside his 95% area, 1..5 =
            # the 95/80/60/40/20% layers), d = points per shot vs the league x100 for every cell with lvl > 0, n = his shots.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS nba_shot_fields (
                    player_id TEXT NOT NULL,
                    season    TEXT NOT NULL,
                    data      JSONB NOT NULL,
                    built_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                    PRIMARY KEY (player_id, season)
                )
            """)
            # Stats pages' data (routes.py /stats/*): one JSON per page, POSTed by the nightly refresh on the commissioner's
            # Mac (nba-pipeline scripts/nightly_stats.sh) — served over the static file in backend/nba/ when present.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS nba_stats_json (
                    name     TEXT PRIMARY KEY,           -- 'shot-value' | 'playmaking' | 'rebounding'
                    season   TEXT NOT NULL,
                    data     JSONB NOT NULL,
                    built_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            # The commissioner's notes on stats pages (routes.py /admin/stats-notes; first used by /stats/defense, 2026-10-17):
            # one text per (page, season, team, key) — key is a player id or "pidA-pidB" for a pair. Admin only, never public.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS nba_stats_notes (
                    page       TEXT NOT NULL,
                    season     TEXT NOT NULL,
                    team       TEXT NOT NULL,
                    key        TEXT NOT NULL,
                    body       TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    PRIMARY KEY (page, season, team, key)
                )
            """)
            # Live games (live.py): the current state of each game being pulled, and a snapshot of every pull (kept, so a game
            # can be replayed to design the live look).
            cur.execute("""
                CREATE TABLE IF NOT EXISTS nba_live_state (
                    game_id    TEXT PRIMARY KEY,
                    status     TEXT NOT NULL,
                    period     INTEGER,
                    clock      TEXT,                 -- PT04M12.00S
                    clutch     BOOLEAN NOT NULL DEFAULT FALSE,
                    oncourt    JSONB,                -- player ids on the floor
                    home_score INTEGER,
                    away_score INTEGER,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS nba_live_snapshots (
                    id        BIGSERIAL PRIMARY KEY,
                    game_id   TEXT NOT NULL,
                    pulled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    period    INTEGER,
                    clock     TEXT,
                    status    TEXT,
                    players   JSONB NOT NULL
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS nba_live_snapshots_game ON nba_live_snapshots (game_id, pulled_at)")
            # The raw feed as it arrived (live.py): every box score pull, every 10th play-by-play pull + the final one —
            # so a game can be re-parsed later if the parsing was wrong.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS nba_live_raw (
                    id        BIGSERIAL PRIMARY KEY,
                    game_id   TEXT NOT NULL,
                    kind      TEXT NOT NULL,          -- boxscore / playbyplay
                    pulled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    payload   JSONB NOT NULL
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS nba_live_raw_game ON nba_live_raw (game_id, kind, pulled_at)")
            # A team's defensive line for one game (TEAM scoring, TEAM_SCORING.md): what the opponent got and what the
            # defense forced. Points allowed come from nba_games' final scores.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS nba_team_game_stats (
                    game_id           TEXT NOT NULL,
                    team              TEXT NOT NULL,       -- tricode
                    season            TEXT NOT NULL,
                    game_date         DATE NOT NULL,
                    opp_pts_fb        INTEGER,             -- opponent fast-break points (TeamGameLogs Misc)
                    opp_pts_paint     INTEGER,             -- opponent points in the paint
                    opp_tov           INTEGER,             -- opponent turnovers incl. team turnovers (team logs)
                    dreb              INTEGER,
                    opp_dreb          INTEGER,
                    shot_clock_forced INTEGER,             -- the opponent's own shot clock violations that day
                    loaded_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
                    PRIMARY KEY (game_id, team)
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS nba_team_game_stats_season ON nba_team_game_stats (season, team)")

            # Who's injured right now (injuries.py, ESPN feed every 30 min). Present state only: each sync replaces
            # every row; a player not listed is healthy.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS nba_injuries (
                    player_id   TEXT,                    -- our NBA player id; NULL if the name didn't match
                    espn_id     TEXT,
                    name        TEXT NOT NULL,
                    team        TEXT,                    -- tricode
                    status      TEXT,                    -- Out / Day-To-Day / Out For Season / Suspension
                    short       TEXT,                    -- OUT / GTD / ...
                    injury      TEXT,                    -- "Left Ankle Sprain"
                    return_date DATE,                    -- ESPN's estimate, when given
                    comment     TEXT,
                    reported_at TIMESTAMPTZ,
                    synced_at   TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS nba_injuries_player ON nba_injuries (player_id)")
            # Shot charts drawn by nba-pipeline (models/shot_chart_batch.py) and uploaded with the internal key:
            # one SVG per player per season, replaced whole on each rebuild.
            cur.execute("""
                CREATE TABLE IF NOT EXISTS nba_shot_charts (
                    season    TEXT NOT NULL,            -- '2025-26'
                    player_id TEXT NOT NULL,
                    svg       TEXT NOT NULL,
                    built_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                    PRIMARY KEY (season, player_id)
                )
            """)
        conn.commit()
    finally:
        conn.close()
