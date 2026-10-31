"""Weekly recap (recap.py): results, players of the week, free agents that beat a starter, the standings — and the
optional awards only when they qualify. Draft Value is live from Week 1's start."""
from datetime import date

from backend.fantasy_2026_27 import recap
from tests.integration.conftest import S


def test_week_report_after_the_week_ends(league):
    cur = league.cur
    assert recap.weekly(cur, S, 1) is None                       # week 1 isn't over
    league.clock(date(2025, 10, 27))
    r = recap.weekly(cur, S, 1)
    assert r and r["best"] in r["teams"] and r["worst"] in r["teams"]
    assert {p["position"] if p["kind"] == "player" else "TEAM" for p in r["players"]} <= {"G", "F", "C", "TEAM"}
    owned = {p["id"] for t in r["faces"].values() for p in t}
    assert all(f["id"] not in owned for f in r["free_agents"])    # free agents are nobody's
    assert len(r["standings"]) == len(r["teams"]) and r["gb"][-1]["week"] == 1
    assert "improbable" not in r["awards"] and "pickups" not in r["awards"]   # nothing qualified: no card
    assert recap.week_recap(cur, S, 1) == recap.week_recap(cur, S, 1)        # frozen once built
    assert [w["week"] for w in recap.recap(cur, S)["weeks"]] == [1]


def test_restat_rebuilds_a_frozen_week(league):
    """2026-10-26: a stat correction (clutch recount) reaches a frozen recap only through restat_week."""
    cur = league.cur
    league.clock(date(2025, 10, 27))
    before = recap.week_recap(cur, S, 1)
    star = before["players"][0]
    cur.execute("""UPDATE nba_player_games SET pts = pts + 50 WHERE player_id = %s AND game_id IN
                   (SELECT game_id FROM nba_games WHERE game_date BETWEEN '2025-10-20' AND '2025-10-26')""", (star["id"],))
    assert recap.week_recap(cur, S, 1) == before                     # still frozen
    out = recap.restat_week(cur, S, 1)
    assert out["old_recap"] == before
    new = next(p for p in out["recap"]["players"] if p["id"] == star["id"])
    assert new["score"] > star["score"]
    assert recap.week_recap(cur, S, 1) == out["recap"]               # frozen again


def test_draft_value_is_live(league):
    """2026-10-30: Draft Value counts the current week's games so far — no waiting for the week to end — and only
    regular-season weeks."""
    cur = league.cur
    from tests.integration.test_recap_draft import pool
    pool(cur)                                                     # a draft to value
    league.clock(date(2025, 10, 23))                              # mid week 1
    v = recap.draft_value(cur, S, recap.build_draft(cur, S))
    assert v is not None and "through" not in v
    assert isinstance(v["regrets"], list)                           # the Biggest regrets list (dropped picks)
    wk = [r["added_wk"] for r in v["regrets"]]
    assert wk == sorted(wk, reverse=True)                            # ranked by the per-week number it shows
    assert any(p["weeks"] == 1 for p in v["picks"])                  # week 1 counts while it's on
