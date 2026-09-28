from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from backend.auth import read_session_cookie, require_admin
from backend.config import INTERNAL_API_KEY
from backend.db import get_db

from .logic import SLOTS, nba_team_points, player_points, simulate_draft, team_game_points
from .schema import SCENARIOS, PoolLocked, ensure_teams, refresh_pool
from .weeks import season_weeks, week_for

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


# ---- Real NBA data: weeks, schedule, per-entity game logs + projections ----

SEASONS_AVAILABLE = ("2026-27", "2025-26", "2024-25", "2023-24", "2022-23")
LIVE_SEASON = "2026-27"
MIN_GAMES_FOR_SEASON_AVG = 10  # below this, project from last season instead


def _season_arg(season: Optional[str]) -> str:
    if season and season not in SEASONS_AVAILABLE:
        raise HTTPException(status_code=400, detail=f"season must be one of {SEASONS_AVAILABLE}")
    return season or LIVE_SEASON


def _prev_season(season: str) -> str:
    y = int(season[:4]) - 1
    return f"{y}-{str(y + 1)[2:]}"


def _jsonable_week(w):
    return {**w, "start": w["start"].isoformat(), "end": w["end"].isoformat()}


@router.get("/weeks")
async def weeks(season: Optional[str] = None):
    season = _season_arg(season)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            ws = season_weeks(cur, season)
    finally:
        conn.close()
    return {"season": season, "weeks": [_jsonable_week(w) for w in ws]}


@router.post("/admin/pool/refresh")
async def admin_refresh_pool(request: Request):
    """Rebuild the draftable pool from loaded box scores (refuses if live has rosters)."""
    require_admin(request)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            try:
                result = refresh_pool(cur)
            except PoolLocked as e:
                raise HTTPException(status_code=409, detail=str(e))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        conn.commit()
    finally:
        conn.close()
    return result


@router.get("/schedule")
async def schedule_week(season: Optional[str] = None, week: Optional[int] = None):
    """One fantasy week of the NBA schedule: games by day plus each NBA team's game count."""
    season = _season_arg(season)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            ws = season_weeks(cur, season)
            if not ws:
                return {"season": season, "weeks": [], "week": None, "games": [], "team_counts": {}}
            if week is None:
                current = week_for(ws, date.today())
                sel = current or (ws[0] if date.today() < ws[0]["start"] else ws[-1])
            else:
                sel = next((w for w in ws if w["week"] == week), None)
                if not sel:
                    raise HTTPException(status_code=404, detail="no such week")
            cur.execute("""
                SELECT game_id, game_type, game_date, tipoff_utc, time_tbd, status, status_text,
                       home_team, away_team, home_score, away_score, label
                FROM nba_games
                WHERE season = %s AND missing_since IS NULL AND game_date BETWEEN %s AND %s
                  AND game_type IN ('regular', 'cup_final')
                ORDER BY game_date, tipoff_utc NULLS LAST, game_id
            """, (season, sel["start"], sel["end"]))
            games = cur.fetchall()
    finally:
        conn.close()
    counts = {}
    for g in games:
        # Only regular-season games that will actually be played count for fantasy.
        if g["game_type"] != "regular" or g["status"] in ("postponed", "cancelled"):
            continue
        for t in (g["home_team"], g["away_team"]):
            if t:
                counts[t] = counts.get(t, 0) + 1
    return {"season": season, "weeks": [_jsonable_week(w) for w in ws], "week": _jsonable_week(sel),
            "games": games, "team_counts": counts}


def _player_avg(cur, player_id: str, season: str, before: Optional[date] = None):
    """(avg fantasy pts per game played, games) over a season's regular-season games."""
    cur.execute("""
        SELECT pg.* FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
        WHERE pg.player_id = %s AND pg.season = %s AND pg.minutes > 0 AND g.game_type = 'regular'
          AND (%s::date IS NULL OR g.game_date < %s::date)
    """, (player_id, season, before, before))
    rows = cur.fetchall()
    if not rows:
        return None, 0
    return round(sum(player_points(r) for r in rows) / len(rows), 1), len(rows)


def _team_avg(cur, team: str, season: str, before: Optional[date] = None):
    cur.execute("""
        SELECT home_team, home_score, away_score FROM nba_games
        WHERE season = %s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL
          AND (home_team = %s OR away_team = %s) AND (%s::date IS NULL OR game_date < %s::date)
    """, (season, team, team, before, before))
    rows = cur.fetchall()
    if not rows:
        return None, 0
    pts = []
    for g in rows:
        mine, theirs = (g["home_score"], g["away_score"]) if g["home_team"] == team else (g["away_score"], g["home_score"])
        pts.append(team_game_points(mine > theirs, mine, theirs))
    return round(sum(pts) / len(pts), 1), len(pts)


