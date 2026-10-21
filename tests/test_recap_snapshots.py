"""Recap projections (snapshots.py): the per-game blend and a week's projection scaled by games actually played."""
from backend.fantasy_2026_27.snapshots import blend, proj_for


def test_blend_is_a_quarter_preseason_once_he_has_four_recent_games():
    assert blend(30.0, []) == 30.0                          # no games in the last 4 weeks: the preseason projection
    assert blend(30.0, [16.0] * 3) == 30.0                  # fewer than 4: still preseason
    assert blend(None, [20.0, 40.0]) == 30.0                # no projection: what he's done
    assert blend(30.0, [16.0] * 4) == 19.5                  # 4+ games: 25% preseason + 75% the 4-week average
    assert blend(30.0, [16.0] * 12) == 19.5


def test_projection_follows_games_played():
    assert proj_for(25.0, 8.0, 0) == 0.0                    # didn't play: projected 0, no letdown
    assert proj_for(25.0, 8.0, 1) == 25.0                   # one game: his average game
    assert proj_for(25.0, 8.0, 4) > proj_for(25.0, 8.0, 2) > 25.0   # more games, higher best game
