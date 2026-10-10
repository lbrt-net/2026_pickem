"""Auction limits and who's in the draft pool."""
import pytest

from backend.fantasy_2026_27 import draft
from backend.fantasy_2026_27.logic import fits_somewhere

SLOTS = {"G": 1, "F": 1, "C": 1, "TEAM": 1, "FLEX": 1, "BENCH": 2}
SET = {"roster_slots": SLOTS, "auction_budget": 200, "auction_min_bid": 1, "auction_min_raise_pct": 4}


def picks(team, n, price=1):
    slots = ["G", "F", "C", "TEAM", "FLEX", "BENCH", "BENCH"]
    return [{"team_id": team, "price": price, "slot": slots[i], "player_id": f"p{i}", "nba_team_id": None} for i in range(n)]


def test_max_bid_is_everything_left():
    b = draft._budgets(SET, ["A"], picks("A", 1, 50))["A"]
    assert (b["remaining"], b["open_spots"], b["max_bid"]) == (150, 6, 150)


@pytest.mark.parametrize("high, next_bid", [(1, 2), (25, 26), (26, 28), (50, 52), (100, 104), (150, 156)])
def test_minimum_raise(high, next_bid):
    assert draft.min_next_bid(SET, high) == next_bid


def test_full_roster_can_not_bid():
    b = draft._budgets(SET, ["A"], picks("A", 7))["A"]
    assert not b["can_bid"] and b["max_bid"] == 0
    with pytest.raises(ValueError):
        draft._check_bid(SET, ["A"], picks("A", 7), "A", {"id": "x", "kind": "player", "position": "G", "name": "x"}, 1)


def test_no_money_can_not_bid():
    b = draft._budgets(SET, ["A"], picks("A", 1, 200))["A"]
    assert not b["can_bid"]
    with pytest.raises(ValueError):
        draft._check_bid(SET, ["A"], picks("A", 1, 200), "A", {"id": "x", "kind": "player", "position": "F", "name": "x"}, 1)


def test_cant_bid_over_what_you_have():
    with pytest.raises(ValueError):
        draft._check_bid(SET, ["A"], picks("A", 1, 50), "A", {"id": "x", "kind": "player", "position": "F", "name": "x"}, 151)


def test_pool_only_holds_entities_that_fit_a_spot():
    no_team_spot = {"G": 1, "F": 1, "C": 1}
    assert fits_somewhere({"kind": "player", "position": "G"}, no_team_spot)
    assert not fits_somewhere({"kind": "nba_team"}, no_team_spot), "no TM / Flex / Bench spot: NBA teams can't be drafted"
    assert not fits_somewhere({"kind": "player", "position": None}, no_team_spot), "no position and no Flex / Bench: out"
    assert fits_somewhere({"kind": "nba_team"}, SLOTS) and fits_somewhere({"kind": "player", "position": None}, SLOTS)
