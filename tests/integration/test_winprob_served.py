"""The win chance is served from the last build (fast); a roster change rebuilds it at once (2026-10-19)."""
from backend.fantasy_2026_27 import winprob
from tests.integration.conftest import S


def test_served_then_rebuilt_on_roster_change(league):
    cur = league.cur
    winprob._WP.clear()
    league.commit()
    first = winprob.served(cur, S, 1)
    t0 = winprob._WP[(S, 1)][0]
    assert winprob.served(cur, S, 1) == first and winprob._WP[(S, 1)][0] == t0   # second load: the saved one
    cur.execute("UPDATE fantasy_rosters SET slot = 'BENCH' WHERE scenario = %s AND player_id = 'pb1'", (S,))
    league.commit()
    winprob.served(cur, S, 1)
    assert winprob._WP[(S, 1)][0] > t0                                             # a move rebuilds right away
