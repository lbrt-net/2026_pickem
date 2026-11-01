"""Injury sync times (DECISIONS.md "Injury log", 2026-10-30): Mondays every 15 minutes 7 AM–11 PM Central, other
days at noon and 4 PM Central (+ 6 PM and 8 PM on game days, 2026-10-31), every day at 1 AM."""
from datetime import datetime

from backend.nba.scheduler import CENTRAL, next_injury_run


def at(*a):
    return datetime(*a, tzinfo=CENTRAL)


def test_other_days_noon_and_four():
    assert next_injury_run(at(2026, 10, 30, 9, 0)) == at(2026, 10, 30, 12, 0)     # Friday morning → noon
    assert next_injury_run(at(2026, 10, 30, 12, 0)) == at(2026, 10, 30, 16, 0)    # noon → 4 PM
    assert next_injury_run(at(2026, 10, 30, 16, 5)) == at(2026, 10, 31, 1, 0)     # after 4 → 1 AM
    assert next_injury_run(at(2026, 10, 31, 1, 0)) == at(2026, 10, 31, 12, 0)     # 1 AM → noon


def test_mondays_every_fifteen():
    assert next_injury_run(at(2026, 11, 1, 16, 30)) == at(2026, 11, 2, 1, 0)      # Sunday after 4 → Monday 1 AM
    assert next_injury_run(at(2026, 11, 2, 1, 0)) == at(2026, 11, 2, 7, 0)        # → Monday 7 AM
    assert next_injury_run(at(2026, 11, 2, 9, 1)) == at(2026, 11, 2, 9, 15)



def test_game_days_add_six_and_eight():
    games = {at(2026, 10, 30, 0, 0).date()}
    assert next_injury_run(at(2026, 10, 30, 16, 0), games) == at(2026, 10, 30, 18, 0)   # game day: 4 PM → 6 PM
    assert next_injury_run(at(2026, 10, 30, 18, 0), games) == at(2026, 10, 30, 20, 0)   # → 8 PM
    assert next_injury_run(at(2026, 10, 30, 20, 0), games) == at(2026, 10, 31, 1, 0)    # → 1 AM
    assert next_injury_run(at(2026, 10, 31, 16, 0), games) == at(2026, 11, 1, 1, 0)     # no game the 31st: no 6 / 8
