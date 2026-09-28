"""Scoring, roster rules, and the simulated draft — shared by routes and schema."""

# Roster format: 2 G, 2 F, 2 C, 2 NBA Team, 3 Flex (any player or NBA team).
SLOTS = {"G": 2, "F": 2, "C": 2, "TEAM": 2, "FLEX": 3}
# Real box scores only list G/F/C (for starters); PG/SG/SF/PF kept for the old dummy pool.
# A player with no known position can only fill FLEX.
SLOT_POSITIONS = {"G": {"PG", "SG", "G"}, "F": {"SF", "PF", "F"}, "C": {"C"}}

# User's scoring (nba-pipeline/fantasy/fantasy_scoring.py). ROADMAP: confirm.
SCORING = {"pts": 1.0, "fgx": -0.5, "fg3m": 0.5, "ftx": -0.5, "oreb": 1.5, "dreb": 0.5,
           "ast": 1.0, "stl": 2.0, "blk": 1.5, "tov": -2.0}


def _g(p, *keys):
    for k in keys:
        if k in p and p[k] is not None:
            return p[k]
    return 0


def player_points(p) -> float:
    """Fantasy points for one box score line or a per-game average row
    (accepts oreb/dreb or off_reb/def_reb)."""
    fgx = _g(p, "fga") - _g(p, "fgm")
    ftx = _g(p, "fta") - _g(p, "ftm")
    return round(
        SCORING["pts"] * _g(p, "pts") + SCORING["fgx"] * fgx + SCORING["fg3m"] * _g(p, "fg3m")
        + SCORING["ftx"] * ftx + SCORING["oreb"] * _g(p, "oreb", "off_reb") + SCORING["dreb"] * _g(p, "dreb", "def_reb")
        + SCORING["ast"] * _g(p, "ast") + SCORING["stl"] * _g(p, "stl") + SCORING["blk"] * _g(p, "blk")
        + SCORING["tov"] * _g(p, "tov"), 1)


# Placeholder until NBA-team-slot scoring is decided (ROADMAP open decision):
# 50 for a win plus the point margin, per game.
def team_game_points(won: bool, pts: float, opp_pts: float) -> float:
    return round(50 * (1 if won else 0) + (pts - opp_pts), 1)


def nba_team_points(t) -> float:
    """Per-game average of team_game_points from season totals/averages."""
    win_pct = t["wins"] / t["games_played"] if t["games_played"] else 0
    return round(50 * win_pct + (t["pts"] - t["opp_pts"]), 1)


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


def simulate_draft(cur, scenario):
    """Snake draft, best available fantasy points first, respecting slots."""
    cur.execute("SELECT id FROM fantasy_teams WHERE scenario = %s ORDER BY name", (scenario,))
    order = [r["id"] for r in cur.fetchall()]
    if not order:
        return
    cur.execute("SELECT * FROM fantasy_players")
    pool = [{"kind": "player", "id": p["id"], "position": p["position"], "pts": player_points(p)} for p in cur.fetchall()]
    cur.execute("SELECT * FROM fantasy_nba_teams")
    pool += [{"kind": "nba_team", "id": t["id"], "position": "TEAM", "pts": nba_team_points(t)} for t in cur.fetchall()]
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
