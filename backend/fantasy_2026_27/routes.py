from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import StreamingResponse
from psycopg2.extras import Json

from backend.auth import read_session_cookie, require_admin
from backend.config import INTERNAL_API_KEY
from backend.db import get_db

from .logic import (nba_team_points, player_points, score_breakdown,
                    simulate_draft, team_game_points)
from .schema import SCENARIOS, PoolLocked, ensure_teams, refresh_pool
from . import draft, lineup, engine, projections, history, transactions, waivers, health, winprob, board as board_mod, scoring as scoring_mod
from . import league as league_mod
from . import live
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


def _actor(request: Request) -> dict:
    """Who's acting: the logged-in user, or — with the internal key — the commissioner (scripts, practice runs)."""
    key = request.headers.get("X-Internal-Key")
    if key and INTERNAL_API_KEY and key == INTERNAL_API_KEY:
        return {"is_admin": True}
    return read_session_cookie(request) or {}


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
def list_players(request: Request, scenario: Optional[str] = None):
    scenario = _scenario(request, scenario)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            waivers.process(cur, scenario)  # settle waivers that are up, then who's on them now
            held = waivers.on_waivers(cur, scenario)
            owned = _ownership(cur, scenario)
            season_pool = projections.pool_for(cur, scenario)  # None = no pool for this season (old behavior)
            cur.execute("SELECT * FROM fantasy_players ORDER BY name")
            rows = cur.fetchall()
        conn.commit()
    finally:
        conn.close()

    def pool_fields(r):
        if season_pool is None:
            return {"in_pool": None}
        p = season_pool.get(r["id"])
        if not p:
            return {"in_pool": False}
        return {"in_pool": True, "position": p["position"] or r["position"], "nba_team": p["nba_team"] or r["nba_team"],
                "proj_avg": p["proj_avg"], "proj_max": p.get("proj_max"), "proj_flags": p["flags"], "pool_source": p["source"]}
    return [{**dict(r), "fantasy_points": player_points(r), **pool_fields(r), **_owner_fields(owned.get(r["id"])),
             "waivers": held.get(r["id"])} for r in rows]


@router.get("/nba-teams")
def list_nba_teams(request: Request, scenario: Optional[str] = None):
    scenario = _scenario(request, scenario)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            owned = _ownership(cur, scenario)
            held = waivers.on_waivers(cur, scenario)
            cur.execute("SELECT * FROM fantasy_nba_teams ORDER BY name")
            rows = cur.fetchall()
        conn.commit()
    finally:
        conn.close()
    return [{**dict(r), "fantasy_points": nba_team_points(r), **_owner_fields(owned.get(r["id"])), "waivers": held.get(r["id"])} for r in rows]


