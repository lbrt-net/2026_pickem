"""Automatic playoffs: the bracket follows the number of teams (under 4: 1-week final; 4–6: top 4; 7+: top 6)."""
from backend.fantasy_2026_27.weeks import auto_playoffs, playoff_byes


def test_bracket_by_team_count():
    for n in (2, 3):
        teams, rounds = auto_playoffs(n)
        assert teams == 2 and [r["name"] for r in rounds] == ["Championship"] and rounds[0]["weeks"] == 1
    for n in (4, 5, 6):
        teams, rounds = auto_playoffs(n)
        assert teams == 4 and [r["name"] for r in rounds] == ["Semifinals", "Championship"]
    for n in (7, 8, 12, 16):
        teams, rounds = auto_playoffs(n)
        assert teams == 6 and len(rounds) == 3 and playoff_byes({"playoff_teams": teams, "playoff_rounds": rounds}) == 2
