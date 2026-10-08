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
        conn.commit()
    finally:
        conn.close()
