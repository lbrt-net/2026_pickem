"""Balanced schedule (schedule_balance.build): 11 teams over 18 weeks — byes even, opponent strength close."""
from backend.fantasy_2026_27 import schedule_balance as sb


def test_eleven_teams_balanced():
    teams = [{"id": f"t{i}", "name": f"T{i}", "owner_user_id": None, "owner_name": n}
             for i, n in enumerate(["nana", "reptar", "cody", "weinis", "lunar", "x", "y", "z", "q", "r", "s"])]
    teams[5]["owner_user_id"] = "97705344175702016"  # elbert, the strongest
    weeks, rep = sb.build(teams, 18, tries=800)
    assert len(weeks) == 18 and all(len(w) == 6 for w in weeks)  # 5 games + 1 bye each week
    byes = [t["byes"] for t in rep["teams"].values()]
    assert max(byes) - min(byes) <= 1
    assert rep["spread"] < 0.05
    two = [t for t in rep["teams"].values() if t["byes"] == 2]
    one = [t for t in rep["teams"].values() if t["byes"] == 1]
    assert min(t["strength"] for t in two) >= max(t["strength"] for t in one), "extra byes go to the strongest teams"
    for w in weeks:  # each team once a week
        seen = [x for p in w for x in p if x]
        assert len(seen) == len(set(seen))
