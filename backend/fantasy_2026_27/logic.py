"""Scoring, roster rules, and the simulated draft — shared by routes and schema."""

# Roster format: 2 G, 2 F, 2 C, 2 NBA Team, 3 Flex (any player or NBA team).
SLOTS = {"G": 2, "F": 2, "C": 2, "TEAM": 2, "FLEX": 3}
# Real box scores only list G/F/C (for starters); PG/SG/SF/PF kept for the old dummy pool.
# A player with no known position can only fill FLEX.
SLOT_POSITIONS = {"G": {"PG", "SG", "G"}, "F": {"SF", "PF", "F"}, "C": {"C"}}

# Basic scoring — locked design in FANTASY_SCORING.md. `blkd` (own shot blocked) counts
# as 0 until its source (misc box score / play-by-play) is loaded.
SCORING = {"pts": 1.0, "fgx": -0.5, "blkd": -0.5, "fg3m": 0.5, "ftx": -1.0, "oreb": 1.5, "dreb": 0.5,
           "ast": 1.0, "stl": 2.0, "blk": 1.5, "tov": -2.0}


def _g(p, *keys):
    for k in keys:
        if k in p and p[k] is not None:
            return p[k]
    return 0


# Display order + labels for the scoring rules (the one place pages get them from).
SCORING_RULES = [
    ("pts", "PTS", "Points"), ("fgx", "FG-", "Missed field goals"), ("blkd", "BLKD", "Own shot blocked"),
    ("fg3m", "3PTM", "3-pointers made"), ("ftx", "FT-", "Missed free throws"),
    ("oreb", "OREB", "Offensive rebounds"), ("dreb", "DREB", "Defensive rebounds"), ("ast", "AST", "Assists"),
    ("stl", "STL", "Steals"), ("blk", "BLK", "Blocks"), ("tov", "TO", "Turnovers"),
]


def scoring_counts(p) -> dict:
    """Raw box score line (or per-game average row) → the count for each scoring category.
    Derived stats (misses) are computed here and nowhere else."""
    return {
        "pts": _g(p, "pts"), "fgx": _g(p, "fga") - _g(p, "fgm"), "blkd": _g(p, "blkd"),
        "fg3m": _g(p, "fg3m"), "ftx": _g(p, "fta") - _g(p, "ftm"),
        "oreb": _g(p, "oreb", "off_reb"), "dreb": _g(p, "dreb", "def_reb"), "ast": _g(p, "ast"),
        "stl": _g(p, "stl"), "blk": _g(p, "blk"), "tov": _g(p, "tov"),
    }


def score_breakdown(p) -> dict:
    """Fantasy points per category, e.g. {"pts": 23.0, "fgx": -5.5, ...}."""
    return {k: round(SCORING[k] * v, 2) + 0.0 for k, v in scoring_counts(p).items()}  # +0.0: no "-0.0"


def player_points(p) -> float:
    """Fantasy points for one box score line or a per-game average row
    (accepts oreb/dreb or off_reb/def_reb)."""
    return round(sum(score_breakdown(p).values()), 1)


# NBA team slots: point margin per game, TOTALED over the week (the steady contrast to players'
# best single game). Can be negative. Balance vs. player scores comes later.
def team_game_points(won: bool, pts: float, opp_pts: float) -> float:
    return round(pts - opp_pts, 1)


def nba_team_points(t) -> float:
    """Per-game average of team_game_points (average point margin)."""
    return round(t["pts"] - t["opp_pts"], 1)


def _open_slot(filled, pick):
    """Which roster slot a pick goes into for a team, or None if it can't fit."""
    if pick["kind"] == "nba_team":
        specific = "TEAM"
    else:
        specific = next((s for s, positions in SLOT_POSITIONS.items() if pick["position"] in positions), None)
    if specific and filled[specific] < SLOTS[specific]:
        return specific
    if filled["FLEX"] < SLOTS["FLEX"]:
        return "FLEX"
    return None


def simulate_draft(cur, scenario, rank_points: dict | None = None):
    """Snake draft, best available fantasy points first, respecting slots.
    `rank_points` (entity id → value) overrides the ranking — the replay drafts on the
    season *before* the one being replayed, so it can't see the future."""
    cur.execute("SELECT id FROM fantasy_teams WHERE scenario = %s ORDER BY name", (scenario,))
    order = [r["id"] for r in cur.fetchall()]
    if not order:
        return
    cur.execute("SELECT * FROM fantasy_players")
    pool = [{"kind": "player", "id": p["id"], "position": p["position"], "pts": player_points(p)} for p in cur.fetchall()]
    cur.execute("SELECT * FROM fantasy_nba_teams")
    pool += [{"kind": "nba_team", "id": t["id"], "position": "TEAM", "pts": nba_team_points(t)} for t in cur.fetchall()]
    if rank_points is not None:
        for e in pool:
            e["pts"] = rank_points.get(e["id"], float("-inf"))
    pool.sort(key=lambda e: -e["pts"])

    filled = {tid: {s: 0 for s in SLOTS} for tid in order}
    rounds = sum(SLOTS.values())
    for rnd in range(rounds):
        for tid in (order if rnd % 2 == 0 else reversed(order)):
            for i, pick in enumerate(pool):
                slot = _open_slot(filled[tid], pick)
                if slot:
                    filled[tid][slot] += 1
                    pool.pop(i)
                    cur.execute("""
                        INSERT INTO fantasy_rosters (scenario, team_id, slot, player_id, nba_team_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (scenario, tid, slot,
                          pick["id"] if pick["kind"] == "player" else None,
                          pick["id"] if pick["kind"] == "nba_team" else None))
                    break
