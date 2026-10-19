"""Game factors net to zero (2026-10-18): over a whole schedule the average game's factor is exactly 1.0."""
import random
from datetime import date, timedelta

from backend.fantasy_2026_27 import opponent


def test_factors_average_one_over_a_schedule():
    rnd = random.Random(3)
    teams = [f"T{i:02d}" for i in range(30)]
    games, dates = [], {t: set() for t in teams}
    start = date(2026, 10, 20)
    for day in range(160):  # ~1230 games, random pairings, some back-to-backs
        d = start + timedelta(days=day)
        pool = rnd.sample(teams, rnd.choice([10, 14, 18, 20]))
        for h, a in zip(pool[::2], pool[1::2]):
            games.append((h, a, d))
            dates[h].add(d)
            dates[a].add(d)
    # ratings: each team's own number, the league average = the game-weighted mean
    raw = {t: (110 + rnd.uniform(-6, 6), 99 + rnd.uniform(-3, 3), rnd.uniform(-10, 10)) for t in teams}
    n = {t: len(dates[t]) for t in teams}
    lg = tuple(sum(raw[t][i] * n[t] for t in teams) / sum(n.values()) for i in range(3))
    n_all = sum(len(ds) for ds in dates.values())
    tbl = {"rating": raw, "lg": lg, "dates": dates,
           "b2b_share": sum(1 for ds in dates.values() for d in ds if d - timedelta(days=1) in ds) / n_all}
    fs = [opponent.factor(tbl, opp, home, d) for h, a, d in games for opp, home in ((a, True), (h, False))]
    assert abs(sum(fs) / len(fs) - 1.0) < 1e-9
