"""Transaction Log rows (transactions._join_moves, 2026-10-27): a drop on its own and the same team's next add-only
checkout in the same week are one move (UNO: Miles Bridges dropped 9:50 PM, Jaden McDaniels added the next day)."""
from backend.fantasy_2026_27.transactions import _join_moves


def g(team, at, adds=(), drops=(), week=2, via=None):
    return {"team_id": team, "at": at, "week": week, "via": via, "adds": list(adds), "drops": list(drops)}


def test_drop_then_next_add_is_one_move():
    items = [  # newest first, like the log
        g("UNO", "10-27 17:53", adds=["McDaniels"]),
        g("SEPH", "10-27 10:56", adds=["Barrett"]),
        g("CODY", "10-26 21:51", adds=["Miller"]),
        g("UNO", "10-26 21:50", drops=["Bridges"]),
        g("CODY", "10-26 21:49", drops=["Ball"]),
    ]
    out = _join_moves(items)
    assert [(x["team_id"], x["adds"], x["drops"], x.get("drop_at")) for x in out] == [
        ("UNO", ["McDaniels"], ["Bridges"], "10-26 21:50"),
        ("SEPH", ["Barrett"], [], None),
        ("CODY", ["Miller"], ["Ball"], "10-26 21:49"),
    ]


def test_what_stays_apart():
    items = [
        g("A", "3", adds=["x"], week=3),          # next week: not joined
        g("A", "2", drops=["y"], week=2),
        g("B", "2b", adds=["p"], drops=["q"]),    # a full swap after a drop: not joined
        g("B", "1b", drops=["r"]),
        g("C", "2c", adds=["s"], via="trade"),     # trades stay their own entries
        g("C", "1c", drops=["t"]),
    ]
    assert len(_join_moves(items)) == 6
