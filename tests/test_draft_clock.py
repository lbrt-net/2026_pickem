"""Chess-clock bidding (+N s a bid, up to the full clock); end-of-draft nomination clock once no team still drafting has more than 25% of the budget (DECISIONS.md)."""
import pytest

from backend.fantasy_2026_27 import draft

S = {"nomination_seconds": 60, "late_nomination_seconds": 15, "auction_budget": 200}  # 25% = $50


def b(remaining, can_bid=True):
    return {"remaining": remaining, "can_bid": can_bid}


@pytest.mark.parametrize("budgets, secs", [
    ({"a": b(51), "b": b(10)}, 60),        # someone still has more than $50
    ({"a": b(50), "b": b(10)}, 15),        # nobody over $50 → the end-of-draft clock
    ({"a": b(120, False), "b": b(40)}, 15),  # a full roster's leftover money doesn't count
    ({}, 60),
])
def test_end_of_draft_clock_once_nobody_has_over_50(budgets, secs):
    assert draft.nomination_seconds(S, budgets) == secs


def test_each_bid_adds_three_seconds_up_to_the_full_clock():
    from datetime import datetime, timedelta, timezone
    now = datetime(2026, 10, 17, tzinfo=timezone.utc)
    st = {"bid_seconds": 10, "bid_increment_seconds": 3}
    assert draft.bid_deadline(st, now + timedelta(seconds=2), now) == now + timedelta(seconds=5)
    assert draft.bid_deadline(st, now + timedelta(seconds=9), now) == now + timedelta(seconds=10)  # capped
    assert draft.bid_deadline(st, now - timedelta(seconds=1), now) == now + timedelta(seconds=3)
