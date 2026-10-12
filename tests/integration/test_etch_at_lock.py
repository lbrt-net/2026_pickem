"""Lineup history is saved at locks (etch.etch_league, run by nba/scheduler.py at each lock moment): only entities
whose first game of the week has locked get a row; a second run writes nothing; later moves don't change it."""
from datetime import date

from backend.fantasy_2026_27 import etch
from tests.integration.conftest import S


def rows(cur):
    cur.execute("SELECT team_id, entity_id, slot FROM fantasy_lineups WHERE scenario = %s AND week = 1 ORDER BY 1, 2", (S,))
    return [tuple(r.values()) for r in cur.fetchall()]


def test_saved_at_lock_only_locked_once(league):
    cur = league.cur
    league.clock(date(2025, 10, 20))                    # Monday, no games yet: nobody locked
    assert etch.etch_league(cur, S) == 0 and rows(cur) == []
    league.clock(date(2025, 10, 21))                    # AAA and BBB play (g1): their players lock, CCC's don't
    assert etch.etch_league(cur, S) > 0
    saved = rows(cur)
    assert saved and {e for _, e, _ in saved} <= {"pa1", "pa2", "pb1", "pb2"}, "only locked players are saved"
    assert etch.etch_league(cur, S) == 0 and rows(cur) == saved, "a second run writes nothing"
