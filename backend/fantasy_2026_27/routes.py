from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from backend.auth import read_session_cookie, require_admin
from backend.config import INTERNAL_API_KEY
from backend.db import get_db

from .logic import (SCORING, SCORING_RULES, nba_team_points, player_points, score_breakdown,
                    simulate_draft, team_game_points)
from .schema import SCENARIOS, PoolLocked, ensure_teams, refresh_pool
from . import draft, engine
from . import league as league_mod
from .settings import logo_url
from .weeks import DEFAULT_SETTINGS, league_settings, playoff_byes, season_weeks, slot_list, week_for

router = APIRouter()

TEST_SCENARIOS = ("test_pre", "test_post")


PUBLIC_SCENARIOS = ("live", "replay")  # replay = the 2025-26 test league, open to everyone


def _scenario(request: Request, scenario: Optional[str]) -> str:
    """Live and the test league are public; other sandboxes are admin-only (else live)."""
    if not scenario or scenario not in SCENARIOS:
        return "live"
    if scenario in PUBLIC_SCENARIOS:
        return scenario
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
            cur.execute("""
                SELECT id, name, abbreviation, color, glyph, owner_user_id, logo_updated, picture_url FROM fantasy_teams WHERE scenario = %s ORDER BY name
            """, (scenario,))
            teams = {t["id"]: {"id": t["id"], "name": t["name"], "abbreviation": t["abbreviation"], "color": t["color"], "glyph": t["glyph"],
                               "owner_user_id": t["owner_user_id"], "logo_url": logo_url(t),
                               "roster": [], "total_fantasy_points": 0.0} for t in cur.fetchall()}
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
    slots = slot_list(_settings_for(scenario))
    for t in teams.values():
        t["total_fantasy_points"] = round(t["total_fantasy_points"], 1)
        t["slot_list"] = slots  # the league's roster layout, for laying out empty spots
    return sorted(teams.values(), key=lambda t: -t["total_fantasy_points"])


def _settings_for(scenario: str) -> dict:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            return league_settings(cur, scenario)
    finally:
        conn.close()


def _db(fn):
    """Run fn(cur) in a transaction; ValueError → 400, PermissionError → 403."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            try:
                result = fn(cur)
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        conn.commit()
        return result
    finally:
        conn.close()


@router.get("/draft")
async def draft_state(request: Request, scenario: Optional[str] = None):
    """Live draft state: status, snake order, picks so far, who's on the clock and the deadline.
    Expired pick clocks are auto-picked as part of this read."""
    scenario = _scenario(request, scenario)
    return _db(lambda cur: draft.state(cur, scenario))


@router.post("/draft/pick")
async def draft_pick(request: Request, scenario: Optional[str] = None):
    """The team on the clock drafts. Body: {"entity_id": "<NBA player id or team tricode>"}.
    The team's owner or any admin (commissioner picks for bots) may pick."""
    user = read_session_cookie(request) or {}
    if not user:
        raise HTTPException(status_code=401, detail="Log in first")
    scenario = _scenario(request, scenario)
    body = await request.json()
    _db(lambda cur: draft.make_pick(cur, scenario, str(body.get("entity_id", "")), user))
    return await draft_state(request, scenario)


@router.post("/draft/nominate")
async def draft_nominate(request: Request, scenario: Optional[str] = None):
    """Auction: the nominating team puts a player up. Body: {"entity_id", "amount", "team_id"?}
    (team_id lets the commissioner act for a bot/fake team)."""
    user = read_session_cookie(request) or {}
    if not user:
        raise HTTPException(status_code=401, detail="Log in first")
    scenario = _scenario(request, scenario)
    body = await request.json()
    _db(lambda cur: draft.nominate(cur, scenario, user, str(body.get("entity_id", "")), int(body.get("amount", 0)), body.get("team_id")))
    return await draft_state(request, scenario)


@router.post("/draft/bid")
async def draft_bid(request: Request, scenario: Optional[str] = None):
    """Auction: top the high bid on the player up for bid. Body: {"amount", "team_id"?}."""
    user = read_session_cookie(request) or {}
    if not user:
        raise HTTPException(status_code=401, detail="Log in first")
    scenario = _scenario(request, scenario)
    body = await request.json()
    _db(lambda cur: draft.bid(cur, scenario, user, int(body.get("amount", 0)), body.get("team_id")))
    return await draft_state(request, scenario)


