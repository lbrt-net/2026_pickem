"""League activity: only moves that happened (a real drop at once, an add once he locks in), one entry per team per
week with the net change, never the impact number."""
from backend.fantasy_2026_27 import activity, transactions
from tests.integration.conftest import A, S

ADMIN = {"is_admin": True}


def entries(cur):
    return [e for e in activity.activity(cur, S)["entries"] if e["kind"] == "moves"]


def lock_in(cur, team, pid, week=1):
    cur.execute("INSERT INTO fantasy_lineups (scenario, team_id, week, entity_id, slot) VALUES (%s, %s, %s, %s, 'BENCH')", (S, team, week, pid))


def test_add_waits_for_his_lock_and_drops_show_at_once(league):
    cur = league.cur
    transactions.checkout(cur, S, ADMIN, A, ["pc2"], ["pb1"], apply=True)   # pb1 was drafted: a real drop
    [e] = entries(cur)
    assert [p["id"] for p in e["drops"]] == ["pb1"] and e["adds"] == []      # the add hasn't happened yet
    lock_in(cur, A, "pc2")
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
