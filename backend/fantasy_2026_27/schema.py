import hashlib

from backend.db import get_db

from .logic import simulate_draft
from .settings import TEAM_COLORS, default_abbreviation, default_color

SCENARIOS = ("live", "test_pre", "test_post", "replay")
# Each sandbox is a league with an NBA season and a clock. sim_date NULL = real today.
LEAGUE_DEFAULTS = {"live": "2026-27", "test_pre": "2026-27", "test_post": "2026-27", "replay": "2025-26"}


def init_schema() -> None:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Earlier dummy version had 10 fake teams and no scenarios — it
            # held no real data, so drop it rather than migrate.
            cur.execute("""
                SELECT 1 FROM information_schema.tables WHERE table_name = 'fantasy_teams'
            """)
            if cur.fetchone():
                cur.execute("""
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'fantasy_teams' AND column_name = 'scenario'
                """)
                if not cur.fetchone():
                    cur.execute("DROP TABLE IF EXISTS fantasy_rosters")
                    cur.execute("DROP TABLE IF EXISTS fantasy_teams")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS fantasy_players (
                    id           TEXT PRIMARY KEY,
                    name         TEXT NOT NULL,
                    position     TEXT,
                    nba_team     TEXT,
                    games_played INTEGER NOT NULL DEFAULT 0,
                    minutes      FLOAT NOT NULL DEFAULT 0,
                    pts          FLOAT NOT NULL DEFAULT 0,
                    off_reb      FLOAT NOT NULL DEFAULT 0,
                    def_reb      FLOAT NOT NULL DEFAULT 0,
                    ast          FLOAT NOT NULL DEFAULT 0,
                    stl          FLOAT NOT NULL DEFAULT 0,
                    blk          FLOAT NOT NULL DEFAULT 0
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS fantasy_nba_teams (
                    id           TEXT PRIMARY KEY,
                    name         TEXT NOT NULL,
                    games_played INTEGER NOT NULL DEFAULT 0,
                    wins         INTEGER NOT NULL DEFAULT 0,
                    pts          FLOAT NOT NULL DEFAULT 0,
                    opp_pts      FLOAT NOT NULL DEFAULT 0
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS fantasy_teams (
                    id            TEXT PRIMARY KEY,
                    scenario      TEXT NOT NULL,
                    owner_user_id TEXT NOT NULL REFERENCES users(discord_id),
                    name          TEXT NOT NULL,
                    UNIQUE (scenario, owner_user_id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS fantasy_rosters (
                    id          SERIAL PRIMARY KEY,
                    scenario    TEXT NOT NULL,
                    team_id     TEXT NOT NULL REFERENCES fantasy_teams(id) ON DELETE CASCADE,
                    slot        TEXT NOT NULL,
                    player_id   TEXT REFERENCES fantasy_players(id),
                    nba_team_id TEXT REFERENCES fantasy_nba_teams(id),
                    CHECK ((player_id IS NULL) <> (nba_team_id IS NULL)),
                    UNIQUE (scenario, player_id),
                    UNIQUE (scenario, nba_team_id)
                )
            """)

            for col in ("fgm", "fga", "fg3m", "ftm", "fta", "tov"):
                cur.execute(f"ALTER TABLE fantasy_players ADD COLUMN IF NOT EXISTS {col} FLOAT NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE fantasy_players ADD COLUMN IF NOT EXISTS stats_season TEXT")
            cur.execute("ALTER TABLE fantasy_nba_teams ADD COLUMN IF NOT EXISTS stats_season TEXT")

            # Team settings (see settings.py).
            cur.execute("ALTER TABLE fantasy_teams ADD COLUMN IF NOT EXISTS abbreviation TEXT")
            cur.execute("ALTER TABLE fantasy_teams ADD COLUMN IF NOT EXISTS logo BYTEA")
            cur.execute("ALTER TABLE fantasy_teams ADD COLUMN IF NOT EXISTS logo_type TEXT")
            cur.execute("ALTER TABLE fantasy_teams ADD COLUMN IF NOT EXISTS logo_updated TIMESTAMPTZ")
            cur.execute("ALTER TABLE fantasy_teams ADD COLUMN IF NOT EXISTS color TEXT")
            cur.execute("ALTER TABLE fantasy_teams ADD COLUMN IF NOT EXISTS color_custom BOOLEAN NOT NULL DEFAULT FALSE")
            for scenario in SCENARIOS:
                assign_default_colors(cur, scenario)
            cur.execute("SELECT id, name FROM fantasy_teams WHERE abbreviation IS NULL")
            for t in cur.fetchall():
                cur.execute("UPDATE fantasy_teams SET abbreviation = %s WHERE id = %s", (default_abbreviation(t["name"]), t["id"]))
            cur.execute("""
                CREATE TABLE IF NOT EXISTS fantasy_notification_prefs (
                    discord_id TEXT NOT NULL REFERENCES users(discord_id),
                    category   TEXT NOT NULL,
                    enabled    BOOLEAN NOT NULL,
                    PRIMARY KEY (discord_id, category)
                )
            """)

            # Real players once box scores are loaded; the dummy pool only until then.
            cur.execute("SELECT count(*) AS n FROM fantasy_players")
            empty = cur.fetchone()["n"] == 0
            if (empty or _pool_is_dummy(cur)) and _stats_season(cur):
                try:
                    refresh_pool(cur)
                except PoolLocked:
                    pass
            elif empty:
                _seed_players(cur)
                _seed_nba_teams(cur)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS fantasy_leagues (
                    scenario   TEXT PRIMARY KEY,
                    season     TEXT NOT NULL,
                    sim_date   DATE,                 -- NULL = follow the real date
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            for scenario, season in LEAGUE_DEFAULTS.items():
                cur.execute("INSERT INTO fantasy_leagues (scenario, season) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                            (scenario, season))
            for scenario in SCENARIOS:
                ensure_teams(cur, scenario)

            # The post-draft sandbox should start out drafted.
            cur.execute("SELECT COUNT(*) FROM fantasy_rosters WHERE scenario = 'test_post'")
            if cur.fetchone()["count"] == 0:
                simulate_draft(cur, "test_post")

        conn.commit()
    finally:
        conn.close()


def ensure_teams(cur, scenario: str) -> None:
    """One fantasy team per visible pickem user, per scenario."""
    cur.execute("""
        SELECT discord_id, username FROM users u WHERE NOT is_hidden
          AND NOT EXISTS (SELECT 1 FROM fantasy_teams t WHERE t.id = %s || ':' || u.discord_id)
        ORDER BY discord_id
    """, (scenario,))
    for u in cur.fetchall():
        # Defaults: Discord display name, first 4 letters/numbers of it as the abbreviation.
        cur.execute("""
            INSERT INTO fantasy_teams (id, scenario, owner_user_id, name, abbreviation)
            VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING
        """, (f"{scenario}:{u['discord_id']}", scenario, u["discord_id"], u["username"][:50],
              default_abbreviation(u["username"])))
    assign_default_colors(cur, scenario)


def assign_default_colors(cur, scenario: str) -> None:
    """Give a default color to every team in the league that needs one: no color yet, or a
    non-custom color that isn't in TEAM_COLORS (the old hash formula). Custom picks and
    existing palette colors are kept, so adding colors to the palette changes nothing."""
    cur.execute("""
        SELECT t.id, t.color, t.color_custom, COALESCE(u.handle, u.username) AS uname
        FROM fantasy_teams t JOIN users u ON u.discord_id = t.owner_user_id
        WHERE t.scenario = %s ORDER BY t.owner_user_id
    """, (scenario,))
    teams = cur.fetchall()
    keep = lambda t: t["color_custom"] or t["color"] in TEAM_COLORS
    taken = {t["color"] for t in teams if keep(t)}
    for t in teams:
        if keep(t):
            continue
        color = default_color(t["uname"], taken)
        taken.add(color)
        cur.execute("UPDATE fantasy_teams SET color = %s WHERE id = %s", (color, t["id"]))


def _jitter(name: str, salt: str) -> float:
    """Deterministic 0.9–1.1 multiplier so dummy stat lines aren't identical."""
    h = int(hashlib.md5(f"{name}:{salt}".encode()).hexdigest()[:8], 16)
    return 0.9 + (h % 2001) / 10000


# Per-game stat template for a tier-1.0 player at each position.
_TEMPLATE = {
    "PG": dict(minutes=35, pts=26, off_reb=0.6, def_reb=4.0, ast=8.5, stl=1.3, blk=0.3),
    "SG": dict(minutes=34, pts=25, off_reb=0.7, def_reb=4.0, ast=5.0, stl=1.2, blk=0.4),
    "SF": dict(minutes=34, pts=24, off_reb=1.0, def_reb=5.5, ast=4.5, stl=1.2, blk=0.6),
    "PF": dict(minutes=33, pts=23, off_reb=2.0, def_reb=7.0, ast=3.5, stl=1.0, blk=1.1),
    "C":  dict(minutes=31, pts=20, off_reb=3.0, def_reb=8.5, ast=3.0, stl=0.8, blk=1.8),
}

# Original 24 hand-written lines, kept exactly as first seeded.
_FIXED = [
    ("p1",  "Tyrese Haliburton",     "PG", "IND", 45, 32.5, 21.2, 0.7, 2.7, 10.8, 1.2, 0.3),
    ("p2",  "Anthony Edwards",       "SG", "MIN", 48, 35.8, 27.6, 1.0, 4.8, 4.4,  1.3, 0.6),
    ("p3",  "Jayson Tatum",          "SF", "BOS", 50, 36.0, 26.9, 1.1, 7.0, 4.9,  1.0, 0.6),
    ("p4",  "Giannis Antetokounmpo", "PF", "MIL", 46, 34.2, 30.4, 2.4, 9.1, 6.2,  1.1, 1.1),
    ("p5",  "Nikola Jokic",          "C",  "DEN", 49, 34.6, 29.1, 2.9, 10.0, 10.2, 1.4, 0.8),
    ("p6",  "Devin Booker",          "SG", "PHX", 44, 35.5, 25.3, 0.5, 4.0, 6.8,  0.9, 0.4),
    ("p7",  "Domantas Sabonis",      "C",  "SAC", 47, 34.8, 19.4, 3.5, 9.7, 7.1,  0.7, 0.5),
    ("p8",  "Jaylen Brown",          "SF", "BOS", 48, 34.0, 23.8, 1.0, 4.6, 3.5,  1.1, 0.4),
    ("p9",  "Bam Adebayo",           "C",  "MIA", 45, 33.5, 18.7, 2.2, 7.7, 4.0,  1.1, 0.9),
    ("p10", "Jalen Williams",        "SF", "OKC", 49, 33.0, 22.5, 1.0, 4.0, 4.8,  1.5, 0.9),
    ("p11", "Alperen Sengun",        "C",  "HOU", 46, 32.0, 20.3, 2.8, 6.3, 5.2,  1.2, 0.8),
    ("p12", "Coby White",            "PG", "CHI", 47, 34.5, 19.8, 0.6, 3.6, 5.1,  1.0, 0.2),
    ("p13", "Jordan Poole",          "SG", "WAS", 42, 31.0, 18.2, 0.5, 2.7, 4.3,  0.8, 0.2),
    ("p14", "Herbert Jones",         "SF", "NOP", 43, 28.5, 11.4, 0.9, 3.2, 2.1,  1.5, 0.9),
    ("p15", "Deandre Ayton",         "C",  "POR", 44, 30.0, 16.8, 3.0, 7.5, 1.8,  0.5, 0.7),
    ("p16", "Cam Johnson",           "SF", "BRK", 46, 29.5, 15.9, 0.9, 3.7, 2.4,  0.7, 0.4),
    ("p17", "Franz Wagner",          "SF", "ORL", 48, 33.5, 21.0, 0.9, 4.6, 3.8,  1.0, 0.4),
    ("p18", "Scottie Barnes",        "PF", "TOR", 47, 34.0, 18.5, 1.5, 6.6, 5.8,  1.2, 1.0),
    ("p19", "Devin Vassell",         "SG", "SAS", 45, 31.5, 17.9, 0.6, 3.5, 2.9,  1.1, 0.6),
    ("p20", "Jalen Suggs",           "PG", "ORL", 44, 29.0, 13.2, 0.7, 3.1, 2.9,  1.4, 0.5),
    ("p21", "Julius Randle",         "PF", "NYK", 46, 33.0, 24.0, 2.0, 7.0, 5.0,  0.8, 0.3),
    ("p22", "Paul George",           "SF", "PHI", 44, 34.0, 22.5, 0.9, 5.2, 3.9,  1.5, 0.4),
    ("p23", "Jalen Brunson",         "PG", "NYK", 48, 35.0, 26.0, 0.5, 2.9, 6.7,  0.9, 0.2),
    ("p24", "Joel Embiid",           "C",  "PHI", 40, 33.0, 31.0, 2.0, 8.5, 4.0,  1.0, 1.6),
]

# Additional 56: (name, position, nba_team, tier). Stats derived from tier.
_GENERATED = [
    ("Luka Doncic", "PG", "LAL", 1.08), ("Shai Gilgeous-Alexander", "PG", "OKC", 1.10),
    ("Stephen Curry", "PG", "GSW", 0.98), ("Trae Young", "PG", "ATL", 0.95),
    ("Ja Morant", "PG", "MEM", 0.90), ("De'Aaron Fox", "PG", "SAS", 0.88),
    ("Damian Lillard", "PG", "MIL", 0.90), ("LaMelo Ball", "PG", "CHA", 0.92),
    ("Cade Cunningham", "PG", "DET", 0.97), ("Jamal Murray", "PG", "DEN", 0.84),
    ("Darius Garland", "PG", "CLE", 0.80), ("Tyrese Maxey", "PG", "PHI", 0.93),
    ("Donovan Mitchell", "SG", "CLE", 0.97), ("Jalen Green", "SG", "PHX", 0.82),
    ("Anfernee Simons", "SG", "POR", 0.78), ("Desmond Bane", "SG", "ORL", 0.80),
    ("Austin Reaves", "SG", "LAL", 0.80), ("Derrick White", "SG", "BOS", 0.76),
    ("Zach LaVine", "SG", "SAC", 0.83), ("CJ McCollum", "SG", "WAS", 0.74),
    ("Bradley Beal", "SG", "LAC", 0.70),
    ("LeBron James", "SF", "LAL", 0.97), ("Kevin Durant", "SF", "HOU", 0.98),
    ("Kawhi Leonard", "SF", "LAC", 0.92), ("Jimmy Butler", "SF", "GSW", 0.82),
    ("Mikal Bridges", "SF", "NYK", 0.76), ("Brandon Miller", "SF", "CHA", 0.80),
    ("Jaden McDaniels", "SF", "MIN", 0.66), ("OG Anunoby", "SF", "NYK", 0.72),
    ("Zion Williamson", "PF", "NOP", 0.92), ("Paolo Banchero", "PF", "ORL", 0.96),
    ("Evan Mobley", "PF", "CLE", 0.88), ("Jaren Jackson Jr.", "PF", "MEM", 0.86),
    ("Pascal Siakam", "PF", "IND", 0.84), ("Lauri Markkanen", "PF", "UTA", 0.82),
    ("Jabari Smith Jr.", "PF", "HOU", 0.70), ("Aaron Gordon", "PF", "DEN", 0.70),
    ("Anthony Davis", "PF", "DAL", 1.00), ("Jalen Johnson", "PF", "ATL", 0.86),
    ("Michael Porter Jr.", "PF", "BRK", 0.80), ("Keegan Murray", "PF", "SAC", 0.72),
    ("Victor Wembanyama", "C", "SAS", 1.10), ("Karl-Anthony Towns", "C", "NYK", 1.00),
    ("Rudy Gobert", "C", "MIN", 0.78), ("Chet Holmgren", "C", "OKC", 0.86),
    ("Jarrett Allen", "C", "CLE", 0.78), ("Myles Turner", "C", "MIL", 0.76),
    ("Nikola Vucevic", "C", "CHI", 0.84), ("Ivica Zubac", "C", "LAC", 0.80),
    ("Walker Kessler", "C", "UTA", 0.72), ("Jalen Duren", "C", "DET", 0.76),
    ("Brook Lopez", "C", "LAC", 0.64), ("Kristaps Porzingis", "C", "ATL", 0.80),
    ("Clint Capela", "C", "HOU", 0.62), ("Daniel Gafford", "C", "DAL", 0.66),
    ("Onyeka Okongwu", "C", "ATL", 0.72),
]


def _seed_players(cur) -> None:
    rows = list(_FIXED)
    for i, (name, pos, nba_team, tier) in enumerate(_GENERATED, start=25):
        t = _TEMPLATE[pos]
        minute_scale = 0.75 + 0.25 * tier  # minutes vary less than production
        stat = lambda k: round(t[k] * tier * _jitter(name, k), 1)
        rows.append((
            f"p{i}", name, pos, nba_team,
            int(38 + 60 * (_jitter(name, "gp") - 0.9)),  # 38–50 games
            round(t["minutes"] * minute_scale * _jitter(name, "min"), 1),
            stat("pts"), stat("off_reb"), stat("def_reb"), stat("ast"), stat("stl"), stat("blk"),
        ))
    for r in rows:
        cur.execute("""
            INSERT INTO fantasy_players
                (id, name, position, nba_team, games_played, minutes, pts, off_reb, def_reb, ast, stl, blk)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, r)


_NBA_TEAMS = [
    ("ATL", "Atlanta Hawks"), ("BOS", "Boston Celtics"), ("BKN", "Brooklyn Nets"),
    ("CHA", "Charlotte Hornets"), ("CHI", "Chicago Bulls"), ("CLE", "Cleveland Cavaliers"),
    ("DAL", "Dallas Mavericks"), ("DEN", "Denver Nuggets"), ("DET", "Detroit Pistons"),
    ("GSW", "Golden State Warriors"), ("HOU", "Houston Rockets"), ("IND", "Indiana Pacers"),
    ("LAC", "LA Clippers"), ("LAL", "LA Lakers"), ("MEM", "Memphis Grizzlies"),
    ("MIA", "Miami Heat"), ("MIL", "Milwaukee Bucks"), ("MIN", "Minnesota Timberwolves"),
    ("NOP", "New Orleans Pelicans"), ("NYK", "New York Knicks"), ("OKC", "Oklahoma City Thunder"),
    ("ORL", "Orlando Magic"), ("PHI", "Philadelphia 76ers"), ("PHX", "Phoenix Suns"),
    ("POR", "Portland Trail Blazers"), ("SAC", "Sacramento Kings"), ("SAS", "San Antonio Spurs"),
    ("TOR", "Toronto Raptors"), ("UTA", "Utah Jazz"), ("WAS", "Washington Wizards"),
]


def _seed_nba_teams(cur) -> None:
    for abbr, name in _NBA_TEAMS:
        gp = 50
        wins = int(10 + 30 * (_jitter(abbr, "w") - 0.9) / 0.2)  # 10–40 wins
        pts = round(112 * _jitter(abbr, "pts"), 1)
        opp = round(112 * _jitter(abbr, "opp"), 1)
        cur.execute("""
            INSERT INTO fantasy_nba_teams (id, name, games_played, wins, pts, opp_pts)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (abbr, name, gp, wins, pts, opp))


NBA_TEAM_NAMES = dict(_NBA_TEAMS)


class PoolLocked(Exception):
    pass


def _pool_is_dummy(cur) -> bool:
    cur.execute("SELECT 1 FROM fantasy_players WHERE id LIKE 'p%%' LIMIT 1")
    return cur.fetchone() is not None


def _stats_season(cur) -> str | None:
    """Most recent season with loaded box scores — the pool's stats come from it."""
    if not _has_table(cur, "nba_player_games"):
        return None
    cur.execute("""
        SELECT season FROM nba_player_games GROUP BY season HAVING count(*) > 1000 ORDER BY season DESC LIMIT 1
    """)
    row = cur.fetchone()
    return row["season"] if row else None


def _has_table(cur, name: str) -> bool:
    cur.execute("SELECT to_regclass(%s) AS t", (name,))
    return cur.fetchone()["t"] is not None


def refresh_pool(cur) -> dict:
    """Rebuild the draftable pool from real box scores: every player who played in
    the stats season (per-game averages over games played) and the 30 NBA teams.
    Refuses if the live league has rosters; resets test sandboxes (test_post re-drafted)."""
    season = _stats_season(cur)
    if not season:
        raise ValueError("no box scores loaded")
    cur.execute("SELECT count(*) AS n FROM fantasy_rosters WHERE scenario = 'live'")
    if cur.fetchone()["n"]:
        raise PoolLocked("live league has rosters; not touching the pool")

    cur.execute("DELETE FROM fantasy_rosters")
    cur.execute("DELETE FROM fantasy_players")
    cur.execute("""
        WITH played AS (          -- regular-season games actually played (game id "002…")
            SELECT * FROM nba_player_games
            WHERE season = %(s)s AND minutes > 0 AND substr(game_id, 3, 1) = '2'
        ), latest AS (            -- name + team from their last game
            SELECT DISTINCT ON (player_id) player_id, player_name, team
            FROM nba_player_games WHERE season = %(s)s AND substr(game_id, 3, 1) <> '3'  -- skip All-Star games
            ORDER BY player_id, game_id DESC
        ), pos AS (
            SELECT DISTINCT ON (player_id) player_id, position
            FROM nba_player_games WHERE position IS NOT NULL
            GROUP BY player_id, position ORDER BY player_id, count(*) DESC
        )
        INSERT INTO fantasy_players (id, name, position, nba_team, games_played, minutes, pts, off_reb, def_reb,
                                     ast, stl, blk, fgm, fga, fg3m, ftm, fta, tov, stats_season)
        SELECT p.player_id, l.player_name, pos.position, l.team, count(*),
               round(avg(minutes)::numeric, 1), round(avg(pts)::numeric, 1), round(avg(oreb)::numeric, 1),
               round(avg(dreb)::numeric, 1), round(avg(ast)::numeric, 1), round(avg(stl)::numeric, 1),
               round(avg(blk)::numeric, 1), round(avg(fgm)::numeric, 1), round(avg(fga)::numeric, 1),
               round(avg(fg3m)::numeric, 1), round(avg(ftm)::numeric, 1), round(avg(fta)::numeric, 1),
               round(avg(tov)::numeric, 1), %(s)s
        FROM played p JOIN latest l ON l.player_id = p.player_id LEFT JOIN pos ON pos.player_id = p.player_id
        GROUP BY p.player_id, l.player_name, l.team, pos.position
    """, {"s": season})
    cur.execute("SELECT count(*) AS n FROM fantasy_players")
    players = cur.fetchone()["n"]

    cur.execute("DELETE FROM fantasy_nba_teams")
    cur.execute("""
        WITH sides AS (
            SELECT home_team AS team, home_score AS pts, away_score AS opp FROM nba_games
            WHERE season = %(s)s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL
            UNION ALL
            SELECT away_team, away_score, home_score FROM nba_games
            WHERE season = %(s)s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL
        )
        SELECT team, count(*) AS gp, count(*) FILTER (WHERE pts > opp) AS wins,
               round(avg(pts)::numeric, 1) AS pts, round(avg(opp)::numeric, 1) AS opp
        FROM sides WHERE team IS NOT NULL AND pts IS NOT NULL GROUP BY team
    """, {"s": season})
    for t in cur.fetchall():
        cur.execute("""
            INSERT INTO fantasy_nba_teams (id, name, games_played, wins, pts, opp_pts, stats_season)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (t["team"], NBA_TEAM_NAMES.get(t["team"], t["team"]), t["gp"], t["wins"], t["pts"], t["opp"], season))
    cur.execute("SELECT count(*) AS n FROM fantasy_nba_teams")
    teams = cur.fetchone()["n"]

    for scenario in SCENARIOS:
        ensure_teams(cur, scenario)
    simulate_draft(cur, "test_post")
    return {"stats_season": season, "players": players, "nba_teams": teams}