@router.post("/admin/draft/{action}")
async def draft_admin(action: str, request: Request, scenario: Optional[str] = None):
    """Commissioner: order (body {"team_ids": [...]}, before the draft), randomize (order, before
    the draft), start (clears rosters, clock starts), reset (back to before the draft),
    autopick (current pick; auction: close bidding now / nominate now), autodraft (all remaining;
    auction: every player to its nominator at the minimum bid)."""
    user = require_admin(request)
    scenario = scenario if scenario in SCENARIOS else "live"
    body = await request.json() if action == "order" else {}
    actions = {
        "order": lambda cur: draft.set_order(cur, scenario, [str(t) for t in body.get("team_ids", [])]),
        "randomize": lambda cur: draft.randomize_order(cur, scenario),
        "start": lambda cur: draft.start(cur, scenario),
        "reset": lambda cur: draft.reset(cur, scenario),
        "autopick": lambda cur: draft.auto_pick_now(cur, scenario, user),
        "autodraft": lambda cur: draft.auto_pick_now(cur, scenario, user, rest=True),
    }
    if action not in actions:
        raise HTTPException(status_code=404, detail="unknown draft action")
    _db(actions[action])
    return await draft_state(request, scenario)


@router.get("/league/members")
async def league_members(request: Request, scenario: Optional[str] = None):
    """Teams in the league, whether the viewer is in it, and whether they can join or leave."""
    scenario = _scenario(request, scenario)
    viewer = read_session_cookie(request)
    return _db(lambda cur: league_mod.members(cur, scenario, viewer))


@router.post("/league/join")
async def league_join(request: Request, scenario: Optional[str] = None):
    """Join before the draft starts. Body (all optional): {"name", "abbreviation", "picture":
    "avatar"|"upload"|"glyph", "glyph", "color"}. Blank name/abbreviation = Discord display name +
    automatic abbreviation. An uploaded picture follows via PUT /teams/{team_id}/logo."""
    user = read_session_cookie(request)
    if not user:
        raise HTTPException(status_code=401, detail="Log in first")
    scenario = _scenario(request, scenario)
    body = await request.json()
    team_id = _db(lambda cur: league_mod.join(
        cur, scenario, user, body.get("name"), body.get("abbreviation"),
        body.get("picture"), body.get("glyph"), body.get("color")))
    return {"team_id": team_id, **(await league_members(request, scenario))}


@router.post("/league/leave")
async def league_leave(request: Request, scenario: Optional[str] = None):
    """Before the draft: the team is removed. After it starts: the team becomes a bot the commissioner controls."""
    user = read_session_cookie(request)
    if not user:
        raise HTTPException(status_code=401, detail="Log in first")
    scenario = _scenario(request, scenario)
    _db(lambda cur: league_mod.leave(cur, scenario, user))
    return await league_members(request, scenario)


@router.post("/admin/league/teams/{team_id}/remove")
async def admin_remove_team(team_id: str, request: Request, scenario: Optional[str] = None):
    """Commissioner: remove a team. Before the draft it's deleted; once the draft has started it
    stays as a bot the commissioner controls."""
    require_admin(request)
    scenario = _scenario(request, scenario)
    _db(lambda cur: league_mod.remove_team(cur, scenario, team_id))
    return await league_members(request, scenario)


@router.get("/league")
async def league(request: Request, scenario: Optional[str] = None):
    scenario = _scenario(request, scenario)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM fantasy_rosters WHERE scenario = %s", (scenario,))
            drafted = cur.fetchone()["count"]
            s = league_settings(cur, scenario)
    finally:
        conn.close()
    return {"scenario": scenario, "phase": "post_draft" if drafted else "pre_draft",
            "slots": s["roster_slots"], "slot_list": slot_list(s)}


@router.post("/admin/scenario/{scenario}/reset")
async def reset_scenario(scenario: str, request: Request):
    """Reset a test sandbox. Never touches live."""
    require_admin(request)
    if scenario not in TEST_SCENARIOS:
        raise HTTPException(status_code=400, detail="Only test scenarios can be reset")

    def run(cur):
        draft.reset(cur, scenario)
        ensure_teams(cur, scenario)
        if scenario == "test_post":
            simulate_draft(cur, scenario, league_settings(cur, scenario)["roster_slots"])
    _db(run)
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


@router.get("/scoring")
async def scoring_rules():
    """The basic scoring rules, in display order — pages read these instead of hardcoding."""
    return {"format": "best_single_game_per_week",
            "rules": [{"key": k, "label": label, "name": name, "points": SCORING[k]} for k, label, name in SCORING_RULES],
            "pending": {"blkd": "counts 0 until the misc box score is loaded"}}


@router.post("/scoring/preview")
async def scoring_preview(request: Request):
    """Score a raw stat line (the Scoring page's calculator), with the same code as real games.
    Body: raw box score numbers, e.g. {"pts": 3, "fgm": 1, "fga": 1, "fg3m": 1}."""
    line = await request.json()
    if not isinstance(line, dict) or not all(isinstance(v, (int, float)) for v in line.values()):
        raise HTTPException(status_code=400, detail="send a JSON object of numbers")
    return {"breakdown": score_breakdown(line), "fantasy_points": player_points(line)}


