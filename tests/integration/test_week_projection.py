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
    # the week total is built from the same per-game numbers: each remaining game's own number, never below his 37.5
    left = [g for g in e["games"] if not g["played"]]
    assert left and all(g["proj"] is not None for g in left)
    # chance of playing: lineup._chances — no preseason availability in the test league → recent share, 0.9 this early
    want = projections.week_best(40 - 2.5 / 14, 5 / 0.5642 / 40, [g["proj"] / e["game_proj"] for g in left], {"zero": 0.0, "q": 0.9}, 37.5)
    assert e["projected"] > 37.5 and abs(e["projected"] - want) < 0.3


def test_different_games_beat_their_average():
    # 27.1 and 28.1 have a higher expected best than two games of 27.6
    lvl = 27.6
    assert projections.week_best(lvl, 0.3, [27.1 / lvl, 28.1 / lvl], None, None) > projections.week_best(lvl, 0.3, [1.0, 1.0], None, None)


def test_no_games_no_change_however_late(league):
    cur = league.cur
    cur.execute("INSERT INTO fantasy_players (id, name, position, nba_team) VALUES ('pz1', 'Zed Hurt', 'G', 'AAA')")
    cur.execute("INSERT INTO fantasy_rosters (scenario, team_id, slot, player_id, pick_no) VALUES (%s, %s, 'BENCH', 'pz1', 9)", (S, C))
    cur.execute("INSERT INTO fantasy_pool (season, player_id, name, proj_avg, source) VALUES ('2025-26', 'pz1', 'Zed Hurt', 22, 'manual')")
    league.clock(date(2025, 11, 5))                  # week 3, still no games: still exactly his preseason number
    assert _entry(cur, C, "pz1")["game_proj"] == 22


def test_game_factors():
    from datetime import date as d
    from backend.fantasy_2026_27 import opponent
    day = d(2025, 11, 5)
    blank = {"rating": {}, "lg": None, "dates": {"BBB": {d(2025, 11, 4)}}}
    assert opponent.factor(blank, "AAA", True, day) > opponent.factor(blank, "AAA", False, day)   # home from day 1
    assert opponent.factor(blank, "BBB", True, day) > opponent.factor(blank, "AAA", True, day)    # opponent played yesterday
    lg = (114.0, 99.0, 0.0)
    soft = {"rating": {"SFT": (120.0, 103.0, -5.0), "AVG": lg}, "lg": lg, "dates": {}}
    assert opponent.factor(soft, "SFT", True, day) > opponent.factor(soft, "AVG", True, day)      # soft, fast, weak opponent
    # opponent ratings start at the league average: 1 game played = 1/14 of the way to its own number
    assert projections.blend(114.0, [128.0]) == 115.0


def test_week_is_chance_of_k_games_times_best_of_k():
    # 3 identical games, 87% each, no whole-week-out chance: Σ P(k games) × expected best of k
    from math import comb
    lvl, cv, q = 30.4, 0.3725, 0.865
    best = [0.0] + [projections.week_best(lvl, cv, [1.0] * k, None, None) for k in (1, 2, 3)]
    want = sum(comb(3, k) * q ** k * (1 - q) ** (3 - k) * best[k] for k in range(4))
    assert abs(projections.week_best(lvl, cv, [1.0] * 3, {"zero": 0.0, "q": q}, None) - want) < 0.05


def test_healthy_player_never_loses_a_whole_week_at_random(league):
    from backend.fantasy_2026_27 import lineup as lu
    cur = league.cur
    e = {"id": "pa1", "kind": "player", "nba_team": "AAA"}
    zero, qs = lu._chances(cur, e, "2025-26", date(2025, 10, 20), 3, {"zero": 0.17, "q": 0.96})
    assert zero == 0.0 and qs == [0.96] * 3          # the season model's 17% stretch share isn't charged to his week
