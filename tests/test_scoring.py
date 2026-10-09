"""Scoring rules (backend/fantasy_2026_27/scoring.py, FANTASY_SCORING.md, TEAM_SCORING.md)."""
import pytest

from backend.fantasy_2026_27 import scoring


def team_points(pts_allowed, extra=None):
    return scoring.score_game(scoring.DEFAULT["team"], scoring.team_line(110, pts_allowed, extra or {}))["breakdown"]


@pytest.mark.parametrize("allowed, under125, under100", [
    (130, 0, 0),    # over 125: nothing
    (125, 0, 0),
    (120, 5, 0),    # +1 per point under 125
    (100, 25, 0),   # down to 100 …
    (99, 25, 5),    # … then capped at 25, and +5 for holding them under 100 (2026-10-09 rule)
    (80, 25, 5),
])
def test_points_allowed_capped_at_100(allowed, under125, under100):
    b = team_points(allowed)
    assert b["under125"] == under125
    assert b["under100"] == under100


def test_steps_floor_is_validated():
    rules = {"player": scoring.DEFAULT["player"], "team": {**scoring.DEFAULT["team"], "components": [
        {"id": "x", "type": "steps", "stat": "pts_allowed", "below": 100, "floor": 120, "step": 1, "points": 1}]}}
    with pytest.raises(ValueError):
        scoring.validate(rules)


def test_week_modes():
    best = {"week": "best_game", "components": []}
    total = {"week": "sum", "components": []}
    assert scoring.week_score(best, [10, 30, 20]) == 30   # players: their best game of the week
    assert scoring.week_score(total, [10, 30, 20]) == 60
    assert scoring.week_score(best, []) is None           # no games: no score


def test_default_rules_are_valid_and_versioned():
    v = scoring.validate({"player": scoring.DEFAULT["player"], "team": scoring.DEFAULT["team"]})
    assert v["version"] == scoring.DEFAULT["version"]
