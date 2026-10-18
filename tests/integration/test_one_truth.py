"""One truth per fact (DATA.md, 2026-10-18). The two places a player's position / NBA team live start out DISAGREEING
here (like draft night); after truth.sync every view the site serves must show the pool's values, and a real trade
(his latest game for a new team) moves him everywhere."""
from datetime import date

from fastapi.testclient import TestClient

from backend.fantasy_2026_27 import projections, truth
from backend.main import app
from tests.integration.conftest import A, S

POOL = {"pa1": ("F", "AAA"), "pb1": ("C", "BBB"), "pa2": ("G", "AAA"), "pb2": ("G", "BBB"), "pc1": ("F", "CCC"), "pc2": ("C", "CCC")}


def _views(c):
    q = f"?scenario={S}"
    out = {}
    for p in c.get(f"/fantasy/2026_27/players{q}").json():
        if p["id"] in POOL:
            out.setdefault(p["id"], {})["players"] = (p.get("position"), p.get("nba_team"))
    for t in c.get(f"/fantasy/2026_27/teams{q}").json():
        for e in t["roster"]:
            if e["id"] in POOL:
                out.setdefault(e["id"], {})["teams"] = (e.get("position"), e.get("nba_team"))
    for p in c.get(f"/fantasy/2026_27/draft{q}").json()["picks"]:
        if str(p["id"]) in POOL:
            out.setdefault(str(p["id"]), {})["draft"] = (p.get("position"), None)
    return out


def test_every_view_shows_the_pool(league):
    cur = league.cur
    for pid, (pos, team) in POOL.items():
        cur.execute("""INSERT INTO fantasy_pool (season, player_id, name, nba_team, position, source)
                       VALUES ('2025-26', %s, %s, %s, %s, 'manual')""", (pid, pid, team, pos))
    cur.execute("UPDATE fantasy_players SET position = 'C' WHERE id = 'pa1'")      # the old table disagrees
    cur.execute("DELETE FROM nba_player_games")                                     # no trades in this test
    truth.sync(cur)
    league.commit()
    projections.clear_cache()
    views = _views(TestClient(app))
    for pid, seen in views.items():
        for where, (pos, team) in seen.items():
            assert pos == POOL[pid][0], f"{pid} position on {where}: {pos} vs pool {POOL[pid][0]}"
            if team is not None:
                assert team == POOL[pid][1], f"{pid} NBA team on {where}: {team} vs pool {POOL[pid][1]}"
    assert views["pa1"]["teams"][0] == "F"                                          # the rostered one too


def test_a_real_trade_moves_the_player_everywhere(league):
    cur = league.cur
    for pid, (pos, team) in POOL.items():
        cur.execute("""INSERT INTO fantasy_pool (season, player_id, name, nba_team, position, source)
                       VALUES ('2025-26', %s, %s, %s, %s, 'manual')""", (pid, pid, team, pos))
    cur.execute("""INSERT INTO nba_games (game_id, season, game_type, game_date, status, home_team, away_team, home_score, away_score)
                   VALUES ('gx', '2025-26', 'regular', %s, 'final', 'CCC', 'BBB', 100, 99)""", (date(2025, 11, 1),))
    cur.execute("""INSERT INTO nba_player_games (game_id, player_id, season, player_name, team, starter, minutes, pts)
                   VALUES ('gx', 'pa1', '2025-26', 'pa1', 'CCC', TRUE, 30, 10)""")   # pa1 now plays for CCC
    truth.sync(cur)
    league.commit()
    projections.clear_cache()
    views = _views(TestClient(app))
    assert views["pa1"]["players"][1] == "CCC" and views["pa1"]["teams"][1] == "CCC"
