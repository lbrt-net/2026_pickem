"""Late in an auction (no team still drafting has more than $50), nominating clocks are cut in half (DECISIONS.md)."""
import pytest

from backend.fantasy_2026_27 import draft

S = {"nomination_seconds": 60}


def b(remaining, can_bid=True):
    return {"remaining": remaining, "can_bid": can_bid}


@pytest.mark.parametrize("budgets, secs", [
    ({"a": b(51), "b": b(10)}, 60),        # someone still has more than $50
    ({"a": b(50), "b": b(10)}, 30),        # nobody over $50 → half
    ({"a": b(120, False), "b": b(40)}, 30),  # a full roster's leftover money doesn't count
    ({}, 60),
])
def test_half_clock_once_nobody_has_over_50(budgets, secs):
    assert draft.nomination_seconds(S, budgets) == secs


def test_never_under_ten_seconds():
    assert draft.nomination_seconds({"nomination_seconds": 12}, {"a": b(5)}) == 10
    assert draft.nomination_seconds({"nomination_seconds": 8}, {"a": b(5)}) == 8
