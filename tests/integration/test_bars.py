"""Roster's stat bar (bars.py): weekly best games by category over real Mon–Sun weeks."""
from backend.fantasy_2026_27 import bars
from tests.integration.conftest import S


def test_actual_season_bar_adds_up(league):
    from datetime import date
    league.clock(date(2025, 10, 26))
    out = bars.bars(league.cur, S, ["pa1", "pb1", "AAA"], "actual", "season")
    e = out["entities"]
    assert "pa1" in e and e["pa1"]["weeks"] == 1
    assert abs(sum(p["points"] for p in e["pa1"]["parts"]) - e["pa1"]["score"]) < 0.6, "parts add up to his weekly best"


def test_bad_window_refused(league):
    import pytest
    with pytest.raises(ValueError):
        bars.bars(league.cur, S, ["pa1"], "actual", "d14")
