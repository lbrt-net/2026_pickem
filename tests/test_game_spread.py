"""A player's game-to-game spread (projections.game_cv) comes from his last 82 games, not his last 4 weeks (2026-10-27)."""
from backend.fantasy_2026_27 import projections

CURVE = {"e": [30.3, 36.47]}  # Edwards' preseason curve: spread 0.361 of his number


def test_spread_uses_his_last_82_games():
    hot_week = [46.5, 17.0, 16.0, 79.0]  # Edwards' first 4 games, one a 34-point clutch night
    last_season = [33.0 + (8 if i % 2 else -8) for i in range(100)]  # steady: spread 8 on 33
    only_4 = projections.game_cv(CURVE, hot_week)
    long = projections.game_cv(CURVE, last_season + hot_week)
    assert only_4 > 0.55  # 4 games alone: a spread no star really has
    assert long < 0.40
    # only the last 82 count: older games drop out
    assert projections.game_cv(CURVE, [0.0] * 50 + last_season + hot_week) == long


def test_edwards_79_barely_moves():
    """Already 79 with 3 games left at 37.3: the week is 79 plus a small chance one beats it, not 79.6."""
    cv = projections.game_cv(CURVE, [33.0 + (8 if i % 2 else -8) for i in range(78)] + [46.5, 17.0, 16.0, 79.0])
    proj, _ = projections.week_dist(37.3, cv, [1.0, 1.0, 1.0], None, 79.0)
    assert 79.0 <= proj < 79.3
