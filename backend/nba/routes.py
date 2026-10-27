import asyncio
from datetime import date
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Request

from backend.auth import require_admin
from backend.db import get_db

from . import injuries, schedule

router = APIRouter()


@router.get("/schedule")
async def get_schedule(season: str = "2026-27", start: Optional[date] = None, end: Optional[date] = None,
                       team: Optional[str] = None, include_missing: bool = False):
    """Games for a season, optionally within [start, end] and/or for one team (tricode)."""
    where, args = ["season = %s"], [season]
    if start:
        where.append("game_date >= %s"); args.append(start)
    if end:
        where.append("game_date <= %s"); args.append(end)
    if team:
        where.append("(home_team = %s OR away_team = %s)"); args += [team.upper(), team.upper()]
    if not include_missing:
        where.append("missing_since IS NULL")
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM nba_games WHERE {' AND '.join(where)} ORDER BY game_date, tipoff_utc NULLS LAST, game_id", args)
            return cur.fetchall()
    finally:
        conn.close()


def _stats_json(name: str, static: str):
    """The page's data: the nightly refresh's copy in nba_stats_json if there is one, else the static file shipped with the app."""
    import json, logging, pathlib
    def run():
        try:
            conn = get_db()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT data FROM nba_stats_json WHERE name = %s", (name,))
                    row = cur.fetchone()
                if not row:
                    return None
                data = row["data"] if isinstance(row, dict) else row[0]
                return json.loads(data) if isinstance(data, str) else data
            finally:
                conn.close()
        except Exception:  # the static file is always there; never let the DB copy take the page down
            logging.getLogger("nba").exception("stats json read failed (%s); serving the static file", name)
            return None
    return run, json.loads((pathlib.Path(__file__).parent / static).read_text())


async def _league_page(name: str, static: str, league: str):
    """One stats page's data for a league (2026-10-19). NBA: unchanged. WNBA: the uploaded copy under 'wnba-<name>', else
    the static file wnba/<name>.json if one ships, else an empty page that says so."""
    import json, pathlib
    if league != "wnba":
        run, st = _stats_json(name, static)
        return (await asyncio.to_thread(run)) or st
    f = pathlib.Path(__file__).parent / "wnba" / f"{name}.json"
    empty = {"meta": {"league": "wnba", "empty": True}, "players": []}
    run, _ = _stats_json(f"wnba-{name}", static)
    return (await asyncio.to_thread(run)) or (json.loads(f.read_text()) if f.exists() else empty)


