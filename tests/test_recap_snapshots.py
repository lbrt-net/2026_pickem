"""Recap projections (snapshots.py): the per-game blend and a week's projection scaled by games actually played."""
from backend.fantasy_2026_27.snapshots import blend, proj_for


def test_blend_leans_on_recent_games_as_they_pile_up():
    assert blend(30.0, []) == 30.0                          # no games yet: the preseason projection
    assert blend(None, [20.0, 40.0]) == 30.0                # no projection: what he's done
    assert round(blend(30.0, [18.0] * 8), 2) == 26.0        # 8 games: a third recent
    assert round(blend(30.0, [18.0] * 40), 2) == 22.0       # 16+ games: two thirds recent, never all


def test_projection_follows_games_played():
    assert proj_for(25.0, 8.0, 0) == 0.0                    # didn't play: projected 0, no letdown
    assert proj_for(25.0, 8.0, 1) == 25.0                   # one game: his average game
    assert proj_for(25.0, 8.0, 4) > proj_for(25.0, 8.0, 2) > 25.0   # more games, higher best game
