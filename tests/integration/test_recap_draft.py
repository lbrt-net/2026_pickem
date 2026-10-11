"""Draft Grades (recap.py): points added over the best player left at the position; snake yardstick = the Nth-best
player; auction = money on a curve; frozen at draft completion."""
from psycopg2.extras import Json

from backend.fantasy_2026_27 import recap
from tests.integration.conftest import A, B, S

PROJ = {"pa1": 40, "pa2": 30, "pb1": 35, "pb2": 20, "pc1": 25, "pc2": 22}


def pool(cur):
    cur.execute("DELETE FROM fantasy_pool WHERE season = '2025-26'")
    cur.execute("SELECT id, name, position, nba_team FROM fantasy_players WHERE id = ANY(%s)", (list(PROJ),))
    for r in cur.fetchall():
        cur.execute("""INSERT INTO fantasy_pool (season, player_id, name, nba_team, position, proj_max, source)
                       VALUES ('2025-26', %s, %s, %s, %s, %s, 'manual')""", (r["id"], r["name"], r["nba_team"], r["position"], PROJ[r["id"]]))


def test_snake_points_added_and_yardstick(league):
    cur = league.cur
    pool(cur)
    d = recap.build_draft(cur, S)
    assert d["type"] == "snake"
    picks = {p["id"]: p for p in d["picks"]}
    rep = d["replacement"]
    for pid, p in picks.items():
        assert p["added"] == round(PROJ[pid] - rep.get(p["pos"], {"proj": 0})["proj"], 1)   # over the best free player at his spot
    assert {t["id"] for t in d["teams"]} >= {A, B}
    assert set(d["awards"]) >= {"worst", "best_pick", "best_late", "reach", "bench"}


def test_auction_worth_follows_the_money_and_freezes(league):
    cur = league.cur
    pool(cur)
    cur.execute("UPDATE fantasy_leagues SET settings = settings || %s WHERE scenario = %s", (Json({"draft_type": "auction"}), S))
    for pid, price in (("pa1", 60), ("pb1", 40), ("pa2", 30), ("pb2", 2)):
        cur.execute("UPDATE fantasy_rosters SET price = %s WHERE scenario = %s AND player_id = %s", (price, S, pid))
    d = recap.freeze_draft(cur, S)
    assert d["type"] == "auction"
    worth = {p["id"]: p["worth"] for p in d["picks"]}
    assert worth["pa1"] > worth["pb2"] > worth["pb1"] > worth["pa2"]      # worth follows points added (+40 > +20 > +13 > +5)
    assert set(d["awards"]) >= {"best_buy", "best_cheap", "overpay", "worst", "bench"}
    cur.execute("UPDATE fantasy_rosters SET price = 1 WHERE scenario = %s", (S,))   # rosters change later…
    assert recap.recap(cur, S)["draft"]["picks"] == d["picks"]               # …the grades don't
