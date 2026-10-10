"""Matchup schedule (set automatically): fair over a whole season — any team count, any season length.
- Even number of teams: every team plays exactly one game every week.
- Odd number: one bye a week, spread evenly (every team's bye count within 1 of the others).
- Every pair of teams meets about as often as every other pair (within 1)."""
import itertools
from collections import Counter

import pytest

from backend.fantasy_2026_27.engine import pairings, week_pairings



def teams(n):
    return [{"id": f"t{i}", "name": f"Team {i:02d}"} for i in range(n)]


@pytest.mark.parametrize("weeks", [10, 14, 19, 22])
@pytest.mark.parametrize("n", [4, 5, 6, 7, 8, 9, 10, 12, 14, 16])
def test_season_is_fair(n, weeks):
    ts = teams(n)
    ids = [t["id"] for t in ts]
    games, byes, meetings = Counter(), Counter(), Counter()
    for week in range(1, weeks + 1):
        played = [t["id"] for g in pairings(ts, week) for t in g]
        assert len(played) == len(set(played)), f"week {week}: someone plays twice"
        for i in ids:
            games[i] += played.count(i)
            byes[i] += i not in played
        for a, b in pairings(ts, week):
            meetings[frozenset((a["id"], b["id"]))] += 1
    if n % 2 == 0:
        assert all(byes[i] == 0 for i in ids), "even leagues: everyone plays every week"
        assert all(games[i] == weeks for i in ids)
    else:
        assert sum(byes.values()) == weeks, "odd leagues: exactly one bye a week"
        assert max(byes.values()) - min(byes.values()) <= 1, f"byes uneven: {dict(byes)}"
    counts = [meetings[frozenset(p)] for p in itertools.combinations(ids, 2)]
    assert max(counts) - min(counts) <= 1, "every pair meets about as often"


def test_commissioner_override_wins():
    ts = teams(4)
    games = week_pairings(ts, 3, {3: [("t0", "t3"), ("t1", "t2")]})
    assert [(a["id"], b["id"]) for a, b in games] == [("t0", "t3"), ("t1", "t2")]
