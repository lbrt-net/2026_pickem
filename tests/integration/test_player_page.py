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
    assert player_page.qualified(25, 260) and not player_page.qualified(9, 300) and not player_page.qualified(30, 240)
    assert not player_page.qualified(40, 360)  # 9 MPG


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
