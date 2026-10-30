"""Injury updates in the Transaction Log (DECISIONS.md "Injury log", 2026-10-30): each injury sync logs what changed
between the old list and the new one, and the log shows it with the fantasy team that has the player now."""
from datetime import date

from backend.fantasy_2026_27 import transactions
from backend.nba import injuries
from tests.integration.conftest import A, S


def row(pid, status, ret=None, injury="Ankle"):
    return {"player_id": pid, "espn_id": f"e{pid}", "name": pid, "team": "BOS", "status": status, "injury": injury,
            "return_date": ret, "comment": None}


def test_changes_listed_status_return_cleared():
    old = [row("a", "Out", date(2026, 11, 5)), row("b", "Day-To-Day"), row("c", "Out"), row("d", "Out", date(2026, 11, 2))]
    new = [row("a", "Out", "2026-11-05"), row("b", "Out"), row("d", "Out", "2026-11-09"), row("e", "Day-To-Day")]
    ev = {e["player_id"]: e for e in injuries.changes(old, new)}
    assert "a" not in ev                                                    # same status, same date: nothing
    assert (ev["b"]["kind"], ev["b"]["prev_status"], ev["b"]["status"]) == ("status", "Day-To-Day", "Out")
    assert (ev["c"]["kind"], ev["c"]["prev_status"], ev["c"]["status"]) == ("cleared", "Out", None)
    assert (ev["d"]["kind"], ev["d"]["prev_return"], ev["d"]["return_date"]) == ("return", "2026-11-02", "2026-11-09")
    assert (ev["e"]["kind"], ev["e"]["prev_status"]) == ("listed", None)


def test_log_shows_updates_with_the_team_that_has_him(league):
    cur = league.cur
    injuries.record(cur, injuries.changes([], [row("pa1", "Out", "2026-11-05")]))
    injuries.record(cur, injuries.changes([row("pa1", "Out")], []))
    injuries.record(cur, injuries.changes([], [row("not-in-pool", "Out")]))   # not a pool player: not shown
    log = transactions.log(cur, S)["injuries"]
    assert [e["kind"] for e in log] == ["cleared", "listed"]                  # newest first
    assert all(e["player"]["id"] == "pa1" and e["team_id"] == A for e in log)
    assert log[1]["return_date"] == "2026-11-05"
    assert set(log[0]) >= {"mpg_now", "avg_now", "gp_now", "team_games", "mpg2", "avg2"}             # for the page's filters


def test_per_game_pools_seasons(league):
    assert transactions.past_season(1) == "2025-26" and transactions.past_season(2) == "2024-25"
    got = transactions.per_game(league.cur, [transactions.past_season(1), transactions.past_season(2)], "2")["pa1"]
    assert got["mpg2"] == 30.0 and got["avg2"] > 0 and got["gp2"] > 0                           # the test league's games are 2025-26
