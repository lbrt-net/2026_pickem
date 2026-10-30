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


def test_a_report_update_is_one_change_not_cleared_plus_listed():
    """ESPN gives an updated entry a new id; the same player is still one change (2026-10-30 fix)."""
    old = [{**row("a", "Out", date(2026, 10, 30)), "espn_id": "111"}]
    new = [{**row("a", "Out", "2026-11-04"), "espn_id": "222"}]
    ev = injuries.changes(old, new)
    assert [(e["kind"], e["prev_return"], e["return_date"]) for e in ev] == [("return", "2026-10-30", "2026-11-04")]


def test_log_carries_status_now_missed_and_projection(league):
    cur = league.cur
    cur.execute("INSERT INTO nba_injuries (player_id, name, status) VALUES ('pa1', 'pa1', 'Day-To-Day')")
    injuries.record(cur, injuries.changes([], [row("pa1", "Out", "2026-11-05")]))
    e = transactions.log(cur, S)["injuries"][0]
    assert e["current"] == "Day-To-Day"                                      # the dot on the headshot: status now
    assert {"missed", "sat_since", "will_miss", "proj_mpg", "proj_avg"} <= set(e)
    assert isinstance(e["missed"], int)


def test_shown_time_is_espns_and_the_sync_time_is_kept(league):
    cur = league.cur
    injuries.record(cur, injuries.changes([], [{**row("pa1", "Out"), "reported_at": "2026-10-29T23:40:00Z"}]))
    e = transactions.log(cur, S)["injuries"][0]
    assert e["at"].startswith("2026-10-29T23:40") or e["at"].startswith("2026-10-29T18:40")
    assert e["synced_at"] != e["at"]                                         # our pull time stays on record


def test_total_out_is_the_whole_stint():
    from datetime import date
    from backend.fantasy_2026_27.transactions import _missed
    d = lambda n: date(2026, 10, n)
    # (date, game id, final): played g1, sat g2 before the report on the 28th, sat g3 and g4 after, g5 not played yet
    games = [(d(25), "g1", True), (d(27), "g2", True), (d(28), "g3", True), (d(29), "g4", True), (d(31), "g5", False)]
    out = _missed(games, {"g1"}, {"asof": d(28), "kind": "listed", "status": "Out", "return_date": date(2026, 11, 2)})
    assert out == {"missed": 1, "sat_since": 2, "will_miss": 1}
    back = _missed(games, {"g1", "g4"}, {"asof": d(28), "kind": "listed", "status": "Out", "return_date": date(2026, 11, 2)})
    assert back == {"missed": 1, "sat_since": 1, "will_miss": None}            # played g4: stint over
    cleared = _missed(games, {"g1"}, {"asof": d(28), "kind": "cleared", "status": None, "return_date": None})
    assert cleared["missed"] == 1 and cleared["sat_since"] == 0               # Luka: what he missed before