@router.post("/admin/stats-json")
async def upload_stats_json(request: Request, body: dict = Body(...)):
    """Replace a stats page's data: {name, season, data}. Internal key or admin session. The nightly refresh posts here."""
    require_admin(request)
    name, season, data = body["name"], body["season"], body["data"]
    import re
    if name.removeprefix("wnba-") not in ("shot-value", "playmaking", "rebounding", "lineups", "shot-breakdown", "defense", "standings") \
            and not re.fullmatch(r"rot:\d{4}-\d{2}:(index|[A-Z]{3})\.json", name):   # rotations: one row per team file
        raise HTTPException(400, "unknown page")
    import json
    def run():
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO nba_stats_json (name, season, data, built_at) VALUES (%s, %s, %s::jsonb, now())
                               ON CONFLICT (name) DO UPDATE SET season = EXCLUDED.season, data = EXCLUDED.data, built_at = now()""",
                            (name, season, json.dumps(data)))
            conn.commit()
            return {"name": name, "season": season, "players": len(data.get("players", []))}
        finally:
            conn.close()
    return await asyncio.to_thread(run)


@router.get("/stats/rotations/{season}/{fname}")
async def rotations_file(season: str, fname: str):
    """Lineups page (rotation patterns) for a season in progress: the nightly refresh's copy of one team file
    (nba-pipeline/models/rotations.py → rot:<season>:<file>); 404 when there is none (the page falls back to the static files)."""
    import json
    def run():
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT data FROM nba_stats_json WHERE name = %s", (f"rot:{season}:{fname}",))
                row = cur.fetchone()
            if not row: return None
            data = row["data"] if isinstance(row, dict) else row[0]
            return json.loads(data) if isinstance(data, str) else data
        finally:
            conn.close()
    d = await asyncio.to_thread(run)
    if d is None: raise HTTPException(404, "no rotations for that season")
    return d


@router.get("/stats/shot-value")
async def shot_value(league: str = "nba"):
    """Shot making vs the league, model v7 (nba-pipeline/models/shot_value.py): the season's 300 biggest shot-takers, each
    with shots, minutes, possessions on the floor (team possessions from the play-by-play x his share of team minutes),
    expected points from his shot profile (nine distance zones x five shot families), points added = points - expected,
    the same per 75 possessions, percentiles of expected pts/shot, pts/shot and added/75 among the 300, his shot diet
    (rim / 3-8 / 8-16 / long two / three shares), and the skill / residual split vs his own level last season.
    v9 (2026-10-15) adds the play's context — transition / semi-transition / half-court / putback, and context × three —
    to the expectation (nba-pipeline analysis/TRANSITION.md). Static file from models/export_site.py, rebuilt by hand."""
    return await _league_page("shot-value", "shot_value_v9.json", league)


@router.get("/stats/rebounding")
async def rebounding(league: str = "nba"):
    """Rebounding actual vs expected (nba-pipeline/models/rebounding.py + rebounding_tables.py), 2024-25 with lineups:
    every player with 400+ live rebound chances on the floor, defense and offense blocks. Per block: chances; his own
    share of the chances expected from the shot alone (league rate for that miss distance), expected accounting for
    the other nine on the floor (an average player in his spot), actual, effect (actual - other nine) in points and
    boards; the team's rebound rate the same four ways; for teammates (team effect - own effect) in points and boards;
    and the by-miss-distance split [chances, team expected, team actual, own expected, own actual]. Static file."""
    return await _league_page("rebounding", "rebounding_2024_25.json", league)


@router.get("/stats/playmaking")
async def playmaking(league: str = "nba"):
    """Box Creation (Ben Taylor, public 2017 form) per 100 possessions for every player with 500+ minutes, with the
    formula's pieces (assist term, scoring term, shooting term, interaction, constant) so the page can show where a
    player's number comes from. Static file from nba-pipeline/models/box_creation.py."""
    return await _league_page("playmaking", "box_creation_2025_26.json", league)


@router.get("/stats/lineups")
async def lineups():
    """Net rating (points scored minus allowed per 100 possessions) of every 1-, 2-, 3- and 5-man group with enough
    possessions together; 1-man rows carry on/off. Keyed on player ids; names attached by id. Static file from
    nba-pipeline/models/lineups.py (or the nightly copy in nba_stats_json)."""
    run, static = _stats_json("lineups", "lineups_2025_26.json")
    return (await asyncio.to_thread(run)) or static


@router.get("/stats/shot-breakdown")
async def shot_breakdown(league: str = "nba"):
    """Who gains or loses in each piece of the shot model: per distance zone / shot type / situation / shot-clock range,
    each player's points added there; and the change in each player's points added when shot type, situation and
    shot clock were added to the model. Keyed on player ids. From nba-pipeline/models/export_breakdown.py."""
    return await _league_page("shot-breakdown", "shot_breakdown_2025_26.json", league)


@router.get("/stats/standings")
async def standings(league: str = "nba"):
    """Standings and projected standings for the season in progress, per date (nba-pipeline/models/standings.py): actual
    W-L and games back through each date, and the projection made with what was known then — team strength from
    player ratings (last season's lineup plus-minus) x projected minutes, a normal win chance, 10,000 simulations;
    projected wins, top-6 and play-in odds by conference. The nightly refresh posts a new copy."""
    return await _league_page("standings", "standings_2026_27.json", league)


@router.get("/stats/defense")
async def defense():
    """Every team's defenders from the lineup possessions (nba-pipeline/models/defense_page.py): per player DRtg raw and
    opponent-adjusted, on/off, share of possessions against top-30 / top-90 scorers and third-string units, the opposing
    offense's strength, lift and stability across teammates; per pair possessions, minutes and DRtg together and each
    without the other; per pair the third men (pair with him vs without him). Facts only; no credit split between
    teammates. Garbage time out. Keyed on player ids."""
    run, static = _stats_json("defense", "defense_2025_26.json")
    return (await asyncio.to_thread(run)) or static


