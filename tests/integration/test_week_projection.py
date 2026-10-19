"""Weekly projections lean on what he's actually done this season, by games PLAYED (DECISIONS.md "Weekly projections",
2026-10-18): 1/14 more of his own games per game played, all of them after 14. Weeks passing alone change nothing (a
player out injured keeps his preseason number), and no screen falls back to the bare preseason number once he's played."""
from datetime import date

from psycopg2.extras import Json

from backend.fantasy_2026_27 import lineup, projections
from tests.integration.conftest import A, C, S


def _entry(cur, team, eid, week=None):
    return next(e for e in lineup.week_view(cur, S, team, week)["entries"] if e["id"] == eid)


def test_rule():
    assert projections.season_weight(0) == 0.0
    assert projections.season_weight(7) == 0.5
    assert projections.season_weight(14) == projections.season_weight(30) == 1.0


def test_week_one_games_already_count(league):
    cur = league.cur
    cur.execute("INSERT INTO fantasy_pool (season, player_id, name, proj_avg, proj_week, source) VALUES ('2025-26', 'pa1', 'Alpha One', 40, %s, 'manual')",
                (Json({"e": [40, 45, 50]}),))
    league.clock(date(2025, 10, 22))                 # week 1: he's played one game (37.5), one left
    e = _entry(cur, A, "pa1", 1)
    assert e["game_proj"] == round(40 - 2.5 / 14, 1)     # one game = 1/14 of the way to his own average
    assert 37.5 < e["projected"] < 40                    # the week total moved too (the old calendar rule kept week 1 on 40)


def test_no_games_no_change_however_late(league):
    cur = league.cur
    cur.execute("INSERT INTO fantasy_players (id, name, position, nba_team) VALUES ('pz1', 'Zed Hurt', 'G', 'AAA')")
    cur.execute("INSERT INTO fantasy_rosters (scenario, team_id, slot, player_id, pick_no) VALUES (%s, %s, 'BENCH', 'pz1', 9)", (S, C))
    cur.execute("INSERT INTO fantasy_pool (season, player_id, name, proj_avg, source) VALUES ('2025-26', 'pz1', 'Zed Hurt', 22, 'manual')")
    league.clock(date(2025, 11, 5))                  # week 3, still no games: still exactly his preseason number
    assert _entry(cur, C, "pz1")["game_proj"] == 22
