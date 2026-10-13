"""Winnings (winnings.py): pool = buy-in × paid members + extras; only paid members collect; `would` = everyone paid."""
from backend.fantasy_2026_27 import winnings
from tests.integration.conftest import S


def test_pool_and_payouts(league):
    cur = league.cur
    cur.execute("SELECT id, owner_user_id FROM fantasy_teams WHERE scenario = %s ORDER BY id", (S,))
    teams = cur.fetchall()
    winnings.save(cur, S, {"paid": [teams[0]["owner_user_id"]], "extras": [{"name": "Cody", "amount": 25}], "weekly": 5})
    w = winnings.winnings(cur, S)
    assert w["actual"]["pool"] == 25 * 1 + 25
    assert w["would"]["pool"] == 25 * len(teams) + 25
    assert w["actual"]["regular"] <= w["actual"]["pool"]
    for r in w["actual"]["rows"]:
        if r["winner"]:
            assert r["winner"]["team"] == teams[0]["id"], "only a paid team collects"
    playoff_rows = [r for r in w["actual"]["rows"] if r["kind"] == "playoff"]
    assert round(sum(r["amount"] for r in playoff_rows), 2) == round(w["actual"]["playoff"], 2)