@router.get("/admin/stats-notes")
async def get_stats_notes(request: Request, page: str, season: str):
    """The commissioner's notes on one stats page and season: [{team, key, body, updated_at}]. Admin only."""
    require_admin(request)
    def run():
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT team, key, body, updated_at FROM nba_stats_notes WHERE page = %s AND season = %s ORDER BY team, key",
                            (page, season))
                return cur.fetchall()
        finally:
            conn.close()
    return await asyncio.to_thread(run)


@router.post("/admin/stats-notes")
async def save_stats_note(request: Request, body: dict = Body(...)):
    """Save one note {page, season, team, key, body}; an empty body deletes it. Admin only."""
    require_admin(request)
    page, season, team, key, text = (str(body.get(k, "")) for k in ("page", "season", "team", "key", "body"))
    if not (page and season and team and key) or len(text) > 50000:
        raise HTTPException(400, "page, season, team and key are required; body up to 50,000 characters")
    def run():
        conn = get_db()
        try:
            with conn.cursor() as cur:
                if text.strip():
                    cur.execute("""INSERT INTO nba_stats_notes (page, season, team, key, body, updated_at) VALUES (%s, %s, %s, %s, %s, now())
                                   ON CONFLICT (page, season, team, key) DO UPDATE SET body = EXCLUDED.body, updated_at = now()
                                   RETURNING updated_at""", (page, season, team, key, text))
                    at = cur.fetchone()
                else:
                    cur.execute("DELETE FROM nba_stats_notes WHERE page = %s AND season = %s AND team = %s AND key = %s", (page, season, team, key))
                    at = None
            conn.commit()
            return {"saved": bool(text.strip()), "updated_at": (at["updated_at"] if isinstance(at, dict) else at[0]) if at else None}
        finally:
            conn.close()
    return await asyncio.to_thread(run)


