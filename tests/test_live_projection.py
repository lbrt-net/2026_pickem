"""A game in progress is one more uncertain game, not a sure number (2026-11-08: a matchup read 0% at halftime)."""
from backend.fantasy_2026_27 import projections


def test_live_game_keeps_its_swing():
    # Flagg: best so far 31.5, tonight on pace for 39.5 at the half, nothing else left this week
    mean, var = projections.week_dist(30.0, 0.35, [], None, 31.5, None, [(39.5, 7.0, 1.0)])
    assert mean > 39.5          # the best of 31.5 and an uncertain 39.5 is above 39.5
    assert var > 10             # and it can still swing: no 0% / 100% while a game is on


def test_final_buzzer_is_settled():
    mean, var = projections.week_dist(30.0, 0.35, [], None, 31.5, None, [(39.5, 0.0, 1.0)])
    assert abs(mean - 39.5) < 0.1 and var < 0.1


def test_no_games_no_live_is_the_floor():
    assert projections.week_dist(30.0, 0.35, [], None, 31.5) == (31.5, 0.0)
