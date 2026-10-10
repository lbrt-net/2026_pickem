"""Bidding opens in draft order after the nominator: the next team right away, then +step per team in between;
the head start rotates with the nominator; 0 = everyone at once."""
from datetime import datetime, timedelta, timezone

from backend.fantasy_2026_27.draft import bid_opens_at

T0 = datetime(2026, 10, 20, 0, 0, tzinfo=timezone.utc)
ORDER = ["a", "b", "c", "d", "e"]


def lot(by):
    return {"opened_at": T0.isoformat(), "nominated_by": by}


def wait(team, by, step=250):
    return (bid_opens_at({"auction_open_step_ms": step}, ORDER, lot(by), team) - T0) / timedelta(milliseconds=1)


def test_opens_in_draft_order_after_the_nominator():
    assert [wait(t, "b") for t in ["c", "d", "e", "a"]] == [0, 250, 500, 750]


def test_wraps_around_and_rotates():
    assert [wait(t, "e") for t in ["a", "b", "c", "d"]] == [0, 250, 500, 750]


def test_off_means_all_at_once():
    assert {wait(t, "b", step=0) for t in ORDER} == {0}


def test_old_lot_without_open_time_is_open():
    assert bid_opens_at({"auction_open_step_ms": 250}, ORDER, {"nominated_by": "a"}, "c") is None