def _league_settings(cur, request: Request, scenario: Optional[str]) -> dict:
    """Commissioner settings of the (sandbox-gated) league — used for every week calculation."""
    return engine.settings(engine.league(cur, _scenario(request, scenario)))


@router.get("/weeks")
async def weeks(request: Request, season: Optional[str] = None, scenario: Optional[str] = None):
    season = _season_arg(season)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            ws = season_weeks(cur, season, _league_settings(cur, request, scenario))
    finally:
        conn.close()
    return {"season": season, "weeks": [_jsonable_week(w) for w in ws]}


@router.get("/league/settings")
async def get_league_settings(request: Request, scenario: Optional[str] = None):
    """The commissioner's settings for a league (defaults filled in), plus the week layout they
    produce for that league's season."""
    scenario = _scenario(request, scenario)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            lg = engine.league(cur, scenario)
            s = engine.settings(lg)
            ws = season_weeks(cur, lg["season"], s)
    finally:
        conn.close()
    return {"scenario": scenario, "season": lg["season"], "settings": s, "defaults": DEFAULT_SETTINGS,
            "playoff_byes": playoff_byes(s), "weeks": [_jsonable_week(w) for w in ws]}


@router.put("/admin/league/settings")
async def put_league_settings(request: Request, scenario: Optional[str] = None):
    """Commissioner: change a league's settings. Body: any subset of
    {"league_name", "playoff_teams", "playoff_rounds": [{"name", "weeks"}], "cutoff_days", "fuse_all_star",
    "matchup_schedule"}. Validated against the league's season before saving."""
    require_admin(request)
    scenario = scenario if scenario in SCENARIOS else "live"
    changes = await request.json()
    if not isinstance(changes, dict):
        raise HTTPException(status_code=400, detail="send a JSON object of settings")
    conn = get_db()
    try:
        with conn.cursor() as cur:
            try:
                engine.save_settings(cur, scenario, changes)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        conn.commit()
    finally:
        conn.close()
    return await get_league_settings(request, scenario)


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
async def schedule_week(request: Request, season: Optional[str] = None, week: Optional[int] = None,
                        scenario: Optional[str] = None):
    """One fantasy week of the NBA schedule: games by day plus each NBA team's game count."""
    season = _season_arg(season)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            ws = season_weeks(cur, season, _league_settings(cur, request, scenario))
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
async def entity_games(request: Request, entity_id: str, season: Optional[str] = None, scenario: Optional[str] = None):
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
            ws = season_weeks(cur, season, _league_settings(cur, request, scenario))
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
                    SELECT player_name, team FROM nba_player_games
                    WHERE player_id = %s AND substr(game_id, 3, 1) <> '3' ORDER BY game_id DESC LIMIT 1
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
            played = b["minutes"] > 0
            row.update(minutes=b["minutes"], pts=b["pts"], reb=b["oreb"] + b["dreb"], ast=b["ast"], stl=b["stl"],
                       blk=b["blk"], tov=b["tov"], dnp=b["dnp_reason"],
                       box={k: b[k] for k in ("fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb", "blkd", "pfd", "pf")},
                       breakdown=score_breakdown(b) if played else None,
                       fantasy_points=player_points(b) if played else 0)
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


# ---- League engine: clock + results (replay sandbox scaffolding) ----

@router.get("/results")
async def league_results(request: Request, scenario: Optional[str] = None):
    """Weekly matchups (best game per player, point margin per NBA team slot) and standings,
    from real box scores up to the league's as-of date."""
    scenario = _scenario(request, scenario)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            try:
                return engine.results(cur, scenario)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.post("/admin/league/replay/clock")
async def replay_clock(request: Request):
    """Move the replay clock. Body: {"date": "2025-11-03"} or {"days": 1} or {"weeks": 1}."""
    require_admin(request)
    body = await request.json()
    conn = get_db()
    try:
        with conn.cursor() as cur:
            lg = engine.league(cur, engine.REPLAY)
            current = engine.as_of(lg)
            if "date" in body:
                try:
                    target = date.fromisoformat(body["date"])
                except (TypeError, ValueError):
                    raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
            elif "days" in body or "weeks" in body:
                target = current + timedelta(days=int(body.get("days", 0)) + 7 * int(body.get("weeks", 0)))
            else:
                raise HTTPException(status_code=400, detail="send date, days, or weeks")
            engine.set_clock(cur, engine.REPLAY, target)
        conn.commit()
    finally:
        conn.close()
    return {"sim_date": target.isoformat()}


@router.post("/admin/league/replay/reset")
async def replay_reset(request: Request):
    """Re-draft the replay league on the prior season's stats and rewind the clock to opening week."""
    require_admin(request)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            try:
                result = engine.reset_replay(cur)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        conn.commit()
    finally:
        conn.close()
    return result
