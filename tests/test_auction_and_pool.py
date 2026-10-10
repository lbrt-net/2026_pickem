"""Auction limits and who's in the draft pool — across a spread of league setups (tests/leagues.py)."""
import math

import pytest

from backend.fantasy_2026_27 import draft
from backend.fantasy_2026_27.logic import fits_somewhere
from tests.leagues import LAYOUTS, LEAGUES, settings

IDS = [lg[0] for lg in LEAGUES]


def spots(s):
    return [t for t, n in s["roster_slots"].items() for _ in range(n)]


def buys(s, team, n, price):
    return [{"team_id": team, "price": price, "slot": spots(s)[i], "player_id": f"p{i}", "nba_team_id": None} for i in range(n)]


def anyone(s):
    """A player who fits the first spot type in this layout."""
    t = next(iter(s["roster_slots"]))
    return {"id": "x", "name": "x", "kind": "nba_team" if t == "TEAM" else "player", "position": t if t in ("G", "F", "C") else "G"}


@pytest.mark.parametrize("lg", LEAGUES, ids=IDS)
def test_max_bid_is_everything_left(lg):
    s = settings(lg)
    price = s["auction_budget"] // 4
    b = draft._budgets(s, ["A"], buys(s, "A", 1, price))["A"]
    assert b["remaining"] == s["auction_budget"] - price
    assert b["open_spots"] == len(spots(s)) - 1
    assert b["max_bid"] == b["remaining"]
    assert b["safe_max"] == max(b["remaining"] - s["auction_min_bid"] * (b["open_spots"] - 1), 0)


@pytest.mark.parametrize("lg", LEAGUES, ids=IDS)
@pytest.mark.parametrize("high", [1, 7, 25, 26, 99, 150, 401])
def test_minimum_raise(lg, high):
    s = settings(lg)
    nxt = draft.min_next_bid(s, high)
    assert nxt - high >= 1, "always at least $1"
    assert nxt - high == max(1, math.ceil(high * s["auction_min_raise_pct"] / 100 - 1e-9)), "the league's % of the high bid, rounded up"


@pytest.mark.parametrize("lg", LEAGUES, ids=IDS)
def test_full_roster_can_not_bid(lg):
    s = settings(lg)
    full = buys(s, "A", len(spots(s)), s["auction_min_bid"])
    assert not draft._budgets(s, ["A"], full)["A"]["can_bid"]
    with pytest.raises(ValueError):
        draft._check_bid(s, ["A"], full, "A", anyone(s), s["auction_min_bid"])


@pytest.mark.parametrize("lg", LEAGUES, ids=IDS)
def test_no_money_can_not_bid(lg):
    s = settings(lg)
    broke = buys(s, "A", 1, s["auction_budget"])
    assert not draft._budgets(s, ["A"], broke)["A"]["can_bid"]
    with pytest.raises(ValueError):
        draft._check_bid(s, ["A"], broke, "A", anyone(s), s["auction_min_bid"])


@pytest.mark.parametrize("lg", LEAGUES, ids=IDS)
def test_cant_bid_over_what_you_have_or_under_the_minimum(lg):
    s = settings(lg)
    have = buys(s, "A", 1, s["auction_min_bid"])
    left = s["auction_budget"] - s["auction_min_bid"]
    with pytest.raises(ValueError):
        draft._check_bid(s, ["A"], have, "A", anyone(s), left + 1)
    if s["auction_min_bid"] > 1:
        with pytest.raises(ValueError):
            draft._check_bid(s, ["A"], have, "A", anyone(s), s["auction_min_bid"] - 1)


@pytest.mark.parametrize("layout", list(LAYOUTS), ids=list(LAYOUTS))
def test_pool_only_holds_entities_that_fit_a_spot(layout):
    slots = LAYOUTS[layout]
    for pos in ("G", "F", "C"):
        assert fits_somewhere({"kind": "player", "position": pos}, slots) == bool(slots.get(pos) or slots.get("FLEX") or slots.get("BENCH"))
    assert fits_somewhere({"kind": "nba_team"}, slots) == bool(slots.get("TEAM") or slots.get("FLEX") or slots.get("BENCH"))
    assert fits_somewhere({"kind": "player", "position": None}, slots) == bool(slots.get("FLEX") or slots.get("BENCH"))
