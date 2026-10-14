"""Balanced schedule inputs (schedule_balance.py): past seasons as data, strength = 3-season win % (.400 when missed)."""
from backend.fantasy_2026_27 import schedule_balance as sb


def test_seeded_strengths_match_the_commissioners_numbers(league):
    h = sb.history(league.cur)
    assert h["seasons"] == ["2025-26", "2024-25", "2023-24"]
    s = {m["manager"]: m["strength"] for m in h["managers"]}
    assert s["elbert"] == 0.732 and s["mits"] == 0.539 and s["weinis"] == 0.172
    assert s["notre"] == round((9 / 13 + 0.4 + 0.4) / 3, 3)  # two missed seasons count .400


def test_edit_and_match(league):
    h = sb.save_history(league.cur, [{"manager": "zed", "aliases": "zeddy,thez", "records": {"2025-26": [10, 0], "2024-25": [0, 10]}}])
    assert h["seasons"] == ["2025-26", "2024-25"] and h["managers"][0]["strength"] == 0.5
    assert sb.strength_for({"owner_name": "TheZ123", "name": "x"}, h) == (0.5, "zed")
    assert sb.strength_for({"owner_name": "nobody", "name": "x"}, h) == (sb.DEFAULT, None)
