"""The win chance is a formula on the projections (2026-10-19): it can't disagree with the projected totals."""
from backend.fantasy_2026_27 import projections
from backend.fantasy_2026_27.winprob import formula


def test_follows_the_totals():
    a, b = [(40.0, 60.0), (30.0, 50.0)], [(35.0, 60.0), (30.0, 50.0)]
    assert formula(a, b) > 0.5 > formula(b, a)
    assert abs(formula(a, b) + formula(b, a) - 1) < 1e-12
    assert formula([(30.0, 50.0)], [(30.0, 50.0)]) == 0.5


def test_nothing_left_is_the_result():
    assert formula([(41.0, 0.0)], [(40.0, 0.0)]) == 1.0 and formula([(40.0, 0.0)], [(40.0, 0.0)]) == 0.5


def test_week_spread_shrinks_once_his_best_is_in():
    _, v_open = projections.week_dist(30.0, 0.35, [1, 1, 1], None, None)
    _, v_locked = projections.week_dist(30.0, 0.35, [1, 1, 1], None, 55.0)   # already scored 55: little upside left
    assert v_locked < v_open
