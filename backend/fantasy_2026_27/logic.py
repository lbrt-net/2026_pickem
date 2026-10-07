"""Scoring, roster rules, and the simulated draft — shared by routes and schema."""

# Roster layout is a league setting (weeks.DEFAULT_SETTINGS["roster_slots"]); these are the
# slot types' rules. Real box scores only list G/F/C (starters); PG/SG/SF/PF are the old dummy pool.
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


def open_slot(filled: dict, pick: dict, slots: dict) -> str | None:
    """Which roster slot a pick goes into, or None if it can't fit. Most specific slot first:
    TEAM for NBA teams; G/F/C by position for players; FLEX for either; BENCH
    (anyone) only once no starting spot fits.
    `filled` = slot type → how many used; `slots` = the league's roster_slots."""
    def free(t):
        return filled.get(t, 0) < slots.get(t, 0)
    if pick["kind"] == "nba_team":
        order = ["TEAM"]
    else:
        pos = next((s for s, positions in SLOT_POSITIONS.items() if pick.get("position") in positions), None)
        order = [pos] if pos else []
    for t in order + ["FLEX", "BENCH"]:
        if free(t):
            return t
    return None


def draft_pool(cur, rank_points: dict | None = None, season_pool: dict | None = None) -> list[dict]:
    """Every draftable entity, best first. `rank_points` (entity id → value) overrides the
    ranking — PROJ AVG when the league's season has a pool; the replay without one ranks on the
    season before the one being replayed (no peeking). `season_pool` (projections.pool) limits
    players to that season's pool and gives each his position for the season."""
    cur.execute("SELECT * FROM fantasy_players")
    pool = [{"kind": "player", "id": p["id"], "name": p["name"],
             "position": (season_pool[p["id"]]["position"] or p["position"]) if season_pool else p["position"],
             "pts": player_points(p)}
            for p in cur.fetchall() if season_pool is None or p["id"] in season_pool]
    cur.execute("SELECT * FROM fantasy_nba_teams")
    pool += [{"kind": "nba_team", "id": t["id"], "name": t["name"], "position": "TEAM", "pts": nba_team_points(t)}
             for t in cur.fetchall()]
    if rank_points is not None:
        for e in pool:
            e["pts"] = rank_points.get(e["id"], float("-inf"))
    return sorted(pool, key=lambda e: -e["pts"])


def simulate_draft(cur, scenario, slots: dict, rank_points: dict | None = None):
    """Instant snake draft, best available first, respecting the league's roster slots."""
    cur.execute("SELECT id FROM fantasy_teams WHERE scenario = %s ORDER BY name", (scenario,))
    order = [r["id"] for r in cur.fetchall()]
    if not order:
        return
    pool = draft_pool(cur, rank_points)
    filled = {tid: {} for tid in order}
    pick_no = 0
    for rnd in range(sum(slots.values())):
        for tid in (order if rnd % 2 == 0 else reversed(order)):
            for i, pick in enumerate(pool):
                slot = open_slot(filled[tid], pick, slots)
                if slot:
                    filled[tid][slot] = filled[tid].get(slot, 0) + 1
                    pool.pop(i)
                    pick_no += 1
                    cur.execute("""
                        INSERT INTO fantasy_rosters (scenario, team_id, slot, player_id, nba_team_id, pick_no, auto)
                        VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                    """, (scenario, tid, slot,
                          pick["id"] if pick["kind"] == "player" else None,
                          pick["id"] if pick["kind"] == "nba_team" else None, pick_no))
                    break
