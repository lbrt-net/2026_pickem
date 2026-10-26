"""League activity: only moves that happened (a real drop at once, an add once he locks in), one entry per team per
week with the net change, never the impact number."""
from backend.fantasy_2026_27 import activity, transactions
from tests.integration.conftest import A, S

ADMIN = {"is_admin": True}


def entries(cur):
    return [e for e in activity.activity(cur, S)["entries"] if e["kind"] == "moves"]


def lock_in(cur, team, pid, week=1):
    # a lock = a row in the roster lock record
    cur.execute("SELECT count(*) AS n FROM fantasy_lock_ledger WHERE scenario = %s AND team_id = %s AND week = %s AND slot = 'BENCH'", (S, team, week))
    n = cur.fetchone()["n"]
    cur.execute("""INSERT INTO fantasy_lock_ledger (scenario, team_id, week, slot, spot_no, entity_id, entity_kind, locked_at)
                   VALUES (%s, %s, %s, 'BENCH', %s, %s, 'player', now())""", (S, team, week, n, pid))


def test_add_and_drop_show_together_at_once(league):
    """2026-10-25: the add shows with the drop it came with right away — no waiting for him to lock in."""
    cur = league.cur
    transactions.checkout(cur, S, ADMIN, A, ["pc2"], ["pb1"], apply=True)   # pb1 was drafted: a real drop
    [e] = entries(cur)
    assert [p["id"] for p in e["adds"]] == ["pc2"] and [p["id"] for p in e["drops"]] == ["pb1"]   # one entry, net change
    assert "_score" not in e and "impact" not in e


def test_add_then_drop_before_any_lock_never_shows(league):
    cur = league.cur
    transactions.checkout(cur, S, ADMIN, A, ["pc1"], [], apply=True)
    transactions.checkout(cur, S, ADMIN, A, [], ["pc1"], apply=True)
    assert entries(cur) == []


def test_drop_then_claim_back_in_the_same_week_is_no_change(league):
    cur = league.cur
    transactions.checkout(cur, S, ADMIN, A, [], ["pa1"], apply=True)           # drafted: a real drop
    cur.execute("INSERT INTO fantasy_transactions (scenario, team_id, kind, entity_id, asof, via) VALUES (%s, %s, 'add', 'pa1', '2025-10-20', 'waivers')", (S, A))
    lock_in(cur, A, "pa1")
    assert entries(cur) == []


def test_activity_with_a_loaded_pool(league):
    # 2026-10-21: with a pool loaded, the value lookup passed the whole pool where the season's name belonged and the
    # Home page's League activity failed every time (the other checks run without a pool)
    from datetime import date
    from psycopg2.extras import Json
    from backend.fantasy_2026_27 import activity
    from tests.integration.conftest import S
    cur = league.cur
    cur.execute("""INSERT INTO fantasy_pool (season, player_id, name, nba_team, proj_avg, proj_max, proj_weeks, source)
                   VALUES ('2025-26', 'pa1', 'A', 'AAA', 30, 40, %s, 'manual')""", (Json([{"week": 1, "games": 2, "plays": 1.8, "e": 38, "e_on": 39}]),))
    league.clock(date(2025, 10, 24))
    assert "entries" in activity.activity(cur, S)
