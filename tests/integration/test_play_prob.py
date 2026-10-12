"""1+ Game % (lineup._play_prob): played once → 1; week over with no game → 0; a missed-game streak lowers it."""
from backend.fantasy_2026_27 import lineup


def test_played_once_is_certain_and_no_games_left_is_zero(league):
    e = {"id": "pa1", "kind": "player", "nba_team": "AAA"}
    assert lineup._play_prob(league.cur, e, "2025-26", None, True, 2, 30.0, None) == 1.0
    assert lineup._play_prob(league.cur, e, "2025-26", None, True, 0, None, None) == 0.0


def test_streak_math_lowers_the_chance():
    q = lineup.MISS_STREAK[0]
    healthy = 1 - (1 - q) ** 3
    one_miss = 1 - (1 - lineup.MISS_STREAK[1]) * (1 - lineup.MISS_STREAK[2]) * (1 - lineup.MISS_STREAK[3])
    assert one_miss < healthy and round(one_miss, 2) == 0.77
