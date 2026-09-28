"""Scoring, roster rules, and the simulated draft — shared by routes and schema."""

# Roster format: 2 G, 2 F, 2 C, 2 NBA Team, 3 Flex (any player or NBA team).
SLOTS = {"G": 2, "F": 2, "C": 2, "TEAM": 2, "FLEX": 3}
SLOT_POSITIONS = {"G": {"PG", "SG"}, "F": {"SF", "PF"}, "C": {"C"}}


# Placeholder scoring — the league's real scoring rules aren't decided yet.
def player_points(p) -> float:
    return round(p["pts"] + 1.2 * (p["off_reb"] + p["def_reb"]) + 1.5 * p["ast"] + 3 * p["stl"] + 3 * p["blk"], 1)


def nba_team_points(t) -> float:
    win_pct = t["wins"] / t["games_played"] if t["games_played"] else 0
    return round(50 * win_pct + (t["pts"] - t["opp_pts"]), 1)


def _open_slot(filled, pick):
    """Which roster slot a pick goes into for a team, or None if it can't fit."""
    if pick["kind"] == "nba_team":
        specific = "TEAM"
    else:
        specific = next(s for s, positions in SLOT_POSITIONS.items() if pick["position"] in positions)
    if filled[specific] < SLOTS[specific]:
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
