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


def test_two_week_final_is_two_legs():
    from datetime import date, timedelta
    from backend.fantasy_2026_27.weeks import build_weeks, normalize_settings
    start = date(2025, 10, 20)
    days = {start + timedelta(days=d) for d in range(0, 7 * 24) if d % 7 in (1, 3, 5)}
    asb = [date(2026, 2, 15)]
    s = normalize_settings({"playoff_auto": False, "playoff_teams": 6,
                            "playoff_rounds": [{"name": "Quarterfinals", "weeks": 1}, {"name": "Semifinals", "weeks": 1},
                                               {"name": "Championship", "weeks": 2}]})
    weeks = build_weeks(days, asb, s)
    po = [w for w in weeks if w["kind"] == "playoffs"]
    assert [w["label"] for w in po] == ["Quarterfinals", "Semifinals", "Championship · Leg 1", "Championship · Leg 2"]
    assert all(w["calendar_weeks"] == 1 for w in po[-2:])                     # each leg is its own week
