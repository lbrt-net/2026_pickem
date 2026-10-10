"""Scoring, roster rules, and the simulated draft — shared by routes and schema."""

# Roster layout is a league setting (weeks.DEFAULT_SETTINGS["roster_slots"]); these are the
# slot types' rules. Real box scores only list G/F/C (starters); PG/SG/SF/PF are the old dummy pool.
SLOT_POSITIONS = {"G": {"PG", "SG", "G"}, "F": {"SF", "PF", "F"}, "C": {"C"}}

# Scoring lives in scoring.py (rulesets as data, one scorer). These are the old entry points, kept so callers
# that don't know their league score with the defaults; pass `rules` (scoring.league_rules) to use a league's own.
from . import scoring as _scoring

SCORING = {c["stat"]: c["points"] for c in _scoring.DEFAULT["player"]["components"] if c["type"] == "per_stat"}
# Display order + labels for the default player rules.
SCORING_RULES = [(c["id"], c["label"], c["name"]) for c in _scoring.DEFAULT["player"]["components"]]


def scoring_counts(p) -> dict:
    """Raw box score line (or per-game average row) → the count for each default scoring category."""
    line = _scoring.player_line(p)
    return {c["id"]: line.get(c["stat"], 0) for c in _scoring.DEFAULT["player"]["components"]}


def score_breakdown(p, rules=None) -> dict:
    """Fantasy points per component, e.g. {"pts": 23.0, "fgx": -5.5, ...}."""
    return _scoring.score_game((rules or _scoring.DEFAULT)["player"], _scoring.player_line(p))["breakdown"]


def player_points(p, rules=None) -> float:
    """Fantasy points for one box score line or a per-game average row (accepts oreb/dreb or off_reb/def_reb)."""
    return _scoring.score_game((rules or _scoring.DEFAULT)["player"], _scoring.player_line(p))["total"]


def team_game_points(won: bool, pts: float, opp_pts: float, rules=None, extra=None) -> float:
    """One NBA team game's fantasy points (default rules: its point margin; the week sums them)."""
    return _scoring.score_game((rules or _scoring.DEFAULT)["team"], _scoring.team_line(pts, opp_pts, extra))["total"]


def nba_team_points(t) -> float:
    """Per-game average for an NBA team row (season averages: pts / opp_pts) under the default rules."""
    return team_game_points(t["pts"] > t["opp_pts"], t["pts"], t["opp_pts"])


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


def fits_somewhere(entity: dict, slots: dict) -> bool:
    """Can this player / NBA team fill at least one kind of spot under the league's roster rules? (Anything that
    can't — e.g. NBA teams in a league with no TM, Flex or Bench spot — doesn't belong in the pool.)"""
    def ok(t):
        if not slots.get(t):
            return False
        if t in ("FLEX", "BENCH"):
            return True
        if entity.get("kind") == "nba_team":
            return t == "TEAM"
        return t in SLOT_POSITIONS and entity.get("position") in SLOT_POSITIONS[t]
    return any(ok(t) for t in slots)


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
