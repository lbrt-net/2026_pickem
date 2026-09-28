from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from backend.auth import read_session_cookie, require_admin
from backend.config import INTERNAL_API_KEY
from backend.db import get_db

from .logic import SLOTS, nba_team_points, player_points, simulate_draft
from .schema import SCENARIOS, ensure_teams

router = APIRouter()

TEST_SCENARIOS = ("test_pre", "test_post")


def _scenario(request: Request, scenario: Optional[str]) -> str:
    """Only admins may view test sandboxes; everyone else always gets live."""
    if not scenario or scenario == "live" or scenario not in SCENARIOS:
        return "live"
    key = request.headers.get("X-Internal-Key")
    if key and INTERNAL_API_KEY and key == INTERNAL_API_KEY:
        return scenario
    user = read_session_cookie(request) or {}
    return scenario if user.get("is_admin") else "live"


def _ownership(cur, scenario):
    """entity id -> (team_id, team_name, owner_user_id, slot) for one scenario."""
    ensure_teams(cur, scenario)
    cur.execute("""
        SELECT r.player_id, r.nba_team_id, r.slot, t.id AS team_id, t.name AS team_name, t.owner_user_id
        FROM fantasy_rosters r JOIN fantasy_teams t ON t.id = r.team_id
        WHERE r.scenario = %s
    """, (scenario,))
    owned = {}
    for r in cur.fetchall():
        owned[r["player_id"] or r["nba_team_id"]] = r
    return owned


def _owner_fields(row):
    if not row:
        return {"team_id": None, "team_name": None, "owner_user_id": None, "slot": None}
    return {k: row[k] for k in ("team_id", "team_name", "owner_user_id", "slot")}


@router.get("/players")
async def list_players(request: Request, scenario: Optional[str] = None):
    scenario = _scenario(request, scenario)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            owned = _ownership(cur, scenario)
            cur.execute("SELECT * FROM fantasy_players ORDER BY name")
            rows = cur.fetchall()
        conn.commit()
    finally:
        conn.close()
    return [{**dict(r), "fantasy_points": player_points(r), **_owner_fields(owned.get(r["id"]))} for r in rows]


@router.get("/nba-teams")
async def list_nba_teams(request: Request, scenario: Optional[str] = None):
    scenario = _scenario(request, scenario)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            owned = _ownership(cur, scenario)
            cur.execute("SELECT * FROM fantasy_nba_teams ORDER BY name")
            rows = cur.fetchall()
        conn.commit()
    finally:
        conn.close()
    return [{**dict(r), "fantasy_points": nba_team_points(r), **_owner_fields(owned.get(r["id"]))} for r in rows]


@router.get("/teams")
async def list_teams(request: Request, scenario: Optional[str] = None):
    """Each fantasy team with its roster and total fantasy points."""
    scenario = _scenario(request, scenario)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            ensure_teams(cur, scenario)
            cur.execute("SELECT id, name, owner_user_id FROM fantasy_teams WHERE scenario = %s ORDER BY name", (scenario,))
            teams = {t["id"]: {**dict(t), "roster": [], "total_fantasy_points": 0.0} for t in cur.fetchall()}
            cur.execute("""
                SELECT r.team_id, r.slot, p.*, n.id AS nba_id, n.name AS nba_name,
                       n.games_played AS n_gp, n.wins AS n_wins, n.pts AS n_pts, n.opp_pts AS n_opp
                FROM fantasy_rosters r
                LEFT JOIN fantasy_players p ON p.id = r.player_id
                LEFT JOIN fantasy_nba_teams n ON n.id = r.nba_team_id
                WHERE r.scenario = %s
            """, (scenario,))
            for r in cur.fetchall():
                if r["nba_id"]:
                    entry = {"kind": "nba_team", "id": r["nba_id"], "name": r["nba_name"], "position": "TEAM",
                             "fantasy_points": nba_team_points({"games_played": r["n_gp"], "wins": r["n_wins"], "pts": r["n_pts"], "opp_pts": r["n_opp"]})}
                else:
                    entry = {"kind": "player", "id": r["id"], "name": r["name"], "position": r["position"],
                             "nba_team": r["nba_team"], "fantasy_points": player_points(r)}
                team = teams[r["team_id"]]
                team["roster"].append({**entry, "slot": r["slot"]})
                team["total_fantasy_points"] += entry["fantasy_points"]
        conn.commit()
    finally:
        conn.close()
    for t in teams.values():
        t["total_fantasy_points"] = round(t["total_fantasy_points"], 1)
    return sorted(teams.values(), key=lambda t: -t["total_fantasy_points"])


@router.get("/draft")
async def draft(request: Request, scenario: Optional[str] = None):
    """Draft picks in order (roster insert order = pick order), plus each entity's
    rank in the whole pool by fantasy points, so steals/reaches can be judged."""
    scenario = _scenario(request, scenario)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            ensure_teams(cur, scenario)
            cur.execute("SELECT id, name, owner_user_id FROM fantasy_teams WHERE scenario = %s ORDER BY name", (scenario,))
            order = cur.fetchall()
            cur.execute("SELECT * FROM fantasy_players")
            players = {p["id"]: p for p in cur.fetchall()}
            cur.execute("SELECT * FROM fantasy_nba_teams")
            nba = {t["id"]: t for t in cur.fetchall()}
            cur.execute("""
                SELECT r.team_id, r.slot, r.player_id, r.nba_team_id, t.name AS team_name, t.owner_user_id
                FROM fantasy_rosters r JOIN fantasy_teams t ON t.id = r.team_id
                WHERE r.scenario = %s ORDER BY r.id
            """, (scenario,))
            rows = cur.fetchall()
        conn.commit()
    finally:
        conn.close()

    points = {pid: player_points(p) for pid, p in players.items()}
    points.update({tid: nba_team_points(t) for tid, t in nba.items()})
    pool_rank = {eid: i + 1 for i, eid in enumerate(sorted(points, key=lambda e: -points[e]))}

    n = len(order) or 1
    picks = []
    for i, r in enumerate(rows):
        eid = r["player_id"] or r["nba_team_id"]
        ent = players.get(eid) or nba.get(eid)
        picks.append({
            "pick": i + 1, "round": i // n + 1,
            "team_id": r["team_id"], "team_name": r["team_name"], "owner_user_id": r["owner_user_id"],
            "slot": r["slot"], "kind": "player" if r["player_id"] else "nba_team",
            "id": eid, "name": ent["name"], "position": ent.get("position") or "TEAM",
            "fantasy_points": points[eid], "pool_rank": pool_rank[eid],
        })
    return {"order": [dict(t) for t in order], "picks": picks, "rounds": sum(SLOTS.values())}


@router.get("/league")
async def league(request: Request, scenario: Optional[str] = None):
    scenario = _scenario(request, scenario)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM fantasy_rosters WHERE scenario = %s", (scenario,))
            drafted = cur.fetchone()["count"]
    finally:
        conn.close()
    return {"scenario": scenario, "phase": "post_draft" if drafted else "pre_draft", "slots": SLOTS}


@router.post("/admin/scenario/{scenario}/reset")
async def reset_scenario(scenario: str, request: Request):
    """Reset a test sandbox. Never touches live."""
    require_admin(request)
    if scenario not in TEST_SCENARIOS:
        raise HTTPException(status_code=400, detail="Only test scenarios can be reset")
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM fantasy_rosters WHERE scenario = %s", (scenario,))
            ensure_teams(cur, scenario)
            if scenario == "test_post":
                simulate_draft(cur, scenario)
        conn.commit()
    finally:
        conn.close()
    return {"ok": True, "scenario": scenario}
