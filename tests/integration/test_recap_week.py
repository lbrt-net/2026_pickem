"""Weekly recap (recap.py): results, players of the week, free agents that beat a starter, the standings — and the
optional awards only when they qualify. Draft Value appears once Week 1 is over."""
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
