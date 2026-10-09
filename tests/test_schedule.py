"""Matchup schedule: an even round robin — everyone plays everyone once before anyone repeats."""
import itertools

import pytest

from backend.fantasy_2026_27.engine import pairings, week_pairings


def teams(n):
    return [{"id": f"t{i}", "name": f"Team {i:02d}"} for i in range(n)]


@pytest.mark.parametrize("n", [4, 5, 6, 8, 10, 12])
def test_each_cycle_meets_everyone_once(n):
    ts = teams(n)
    cycle = n - 1 if n % 2 == 0 else n
    seen = []
    for week in range(1, cycle + 1):
        games = pairings(ts, week)
        ids = [t["id"] for g in games for t in g]
        assert len(ids) == len(set(ids)), "nobody plays twice in a week"
        assert len(games) == n // 2, "everyone plays (odd leagues: one team sits)"
        seen += [frozenset((a["id"], b["id"])) for a, b in games]
    assert sorted(seen, key=sorted) == sorted({frozenset(p) for p in itertools.combinations([t["id"] for t in ts], 2)}, key=sorted)


def test_next_cycle_repeats_the_first():
    ts = teams(6)
    assert [(a["id"], b["id"]) for a, b in pairings(ts, 1)] == [(a["id"], b["id"]) for a, b in pairings(ts, 6)]


def test_commissioner_override_wins():
    ts = teams(4)
    games = week_pairings(ts, 3, {3: [("t0", "t3"), ("t1", "t2")]})
    assert [(a["id"], b["id"]) for a, b in games] == [("t0", "t3"), ("t1", "t2")]
