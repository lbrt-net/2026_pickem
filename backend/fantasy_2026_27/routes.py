from fastapi import APIRouter

from backend.db import get_db

router = APIRouter()

# Placeholder scoring formula — the league's real scoring categories aren't
# decided yet (see CLAUDE.md conversation history), so this is a stand-in
# just to give the dummy data a single sortable "fantasy points" number.
def _fantasy_points(p) -> float:
    return round(
        p["pts"]
        + 1.2 * (p["off_reb"] + p["def_reb"])
        + 1.5 * p["ast"]
        + 3 * p["stl"]
        + 3 * p["blk"],
        1,
    )


@router.get("/players")
async def list_players():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.*, t.id AS team_id, t.name AS team_name
                FROM fantasy_players p
                LEFT JOIN fantasy_rosters r ON r.player_id = p.id
                LEFT JOIN fantasy_teams t ON t.id = r.team_id
                ORDER BY p.name
            """)
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "position": r["position"],
            "nba_team": r["nba_team"],
            "games_played": r["games_played"],
            "minutes": r["minutes"],
            "pts": r["pts"],
            "off_reb": r["off_reb"],
            "def_reb": r["def_reb"],
            "ast": r["ast"],
            "stl": r["stl"],
            "blk": r["blk"],
            "fantasy_points": _fantasy_points(r),
            "team_id": r["team_id"],
            "team_name": r["team_name"],
        }
        for r in rows
    ]


@router.get("/teams")
async def list_teams():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT t.id, t.name, p.pts, p.off_reb, p.def_reb, p.ast, p.stl, p.blk
                FROM fantasy_teams t
                LEFT JOIN fantasy_rosters r ON r.team_id = t.id
                LEFT JOIN fantasy_players p ON p.id = r.player_id
            """)
            rows = cur.fetchall()
    finally:
        conn.close()

    teams = {}
    for r in rows:
        team = teams.setdefault(r["id"], {"id": r["id"], "name": r["name"], "total_fantasy_points": 0.0, "roster_size": 0})
        if r["pts"] is not None:
            team["total_fantasy_points"] += _fantasy_points(r)
            team["roster_size"] += 1

    for team in teams.values():
        team["total_fantasy_points"] = round(team["total_fantasy_points"], 1)

    return sorted(teams.values(), key=lambda t: -t["total_fantasy_points"])
