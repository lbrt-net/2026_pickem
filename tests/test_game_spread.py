"""A player's swing (projections.game_cv) is his own, over his games in the last 20 weeks, no preseason blend (2026-10-27)."""
from datetime import date, timedelta

from backend.fantasy_2026_27 import projections

CURVE = {"e": [30.3, 36.47]}  # Edwards' preseason curve: swing 0.361 of his number
HOT_WEEK = [46.5, 17.0, 16.0, 79.0]  # Edwards' first 4 games, one a 34-point clutch night
STEADY = [33.0 + (8 if i % 2 else -8) for i in range(50)]  # swing 8 on 33


def test_swing_is_his_own_over_more_games():
    assert projections.game_cv(CURVE, HOT_WEEK) == projections.game_cv(CURVE, [])  # under 10 games: the preseason swing
    assert abs(projections.game_cv(CURVE, []) - 0.361) < 0.001
    own = projections.game_cv(CURVE, STEADY + HOT_WEEK)
    mean = sum(STEADY + HOT_WEEK) / 54
    assert abs(own - (sum((x - mean) ** 2 for x in STEADY + HOT_WEEK) / 54) ** 0.5 / mean) < 1e-9  # no preseason in it


def test_edwards_79_barely_moves():
    """Already 79 with 3 games left at 37.3: the week is 79 plus a small chance one beats it, not 79.6."""
    proj, _ = projections.week_dist(37.3, projections.game_cv(CURVE, STEADY + HOT_WEEK), [1.0, 1.0, 1.0], None, 79.0)
    assert 79.0 <= proj < 79.3


class _Cur:
    def __init__(self, last):
        self.last = last

    def execute(self, *a):
        pass

    def fetchone(self):
        return {"d": self.last}


def test_window_reaches_into_last_season_until_20_weeks_pass():
    start = date(2026, 10, 19)
    weeks = [{"week": i + 1, "start": start + timedelta(weeks=i), "end": start + timedelta(weeks=i, days=6)} for i in range(24)]
    last = date(2026, 4, 12)
    # week 2: 18 weeks still missing → the last 18 weeks of last season
    assert projections.spread_since(_Cur(last), "2026-27", weeks, date(2026, 10, 28)) == last - timedelta(days=7 * 18 - 1)
    # week 22: the 20 weeks are all this season
    assert projections.spread_since(_Cur(last), "2026-27", weeks, weeks[21]["start"]) == weeks[2]["start"]
    assert projections.spread_since(_Cur(None), "2026-27", weeks, date(2026, 10, 28)) is None
