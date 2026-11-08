"""Pickups (DECISIONS.md 2026-11-08): a free agent is suggested only if he'd count that week."""
from backend.fantasy_2026_27.pickups import counts_this_week

MON = [{"tipoff": "2026-11-10T00:00:00+00:00"}, {"tipoff": "2026-11-14T01:00:00+00:00"}]
SUN_NIGHT = "2026-11-09T05:00:00+00:00"


def test_free_agent_before_his_first_game_counts():
    assert counts_this_week(MON, None, SUN_NIGHT)


def test_waiver_ending_after_his_first_game_does_not_count():
    # Okongwu, Week 4: clears Tuesday 07:46 UTC, Atlanta plays Monday night → counts from Week 5
    assert not counts_this_week(MON, "2026-11-10T07:46:02+00:00", SUN_NIGHT)


def test_waiver_ending_before_his_first_game_counts():
    assert counts_this_week(MON, "2026-11-09T03:11:07+00:00", SUN_NIGHT)


def test_first_game_already_tipped_or_no_games():
    assert not counts_this_week(MON, None, "2026-11-10T00:30:00+00:00")
    assert not counts_this_week([], None, SUN_NIGHT)


def test_week_score_weights():
    from backend.fantasy_2026_27.pickups import week_score
    assert week_score(20, 3, 0, 0) == 20
    assert week_score(20, 4, 2, 0) == 20 + 1.5 + 1.4          # an extra game, two soft opponents
    assert week_score(20, 3, 0, 10) == 22                      # minutes change capped at ±4, worth half


def test_level_blends_last_season_early():
    from backend.fantasy_2026_27.pickups import blended
    assert blended(30, 10, 20) == 25                           # 10 games this season = last season's weight
    assert blended(30, 30, 20) == 30 and blended(None, 0, 21) == 21
