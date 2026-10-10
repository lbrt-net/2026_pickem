"""Full-flow checks against a throwaway Postgres (TEST_DATABASE_URL; skipped without one).

Each test gets a fresh database set up by the app's own startup code, then a small test league:
3 teams, 6 players on 3 NBA teams, a week of games (Mon Oct 20 – Sun Oct 26, 2025) and box scores.
Locally: scripts/test_db.sh start, then TEST_DATABASE_URL=postgresql://test@localhost:54329/pickem_test pytest
"""
import os
from datetime import date

import pytest
from psycopg2.extras import Json

if not os.environ.get("TEST_DATABASE_URL"):
    pytest.skip("no TEST_DATABASE_URL — full-flow checks need a throwaway Postgres", allow_module_level=True)

from backend import auth  # noqa: E402
from backend.db import get_db  # noqa: E402
from backend.nba import schema as nba_schema  # noqa: E402
from backend.pickem_2026 import schema as pickem_schema  # noqa: E402
from backend.fantasy_2026_27 import draft, schema as fantasy_schema  # noqa: E402

S = "replay"
A, B, C = "replay:fake-chika2", "replay:fake-wonton2", "replay:fake-mits2"
# id, name, position, NBA team
PLAYERS = [("pa1", "Alpha One", "G", "AAA"), ("pa2", "Alpha Two", "F", "AAA"), ("pb1", "Beta One", "C", "BBB"),
           ("pb2", "Beta Two", "G", "BBB"), ("pc1", "Cee One", "F", "CCC"), ("pc2", "Cee Two", "C", "CCC")]
# game id, date, home, away, home score, away score
GAMES = [("g1", date(2025, 10, 21), "AAA", "BBB", 110, 100), ("g2", date(2025, 10, 23), "AAA", "CCC", 99, 105),
         ("g3", date(2025, 10, 22), "BBB", "CCC", 120, 118)]
# player, game, pts, reb, ast
BOX = [("pa1", "g1", 30, 5, 5), ("pa1", "g2", 10, 2, 2), ("pb1", "g1", 20, 12, 1), ("pb1", "g3", 8, 6, 0),
       ("pb2", "g1", 15, 3, 7), ("pc1", "g2", 25, 6, 3), ("pc2", "g3", 12, 9, 2), ("pa2", "g2", 18, 7, 4)]
ROSTERS = [(A, "pa1", "G", 1), (A, "pb1", "C", 2), (B, "pa2", "F", 3), (B, "pb2", "G", 4)]


def _fresh_schema():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    conn.commit()
    conn.close()
    auth.init_schema()
    pickem_schema.init_schema()
    nba_schema.init_schema()
    fantasy_schema.init_schema()
    for cache in (draft._HOT, draft._REC_CACHE, draft._RANK_CACHE):
        cache.clear()


@pytest.fixture
def league():
    """A fresh test league; yields a cursor helper. Clock starts Mon Oct 20, 2025 (week 1 day 1)."""
    _fresh_schema()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE fantasy_leagues SET season = '2025-26', sim_date = %s, settings = %s WHERE scenario = %s",
                (date(2025, 10, 20), Json({"roster_slots": {"G": 1, "F": 1, "C": 1, "BENCH": 1}}), S))
    cur.execute("DELETE FROM fantasy_rosters WHERE scenario = %s", (S,))
    for pid, name, pos, team in PLAYERS:
        cur.execute("INSERT INTO fantasy_players (id, name, position, nba_team) VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO UPDATE "
                    "SET name = EXCLUDED.name, position = EXCLUDED.position, nba_team = EXCLUDED.nba_team", (pid, name, pos, team))
    for gid, d, home, away, hs, as_ in GAMES:
        cur.execute("""INSERT INTO nba_games (game_id, season, game_type, game_date, status, home_team, away_team, home_score, away_score)
                       VALUES (%s, '2025-26', 'regular', %s, 'final', %s, %s, %s, %s)""", (gid, d, home, away, hs, as_))
    # one filler game a week through the winter, so the season has room for its playoff and cutoff weeks
    for i in range(1, 14):
        cur.execute("""INSERT INTO nba_games (game_id, season, game_type, game_date, status, home_team, away_team)
                       VALUES (%s, '2025-26', 'regular', %s::date + %s * 7, 'scheduled', 'YYY', 'ZZZ')""", (f"f{i}", date(2025, 10, 21), i))
    team_of = {p[0]: p[3] for p in PLAYERS}
    for pid, gid, pts, reb, ast in BOX:
        cur.execute("""INSERT INTO nba_player_games (game_id, player_id, season, player_name, team, starter, minutes, pts, dreb, ast, fgm, fga)
                       VALUES (%s, %s, '2025-26', %s, %s, TRUE, 30, %s, %s, %s, %s, %s)""",
                    (gid, pid, pid, team_of[pid], pts, reb, ast, pts // 2, pts // 2))
    for team, pid, slot, n in ROSTERS:
        cur.execute("INSERT INTO fantasy_rosters (scenario, team_id, slot, player_id, pick_no) VALUES (%s, %s, %s, %s, %s)",
                    (S, team, slot, pid, n))
    conn.commit()

    class League:
        def __init__(self):
            self.conn, self.cur = conn, cur

        def clock(self, d):
            self.cur.execute("UPDATE fantasy_leagues SET sim_date = %s WHERE scenario = %s", (d, S))
            self.conn.commit()

        def commit(self):
            self.conn.commit()

    yield League()
    conn.rollback()
    conn.close()
