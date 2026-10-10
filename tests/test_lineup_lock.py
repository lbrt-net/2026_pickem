"""Lineup locks: a player counts for a week only if he joined the team before his first game of that week locked."""
from datetime import date, datetime, timedelta, timezone

from backend.fantasy_2026_27.etch import joined_in_time

W = {"start": date(2026, 10, 19), "end": date(2026, 10, 25)}
G = {"game_date": date(2026, 10, 21), "tipoff_utc": datetime(2026, 10, 22, 0, 0, tzinfo=timezone.utc)}


def test_drafted_players_always_count():
    assert joined_in_time({"added_asof": None}, W, G, replay=False)


def test_added_before_or_after_the_lock():
    assert joined_in_time({"added_asof": date(2026, 10, 20), "added_at": G["tipoff_utc"] - timedelta(hours=2)}, W, G, replay=False)
    assert not joined_in_time({"added_asof": date(2026, 10, 21), "added_at": G["tipoff_utc"] - timedelta(minutes=2)}, W, G, replay=False)


def test_test_league_treats_game_day_as_played():
    assert not joined_in_time({"added_asof": date(2026, 10, 21)}, W, G, replay=True)
    assert joined_in_time({"added_asof": date(2026, 10, 20)}, W, G, replay=True)
