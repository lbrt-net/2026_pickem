"""Recap snapshots: daily win probability (one per day, kept) and each week's projections (frozen once)."""
from datetime import date

from backend.fantasy_2026_27 import snapshots
from tests.integration.conftest import S


def test_winprob_once_a_day(league):
    cur = league.cur
    n = snapshots.take_winprob(cur, S)
    assert n > 0
    snapshots.take_winprob(cur, S)                           # second run the same day: the first is kept
    cur.execute("SELECT COUNT(*) FROM fantasy_winprob_daily WHERE scenario = %s", (S,))
    assert cur.fetchone()["count"] == n
    league.clock(date(2025, 10, 21))
    snapshots.take_winprob(cur, S)
    cur.execute("SELECT COUNT(DISTINCT asof) FROM fantasy_winprob_daily WHERE scenario = %s", (S,))
    assert cur.fetchone()["count"] == 2


def test_projections_freeze_once_per_week_and_use_recent_games(league):
    cur = league.cur
    cur.execute("INSERT INTO fantasy_pool (season, player_id, name, proj_avg, source) VALUES ('2025-26', 'pa1', 'Alpha One', 30, 'manual')")
    assert snapshots.take_proj(cur, S) > 0                   # week 1: the preseason projection
    assert snapshots.take_proj(cur, S) == 0                  # frozen: never rewritten
    league.clock(date(2025, 10, 27))                         # week 2: week 1's games are recent now
    snapshots.take_proj(cur, S)
    cur.execute("SELECT recent_games, game_mean FROM fantasy_proj_week WHERE scenario = %s AND week = 2 AND entity_id = 'pa1'", (S,))
    r = cur.fetchone()
    assert r and r["recent_games"] == 2 and r["game_mean"] == 30   # 2 games in the last 4 weeks (< 4): still preseason