@router.get("/entity/{entity_id}/games")
async def entity_games(entity_id: str, season: Optional[str] = None):
    """Every game for one draftable entity (a player by NBA id, or an NBA team by
    tricode) in a season: actual fantasy points for games played, a projection for
    games still scheduled, and per-fantasy-week totals.

    Projection per game = this season's average once they have 10+ games before
    today, otherwise last season's average."""
    season = _season_arg(season)
    today = date.today()
    conn = get_db()
    try:
        with conn.cursor() as cur:
            ws = season_weeks(cur, season)
            is_team = not entity_id.isdigit()

            if is_team:
                team = entity_id.upper()
                cur.execute("""
                    SELECT game_id, game_date, status, status_text, home_team, away_team, home_score, away_score
                    FROM nba_games WHERE season = %s AND game_type = 'regular' AND missing_since IS NULL
                      AND (home_team = %s OR away_team = %s) ORDER BY game_date, game_id
                """, (season, team, team))
                sched = cur.fetchall()
                name = team
                box = {}
                cur_avg, cur_n = _team_avg(cur, team, season, today)
                prev_avg, _ = _team_avg(cur, team, _prev_season(season))
            else:
                cur.execute("""
                    SELECT pg.*, g.game_date FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
                    WHERE pg.player_id = %s AND pg.season = %s ORDER BY g.game_date
                """, (entity_id, season))
                box = {r["game_id"]: r for r in cur.fetchall()}
                cur.execute("""
                    SELECT player_name, team FROM nba_player_games WHERE player_id = %s ORDER BY game_id DESC LIMIT 1
                """, (entity_id,))
                who = cur.fetchone()
                if not who:
                    raise HTTPException(status_code=404, detail="no games for this player")
                name, team = who["player_name"], who["team"]
                # Games they played for whichever team, plus their current team's remaining schedule.
                cur.execute("""
                    SELECT game_id, game_date, status, status_text, home_team, away_team, home_score, away_score
                    FROM nba_games WHERE season = %s AND game_type = 'regular' AND missing_since IS NULL
                      AND (game_id = ANY(%s::text[]) OR ((home_team = %s OR away_team = %s) AND status <> 'final'))
                    ORDER BY game_date, game_id
                """, (season, list(box), team, team))
                sched = cur.fetchall()
                cur_avg, cur_n = _player_avg(cur, entity_id, season, today)
                prev_avg, _ = _player_avg(cur, entity_id, _prev_season(season))
    finally:
        conn.close()

    if cur_n >= MIN_GAMES_FOR_SEASON_AVG:
        proj, basis = cur_avg, f"{season} average ({cur_n} games)"
    elif prev_avg is not None:
        proj, basis = prev_avg, f"{_prev_season(season)} average"
    else:
        proj, basis = cur_avg, (f"{season} average ({cur_n} games)" if cur_n else "no history")

    games = []
    for g in sched:
        side_team = team
        if not is_team and g["game_id"] in box:
            side_team = box[g["game_id"]]["team"]
        home = g["home_team"] == side_team
        row = {
            "game_id": g["game_id"], "date": g["game_date"].isoformat(), "status": g["status"],
            "opponent": g["away_team"] if home else g["home_team"], "home": home,
            "week": (week_for(ws, g["game_date"]) or {}).get("week"),
        }
        if is_team and g["status"] == "final":
            mine, theirs = (g["home_score"], g["away_score"]) if home else (g["away_score"], g["home_score"])
            row.update(result=f"{'W' if mine > theirs else 'L'} {mine}-{theirs}", fantasy_points=team_game_points(mine > theirs, mine, theirs))
        elif not is_team and g["game_id"] in box:
            b = box[g["game_id"]]
            row.update(minutes=b["minutes"], pts=b["pts"], reb=b["oreb"] + b["dreb"], ast=b["ast"], stl=b["stl"],
                       blk=b["blk"], tov=b["tov"], dnp=b["dnp_reason"],
                       fantasy_points=player_points(b) if b["minutes"] > 0 else 0)
        elif g["status"] == "final":
            row.update(dnp="Did not play", fantasy_points=0)
        elif g["status"] in ("postponed", "cancelled"):
            row.update(dnp=g["status"].capitalize())
        else:
            row.update(projected=proj)
        games.append(row)

    week_rows = []
    for w in ws:
        gs = [g for g in games if g["week"] == w["week"]]
        actual = round(sum(g.get("fantasy_points") or 0 for g in gs), 1)
        remaining = [g for g in gs if "projected" in g]
        week_rows.append({
            **_jsonable_week(w), "games": len(gs),
            "played": sum(1 for g in gs if (g.get("minutes") or 0) > 0 or (is_team and "result" in g)),
            "actual": actual, "remaining": len(remaining),
            "projected_total": round(actual + sum(g["projected"] or 0 for g in remaining), 1),
        })

    return {"id": entity_id, "name": name, "kind": "nba_team" if is_team else "player", "team": team,
            "season": season, "projection_per_game": proj, "projection_basis": basis,
            "weeks": week_rows, "games": games}
