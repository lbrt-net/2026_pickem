"""Weekly projections: 25% preseason + 75% his average over the last 4 weeks once he has 4+ games there, else preseason
(DECISIONS.md "Weekly projections", 2026-10-20). A player out injured keeps his preseason number."""
from datetime import date

from psycopg2.extras import Json

from backend.fantasy_2026_27 import lineup, projections
from tests.integration.conftest import A, C, S


def _entry(cur, team, eid, week=None):
    return next(e for e in lineup.week_view(cur, S, team, week)["entries"] if e["id"] == eid)


def test_rule():
    assert projections.season_weight(0) == projections.season_weight(3) == 0.0       # under 4 recent games: preseason
    assert projections.season_weight(4) == projections.season_weight(12) == 0.75    # 4+: 75% the last 4 weeks


def test_week_one_games_already_count(league):
    cur = league.cur
    cur.execute("INSERT INTO fantasy_pool (season, player_id, name, proj_avg, proj_week, source) VALUES ('2025-26', 'pa1', 'Alpha One', 40, %s, 'manual')",
                (Json({"e": [40, 45, 50]}),))
    league.clock(date(2025, 10, 22))                 # week 1: he's played one game (37.5), one left
    e = _entry(cur, A, "pa1", 1)
    assert e["game_proj"] == 40                          # one game in the last 4 weeks (< 4): still preseason
    # the week total is built from the same per-game numbers: each remaining game's own number, never below his 37.5
    left = [g for g in e["games"] if not g["played"]]
    assert left and all(g["proj"] is not None for g in left)
    # chance of playing: lineup._chances — no preseason availability in the test league → recent share, 0.9 this early
    want = projections.week_best(40, 5 / 0.5642 / 40, [g["proj"] / e["game_proj"] for g in left], {"zero": 0.0, "q": 0.9}, 37.5)
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
    assert opponent._ramp(114.0, [128.0]) == 115.0


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


def test_on_the_injury_report_is_never_a_sure_thing(league):
    """2026-10-26 (week 1: Knueppel 100%, never played): Out with a return date inside the week → his games after it
    are first games back after misses; Day-To-Day → his next game is one after a miss. Even with no games yet."""
    from backend.fantasy_2026_27 import lineup as lu
    cur = league.cur
    e = {"id": "pa1", "kind": "player", "nba_team": "AAA"}
    av = {"zero": 0.0, "q": 0.96}
    out = {"status": "Out"}
    _, qs = lu._chances(cur, e, "2025-26", date(2025, 10, 20), 2, av, out, out_now=1)
    assert qs[0] < 0.36 and qs[1] < 0.32                  # back after 3+ misses: about a third each
    p = lu._play_prob(cur, e, "2025-26", date(2025, 10, 20), True, 2, None, av, out, 1)
    assert p < 0.6
    _, qs = lu._chances(cur, e, "2025-26", date(2025, 10, 20), 3, av, {"status": "Day-To-Day"})
    assert qs[0] < 0.55
    assert lu._play_prob(cur, e, "2025-26", date(2025, 10, 20), True, 3, None, av) > 0.99   # healthy unchanged


def test_return_week_counts_only_games_after_the_return_date():
    from datetime import date as d
    weeks = [{"week": 1, "start": d(2026, 10, 19), "end": d(2026, 10, 25)}, {"week": 2, "start": d(2026, 10, 26), "end": d(2026, 11, 1)},
             {"week": 3, "start": d(2026, 11, 2), "end": d(2026, 11, 8)}]
    dates = {1: [d(2026, 10, 21), d(2026, 10, 23), d(2026, 10, 25)], 2: [d(2026, 10, 27), d(2026, 10, 29), d(2026, 10, 31)],
             3: [d(2026, 11, 3), d(2026, 11, 5), d(2026, 11, 8)]}
    curve = {"e": [30, 36, 40], "p25": [22, 30, 34], "p90": [45, 49, 51]}
    wp = projections.week_projection(curve, {1: 3, 2: 3, 3: 3}, weeks, None, d(2026, 11, 8), dates)
    assert [w["plays"] for w in wp] == [0, 0, 1]          # out weeks 1–2; back Nov 8 = only that game in week 3
    assert [w["can"] for w in wp] == [0, 0, 1]            # the games shown: what he can play, not his team's 3
