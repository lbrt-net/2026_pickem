"""A spread of league setups the setting-dependent checks run across, so they hold for any league — not just
today's. Add a setup here and every check that uses LEAGUES runs on it too."""
LAYOUTS = {
    "today": {"G": 1, "F": 1, "C": 1, "TEAM": 1, "FLEX": 1, "BENCH": 2},
    "big": {"G": 2, "F": 2, "C": 2, "TEAM": 2, "FLEX": 3, "BENCH": 3},
    "no teams": {"G": 2, "F": 2, "C": 1, "FLEX": 2, "BENCH": 1},
    "starters only": {"G": 1, "F": 1, "C": 1, "TEAM": 1},
}
# (name, roster layout, team count, budget, minimum bid, minimum raise %)
LEAGUES = [
    ("today", "today", 5, 200, 1, 4),
    ("big league", "big", 12, 200, 1, 4),
    ("cheap", "today", 4, 100, 1, 0),
    ("rich", "big", 8, 1000, 5, 10),
    ("no NBA teams", "no teams", 6, 300, 2, 4),
    ("starters only", "starters only", 10, 200, 1, 25),
]


def settings(league):
    _, layout, _, budget, min_bid, raise_pct = league
    return {"roster_slots": LAYOUTS[layout], "auction_budget": budget, "auction_min_bid": min_bid, "auction_min_raise_pct": raise_pct}


def team_ids(league):
    return [f"T{i}" for i in range(league[2])]
