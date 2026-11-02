"""Standings tiebreakers (2026-11-01, the commissioner's): win %, head-to-head (only when every tied team has played
every other), points scored per matchup, points allowed per matchup (fewer first), sign-up date (earlier first)."""
from backend.fantasy_2026_27.engine import rank


def team(i, joined="2026-09-01"):
    return {"id": i, "name": i, "joined_at": joined}


def row(i, w, l, pf, pa, joined="2026-09-01"):
    return {"team": team(i, joined), "w": w, "l": l, "t": 0, "pf": pf, "pa": pa}


def order(rows, h2h=()):
    return [r["team"]["id"] for r in rank(rows, list(h2h))]


def test_win_pct_first_even_with_uneven_games():
    assert order([row("a", 1, 0, 100, 90), row("b", 2, 1, 900, 10), row("c", 0, 1, 500, 1)]) == ["a", "b", "c"]


def test_head_to_head_only_when_everyone_met():
    two = [row("a", 1, 1, 300, 200), row("b", 1, 1, 200, 200)]
    assert order(two, [("b", "a", 120, 100)]) == ["b", "a"]                   # b beat a: head-to-head wins
    three = two + [row("c", 1, 1, 250, 200)]
    assert order(three, [("b", "a", 120, 100)]) == ["a", "c", "b"]            # c never played them: points per matchup


def test_points_for_then_against_then_sign_up():
    assert order([row("a", 1, 0, 100, 90), row("b", 1, 0, 120, 99)]) == ["b", "a"]
    assert order([row("a", 1, 0, 100, 90), row("b", 1, 0, 100, 80)]) == ["b", "a"]
    assert order([row("a", 1, 0, 100, 90, "2026-09-05"), row("b", 1, 0, 100, 90, "2026-09-02")]) == ["b", "a"]
