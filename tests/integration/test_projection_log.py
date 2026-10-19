"""Projection check (2026-10-19): the week's projections are saved before its first game, for players on a team or
not, and filled in with what happened once the week is over."""
from datetime import date

from psycopg2.extras import Json

from backend.fantasy_2026_27 import projection_log
from tests.integration.conftest import S


def test_saved_before_games_then_filled(league):
    cur = league.cur
    for pid, avg in (("pa1", 30), ("pc1", 20)):  # pa1 on a team, pc1 a free agent
        cur.execute("""INSERT INTO fantasy_pool (season, player_id, name, nba_team, proj_avg, proj_week, source)
                       SELECT '2025-26', id, name, nba_team, %s, %s, 'manual' FROM fantasy_players WHERE id = %s""",
                    (avg, Json({"e": [avg, avg * 1.2, avg * 1.3]}), pid))
    cur.execute("UPDATE nba_games SET status = 'scheduled' WHERE game_id IN ('g1', 'g2', 'g3')")  # nothing tipped yet
    league.commit()
    assert projection_log.save_week(cur, S) > 0
    assert projection_log.save_week(cur, S) == 0                                  # once a week
    cur.execute("SELECT entity_id, team_id, projected, play_prob, games FROM fantasy_projection_log WHERE scenario = %s", (S,))
    rows = {r["entity_id"]: r for r in cur.fetchall()}
    assert rows["pa1"]["team_id"] and rows["pc1"]["team_id"] is None              # rostered and free agents alike
    assert rows["pa1"]["projected"] and rows["pa1"]["play_prob"] and rows["pa1"]["games"] == 2
    cur.execute("UPDATE nba_games SET status = 'final' WHERE game_id IN ('g1', 'g2', 'g3')")
    league.clock(date(2025, 10, 27))                                              # the week is over
    assert projection_log.fill_weeks(cur, S) > 0
    cur.execute("SELECT actual, actual_games FROM fantasy_projection_log WHERE scenario = %s AND entity_id = 'pa1'", (S,))
    r = cur.fetchone()
    assert r["actual_games"] == 2 and r["actual"] == 37.5                         # his best game (30 pts, 5 reb, 5 ast)
    rep = projection_log.report(cur, S)
    assert rep["summary"]["n"] > 0 and rep["rows"]


def test_not_saved_once_a_game_started(league):
    cur = league.cur
    cur.execute("INSERT INTO fantasy_pool (season, player_id, name, nba_team, proj_avg, source) VALUES ('2025-26', 'pa1', 'Alpha One', 'AAA', 30, 'manual')")
    league.commit()                                                               # g1 is final in the fixture
    assert projection_log.save_week(cur, S) == 0
