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


def test_winprob_filed_under_the_calendar_week(league):
    """2026-11-01: late in a week every starter has locked and a team's own view opens next week; the snapshot still
    belongs to the week the day is in, and Improbable win only reads the week's own days."""
    from backend.fantasy_2026_27 import recap
    cur = league.cur
    league.clock(date(2025, 10, 25))                         # Saturday of week 1 (Oct 20–26)
    assert snapshots.take_winprob(cur, S) > 0
    cur.execute("SELECT DISTINCT week FROM fantasy_winprob_daily WHERE scenario = %s", (S,))
    assert [r["week"] for r in cur.fetchall()] == [1]
    cur.execute("""INSERT INTO fantasy_winprob_daily (scenario, week, asof, team_a, team_b, p)
                   SELECT scenario, week, DATE '2025-10-17', team_a, team_b, 0.5 FROM fantasy_winprob_daily WHERE scenario = %s""", (S,))
    league.clock(date(2025, 10, 27))
    imp = recap.weekly(cur, S, 1)["awards"].get("improbable")
    assert not imp or "2025-10-17" not in imp["days"]


def test_rebuild_a_missed_day_leaves_everything_as_it_was(league):
    """2026-11-01: a missed snapshot is rebuilt from the night before's clock and that morning's injury report, filed
    under the day's week, and the league's clock and the injury report are untouched afterwards."""
    cur = league.cur
    league.clock(date(2025, 10, 27))
    cur.execute("SELECT sim_date FROM fantasy_leagues WHERE scenario = %s", (S,))
    clock = cur.fetchone()["sim_date"]
    cur.execute("SELECT COUNT(*) FROM nba_injuries")
    hurt = cur.fetchone()["count"]
    out = snapshots.rebuild_winprob(cur, S, date(2025, 10, 23))
    assert out and all(0 <= m["p"] <= 1 for m in out)
    cur.execute("SELECT DISTINCT week FROM fantasy_winprob_daily WHERE scenario = %s AND asof = '2025-10-23'", (S,))
    assert [r["week"] for r in cur.fetchall()] == [1]
    cur.execute("SELECT sim_date FROM fantasy_leagues WHERE scenario = %s", (S,))
    assert cur.fetchone()["sim_date"] == clock
    cur.execute("SELECT COUNT(*) FROM nba_injuries")
    assert cur.fetchone()["count"] == hurt