@router.get("/teams")
def list_teams(request: Request, scenario: Optional[str] = None):
    """Each fantasy team with its roster and total fantasy points."""
    scenario = _scenario(request, scenario)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            ensure_teams(cur, scenario)
            cur.execute("""
                SELECT t.id, t.name, t.abbreviation, t.color, t.glyph, t.owner_user_id, t.logo_updated, t.picture_url, t.picture_mode, u.username AS owner_name
                FROM fantasy_teams t LEFT JOIN users u ON u.discord_id = t.owner_user_id WHERE t.scenario = %s ORDER BY t.name
            """, (scenario,))
            teams = {t["id"]: {"id": t["id"], "name": t["name"], "abbreviation": t["abbreviation"], "color": t["color"], "glyph": t["glyph"],
                               "owner_user_id": t["owner_user_id"], "owner_name": t["owner_name"], "logo_url": logo_url(t),
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


@router.get("/team/{team_id}/week")
def team_week(team_id: str, request: Request, scenario: Optional[str] = None, week: Optional[int] = None):
    """One team's lineup for a week (default: the current week): spots, each player's games that
    week with points, best game, season points per game, and whether he's locked."""
    scenario = _scenario(request, scenario)
    return _db(lambda cur: lineup.week_view(cur, scenario, team_id, week))


@router.get("/team/{team_id}/week/outlook")
def team_week_outlook(team_id: str, request: Request, scenario: Optional[str] = None, week: Optional[int] = None):
    """The same week with current injuries applied (backend only for now; the pages still read /week).
    Per player: injury {status, short, injury, return_date, reported_at} or null; each game's out (Out, before
    ESPN's estimated return date — every game when there's none); games_out; projected and games_left count only
    the games he's expected to play. Day-To-Day projects as usual."""
    scenario = _scenario(request, scenario)
    return _db(lambda cur: lineup.week_view(cur, scenario, team_id, week, injuries=True))


@router.post("/team/{team_id}/move")
def team_move(team_id: str, request: Request, scenario: Optional[str] = None, body_in: Optional[dict] = Body(default=None)):
    """Move a player to another spot. Body: {"entity_id", "to_slot", "swap_with"?}. Owner or
    commissioner. Applies this week if nobody involved has played yet, else from next week."""
    user = read_session_cookie(request) or {}
    if not user:
        raise HTTPException(status_code=401, detail="Log in first")
    scenario = _scenario(request, scenario)
    body = (body_in or {})
    week = body.get("week")
    return _db(lambda cur: lineup.move(cur, scenario, user, team_id, str(body.get("entity_id", "")),
                                       str(body.get("to_slot", "")), body.get("swap_with"), int(week) if week else None,
                                       confirm=bool(body.get("confirm"))))


@router.post("/team/{team_id}/checkout")
def team_checkout(team_id: str, request: Request, scenario: Optional[str] = None, body_in: Optional[dict] = Body(default=None)):
    """Adds and drops (transactions.py). Body: {"adds": [ids], "drops": [ids], "apply": bool}. apply=false only
    checks: {ok, error, roster (after the moves, with change keep/add/drop), spots_used, spots_total}. apply=true
    makes the moves (400 with the reason if the roster wouldn't be legal). Owner or commissioner."""
    user = _actor(request)
    if not user:
        raise HTTPException(status_code=401, detail="Log in first")
    scenario = _scenario(request, scenario)
    body = (body_in or {})
    return _db(lambda cur: transactions.checkout(cur, scenario, user, team_id, body.get("adds") or [], body.get("drops") or [],
                                                 bool(body.get("apply"))))


@router.get("/team/{team_id}/claims")
def team_claims(team_id: str, request: Request, scenario: Optional[str] = None):
    """This team's pending waiver claims and its place in the claim order (owner or commissioner)."""
    user = _actor(request)
    if not user:
        raise HTTPException(status_code=401, detail="Log in first")
    scenario = _scenario(request, scenario)

    def run(cur):
        waivers._team(cur, scenario, team_id, user)
        waivers.process(cur, scenario)
        return waivers.claims_for(cur, scenario, team_id)
    return _db(run)


@router.post("/team/{team_id}/claims")
def team_claim(team_id: str, request: Request, scenario: Optional[str] = None, body_in: Optional[dict] = Body(default=None)):
    """Claim a player on waivers. Body: {"entity_id", "drop_id"?} — drop_id is dropped only if the claim wins."""
    user = _actor(request)
    if not user:
        raise HTTPException(status_code=401, detail="Log in first")
    scenario = _scenario(request, scenario)
    body = body_in or {}
    return _db(lambda cur: waivers.claim(cur, scenario, user, team_id, str(body.get("entity_id", "")), body.get("drop_id") or None))


@router.delete("/team/{team_id}/claims/{claim_id}")
def team_claim_cancel(team_id: str, claim_id: int, request: Request, scenario: Optional[str] = None):
    user = _actor(request)
    if not user:
        raise HTTPException(status_code=401, detail="Log in first")
    scenario = _scenario(request, scenario)
    return _db(lambda cur: waivers.cancel(cur, scenario, user, team_id, claim_id))


@router.get("/admin/health")
def admin_health(request: Request, scenario: Optional[str] = None):
    """The check-up (health.py): what's wrong or out of date in the real data, in plain words. Commissioner / script key."""
    require_admin(request)
    scenario = scenario if scenario in SCENARIOS else "live"
    return _db(lambda cur: health.summary(cur, scenario))


@router.get("/week/winprob")
def week_winprob(request: Request, scenario: Optional[str] = None, week: Optional[int] = None):
    """Win probability for every matchup in a week (winprob.py): the rest of the week played out thousands of times."""
    scenario = _scenario(request, scenario)
    return _db(lambda cur: winprob.week_probs(cur, scenario, week))


@router.get("/transactions")
def transactions_log(request: Request, scenario: Optional[str] = None):
    """Transaction Log: every add / drop checkout, newest first (transactions.log). Draft picks come from GET /draft."""
    scenario = _scenario(request, scenario)
    return _db(lambda cur: transactions.log(cur, scenario))


@router.get("/draft")
def draft_state(request: Request, scenario: Optional[str] = None):  # plain def: runs in a worker thread, so polls don't block the server
    """Live draft state: status, snake order, picks so far, who's on the clock and the deadline.
    Expired pick clocks are auto-picked as part of this read."""
    scenario = _scenario(request, scenario)
    viewer = read_session_cookie(request) or {}
    return _db(lambda cur: draft.state(cur, scenario, viewer))


@router.get("/draft/stream")
def draft_stream(request: Request, scenario: Optional[str] = None):
    """Live updates for the draft room (server-sent events): a 'change' message whenever the draft changes — the
    page then reads GET /draft. Comment lines every 15 s keep it open (live.py)."""
    scenario = _scenario(request, scenario)
    return StreamingResponse(live.stream(scenario), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/draft/pick")
def draft_pick(request: Request, scenario: Optional[str] = None, body_in: Optional[dict] = Body(default=None)):
    """The team on the clock drafts. Body: {"entity_id": "<NBA player id or team tricode>"}.
    The team's owner or any admin (commissioner picks for bots) may pick."""
    user = _actor(request)
    if not user:
        raise HTTPException(status_code=401, detail="Log in first")
    scenario = _scenario(request, scenario)
    body = (body_in or {})
    _db(lambda cur: draft.make_pick(cur, scenario, str(body.get("entity_id", "")), user))
    live.notify(scenario)
    return draft_state(request, scenario)


@router.get("/draft/queue")
def draft_queue_get(request: Request, scenario: Optional[str] = None):
    """Your team's draft queue (entity ids in order). Private to you."""
    user = read_session_cookie(request) or {}
    if not user:
        raise HTTPException(status_code=401, detail="Log in first")
    scenario = _scenario(request, scenario)

    def get(cur):
        cur.execute("SELECT id FROM fantasy_teams WHERE scenario = %s AND owner_user_id = %s", (scenario, user.get("discord_id")))
        row = cur.fetchone()
        return {"entity_ids": draft.queue_ids(cur, scenario, row["id"]) if row else [], "has_team": bool(row)}
    return _db(get)


@router.put("/draft/queue")
def draft_queue_put(request: Request, scenario: Optional[str] = None, body_in: Optional[dict] = Body(default=None)):
    """Replace your team's draft queue. Body: {"entity_ids": [...]} in the order you want them.
    Auto-pick takes the first one still available that fits your roster."""
    user = read_session_cookie(request) or {}
    if not user:
        raise HTTPException(status_code=401, detail="Log in first")
    scenario = _scenario(request, scenario)
    body = (body_in or {})
    _db(lambda cur: draft.set_queue(cur, scenario, user, body.get("entity_ids") or []))
    return draft_queue_get(request, scenario)


@router.put("/admin/draft/queue")
def admin_draft_queue(request: Request, scenario: Optional[str] = None, body_in: Optional[dict] = Body(default=None)):
    """Commissioner: set any team's draft queue. Body: {"team_id", "entity_ids": [...]}."""
    user = require_admin(request)
    scenario = scenario if scenario in SCENARIOS else "live"
    body = (body_in or {})
    team_id = str(body.get("team_id", ""))
    _db(lambda cur: draft.set_queue(cur, scenario, user, body.get("entity_ids") or [], team_id=team_id))
    return _db(lambda cur: {"team_id": team_id, "entity_ids": draft.queue_ids(cur, scenario, team_id)})


@router.post("/draft/nominate")
def draft_nominate(request: Request, scenario: Optional[str] = None, body_in: Optional[dict] = Body(default=None)):
    """Auction: the nominating team puts a player up. Body: {"entity_id", "amount", "team_id"?}
    (team_id lets the commissioner act for a bot/fake team)."""
    user = _actor(request)
    if not user:
        raise HTTPException(status_code=401, detail="Log in first")
    scenario = _scenario(request, scenario)
    body = (body_in or {})
    _db(lambda cur: draft.nominate(cur, scenario, user, str(body.get("entity_id", "")), int(body.get("amount", 0)), body.get("team_id")))
    live.notify(scenario)
    return draft_state(request, scenario)


@router.post("/draft/bid")
def draft_bid(request: Request, scenario: Optional[str] = None, body_in: Optional[dict] = Body(default=None)):
    """Auction: top the high bid on the player up for bid. Body: {"amount", "team_id"?}."""
    user = _actor(request)
    if not user:
        raise HTTPException(status_code=401, detail="Log in first")
    scenario = _scenario(request, scenario)
    body = (body_in or {})
    _db(lambda cur: draft.bid(cur, scenario, user, int(body.get("amount", 0)), body.get("team_id")))
    live.notify(scenario)
    return draft_state(request, scenario)


@router.post("/admin/draft/{action}")
def draft_admin(action: str, request: Request, scenario: Optional[str] = None, body_in: Optional[dict] = Body(default=None)):
    """Commissioner: order (body {"team_ids": [...]}, before the draft), randomize (order, before
    the draft), start (clears rosters, clock starts), reset (back to before the draft),
    autopick (current pick; auction: close bidding now / nominate now), autodraft (all remaining;
    auction: every player to its nominator at the minimum bid), autopick-team (body {"team_id",
    "on"}: that team picks / nominates the moment it's on the clock)."""
    user = require_admin(request)
    scenario = scenario if scenario in SCENARIOS else "live"
    body = (body_in or {}) if action in ("order", "autopick-team") else {}
    actions = {
        "order": lambda cur: draft.set_order(cur, scenario, [str(t) for t in body.get("team_ids", [])]),
        "randomize": lambda cur: draft.randomize_order(cur, scenario),
        "start": lambda cur: draft.start(cur, scenario),
        "reset": lambda cur: draft.reset(cur, scenario),
        "autopick": lambda cur: draft.auto_pick_now(cur, scenario, user),
        "autodraft": lambda cur: draft.auto_pick_now(cur, scenario, user, rest=True),
        "autopick-team": lambda cur: draft.set_autopick(cur, scenario, str(body.get("team_id", "")), bool(body.get("on"))),
    }
    if action not in actions:
        raise HTTPException(status_code=404, detail="unknown draft action")
    _db(actions[action])
    live.notify(scenario)
    return draft_state(request, scenario)


@router.get("/league/members")
def league_members(request: Request, scenario: Optional[str] = None):
    """Teams in the league, whether the viewer is in it, and whether they can join or leave."""
    scenario = _scenario(request, scenario)
    viewer = read_session_cookie(request)
    return _db(lambda cur: league_mod.members(cur, scenario, viewer))


@router.post("/league/join")
def league_join(request: Request, scenario: Optional[str] = None, body_in: Optional[dict] = Body(default=None)):
    """Join before the draft starts. Body (all optional): {"name", "abbreviation", "picture":
    "avatar"|"upload"|"glyph", "glyph", "color"}. Blank name/abbreviation = Discord display name +
    automatic abbreviation. An uploaded picture follows via PUT /teams/{team_id}/logo."""
    user = read_session_cookie(request)
    if not user:
        raise HTTPException(status_code=401, detail="Log in first")
    scenario = _scenario(request, scenario)
    body = (body_in or {})
    team_id = _db(lambda cur: league_mod.join(
        cur, scenario, user, body.get("name"), body.get("abbreviation"),
        body.get("picture"), body.get("glyph"), body.get("color")))
    return {"team_id": team_id, **(league_members(request, scenario))}


@router.post("/league/leave")
def league_leave(request: Request, scenario: Optional[str] = None):
    """Before the draft: the team is removed. After it starts: the team becomes a bot the commissioner controls."""
    user = read_session_cookie(request)
    if not user:
        raise HTTPException(status_code=401, detail="Log in first")
    scenario = _scenario(request, scenario)
    _db(lambda cur: league_mod.leave(cur, scenario, user))
    return league_members(request, scenario)


@router.post("/admin/league/teams/{team_id}/remove")
def admin_remove_team(team_id: str, request: Request, scenario: Optional[str] = None):
    """Commissioner: remove a team. Before the draft it's deleted; once the draft has started it
    stays as a bot the commissioner controls."""
    require_admin(request)
    scenario = _scenario(request, scenario)
    _db(lambda cur: league_mod.remove_team(cur, scenario, team_id))
    return league_members(request, scenario)


@router.get("/league")
def league(request: Request, scenario: Optional[str] = None):
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
def reset_scenario(scenario: str, request: Request):
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
def scoring_rules(request: Request, scenario: Optional[str] = None):
    """The league's scoring rulesets (scoring.py), in display order — pages read these instead of hardcoding.
    player / team: {week: best_game | sum, components: [{id, type, stat, points, label, name, below | at_least}]}.
    `rules` = the player per-stat components in the old {key, label, name, points} shape."""
    scenario = _scenario(request, scenario)
    rules, status = _db(lambda cur: (scoring_mod.league_rules(cur, scenario), projections.build_status(cur, scenario)))
    return {**scoring_mod.describe(rules),
            "rules": [{"key": c["id"], "label": c["label"], "name": c["name"], "points": c["points"]}
                      for c in rules["player"]["components"] if c["type"] == "per_stat"],
            # are the loaded projections built for these rules? (projections.build_status; stale → rebuild with
            # scripts/build_projections.py --post)
            "projections": status}


@router.post("/scoring/preview")
def scoring_preview(request: Request, scenario: Optional[str] = None, body_in: Optional[dict] = Body(default=None)):
    """Score a raw stat line (the Rules page's calculator) with the league's player rules — the same code as
    real games. Body: raw box score numbers, e.g. {"pts": 3, "fgm": 1, "fga": 1, "fg3m": 1}."""
    line = (body_in or {})
    if not isinstance(line, dict) or not all(isinstance(v, (int, float)) for v in line.values()):
        raise HTTPException(status_code=400, detail="send a JSON object of numbers")
    scenario = _scenario(request, scenario)
    rules = _db(lambda cur: scoring_mod.league_rules(cur, scenario))
    return {"breakdown": score_breakdown(line, rules), "fantasy_points": player_points(line, rules)}


def _league_settings(cur, request: Request, scenario: Optional[str]) -> dict:
    """Commissioner settings of the (sandbox-gated) league — used for every week calculation."""
    return engine.settings(engine.league(cur, _scenario(request, scenario)))


@router.get("/weeks")
def weeks(request: Request, season: Optional[str] = None, scenario: Optional[str] = None):
    season = _season_arg(season)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            ws = season_weeks(cur, season, _league_settings(cur, request, scenario))
    finally:
        conn.close()
    return {"season": season, "weeks": [_jsonable_week(w) for w in ws]}


@router.get("/league/settings")
def get_league_settings(request: Request, scenario: Optional[str] = None):
    """The commissioner's settings for a league (defaults filled in), plus the week layout they
    produce for that league's season."""
    scenario = _scenario(request, scenario)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            lg = engine.league(cur, scenario)
            s = engine.settings(lg)
            ws = season_weeks(cur, lg["season"], s)
            cur.execute("SELECT status FROM fantasy_drafts WHERE scenario = %s", (scenario,))
            row = cur.fetchone()
            cur.execute("SELECT 1 FROM fantasy_rosters WHERE scenario = %s LIMIT 1", (scenario,))
            draft_locked = bool((row and row["status"] != "not_started") or cur.fetchone())
    finally:
        conn.close()
    return {"scenario": scenario, "season": lg["season"], "as_of": engine.as_of(lg).isoformat(), "settings": s, "defaults": DEFAULT_SETTINGS,
            "playoff_byes": playoff_byes(s), "weeks": [_jsonable_week(w) for w in ws],
            "draft_locked": draft_locked, "draft_locked_keys": list(engine.DRAFT_LOCKED)}


@router.get("/league/matchups")
def league_matchups(request: Request, scenario: Optional[str] = None):
    """Every regular-season week's matchups (pairs of team ids) and whether the commissioner set it by hand."""
    scenario = _scenario(request, scenario)

    def run(cur):
        lg = engine.league(cur, scenario)
        weeks = engine.weeks_for_league(cur, lg)
        cur.execute("SELECT id, name, abbreviation, color, glyph, owner_user_id, logo_updated, picture_url, picture_mode FROM fantasy_teams WHERE scenario = %s ORDER BY name", (scenario,))
        teams = [{**dict(t), "logo_url": logo_url(t)} for t in cur.fetchall()]
        for t in teams:
            del t["logo_updated"], t["picture_url"], t["picture_mode"]
        overrides = engine.matchup_overrides(cur, scenario)
        out = [{"week": w["week"], "label": w["label"], "start": w["start"].isoformat(), "end": w["end"].isoformat(),
                "custom": w["week"] in overrides,
                "pairs": [[a["id"], b["id"]] for a, b in engine.week_pairings(teams, w["week"], overrides)]}
               for w in weeks if w["kind"] == "regular"]
        return {"teams": teams, "weeks": out}
    return _db(run)


@router.put("/admin/league/matchups")
def put_league_matchups(request: Request, scenario: Optional[str] = None, body_in: Optional[dict] = Body(default=None)):
    """Commissioner: set one week's matchups by hand. Body: {"week": 3, "pairs": [[team_id, team_id], ...]};
    "pairs": null puts the week back on the round robin."""
    require_admin(request)
    scenario = _scenario(request, scenario)
    body = (body_in or {})
    try:
        week = int(body.get("week"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="week must be a number")

    def run(cur):
        cur.execute("SELECT id FROM fantasy_teams WHERE scenario = %s", (scenario,))
        engine.set_matchups(cur, scenario, week, body.get("pairs"), {r["id"] for r in cur.fetchall()})
        return {"ok": True}
    _db(run)
    return league_matchups(request, scenario)


@router.put("/admin/league/settings")
def put_league_settings(request: Request, scenario: Optional[str] = None, body_in: Optional[dict] = Body(default=None)):
    """Commissioner: change a league's settings. Body: any subset of
    {"league_name", "playoff_teams", "playoff_rounds": [{"name", "weeks"}], "cutoff_days", "fuse_all_star",
    "matchup_schedule"}. Validated against the league's season before saving."""
    require_admin(request)
    scenario = scenario if scenario in SCENARIOS else "live"
    changes = (body_in or {})
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
    live.notify(scenario)  # a new draft time / type reaches open draft rooms
    return get_league_settings(request, scenario)


@router.post("/admin/pool/load")
def load_pool(request: Request, body: dict = Body(...)):
    """Load or update a season's draft pool and projections (scripts/load_projections.py).
    Body: {"season": "2026-27", "source": "roster" | "manual", "replace": false,
           "rows": [{player_id, name, nba_team, position (G/F/C), proj_avg, flags, proj_week {e, p25, p90}}],
           "rules"?: {player, team}} — the scoring the projections were built for (scripts/build_projections.py),
    recorded so GET /scoring can say when they're stale. Loading also applies each curve to the season's schedule once (PROJ MAX, per-week projection).
    "manual" adds a player ad hoc (e.g. a signing before he's played). Players who play a game later
    are added automatically as "detected"."""
    require_admin(request)
    season, rows = body.get("season"), body.get("rows")
    if not isinstance(season, str) or not isinstance(rows, list):
        raise HTTPException(status_code=400, detail="need season (str) and rows (list)")
    conn = get_db()
    try:
        with conn.cursor() as cur:
            try:
                out = projections.load(cur, season, rows, body.get("source", "roster"), bool(body.get("replace")))
                draft._HOT.clear()
                if body.get("rules"):  # the player ruleset these projections were built for
                    out["rules_version"] = projections.record_build(cur, season, "player", scoring_mod.validate(body["rules"])["player"])
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        conn.commit()
    finally:
        conn.close()
    return out


@router.get("/players/board")
def players_board(request: Request, view: str = "proj", scenario: Optional[str] = None):
    """The draft list's numbers for one view: view=proj (projected) or a past season ("2025-26" …).
    players: {id: {max, avg, gp, max_low, max_high, rank}, + total in a past season} (board.py)."""
    scenario = _scenario(request, scenario)
    return _db(lambda cur: board_mod.board(cur, scenario, view))


@router.get("/players/actual")
def players_actual(request: Request, window: str = "season", scenario: Optional[str] = None):
    """This season's real numbers for the Players page: window = season / d14 / d28 / w6 (board.actual).
    players: {id: {max, avg, gp, total, rank, + weeks {week no: score} for w6}}."""
    scenario = _scenario(request, scenario)
    return _db(lambda cur: board_mod.actual(cur, scenario, window))


@router.post("/admin/team-pool/load")
def load_team_pool(request: Request, body: dict = Body(...)):
    """Load a season's TEAM projections (scripts/load_team_clutch.py from TEAM_SCORING.md's team_draft4.json).
    Body: {"season": "2026-27", "rows": [{team, proj_avg, proj_max, max_low?, max_high?, curve?}], "rules"?: {player, team}}
    — curve = the team's weekly curve (team_proj_week_2026_27.json: e / p25 / p90 for 1..10 games); with it the team's
    per-week projection is applied to the schedule (projections.apply_team_schedule), which also sets PROJ MAX and MAX low / high.
    — rules = the scoring the projections were built for (scripts/build_projections.py), recorded for GET /scoring."""
    require_admin(request)
    season, rows = body.get("season"), body.get("rows")
    if not isinstance(season, str) or not isinstance(rows, list):
        raise HTTPException(status_code=400, detail="need season (str) and rows (list)")

    def run(cur):
        for r in rows:
            cur.execute("""
                INSERT INTO fantasy_team_pool (season, team, proj_avg, proj_max, max_low, max_high, proj_week) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (season, team) DO UPDATE SET proj_avg = EXCLUDED.proj_avg, proj_max = EXCLUDED.proj_max,
                    max_low = EXCLUDED.max_low, max_high = EXCLUDED.max_high,
                    proj_week = COALESCE(EXCLUDED.proj_week, fantasy_team_pool.proj_week), updated_at = now()
            """, (season, str(r["team"]).upper(), r.get("proj_avg"), r.get("proj_max"), r.get("max_low"), r.get("max_high"),
                  Json(r["curve"]) if r.get("curve") else None))
        applied = projections.apply_team_schedule(cur, season)
        draft._RANK_CACHE.clear()
        draft._HOT.clear()
        out = {"ok": True, "teams": len(rows), "applied": applied}
        if body.get("rules"):  # the team ruleset these projections were built for
            out["rules_version"] = projections.record_build(cur, season, "team", scoring_mod.validate(body["rules"])["team"])
        return out
    return _db(run)


@router.get("/players/{player_id}/history")
def player_history(request: Request, player_id: str, scenario: Optional[str] = None):
    """His weekly scores in past seasons ('23–'26, history.py) and, when the league's season has a pool, his
    projection under that season's schedule: PROJ AVG, PROJ MAX, the weekly-best curve, each week's game
    count and projected score, and his weeks split by game count."""
    scenario = _scenario(request, scenario)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            seasons = history.for_player(cur, player_id)
            season = projections.league_season(cur, scenario)
            cur.execute("""SELECT name, nba_team, position, proj_avg, proj_max, proj_week, proj_weeks, flags
                           FROM fantasy_pool WHERE season = %s AND player_id = %s""", (season, player_id))
            p = cur.fetchone()
        conn.commit()
    finally:
        conn.close()
    proj = None
    if not p:  # an NBA team: its TEAM projection, with its weekly curve on the schedule once loaded
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("""SELECT proj_avg, proj_max, max_low, max_high, proj_week, proj_weeks FROM fantasy_team_pool
                               WHERE season = %s AND team = %s""", (season, player_id.upper()))
                t = cur.fetchone()
        finally:
            conn.close()
        if t:
            proj = {"season": season, "proj_avg": t["proj_avg"], "proj_max": t["proj_max"], "max_low": t["max_low"],
                    "max_high": t["max_high"], "flags": None, "curve": t["proj_week"], "weeks": t["proj_weeks"] or [],
                    "by_games": projections.by_games(t["proj_weeks"]) if t["proj_weeks"] else []}
    if p:
        proj = {"season": season, **{k: p[k] for k in ("name", "nba_team", "position", "proj_avg", "proj_max", "flags")},
                "curve": p["proj_week"], "weeks": p["proj_weeks"], "by_games": projections.by_games(p["proj_weeks"])}
    return {"player_id": player_id, "seasons": seasons, "projection": proj}


@router.post("/admin/history/build")
def build_history(request: Request, body: dict = Body(default={})):
    """Rebuild fantasy_history from the stored box scores. Body: {"seasons": [...]} (default '23–'26)."""
    require_admin(request)
    seasons = body.get("seasons") or list(history.HISTORY_SEASONS)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            try:
                out = [history.build(cur, s) for s in seasons]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        conn.commit()
    finally:
        conn.close()
    return {"built": out}


@router.post("/admin/pool/refresh")
def admin_refresh_pool(request: Request):
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
def schedule_week(request: Request, season: Optional[str] = None, week: Optional[int] = None,
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
        SELECT game_id, home_team, home_score, away_score FROM nba_games
        WHERE season = %s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL
          AND (home_team = %s OR away_team = %s) AND (%s::date IS NULL OR game_date < %s::date)
    """, (season, team, team, before, before))
    rows = cur.fetchall()
    if not rows:
        return None, 0
    tx = scoring_mod.team_extras(cur, [g["game_id"] for g in rows])
    pts = []
    for g in rows:
        mine, theirs = (g["home_score"], g["away_score"]) if g["home_team"] == team else (g["away_score"], g["home_score"])
        pts.append(team_game_points(mine > theirs, mine, theirs, None, tx.get((g["game_id"], team))))
    return round(sum(pts) / len(pts), 1), len(pts)


@router.get("/entity/{entity_id}/games")
def entity_games(request: Request, entity_id: str, season: Optional[str] = None, scenario: Optional[str] = None):
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
            tx = scoring_mod.team_extras(cur, [g["game_id"] for g in sched]) if is_team else {}
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
            row.update(result=f"{'W' if mine > theirs else 'L'} {mine}-{theirs}", fantasy_points=team_game_points(mine > theirs, mine, theirs, None, tx.get((g["game_id"], team))))
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
def league_results(request: Request, scenario: Optional[str] = None):
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
def replay_clock(request: Request, body_in: Optional[dict] = Body(default=None)):
    """Move the replay clock. Body: {"date": "2025-11-03"} or {"days": 1} or {"weeks": 1}."""
    require_admin(request)
    body = (body_in or {})
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
def replay_reset(request: Request):
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
