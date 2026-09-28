from backend.db import get_db


def init_schema() -> None:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS fantasy_teams (
                    id   TEXT PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """)
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
                CREATE TABLE IF NOT EXISTS fantasy_rosters (
                    team_id   TEXT NOT NULL REFERENCES fantasy_teams(id),
                    player_id TEXT NOT NULL REFERENCES fantasy_players(id),
                    PRIMARY KEY (team_id, player_id)
                )
            """)

            cur.execute("SELECT COUNT(*) FROM fantasy_players")
            if cur.fetchone()["count"] == 0:
                _seed(cur)

        conn.commit()
    finally:
        conn.close()


def _seed(cur) -> None:
    teams = [
        ("t1", "Baseline Bandits"),
        ("t2", "Rim Reapers"),
        ("t3", "Baseline Bandits Jr"),
        ("t4", "Screen Time"),
        ("t5", "Full Court Press"),
        ("t6", "Buzzer Beaters"),
        ("t7", "Airball Assassins"),
        ("t8", "Triple Double Trouble"),
        ("t9", "Bench Mob"),
        ("t10", "Zero Dark Thirty"),
    ]
    for team_id, name in teams:
        cur.execute("INSERT INTO fantasy_teams (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING", (team_id, name))

    # id, name, pos, nba_team, gp, min, pts, off_reb, def_reb, ast, stl, blk, team_id (None = free agent)
    players = [
        ("p1",  "Tyrese Haliburton",       "PG", "IND", 45, 32.5, 21.2, 0.7, 2.7, 10.8, 1.2, 0.3, "t1"),
        ("p2",  "Anthony Edwards",          "SG", "MIN", 48, 35.8, 27.6, 1.0, 4.8, 4.4,  1.3, 0.6, "t1"),
        ("p3",  "Jayson Tatum",             "SF", "BOS", 50, 36.0, 26.9, 1.1, 7.0, 4.9,  1.0, 0.6, "t1"),
        ("p4",  "Giannis Antetokounmpo",    "PF", "MIL", 46, 34.2, 30.4, 2.4, 9.1, 6.2,  1.1, 1.1, "t1"),
        ("p5",  "Nikola Jokic",             "C",  "DEN", 49, 34.6, 29.1, 2.9, 10.0, 10.2, 1.4, 0.8, "t1"),
        ("p6",  "Devin Booker",             "SG", "PHX", 44, 35.5, 25.3, 0.5, 4.0, 6.8,  0.9, 0.4, "t2"),
        ("p7",  "Domantas Sabonis",         "C",  "SAC", 47, 34.8, 19.4, 3.5, 9.7, 7.1,  0.7, 0.5, "t2"),
        ("p8",  "Jaylen Brown",             "SF", "BOS", 48, 34.0, 23.8, 1.0, 4.6, 3.5,  1.1, 0.4, "t3"),
        ("p9",  "Bam Adebayo",              "C",  "MIA", 45, 33.5, 18.7, 2.2, 7.7, 4.0,  1.1, 0.9, "t3"),
        ("p10", "Jalen Williams",           "SF", "OKC", 49, 33.0, 22.5, 1.0, 4.0, 4.8,  1.5, 0.9, "t4"),
        ("p11", "Alperen Sengun",           "C",  "HOU", 46, 32.0, 20.3, 2.8, 6.3, 5.2,  1.2, 0.8, "t4"),
        ("p12", "Coby White",               "PG", "CHI", 47, 34.5, 19.8, 0.6, 3.6, 5.1,  1.0, 0.2, "t5"),
        ("p13", "Jordan Poole",             "SG", "WAS", 42, 31.0, 18.2, 0.5, 2.7, 4.3,  0.8, 0.2, "t5"),
        ("p14", "Herbert Jones",            "SF", "NOP", 43, 28.5, 11.4, 0.9, 3.2, 2.1,  1.5, 0.9, "t6"),
        ("p15", "Deandre Ayton",            "C",  "POR", 44, 30.0, 16.8, 3.0, 7.5, 1.8,  0.5, 0.7, "t6"),
        ("p16", "Cam Johnson",              "SF", "BRK", 46, 29.5, 15.9, 0.9, 3.7, 2.4,  0.7, 0.4, "t7"),
        ("p17", "Franz Wagner",             "SF", "ORL", 48, 33.5, 21.0, 0.9, 4.6, 3.8,  1.0, 0.4, "t7"),
        ("p18", "Scottie Barnes",           "PF", "TOR", 47, 34.0, 18.5, 1.5, 6.6, 5.8,  1.2, 1.0, "t8"),
        ("p19", "Devin Vassell",            "SG", "SAS", 45, 31.5, 17.9, 0.6, 3.5, 2.9,  1.1, 0.6, "t8"),
        ("p20", "Jalen Suggs",              "PG", "ORL", 44, 29.0, 13.2, 0.7, 3.1, 2.9,  1.4, 0.5, "t9"),
        # Free agents — unassigned on purpose, so the Players page has real free agents to show
        ("p21", "Julius Randle",            "PF", "NYK", 46, 33.0, 24.0, 2.0, 7.0, 5.0,  0.8, 0.3, None),
        ("p22", "Paul George",              "SF", "PHI", 44, 34.0, 22.5, 0.9, 5.2, 3.9,  1.5, 0.4, None),
        ("p23", "Jalen Brunson",            "PG", "NYK", 48, 35.0, 26.0, 0.5, 2.9, 6.7,  0.9, 0.2, None),
        ("p24", "Joel Embiid",              "C",  "PHI", 40, 33.0, 31.0, 2.0, 8.5, 4.0,  1.0, 1.6, None),
    ]
    for pid, name, pos, nba_team, gp, mins, pts, off_reb, def_reb, ast, stl, blk, team_id in players:
        cur.execute("""
            INSERT INTO fantasy_players
                (id, name, position, nba_team, games_played, minutes, pts, off_reb, def_reb, ast, stl, blk)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (pid, name, pos, nba_team, gp, mins, pts, off_reb, def_reb, ast, stl, blk))
        if team_id:
            cur.execute(
                "INSERT INTO fantasy_rosters (team_id, player_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (team_id, pid)
            )
