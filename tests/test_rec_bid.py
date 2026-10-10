"""Rec bid (bid.py): personal to your roster, money and needs."""
from backend.fantasy_2026_27 import bid, draft

SLOTS = {"G": 1, "F": 1, "C": 1, "TEAM": 1, "FLEX": 1, "BENCH": 2}
SET = {"roster_slots": SLOTS, "auction_budget": 200, "auction_min_bid": 1, "auction_min_raise_pct": 4}


def pool():
    out = []
    for pos, top in (("G", 40), ("F", 38), ("C", 36)):
        out += [{"id": f"{pos}{i}", "kind": "player", "position": pos, "name": f"{pos}{i}", "pts": top - i * 1.2} for i in range(25)]
    out += [{"id": f"T{i}", "kind": "nba_team", "position": "TEAM", "name": f"T{i}", "pts": 33 - i} for i in range(20)]
    return out


def pick(team, eid, slot, price):
    nba = eid.startswith("T")
    return {"team_id": team, "player_id": None if nba else eid, "nba_team_id": eid if nba else None, "slot": slot, "price": price}


ORDER = ["A", "B", "C", "D", "E"]


def recs(picks, team="A"):
    return bid.rec_bids(pool(), picks, SET, draft._budgets(SET, ORDER, picks), team)


def test_never_above_safe_max_and_at_least_minimum():
    r = recs([])
    b = draft._budgets(SET, ORDER, [])["A"]
    assert all(SET["auction_min_bid"] <= v <= b["safe_max"] for v in r.values())


def test_better_player_worth_at_least_as_much():
    r = recs([])
    assert r["G0"] >= r["G10"] >= r["G20"]


def test_open_starting_spots_come_first():
    # A has G and FLEX filled by guards: another guard could only sit on the bench.
    picks = [pick("A", "G0", "G", 60), pick("A", "G1", "FLEX", 40)]
    r = recs(picks)
    best_open = min(max(v for k, v in r.items() if k.startswith(p)) for p in ("F", "C", "T"))
    assert max(v for k, v in r.items() if k.startswith("G")) < best_open


def test_full_roster_gets_no_recs():
    picks = [pick("A", x, s, 1) for x, s in [("G0", "G"), ("F0", "F"), ("C0", "C"), ("T0", "TEAM"), ("G1", "FLEX"), ("G2", "BENCH"), ("G3", "BENCH")]]
    assert recs(picks) == {}
