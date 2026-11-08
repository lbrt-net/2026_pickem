"""2026-11-07: a week's first-day win chance is taken at lock-in (5 minutes before the first tip), never at 3 AM."""
from datetime import date

from backend.fantasy_2026_27.snapshots import waits_for_lock

MON, TUE = date(2026, 11, 2), date(2026, 11, 3)


def test_first_day_waits_for_lock_in():
    assert waits_for_lock(False, MON, MON, at_lock=False)       # 3 AM Monday: skipped
    assert not waits_for_lock(False, MON, MON, at_lock=True)    # lock-in: taken


def test_other_days_and_sim_leagues_unchanged():
    assert not waits_for_lock(False, TUE, MON, at_lock=False)   # Tuesday: the 3 AM run as before
    assert not waits_for_lock(True, MON, MON, at_lock=False)    # a sim-date league has no real lock moment
