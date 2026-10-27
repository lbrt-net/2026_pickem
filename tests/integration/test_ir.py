"""IR: only red / yellow-dot players, only with a confirm; locked there (no moves, no drop) for 4 weeks, counting this
week if he isn't locked yet;
extra room (doesn't count toward the roster); never scores."""
from datetime import date

import pytest

from backend.fantasy_2026_27 import engine, etch, lineup, transactions
from tests.integration.conftest import A, S

ADMIN = {"is_admin": True}


def hurt(cur, pid, status="Out"):
    cur.execute("INSERT INTO nba_injuries (player_id, name, status) VALUES (%s, %s, %s)", (pid, pid, status))


def slot_of(cur, pid):
    cur.execute("SELECT slot, ir_until FROM fantasy_rosters WHERE scenario = %s AND player_id = %s", (S, pid))
    return cur.fetchone()


def test_only_injured_players_with_a_confirm(league):
    cur = league.cur
    with pytest.raises(ValueError, match="injury report"):
        lineup.move(cur, S, ADMIN, A, "pa1", "IR", confirm=True)      # healthy: no
    hurt(cur, "pa1", "Day-To-Day")                                      # yellow dot
    with pytest.raises(ValueError, match="confirm"):
        lineup.move(cur, S, ADMIN, A, "pa1", "IR")                      # no confirm: no
    lineup.move(cur, S, ADMIN, A, "pa1", "IR", confirm=True)
    r = slot_of(cur, "pa1")
    assert r["slot"] == "IR" and r["ir_until"] == 4, "week 1, before his lock: weeks 1–4"


def test_ir_after_this_weeks_lock_is_the_next_4_weeks(league):
    """2026-10-27 (Banchero, moved before his week 2 lock: weeks 2–5; moved after it: 3–6)."""
    cur = league.cur
    hurt(cur, "pa1")
    league.commit()
    league.clock(date(2025, 10, 21))                                    # pa1's game day: locked for week 1
    lineup.move(cur, S, ADMIN, A, "pa1", "IR", confirm=True)
    assert slot_of(cur, "pa1")["ir_until"] == 5, "weeks 2–5"


def test_locked_on_ir_no_moves_no_drop_until_it_ends(league):
    cur = league.cur
    hurt(cur, "pa1")
    lineup.move(cur, S, ADMIN, A, "pa1", "IR", confirm=True)
    with pytest.raises(ValueError, match="locked on IR"):
        lineup.move(cur, S, ADMIN, A, "pa1", "G")
    with pytest.raises(ValueError, match="locked on IR"):
        transactions.checkout(cur, S, ADMIN, A, [], ["pa1"], apply=True)
    league.commit()
    league.clock(date(2025, 11, 24))                                    # week 6: the lock is over
    lineup.move(cur, S, ADMIN, A, "pa1", "G")
    assert slot_of(cur, "pa1")["slot"] == "G" and slot_of(cur, "pa1")["ir_until"] is None


def test_ir_is_extra_room(league):
    cur = league.cur
    transactions.checkout(cur, S, ADMIN, A, ["pc1", "pc2"], [], apply=True)   # A: 4 of 4 spots
    cur.execute("""SELECT id FROM fantasy_players p WHERE NOT EXISTS
                   (SELECT 1 FROM fantasy_rosters r WHERE r.scenario = %s AND r.player_id = p.id) AND position IN ('G', 'PG', 'SG') LIMIT 1""", (S,))
    extra = cur.fetchone()["id"]
    assert not transactions.checkout(cur, S, ADMIN, A, [extra], [], apply=False)["ok"], "full"
    hurt(cur, "pa1")
    lineup.move(cur, S, ADMIN, A, "pa1", "IR", confirm=True)
    assert transactions.checkout(cur, S, ADMIN, A, [extra], [], apply=False)["ok"], "his spot opened up"


def test_last_ir_week_frees_him_for_next_week(league):
    """IR in Week 1 (before his lock) → frozen through Week 4. During Week 4, looking at Week 5, he can move for Week 5;
    Week 4 itself keeps him on IR (the move applies next week), and the Week 4 view still refuses."""
    cur = league.cur
    hurt(cur, "pa1")
    lineup.move(cur, S, ADMIN, A, "pa1", "IR", confirm=True)           # Week 1: through Week 4
    league.commit()
    league.clock(date(2025, 11, 11))                                    # Week 4 (Nov 10–16)
    with pytest.raises(ValueError, match="locked on IR"):
        lineup.move(cur, S, ADMIN, A, "pa1", "G", week_no=4)
    out = lineup.move(cur, S, ADMIN, A, "pa1", "G", week_no=5)
    assert out["applies"] == "next_week"
    lg = engine.league(cur, S)
    wk4 = etch.week_lineups(cur, S, lg["season"], engine.weeks_for_league(cur, lg), engine.as_of(lg), A)[(A, 4)]
    assert {e["id"]: e["slot"] for e in wk4}["pa1"] == "IR", "his Week 4 stays IR in the history"


def test_nba_team_can_never_sit_on_ir(league):
    """lineup.move refuses, and the database itself refuses any other write."""
    import psycopg2
    cur = league.cur
    cur.execute("INSERT INTO fantasy_nba_teams (id, name) VALUES ('AAA', 'Alphas') ON CONFLICT (id) DO NOTHING")
    cur.execute("INSERT INTO fantasy_rosters (scenario, team_id, slot, nba_team_id) VALUES (%s, %s, 'BENCH', 'AAA')", (S, A))
    row = {"nba_team_id": "AAA"}
    with pytest.raises(ValueError, match="only players"):
        lineup.move(cur, S, ADMIN, A, row["nba_team_id"], "IR", confirm=True)
    with pytest.raises(psycopg2.errors.CheckViolation):
        cur.execute("UPDATE fantasy_rosters SET slot = 'IR' WHERE scenario = %s AND nba_team_id = %s", (S, row["nba_team_id"]))


def test_service_time_shows_ir_weeks_right_away(league):
    """2026-10-27 (Banchero): his IR weeks show on Service Time the moment he moves there, before any of them lock."""
    from fastapi.testclient import TestClient
    from backend.main import app
    hurt(league.cur, "pa1")
    lineup.move(league.cur, S, ADMIN, A, "pa1", "IR", confirm=True)    # week 1, before his lock: weeks 1–4
    league.commit()
    st = TestClient(app).get(f"/fantasy/2026_27/service-time?scenario={S}").json()
    pa1 = next(p for p in st["players"] if p["id"] == "pa1")
    assert [(w["week"], w["slot"]) for w in pa1["weeks"]] == [(1, "IR"), (2, "IR"), (3, "IR"), (4, "IR")]
