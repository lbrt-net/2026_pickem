"""Roster fit: where a pick / add goes, whether a roster after add/drop is legal, auction budgets and raises."""
from datetime import date, datetime, timedelta, timezone

from backend.fantasy_2026_27 import draft, transactions
from backend.fantasy_2026_27.etch import joined_in_time
from backend.fantasy_2026_27.logic import open_slot

SLOTS = {"G": 1, "F": 1, "C": 1, "TEAM": 1, "FLEX": 1, "BENCH": 2}
P = lambda i, pos, slot=None: {"id": i, "kind": "player", "name": i, "position": pos, "slot": slot}
T = lambda i, slot=None: {"id": i, "kind": "nba_team", "name": i, "position": "TEAM", "slot": slot}


def test_open_slot_order_own_then_flex_then_bench():
    assert open_slot({}, P("a", "G"), SLOTS) == "G"
    assert open_slot({"G": 1}, P("a", "G"), SLOTS) == "FLEX"
    assert open_slot({"G": 1, "FLEX": 1}, P("a", "G"), SLOTS) == "BENCH"
    assert open_slot({"G": 1, "FLEX": 1, "BENCH": 2}, P("a", "G"), SLOTS) is None
    assert open_slot({}, T("BOS"), SLOTS) == "TEAM"


def test_checkout_seating_keeps_spots_and_fits_adds():
    kept = [P("g", "G", "G"), P("f", "F", "F")]
    seat = transactions._seat(kept, [P("c", "C")], SLOTS)
    assert seat == {"g": "G", "f": "F", "c": "C"}


def test_checkout_reseats_when_greedy_fails():
    # a C sits in FLEX; adding a C plus a G needs nothing special — but a full G and a G add must go FLEX → bench
    kept = [P("g1", "G", "G"), P("c1", "C", "FLEX"), T("BOS", "TEAM"), P("x", "F", "F"), P("b1", "G", "BENCH"), P("b2", "G", "BENCH")]
    seat = transactions._seat(kept, [P("c2", "C")], SLOTS)
    assert seat is not None and seat["c2"] in ("C", "FLEX") and seat["c1"] in ("C", "FLEX")


def test_checkout_rejects_over_the_limit():
    full = [P(f"p{i}", "G", s) for i, s in enumerate(["G", "FLEX", "BENCH", "BENCH"])] + [P("f", "F", "F"), P("c", "C", "C"), T("BOS", "TEAM")]
    assert transactions._seat(full, [P("new", "F")], SLOTS) is None
    assert "8 players for 7 spots" in transactions._why_not(full + [P("new", "F")], SLOTS)


def test_auction_budget_and_raise():
    s = {"roster_slots": SLOTS, "auction_budget": 200, "auction_min_bid": 1, "auction_min_raise_pct": 4}
    b = draft._budgets(s, ["A"], [{"team_id": "A", "price": 50}])["A"]
    assert b == {"spent": 50, "remaining": 150, "open_spots": 6, "safe_max": 145, "max_bid": 150, "can_bid": True}
    assert [draft.min_next_bid(s, h) for h in (1, 25, 26, 50, 100, 150)] == [2, 26, 28, 52, 104, 156]


def test_joined_before_lock():
    w = {"start": date(2026, 10, 19), "end": date(2026, 10, 25)}
    g = {"game_date": date(2026, 10, 21), "tipoff_utc": datetime(2026, 10, 22, 0, 0, tzinfo=timezone.utc)}
    drafted = {"added_asof": None}
    assert joined_in_time(drafted, w, g, replay=False)
    early = {"added_asof": date(2026, 10, 20), "added_at": g["tipoff_utc"] - timedelta(hours=2)}
    late = {"added_asof": date(2026, 10, 21), "added_at": g["tipoff_utc"] - timedelta(minutes=2)}  # inside the 5-min lock
    assert joined_in_time(early, w, g, replay=False)
    assert not joined_in_time(late, w, g, replay=False)
    # the replay treats the whole game day as played
    assert not joined_in_time({"added_asof": date(2026, 10, 21)}, w, g, replay=True)
    assert joined_in_time({"added_asof": date(2026, 10, 20)}, w, g, replay=True)
