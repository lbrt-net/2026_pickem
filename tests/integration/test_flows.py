"""Full flows on a real (throwaway) database: add/drop, waivers, the Transaction Log, lineup locks, weekly scores."""
from datetime import date

import pytest

from backend.fantasy_2026_27 import engine, etch, transactions, waivers
from backend.fantasy_2026_27.logic import player_points
from tests.integration.conftest import A, B, C, S

ADMIN = {"is_admin": True}


def roster(cur, team):
    cur.execute("SELECT player_id FROM fantasy_rosters WHERE scenario = %s AND team_id = %s", (S, team))
    return {r["player_id"] for r in cur.fetchall()}


def log(cur):
    return transactions.log(cur, S)


def week1_lineup(cur, team):
    lg = engine.league(cur, S)
    weeks = engine.weeks_for_league(cur, lg)
    return {e["id"] for e in etch.week_lineups(cur, S, lg["season"], weeks, engine.as_of(lg), team).get((team, 1), [])}


def test_add_then_drop_before_any_lock_is_not_a_real_move(league):
    cur = league.cur
    transactions.checkout(cur, S, ADMIN, A, ["pc1"], [], apply=True)
    assert "pc1" in roster(cur, A)
    assert log(cur)["adds"] == 1
    transactions.checkout(cur, S, ADMIN, A, [], ["pc1"], apply=True)   # same day, before his first game
    assert "pc1" not in roster(cur, A)
    assert log(cur)["items"] == [], "both moves erased"
    assert "pc1" not in waivers.on_waivers(cur, S), "straight back to free agents"


def test_real_drop_goes_to_waivers_and_claims_settle(league):
    cur = league.cur
    transactions.checkout(cur, S, ADMIN, A, [], ["pa1"], apply=True)    # drafted: a real drop
    held = waivers.on_waivers(cur, S)
    assert "pa1" in held and held["pa1"]["until_date"] == "2025-10-22"
    with pytest.raises(ValueError, match="waivers"):
        transactions.checkout(cur, S, ADMIN, A, ["pa1"], [], apply=True)  # not even the team that dropped him
    with pytest.raises(ValueError):
        waivers.claim(cur, S, ADMIN, B, "pc1", None)                      # free agents aren't claimed
    waivers.claim(cur, S, ADMIN, B, "pa1", None)
    waivers.claim(cur, S, ADMIN, C, "pa1", None)
    league.commit()
    league.clock(date(2025, 10, 22))                                       # 2 days later: settled
    assert waivers.process(cur, S) == 1
    owners = [t for t in (B, C) if "pa1" in roster(cur, t)]
    assert len(owners) == 1, "exactly one claim wins"
    cur.execute("SELECT team_id, status FROM fantasy_claims ORDER BY id")
    statuses = {r["team_id"]: r["status"] for r in cur.fetchall()}
    assert sorted(statuses.values()) == ["lost", "won"] and statuses[owners[0]] == "won"
    kinds = [(g["team_id"], g["via"], bool(g["adds"]), bool(g["drops"])) for g in log(cur)["items"]]
    assert (owners[0], "waivers", True, False) in kinds and (A, None, False, True) in kinds


def test_dropped_after_his_lock_still_counts_that_week(league):
    cur = league.cur
    league.clock(date(2025, 10, 21))                                       # pb1's game day: he's locked
    transactions.checkout(cur, S, ADMIN, A, [], ["pb1"], apply=True)
    league.commit()
    assert "pb1" not in roster(cur, A)
    assert "pb1" in week1_lineup(cur, A), "etched into week 1"
    cur.execute("UPDATE fantasy_leagues SET matchups = %s WHERE scenario = %s", ('{"1": [["%s", "%s"]]}' % (A, B), S))
    league.clock(date(2025, 10, 27))                                       # week 1 over (A plays B, no bye)
    res = engine.results(cur, S)
    week1 = res["weeks"][0]
    side = next(s for m in week1["matchups"] for s in (m["home"], m["away"]) if s["team"]["id"] == A)
    cur.execute("SELECT * FROM nba_player_games WHERE player_id = 'pb1'")
    best = max(player_points(r, None) for r in cur.fetchall())
    assert any(s["id"] == "pb1" and s["score"] == pytest.approx(best) for s in side["slots"]), "his best game counts for A"


def test_added_after_his_lock_counts_from_next_week(league):
    cur = league.cur
    league.clock(date(2025, 10, 22))                                       # pc2's first game (g3) is today: locked
    transactions.checkout(cur, S, ADMIN, A, ["pc2"], [], apply=True)
    league.commit()
    assert "pc2" in roster(cur, A)
    assert "pc2" not in week1_lineup(cur, A), "joined after his lock"


def test_cannot_add_someone_elses_player_or_overfill(league):
    cur = league.cur
    with pytest.raises(ValueError, match="is on"):
        transactions.checkout(cur, S, ADMIN, A, ["pa2"], [], apply=True)        # B's player
    transactions.checkout(cur, S, ADMIN, A, ["pc1", "pc2"], [], apply=True)    # A now 4 of 4 spots
    cur.execute("""SELECT id FROM fantasy_players p WHERE NOT EXISTS
                   (SELECT 1 FROM fantasy_rosters r WHERE r.scenario = %s AND r.player_id = p.id) LIMIT 1""", (S,))
    extra = cur.fetchone()["id"]
    preview = transactions.checkout(cur, S, ADMIN, A, [extra], [], apply=False)
    assert not preview["ok"] and "spots" in preview["error"]
    with pytest.raises(ValueError, match="spots"):
        transactions.checkout(cur, S, ADMIN, A, [extra], [], apply=True)
    assert transactions.checkout(cur, S, ADMIN, A, [extra], ["pc2"], apply=False)["ok"], "swapping out the bench player fits"
