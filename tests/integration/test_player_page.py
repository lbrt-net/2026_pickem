"""The player page payload (player_page.py): season line, weekly bests, game log with missed games, draft pick."""
from backend.fantasy_2026_27 import player_page

from .conftest import S


def _page(league, pid):
    player_page._cache.clear()
    return player_page.build(league.cur, S, pid, None, None, False)


def test_header_is_this_season_only(league, monkeypatch):
    assert _page(league, "pa1")["header"] is None  # no 2026-27 games: stats panel + wheel blank
    monkeypatch.setattr(player_page, "LIVE", "2025-26")  # pretend the fixture's season is the current one
    p = _page(league, "pa1")  # played g1 (30 pts) and g2 (10 pts) in the same week
    h = p["header"]
    assert h["season"] == "2025-26" and h["gp"] == 2
    assert h["max"] == max(g[0] for g in h["games"])  # one week: MAX = his best game
    assert sum(b for _, b in h["games"]) == 1  # exactly one weekly best flagged
    assert [w["k"] for w in h["wheel"]] == ["Playmaking", "Stocks", "Boards", "Scoring"]
    assert p["seasons"][0]["proj"] and p["seasons"][1]["season"] == "'26" and p["seasons"][1]["gp"] == 2
    assert len(p["recent"]) == 2 and p["recent"][-1]["date"] == "2025-10-23"


def test_game_log_shows_missed_games(league):
    p = _page(league, "pb2")  # BBB played g1 and g3; pb2 only g1
    rows = p["glog"]["2025-26"]
    assert [r["date"] for r in rows] == ["2025-10-21", "2025-10-22"]
    assert "fp" in rows[0] and rows[1]["out"] == "Did not play"
    assert p["hist"][0]["missed"] == 1


def test_draft_pick_is_a_move(league):
    p = _page(league, "pa1")
    assert any(m["k"] == "draft" and m["pick"] == 1 for m in p["moves"])


def test_percentiles_need_both_rules():
    assert player_page.qualified(20, 500) and not player_page.qualified(19, 600) and not player_page.qualified(24, 490)
    assert not player_page.qualified(40, 760)  # 19 MPG: under the 20-minute line
    assert player_page.qualified(5, 125, 0.25) and not player_page.qualified(4, 125, 0.25)  # a quarter in: 5 games, 125 minutes


def test_shot_fields_this_season_only(league, monkeypatch):
    from psycopg2.extras import Json
    data = {"x0": -250, "y0": -52, "step": 5, "nx": 2, "ny": 1, "lvl": "05", "d": [12], "n": 40}
    league.cur.execute("INSERT INTO nba_shot_fields (player_id, season, data) VALUES ('pa1', '2025-26', %s)", (Json(data),))
    assert player_page.shots(league.cur, "pa1") == {}  # past seasons never show
    monkeypatch.setattr(player_page, "LIVE", "2025-26")
    assert player_page.shots(league.cur, "pa1") == {"2025-26": data}
    assert player_page.shots(league.cur, "pb1") == {}


def test_projection_fills_the_panel_before_games():
    pool_row = {"proj_weeks": [{"week": w, "games": 3, "plays": 2.4} for w in range(1, 11)]}
    board = {"101": {"max": 40.0, "avg": 30.0, "max_low": 33.0, "max_high": 50.0}, "102": {"max": 20.0, "avg": 15.0, "max_low": 16.0, "max_high": 25.0}}
    h = player_page.projected_header("101", pool_row, board, [30.0] * 5 + [20.0, 40.0] * 5)
    assert h["proj"] and h["max"] == 40.0 and h["floor"] == 33.0 and h["ceil"] == 50.0
    assert h["pct"]["max"] == 99 and len(h["sim"]) == 400 and all(x >= 20.0 for x in h["sim"])  # a best of 1+ draws
    assert all(w["p"] is None for w in h["wheel"])  # no projected categories: the wheel waits for games


def test_projected_wheel_from_a_stat_line():
    line = {"pts": 20, "fgm": 8, "fga": 16, "fg3m": 2, "ftm": 2, "fta": 3, "oreb": 1, "dreb": 5, "ast": 6, "stl": 1, "blk": 1, "tov": 3, "blkd": 1}
    w = player_page.projected_wheel(line, 0.5)
    assert set(w) == {"Scoring", "Playmaking", "Boards", "Stocks"} and w["Stocks"] > 0
    assert player_page.projected_wheel(None, 1) is None  # rookies: no line, no wheel


def test_team_page(league, monkeypatch):
    from backend.fantasy_2026_27 import team_page
    monkeypatch.setattr(team_page, "NBA_TEAM_NAMES", {"AAA": "Alpha", "BBB": "Beta", "CCC": "Cee"})
    team_page._cache.clear()
    p = team_page.build(league.cur, S, "aaa", None, False, None)
    assert p["player"]["kind"] == "team" and p["player"]["tier"] == "plain" and p["player"]["name"] == "Alpha"
    rows = p["glog"]["2025-26"]
    assert [r["res"] for r in rows] == ["W 110-100", "L 99-105"] and all("fp" in r for r in rows)
    assert p["seasons"][1]["season"] == "'26" and p["seasons"][1]["gp"] == 2
    assert team_page.build(league.cur, S, "ZZZ", None, False, None) is None
