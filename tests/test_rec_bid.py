"""Rec bid (bid.py, rebuilt 2026-10-15): personal to your roster, money and needs; other teams' money never moves it — across a spread of league setups (tests/leagues.py)."""
import pytest

from backend.fantasy_2026_27 import bid, draft
from tests.leagues import LEAGUES, settings, team_ids

IDS = [lg[0] for lg in LEAGUES]


def pool():
    out = []
    for pos, top in (("G", 40), ("F", 38), ("C", 36)):
        out += [{"id": f"{pos}{i}", "kind": "player", "position": pos, "name": f"{pos}{i}", "pts": top - i * 0.6} for i in range(60)]
    out += [{"id": f"N{i}", "kind": "nba_team", "position": "TEAM", "name": f"N{i}", "pts": 33 - i * 0.8} for i in range(30)]
    return out


def pick(team, eid, slot, price):
    nba = eid.startswith("N")
    return {"team_id": team, "player_id": None if nba else eid, "nba_team_id": eid if nba else None, "slot": slot, "price": price}


def recs(lg, picks):
    s = settings(lg)
    ids = team_ids(lg)
    return bid.rec_bids(pool(), picks, s, draft._budgets(s, ids, picks), ids[0]), draft._budgets(s, ids, picks)[ids[0]]


@pytest.mark.parametrize("lg", LEAGUES, ids=IDS)
def test_never_above_safe_max_and_at_least_minimum(lg):
    r, me = recs(lg, [])
    assert r and all(settings(lg)["auction_min_bid"] <= v <= me["safe_max"] for v in r.values())


@pytest.mark.parametrize("lg", LEAGUES, ids=IDS)
def test_better_player_worth_at_least_as_much(lg):
    r, _ = recs(lg, [])
    for pos in ("G", "F", "C"):
        if f"{pos}0" in r:
            vals = [r[f"{pos}{i}"] for i in range(0, 40, 5) if f"{pos}{i}" in r]
            assert vals == sorted(vals, reverse=True)


@pytest.mark.parametrize("lg", LEAGUES, ids=IDS)
def test_bench_only_is_the_minimum(lg):
    s = settings(lg)
    slots = s["roster_slots"]
    if not (slots.get("G") and slots.get("BENCH")):
        pytest.skip("layout has no bench spot for an extra guard")
    me = team_ids(lg)[0]
    # fill every spot a guard could start in (G and FLEX) with guards: another guard would only sit on the bench
    picks = [pick(me, f"G{i}", "G", 5) for i in range(slots.get("G", 0))]
    picks += [pick(me, f"G{10 + i}", "FLEX", 3) for i in range(slots.get("FLEX", 0))]
    r, _ = recs(lg, picks)
    assert all(v == s["auction_min_bid"] for k, v in r.items() if k.startswith("G"))


@pytest.mark.parametrize("lg", LEAGUES, ids=IDS)
def test_other_teams_money_never_moves_your_numbers(lg):
    # a team that overspent on a star can't bid on the next one: only who's left moves your Rec bids
    ids = team_ids(lg)
    s = settings(lg)
    cheap = [pick(ids[1], "C0", "C", s["auction_min_bid"])]
    pricey = [pick(ids[1], "C0", "C", s["auction_budget"] - 10)]
    a = bid.rec_bids(pool(), cheap, s, draft._budgets(s, ids, cheap), ids[0])
    b = bid.rec_bids(pool(), pricey, s, draft._budgets(s, ids, pricey), ids[0])
    assert a == b


@pytest.mark.parametrize("lg", LEAGUES, ids=IDS)
def test_full_roster_gets_no_recs(lg):
    s = settings(lg)
    me = team_ids(lg)[0]
    picks = [pick(me, f"G{i}" if t != "TEAM" else f"N{i}", t, 1) for i, t in enumerate(t for t, n in s["roster_slots"].items() for _ in range(n))]
    r, _ = recs(lg, picks)
    assert r == {}
