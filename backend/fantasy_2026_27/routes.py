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
                             "fantasy_points": player_points(r)}
                team = teams[r["team_id"]]
                team["roster"].append({**entry, "slot": r["slot"]})
                team["total_fantasy_points"] += entry["fantasy_points"]
        conn.commit()
    finally:
        conn.close()
    for t in teams.values():
        t["total_fantasy_points"] = round(t["total_fantasy_points"], 1)
    return sorted(teams.values(), key=lambda t: -t["total_fantasy_points"])


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
