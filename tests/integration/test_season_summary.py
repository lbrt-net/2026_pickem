"""GET /players/season-summary: every player's line for one past season in one call (Mid-Season Report percentiles)."""
from backend.fantasy_2026_27 import history


def test_every_player_in_one_call(league):
    history.build(league.cur, "2025-26")
    s = history.season_summary(league.cur, "2025-26")
    assert {"pa1", "pb2"} <= set(s)
    assert s["pa1"]["games"] == 2 and s["pa1"]["weeks_played"] == 1  # g1 + g2, same week
    assert s["pa1"]["avg_max"] >= s["pa1"]["fp_per_game"]  # one week: avg weekly best = his best game
    assert history.season_summary(league.cur, "1999-00") == {}
