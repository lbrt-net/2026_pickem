"""One position per player (2026-10-17): the season pool's G/F/C overwrites a stale one in fantasy_players, so seating
and lineup rules agree with what the site shows (Sabonis: pool F, stale C → was seated at C in the live draft)."""
from backend.fantasy_2026_27 import draft, projections
from tests.integration.conftest import S


def test_pool_position_wins(league):
    cur = league.cur
    cur.execute("UPDATE fantasy_players SET position = 'C' WHERE id = 'pa2'")   # stale: the pool says F
    cur.execute("""INSERT INTO fantasy_pool (season, player_id, name, nba_team, position, source)
                   VALUES ('2025-26', 'pa2', 'Alpha Two', 'AAA', 'F', 'manual')""")
    assert draft.sync_positions(cur) >= 1
    cur.execute("SELECT position FROM fantasy_players WHERE id = 'pa2'")
    assert cur.fetchone()["position"] == "F"
    assert draft.sync_positions(cur) == 0                                       # nothing left to fix


def test_loading_the_pool_updates_positions(league):
    cur = league.cur
    cur.execute("UPDATE fantasy_players SET position = 'G' WHERE id = 'pb1'")
    cur.execute("""INSERT INTO fantasy_pool (season, player_id, name, nba_team, position, source)
                   VALUES ('2025-26', 'pb1', 'Beta One', 'BBB', 'C', 'manual')""")
    projections._ensure_players(cur, "2025-26")
    cur.execute("SELECT position FROM fantasy_players WHERE id = 'pb1'")
    assert cur.fetchone()["position"] == "C"
