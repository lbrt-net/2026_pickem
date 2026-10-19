"""Recap projections (snapshots.py): the per-game blend and a week's projection scaled by games actually played."""
from backend.fantasy_2026_27.snapshots import blend, proj_for


def test_blend_moves_onto_the_season_by_games_played():
    assert blend(30.0, []) == 30.0                          # no games yet (or injured all along): the preseason projection
    assert blend(None, [20.0, 40.0]) == 30.0                # no projection: what he's done
    assert round(blend(30.0, [16.0] * 7), 2) == 23.0        # 7 games: half his own games
    assert blend(30.0, [16.0] * 14) == 16.0                 # 14+ games: all his own games
    assert blend(30.0, [16.0] * 40) == 16.0


def test_projection_follows_games_played():
    assert proj_for(25.0, 8.0, 0) == 0.0                    # didn't play: projected 0, no letdown
    assert proj_for(25.0, 8.0, 1) == 25.0                   # one game: his average game
    assert proj_for(25.0, 8.0, 4) > proj_for(25.0, 8.0, 2) > 25.0   # more games, higher best game