@router.get("/stats/shot-chart/{season}/{player_id}")
async def shot_chart(season: str, player_id: str):
    """One player's shot chart for a season as SVG (drawn by nba-pipeline, uploaded by the admin route below)."""
    from fastapi.responses import Response
    def run():
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT svg FROM nba_shot_charts WHERE season = %s AND player_id = %s", (season, player_id))
                row = cur.fetchone()
                return row["svg"] if row else None
        finally:
            conn.close()
    svg = await asyncio.to_thread(run)
    if svg is None:
        raise HTTPException(404, "no chart")
    return Response(content=svg, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=3600"})


@router.post("/admin/shot-charts")
async def upload_shot_charts(request: Request, body: dict = Body(...)):
    """Replace a season's shot charts: {season, charts: [{player_id, svg}, ...]}. Internal key or admin session."""
    require_admin(request)
    season, charts = body["season"], body["charts"]
    def run():
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM nba_shot_charts WHERE season = %s", (season,))
                cur.executemany("INSERT INTO nba_shot_charts (season, player_id, svg) VALUES (%s, %s, %s)",
                                [(season, str(c["player_id"]), c["svg"]) for c in charts])
            conn.commit()
            return {"season": season, "charts": len(charts)}
        finally:
            conn.close()
    return await asyncio.to_thread(run)


@router.get("/injuries")
async def get_injuries(player_id: Optional[str] = None):
    """Who's injured right now (present state only; ESPN feed, synced every 30 minutes). A player not listed is
    healthy. ?player_id= → just that player ([] if healthy). Rows: {player_id (null if unmatched), name, team,
    status (Out / Day-To-Day / ...), short (OUT / GTD), injury, return_date, comment, reported_at, synced_at}."""
    def run():
        conn = get_db()
        try:
            with conn.cursor() as cur:
                return injuries.current(cur, player_id)
        finally:
            conn.close()
    return await asyncio.to_thread(run)


@router.post("/admin/injuries/sync")
async def sync_injuries(request: Request):
    require_admin(request)
    return await asyncio.to_thread(injuries.sync, "manual")


@router.get("/admin/schedule/status")
async def schedule_status(request: Request):
    """Recent sync runs, recent changes, and game counts by status."""
    require_admin(request)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM nba_sync_runs WHERE kind = 'schedule' ORDER BY id DESC LIMIT 20")
            runs = cur.fetchall()
            cur.execute("SELECT * FROM nba_game_changes WHERE kind <> 'added' ORDER BY id DESC LIMIT 100")
            changes = cur.fetchall()
            cur.execute("""
                SELECT season, game_type, status, (missing_since IS NOT NULL) AS missing,
                       count(*) AS games, count(*) FILTER (WHERE time_tbd) AS time_tbd,
                       count(*) FILTER (WHERE home_team IS NULL OR away_team IS NULL) AS teams_tbd
                FROM nba_games GROUP BY 1, 2, 3, 4 ORDER BY 1, 2, 3, 4
            """)
            counts = cur.fetchall()
    finally:
        conn.close()
    return {"runs": runs, "changes": changes, "counts": counts}


@router.post("/admin/schedule/sync")
async def sync_now(request: Request):
    """Fetch the NBA feed from the server and sync right now."""
    require_admin(request)
    return await asyncio.to_thread(schedule.sync, "manual")


@router.post("/admin/schedule/ingest")
async def ingest(request: Request, payload: dict = Body(...)):
    """Fallback when the server can't reach the NBA feed: a machine that can
    (scripts/pull_nba_schedule.py) fetches it and posts the raw JSON here."""
    require_admin(request)
    return await asyncio.to_thread(schedule.sync, "ingest", payload)


@router.post("/admin/schedule/history")
async def load_history(request: Request, body: dict = Body(...)):
    """One-time load of a finished season from local files
    (scripts/load_historical_schedules.py). Body: {"season": "2024-25", "games": [...]}."""
    require_admin(request)
    if not isinstance(body.get("season"), str) or not isinstance(body.get("games"), list):
        raise HTTPException(status_code=400, detail="need season (str) and games (list)")
    return await asyncio.to_thread(schedule.sync, f"history {body['season']}", None, body)


BOX_COLS = ("game_id", "player_id", "season", "player_name", "team", "position", "starter", "dnp_reason", "minutes",
            "fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb", "ast", "stl", "blk", "tov", "pf", "pts", "plus_minus")
MISC_COLS = ("blkd", "pfd")  # optional; only updated when the posted rows include them


@router.get("/admin/live-probe")
async def live_probe(request: Request):
    """Can this server read the NBA live feed? (live.py)"""
    require_admin(request)
    from . import live
    return await asyncio.to_thread(live.probe)


@router.post("/admin/live-pull")
async def live_pull(request: Request):
    """Pull today's live / just-finished games now (live.py) — the scheduler does this every 30 seconds."""
    require_admin(request)
    from . import live
    try:
        return await asyncio.to_thread(live.pull_today)
    except Exception:  # noqa: BLE001 — the commissioner sees why (2026-10-22: the live pull failed silently)
        import traceback
        return {"ok": False, "error": traceback.format_exc()[-3000:]}


@router.get("/admin/live-health")
async def live_health(request: Request):
    """The live pull's health (live.HEALTH) and which games are on now (from our schedule) — for the backup relay."""
    require_admin(request)
    from . import live

    def run():
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("""SELECT game_id FROM nba_games WHERE missing_since IS NULL AND game_type IN ('regular', 'playoff', 'cup')
                               AND (status = 'live' OR (status = 'scheduled' AND tipoff_utc <= now() AND tipoff_utc > now() - interval '5 hours'))""")
                return [r["game_id"] for r in cur.fetchall()]
        finally:
            conn.close()
    return {**live.HEALTH, "games_on": await asyncio.to_thread(run)}


@router.get("/admin/feed-log")
async def feed_log_view(request: Request, limit: int = 300):
    """The Feed Log page: the latest checks of this server → the NBA's live feed, and the last 24 hours' success rate."""
    require_admin(request)

    def run():
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT at, kind, source, status, ms, error FROM nba_feed_log ORDER BY id DESC LIMIT %s", (min(limit, 2000),))
                rows = [{**r, "at": r["at"].isoformat()} for r in cur.fetchall()]
                cur.execute("""SELECT source, count(*) AS n, count(*) FILTER (WHERE status = 200) AS ok, avg(ms) FILTER (WHERE status = 200) AS ms
                               FROM nba_feed_log WHERE at > now() - interval '24 hours' GROUP BY source""")
                day = {r["source"]: {"checks": r["n"], "ok": r["ok"], "avg_ms": round(r["ms"]) if r["ms"] else None} for r in cur.fetchall()}
            return {"rows": rows, "last_24h": day}
        finally:
            conn.close()
    return await asyncio.to_thread(run)


@router.get("/admin/live-snapshots/{game_id}")
async def live_snapshots(request: Request, game_id: str, player_id: str):
    """One player's line at every live pull of a game (nba_live_snapshots, every 30s) — to see when a live number
    stalled or jumped (2026-10-27, Mobley stuck at 29.5)."""
    require_admin(request)

    def run():
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT pulled_at, period, clock, status, players FROM nba_live_snapshots WHERE game_id = %s ORDER BY pulled_at",
                            (game_id,))
                return [{"at": r["pulled_at"].isoformat(), "period": r["period"], "clock": r["clock"], "status": r["status"],
                         "line": next((p for p in r["players"] if p["player_id"] == player_id), None)} for r in cur.fetchall()]
        finally:
            conn.close()
    return await asyncio.to_thread(run)


