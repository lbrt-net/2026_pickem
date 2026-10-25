"""Lineup history is saved at locks (etch.etch_league, run by nba/scheduler.py at each lock moment): only entities
whose first game of the week has locked get a row; a second run writes nothing; later moves don't change it."""
from datetime import date

import pytest

from backend.fantasy_2026_27 import etch
from tests.integration.conftest import A, S


def rows(cur):
    cur.execute("SELECT team_id, entity_id, slot FROM fantasy_lock_ledger WHERE scenario = %s AND week = 1 ORDER BY 1, 2", (S,))  # the roster lock record
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


def test_live_lock_record_can_never_be_changed_or_deleted(league):
    """THE ROSTER LOCK RECORD is carved in metal (2026-10-24): in the live league the database refuses any edit or
    deletion, whatever code tries it."""
    import psycopg2
    cur = league.cur
    cur.execute("""INSERT INTO fantasy_lock_ledger (scenario, team_id, week, slot, spot_no, entity_id, entity_kind, locked_at)
                   VALUES ('live', 'live:t', 1, 'BENCH', 0, 'p1', 'player', now())""")
    for sql in ("UPDATE fantasy_lock_ledger SET entity_id = 'p2' WHERE scenario = 'live'",
                "DELETE FROM fantasy_lock_ledger WHERE scenario = 'live'",
                "TRUNCATE fantasy_lock_ledger"):
        cur.execute("SAVEPOINT s")
        with pytest.raises(psycopg2.Error, match="permanent"):
            cur.execute(sql)
        cur.execute("ROLLBACK TO SAVEPOINT s")


def test_a_locked_spot_never_takes_a_second_player(league):
    """A spot kind with every spot locked can't take anyone: the database refuses a spot that doesn't exist."""
    import psycopg2
    cur = league.cur
    cur.execute("""INSERT INTO fantasy_lock_ledger (scenario, team_id, week, slot, spot_no, entity_id, entity_kind, locked_at)
                   VALUES (%s, %s, 1, 'BENCH', 0, 'pc1', 'player', now())""", (S, A))
    cur.execute("SAVEPOINT s")
    with pytest.raises(psycopg2.Error, match="no such spot"):   # this league has 1 bench spot
        cur.execute("""INSERT INTO fantasy_lock_ledger (scenario, team_id, week, slot, spot_no, entity_id, entity_kind, locked_at)
                       VALUES (%s, %s, 1, 'BENCH', 1, 'pc2', 'player', now())""", (S, A))
    cur.execute("ROLLBACK TO SAVEPOINT s")
    with pytest.raises(psycopg2.Error):                          # and spot 0 is taken
        cur.execute("""INSERT INTO fantasy_lock_ledger (scenario, team_id, week, slot, spot_no, entity_id, entity_kind, locked_at)
                       VALUES (%s, %s, 1, 'BENCH', 0, 'pc2', 'player', now())""", (S, A))
