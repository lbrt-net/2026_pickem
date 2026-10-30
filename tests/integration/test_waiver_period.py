"""2026-10-29 fixes: the claim order is frozen per scoring period; every moved player carries how he moved (via);
Home activity groups a 2-week playoff round as one period; /pickem/2026/stats answers."""
from datetime import date

from backend.fantasy_2026_27 import activity, engine, player_page, trades, transactions, waivers
from tests.integration.conftest import A, B, C, S

ADMIN = {"is_admin": True, "discord_id": "admin"}


def test_claim_order_frozen_inside_a_period(league):
    """The order is reverse standings as they were at the period's first lock (Standings page order: win %, then PF,
    then name, turned around). A matchup that finishes mid-period doesn't reshuffle it; the next period picks it up."""
    cur = league.cur
    cur.execute("UPDATE nba_games SET status = 'scheduled' WHERE game_id = 'g2'")  # B's forward still to play
    league.clock(date(2025, 10, 21))                    # week 1, after its first lock (replay: the first game's day)
    live = lambda: [r["team"]["id"] for r in reversed(engine.results(cur, S)["standings"])]  # the old rule: standings now
    before, live_before = waivers._priority(cur, S), live()
    cur.execute("UPDATE nba_games SET status = 'final', updated_at = now() WHERE game_id = 'g2'")
    league.clock(date(2025, 10, 25))                    # B's last game is final: the matchup is decided mid-week
    table = engine.results(cur, S)["standings"]
    assert any(r["w"] for r in table), "precondition: a matchup finished inside the period"
    assert live() != live_before, "precondition: today's standings did reshuffle"
    assert waivers._priority(cur, S) == before, "a mid-period result never moves the order"
    assert [r["team_id"] for r in transactions.log(cur, S)["waiver_order"]] == before
    league.clock(date(2025, 10, 28))                    # week 2's first lock: week 1 counts now
    order = waivers._priority(cur, S)
    wk1 = waivers.base_standings(engine.results(cur, S), 2)
    assert order == [r["team"]["id"] for r in reversed(wk1)], "reverse of the Standings page's order"
    winner = next(r["team"]["id"] for r in wk1 if r["w"])
    assert order[-1] == winner and order != before


def test_trade_moves_carry_via_trade(league):
    """A traded player reads 'trade' — never a free-agent add — on the Transaction Log, the player page and Home."""
    cur = league.cur
    cur.execute("UPDATE fantasy_drafts SET status = 'complete' WHERE scenario = %s", (S,))
    cur.execute("SELECT id, owner_user_id FROM fantasy_teams WHERE scenario = %s", (S,))
    own = {r["id"]: {"discord_id": r["owner_user_id"]} for r in cur.fetchall()}
    tid = trades.propose(cur, S, own[A], A, B, ["pa1"], ["pb2"], [])
    trades.respond(cur, S, own[B], tid, "accept")
    trades.decide(cur, S, ADMIN, tid, True)
    transactions.checkout(cur, S, ADMIN, C, ["pc1"], [], apply=True)  # a plain free-agent add
    items = transactions.log(cur, S)["items"]
    vias = {(p["id"], side): p["via"] for g in items for side in ("adds", "drops") for p in g[side]}
    assert vias[("pa1", "adds")] == vias[("pa1", "drops")] == "trade"
    assert vias[("pb2", "adds")] == vias[("pb2", "drops")] == "trade"
    assert vias[("pc1", "adds")] is None
    moves = player_page._moves(cur, S, "pa1")
    assert {(m["k"], m["via"]) for m in moves if m["k"] != "draft"} == {("add", "trade"), ("drop", "trade")}
    ent = activity.activity(cur, S)["entries"]
    got = {(p["id"], side): p.get("via") for e in ent if e["kind"] == "moves" for side in ("adds", "drops") for p in e[side]}
    assert got.get(("pa1", "adds")) == "trade" and got.get(("pb2", "drops")) == "trade"
    assert got.get(("pc1", "adds")) is None


def test_pickem_stats_answers():
    """/pickem/2026/stats read a dict row with [0] (KeyError → 500)."""
    import os
    if not os.environ.get("TEST_DATABASE_URL"):
        return
    from fastapi.testclient import TestClient
    from backend.main import app
    from tests.integration.conftest import _fresh_schema
    _fresh_schema()
    r = TestClient(app).get("/pickem/2026/stats")
    assert r.status_code == 200 and isinstance(r.json()["user_count"], int)


def test_home_activity_one_entry_per_period(league):
    """A 2-week playoff round is one period (week = Mon–Sun, period = matchup unit): a team's moves in both legs are one
    Home entry, filed under the round's first week and named for the round."""
    from psycopg2.extras import Json
    cur = league.cur
    cur.execute("UPDATE fantasy_leagues SET settings = %s WHERE scenario = %s",
                (Json({"roster_slots": {"G": 1, "F": 1, "C": 1, "BENCH": 1}, "playoff_auto": False, "playoff_teams": 2,
                       "playoff_rounds": [{"name": "Championship", "weeks": 2}]}), S))
    cur.execute("UPDATE fantasy_drafts SET status = 'complete' WHERE scenario = %s", (S,))
    weeks = engine.weeks_for_league(cur, engine.league(cur, S))
    legs = [w for w in weeks if w["kind"] == "playoffs"]
    assert [w.get("leg") for w in legs] == [1, 2], "precondition: a 2-leg Championship"
    for pid, w, hour in (("pc1", legs[0], 1), ("pc2", legs[1], 2)):
        cur.execute("""INSERT INTO fantasy_transactions (scenario, team_id, kind, entity_id, slot, asof, at)
                       VALUES (%s, %s, 'add', %s, 'BENCH', %s, %s::timestamptz + %s * interval '1 hour')""",
                    (S, A, pid, w["start"], w["start"].isoformat() + " 12:00+00", hour))
    league.clock(legs[1]["end"])
    mine = [e for e in activity.activity(cur, S)["entries"] if e["kind"] == "moves" and e["team_id"] == A]
    assert len(mine) == 1, "both legs = one period = one entry"
    assert mine[0]["week"] == legs[0]["week"] and mine[0]["week_label"] == "Championship"
    assert {p["id"] for p in mine[0]["adds"]} == {"pc1", "pc2"}