@router.post("/admin/live-push")
async def live_push(request: Request, body: dict = Body(...)):
    """The backup relay's copy of one game's feeds: {"game_id", "box": boxscore JSON, "pbp": play-by-play JSON or null}.
    Loaded with the same parser as the server's own pull (live.pull_game)."""
    require_admin(request)
    from . import live

    def run():
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT game_id, season, game_type, game_date, status FROM nba_games WHERE game_id = %s", (body["game_id"],))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="unknown game")
                r = live.pull_game(cur, dict(row), raw_box=body["box"], raw_pbp=body.get("pbp"))
            conn.commit()
            return r
        finally:
            conn.close()
    return await asyncio.to_thread(run)


@router.post("/admin/nightly")
async def nightly_run(request: Request, body: dict = Body(default={})):
    """Run the nightly box score + play-by-play job now (nightly.py, NIGHTLY.md). Body (optional): {"from": "YYYY-MM-DD",
    "to": "YYYY-MM-DD"} for a manual range (a backfill after an outage, or one day); without it, the nightly window."""
    require_admin(request)
    from . import nightly
    try:
        start = date.fromisoformat(body["from"]) if body.get("from") else None
        end = date.fromisoformat(body["to"]) if body.get("to") else None
    except ValueError:
        raise HTTPException(status_code=400, detail="from / to must be YYYY-MM-DD")
    return await asyncio.to_thread(nightly.run, "manual", start, end)


@router.get("/live")
async def live_state():
    """The live state of games being pulled: period, clock, clutch, who's on the floor."""
    def run():
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM nba_live_state WHERE updated_at > now() - interval '1 day'")
                return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
    return await asyncio.to_thread(run)


@router.post("/admin/boxscores")
async def load_boxscores(request: Request, body: dict = Body(...)):
    """Upsert player box score rows (scripts/load_historical_boxscores.py posts
    them in chunks). Body: {"rows": [{game_id, player_id, season, ...}]}."""
    require_admin(request)
    rows = body.get("rows")
    if not isinstance(rows, list):
        raise HTTPException(status_code=400, detail="need rows (list)")

    def upsert():
        from psycopg2.extras import execute_values
        misc = [c for c in MISC_COLS if any(c in r for r in rows)]
        cols = BOX_COLS + tuple(misc)
        values = [tuple(r.get(c) for c in cols) for r in rows]
        conn = get_db()
        try:
            with conn.cursor() as cur:
                execute_values(cur, f"""
                    INSERT INTO nba_player_games ({', '.join(cols)}) VALUES %s
                    ON CONFLICT (game_id, player_id) DO UPDATE SET
                    {', '.join(f'{c} = EXCLUDED.{c}' for c in cols[2:])}, loaded_at = now()
                """, values, page_size=1000)
            conn.commit()
        finally:
            conn.close()
        return {"ok": True, "rows": len(values), "games": len({r.get("game_id") for r in rows})}

    return await asyncio.to_thread(upsert)


