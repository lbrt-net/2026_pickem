"""The win chance can't disagree with the projections (2026-10-18): each player's simulated week averages his projected week."""
import random

from backend.fantasy_2026_27 import winprob
from backend.fantasy_2026_27.lineup import _sim_scale


def _mean_week(st, runs=20000):
    rnd = random.Random(1)
    return sum(winprob._week_value(st, st["mode"], rnd, 0.0) for _ in range(runs)) / runs


def test_simulated_week_matches_projection():
    for scores, games, proj in (([10, 25, 40, 60], [(0.9, 1.0), (0.9, 1.05), (0.9, 0.97)], 38.0),
                                ([20, 22, 24], [(0.5, 1.0), (0.5, 1.0)], 30.0),
                                ([30, 35, 50], [(1.0, 1.0)] * 4, 41.0)):
        st = {"current": None, "scores": scores, "games": games, "mode": "best_game", "proj": proj}
        st["scale"] = _sim_scale(proj, None, scores, games, "best_game")
        assert abs(_mean_week(st) - proj) < 0.6


def test_no_projection_no_change():
    assert _sim_scale(None, None, [10, 20], [(1.0, 1.0)], "best_game") == 1.0
