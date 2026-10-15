"""Projected FLOOR / CEILING (spread.py): level prior moved by the player's own weekly-best spread."""
from backend.fantasy_2026_27 import spread as sp


def test_season_spread_and_prior():
    s = sp.season_spread([20.0] * 5 + [30.0] * 10 + [45.0] * 5)
    assert s and 0 < s[0] < s[1] and s[3] == 20
    assert sp.season_spread([30.0] * 10) is None  # under 15 weeks: not a season
    d0, u0 = sp.spread([], 45)  # no history: the level prior
    assert abs(d0 - (sp.PRIOR_D[3] + sp.COEF_D[0])) < 1e-9


def test_volatile_history_widens_both_ends():
    steady = [(0.10, 0.20, 42.0, 60)]
    wild = [(0.35, 0.60, 42.0, 60)]
    ds, us = sp.spread(steady, 42)
    dw, uw = sp.spread(wild, 42)
    assert dw > ds and uw > us  # a deep past floor drop widens the floor AND the ceiling