@router.post("/admin/shot-fields")
async def load_shot_fields(request: Request, body: dict = Body(...)):
    """Upsert shot chart fields (scripts/build_shot_fields.py). Body: {"rows": [{"player_id", "season", "data"}]}."""
    require_admin(request)
    rows = body.get("rows")
    if not isinstance(rows, list) or any(not isinstance(r, dict) or not {"player_id", "season", "data"} <= set(r) for r in rows):
        raise HTTPException(status_code=400, detail="need rows: {player_id, season, data}")

    def upsert():
        from psycopg2.extras import Json, execute_values
        conn = get_db()
        try:
            with conn.cursor() as cur:
                execute_values(cur, """
                    INSERT INTO nba_shot_fields (player_id, season, data) VALUES %s
                    ON CONFLICT (player_id, season) DO UPDATE SET data = EXCLUDED.data, built_at = now()
                """, [(str(r["player_id"]), r["season"], Json(r["data"])) for r in rows])
            conn.commit()
        finally:
            conn.close()
        return {"ok": True, "rows": len(rows)}

    return await asyncio.to_thread(upsert)


TEAM_STAT_COLS = ("game_id", "team", "season", "game_date", "opp_pts_fb", "opp_pts_paint", "opp_tov", "dreb", "opp_dreb", "shot_clock_forced")


@router.post("/admin/team-games")
async def load_team_games(request: Request, body: dict = Body(...)):
    """Upsert team defensive lines per game (scripts/load_team_clutch.py). Body: {"rows": [{game_id, team, season,
    game_date, opp_pts_fb, opp_pts_paint, opp_tov, dreb, opp_dreb, shot_clock_forced}]}."""
    require_admin(request)
    rows = body.get("rows")
    if not isinstance(rows, list):
        raise HTTPException(status_code=400, detail="need rows (list)")

    def upsert():
        from psycopg2.extras import execute_values
        conn = get_db()
        try:
            with conn.cursor() as cur:
                execute_values(cur, f"""
                    INSERT INTO nba_team_game_stats ({', '.join(TEAM_STAT_COLS)}) VALUES %s
                    ON CONFLICT (game_id, team) DO UPDATE SET
                    {', '.join(f'{c} = EXCLUDED.{c}' for c in TEAM_STAT_COLS[2:])}, loaded_at = now()
                """, [tuple(r.get(c) for c in TEAM_STAT_COLS) for r in rows], page_size=1000)
            conn.commit()
        finally:
            conn.close()
        return {"ok": True, "rows": len(rows)}

    return await asyncio.to_thread(upsert)


@router.post("/admin/clutch")
async def load_clutch(request: Request, body: dict = Body(...)):
    """Set clutch-time points per player-game. Body: {"season": "2025-26", "reset": true, "rows": [{player_id,
    game_date: "YYYY-MM-DD", pts}]}. A player plays at most once a day, so (player, date) finds the game. reset=true
    first sets every played game of the season to 0 (loaded, no clutch points) — send it with the first chunk."""
    require_admin(request)
    season, rows = body.get("season"), body.get("rows")
    if not isinstance(season, str) or not isinstance(rows, list):
        raise HTTPException(status_code=400, detail="need season (str) and rows (list)")

    def apply():
        from psycopg2.extras import execute_values
        conn = get_db()
        try:
            with conn.cursor() as cur:
                if body.get("reset"):
                    cur.execute("UPDATE nba_player_games SET clutch_pts = 0 WHERE season = %s AND minutes > 0", (season,))
                execute_values(cur, """
                    UPDATE nba_player_games pg SET clutch_pts = v.pts
                    FROM (VALUES %s) AS v(player_id, game_date, pts), nba_games g
                    WHERE g.game_id = pg.game_id AND pg.player_id = v.player_id AND g.game_date = v.game_date::date
                """, [(str(r["player_id"]), r["game_date"], int(r["pts"])) for r in rows], page_size=1000)
                n = cur.rowcount
            conn.commit()
        finally:
            conn.close()
        return {"ok": True, "rows": len(rows), "updated": n}

    return await asyncio.to_thread(apply)
