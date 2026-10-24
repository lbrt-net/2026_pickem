"""Live games from the NBA's live feed (cdn.nba.com liveData), pulled every 30 seconds while a game is on.

- Feed: scoreboard/todaysScoreboard_00.json (today's games), boxscore/boxscore_{id}.json (player lines, on-court flag,
  clock), playbyplay/playbyplay_{id}.json (clutch points, shot-clock violations).
- The CDN only answers a full browser header set (HEADERS). Thin headers get 403; nba_api's stats headers carry
  `Host: stats.nba.com`, which makes the CDN redirect forever — so that line is left out.
- One pull of a game writes: player lines → nba_player_games (+ clutch_pts, blkd), team defensive stats →
  nba_team_game_stats, score / status → nba_games, the live state → nba_live_state, and a snapshot of every player's
  line → nba_live_snapshots (kept, so a game can be replayed later to design the live look), and the raw feed →
  nba_live_raw (at the final: the box score), and the play-by-play's shots → nba_game_shots (the raw play-by-play
  itself isn't kept, 2026-10-14).
- Mirrors (MIRRORS): a game can also be copied under another season label as a regular game — the livetest league
  reads only that season, so preseason games never count for the real league.
Clutch = the NBA's definition: last 5 minutes of the 4th quarter or overtime, score within 5 before the play.
"""
import logging
import time
import re
from datetime import datetime, timezone

import requests
from psycopg2.extras import Json

from backend.db import get_db

log = logging.getLogger("nba.live")
BASE = "https://cdn.nba.com/static/json/liveData"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.5", "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive", "Referer": "https://www.nba.com/", "Origin": "https://www.nba.com", "Pragma": "no-cache",
    "Cache-Control": "no-cache", "Sec-Ch-Ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
    "Sec-Ch-Ua-Mobile": "?0", "Sec-Fetch-Dest": "empty",
}
# game id → [(season label, game id prefix)]: also write the game under that season as a regular game (test leagues).
MIRRORS: dict = {}  # was {"0012600044": [("test-live", "T")]} for the 2026-10-12 live demo (livetest league, now off)


# The same files straight from the NBA's storage, behind a different gatekeeper (2026-10-22: cdn.nba.com started
# answering our server with 403 Forbidden — Railway's addresses blocked — while this kept serving the live games).
BACKUP = "https://nba-prod-us-east-1-mediaops-stats.s3.amazonaws.com/NBA/liveData"


def feed_log(kind: str, source: str, status, ms, error: str | None = None) -> None:
    """One line in nba_feed_log (the Feed Log page); never breaks the caller."""
    try:
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO nba_feed_log (kind, source, status, ms, error) VALUES (%s, %s, %s, %s, %s)",
                            (kind, source, status, ms, (error or None) and error[:300]))
                cur.execute("DELETE FROM nba_feed_log WHERE at < now() - interval '60 days'")
            conn.commit()
        finally:
            conn.close()
    except Exception:  # noqa: BLE001
        log.exception("feed log write failed")


def _get(base: str, path: str, headers: dict):
    t = time.time()
    try:
        r = requests.get(f"{base}/{path}", headers=headers, timeout=20, allow_redirects=False)
        return r, int((time.time() - t) * 1000), None
    except requests.RequestException as e:
        return None, int((time.time() - t) * 1000), f"{type(e).__name__}: {e}"


def fetch(path: str) -> dict:
    """One live-data file: cdn.nba.com, and the NBA's storage copy when the CDN refuses or fails. A live pull's
    scoreboard (and any CDN failure) is written to the Feed Log."""
    logged = path.startswith("scoreboard/")
    r, ms, err = _get(BASE, path, HEADERS)
    if r is not None and r.status_code == 200:
        try:
            data = r.json()
            if logged:
                feed_log("pull", "cdn", 200, ms)
            return data
        except ValueError:
            err = "not JSON"
    feed_log("pull", "cdn", r.status_code if r is not None else None, ms, err or f"HTTP {r.status_code}")
    log.warning("live feed %s from the CDN failed (%s) — trying the NBA's storage copy", path, err or (r.status_code if r is not None else None))
    r, ms, err = _get(BACKUP, path, {"User-Agent": HEADERS["User-Agent"], "Accept": "application/json"})
    feed_log("pull", "backup", r.status_code if r is not None else None, ms, err)
    if r is None:
        raise requests.ConnectionError(err)
    r.raise_for_status()
    return r.json()


def probe_log() -> dict:
    """Every 10 minutes (scheduler): today's scoreboard from the CDN and from the storage copy, both logged."""
    out = {}
    for source, base, headers in (("cdn", BASE, HEADERS), ("backup", BACKUP, {"User-Agent": HEADERS["User-Agent"], "Accept": "application/json"})):
        r, ms, err = _get(base, "scoreboard/todaysScoreboard_00.json", headers)
        status = r.status_code if r is not None else None
        feed_log("probe", source, status, ms, err if status != 200 else None)
        out[source] = {"status": status, "ms": ms}
    return out


def scoreboard() -> list[dict]:
    return fetch("scoreboard/todaysScoreboard_00.json")["scoreboard"]["games"]


def _minutes(iso: str | None) -> float:
    m = re.match(r"PT(\d+)M([\d.]+)S", iso or "")
    return round(int(m.group(1)) + float(m.group(2)) / 60, 2) if m else 0.0


def _clock_secs(iso: str | None) -> float:
    m = re.match(r"PT(\d+)M([\d.]+)S", iso or "")
    return int(m.group(1)) * 60 + float(m.group(2)) if m else 0.0


def clutch_time(box: dict, home: dict, away: dict) -> bool:
    """Clutch time right now, from the live box score itself (2026-10-20): 4th quarter or OT, 5:00 or less left, within
    5 points. (The play-by-play lags the box score, so its last play can still read a 5-point game at 119–113.)"""
    try:
        margin = abs(int(home.get("score") or 0) - int(away.get("score") or 0))
    except (TypeError, ValueError):
        return False
    return (box.get("period") or 0) >= 4 and _clock_secs(box.get("gameClock")) <= 300 and margin <= 5


def clutch_and_violations(actions: list[dict]) -> tuple[dict, dict, bool]:
    """({person id: clutch points}, {team tricode: its own shot-clock violations}, clutch time right now?)."""
    clutch, scv, now = {}, {}, False
    for a in actions:
        if a.get("actionType") == "turnover" and "shot clock" in (a.get("subType") or "").lower():
            scv[a.get("teamTricode")] = scv.get(a.get("teamTricode"), 0) + 1
        late = (a.get("period") or 0) >= 4 and _clock_secs(a.get("clock")) <= 300
        try:
            home, away = int(a.get("scoreHome") or 0), int(a.get("scoreAway") or 0)
        except ValueError:
            home = away = 0
        pts = 0
        if a.get("actionType") in ("2pt", "3pt") and a.get("shotResult") == "Made":
            pts = 3 if a["actionType"] == "3pt" else 2
        elif a.get("actionType") == "freethrow" and a.get("shotResult") == "Made":
            pts = 1
        margin_before = abs(home - away) - pts if pts else abs(home - away)
        if late and pts and abs(margin_before) <= 5 and a.get("personId"):
            clutch[a["personId"]] = clutch.get(a["personId"], 0) + pts
        if late:
            now = abs(home - away) <= 5
    return clutch, scv, now


def pull_game(cur, game: dict, raw_box: dict | None = None, raw_pbp: dict | None = None, nightly: bool = False) -> dict:
    """One pull of one game (an nba_games row: game_id, season, game_type, game_date). Returns a summary.
    nightly=True (nightly.py, feeds already fetched and checked): replaces the stored raw feed with this copy and skips
    the live-only writes (live state, per-pull snapshots). One parser for live and nightly."""
    gid = game["game_id"]
    if raw_box is None:
        raw_box = fetch(f"boxscore/boxscore_{gid}.json")
        try:
            raw_pbp = fetch(f"playbyplay/playbyplay_{gid}.json")
        except (requests.RequestException, ValueError):
            raw_pbp = None
    box = raw_box["game"]
    actions = (raw_pbp or {}).get("game", {}).get("actions", []) if raw_pbp else []
    # keep the raw feed once per game, at the final (box score + the full play-by-play), to re-parse later if needed —
    # every-pull copies were for the 2026-10-12 test only (a full slate every 30s would be ~170 MB a night)
    if nightly:  # the nightly re-pull keeps only the latest copy (corrections)
        cur.execute("DELETE FROM nba_live_raw WHERE game_id = %s", (gid,))
    if box.get("gameStatus") == 3:
        cur.execute("SELECT 1 FROM nba_live_raw WHERE game_id = %s LIMIT 1", (gid,))
        if not cur.fetchone():
            cur.execute("INSERT INTO nba_live_raw (game_id, kind, payload) VALUES (%s, 'boxscore', %s)", (gid, Json(raw_box)))
        if raw_pbp:  # the play-by-play's shots are kept (shot chart); the raw play-by-play isn't
            from .shot_fields import shots_rows
            cur.execute("""INSERT INTO nba_game_shots (game_id, season, shots) VALUES (%s, %s, %s)
                           ON CONFLICT (game_id) DO UPDATE SET shots = EXCLUDED.shots, season = EXCLUDED.season, loaded_at = now()""",
                        (gid, game["season"], Json(shots_rows(raw_pbp))))
    clutch, scv, clutch_now = clutch_and_violations(actions)
    status = {2: "live", 3: "final"}.get(box.get("gameStatus"), "scheduled")
    teams = (box["homeTeam"], box["awayTeam"])
    targets = [(game["season"], gid, game["game_type"])] + [(s, p + gid, "regular") for s, p in MIRRORS.get(gid, [])]
    players, oncourt, snap = [], [], []
    for t, opp in (teams, teams[::-1]):
        for p in t.get("players", []):
            s = p.get("statistics") or {}
            mins = _minutes(s.get("minutes"))
            row = {"player_id": str(p["personId"]), "player_name": p.get("name") or "", "team": t["teamTricode"],
                   "position": (p.get("position") or None), "starter": p.get("starter") == "1",
                   "dnp_reason": p.get("notPlayingReason") if p.get("played") != "1" else None, "minutes": mins,
                   "fgm": s.get("fieldGoalsMade", 0), "fga": s.get("fieldGoalsAttempted", 0),
                   "fg3m": s.get("threePointersMade", 0), "fg3a": s.get("threePointersAttempted", 0),
                   "ftm": s.get("freeThrowsMade", 0), "fta": s.get("freeThrowsAttempted", 0),
                   "oreb": s.get("reboundsOffensive", 0), "dreb": s.get("reboundsDefensive", 0),
                   "ast": s.get("assists", 0), "stl": s.get("steals", 0), "blk": s.get("blocks", 0), "tov": s.get("turnovers", 0),
                   "pf": s.get("foulsPersonal", 0), "pts": s.get("points", 0), "plus_minus": int(s.get("plusMinusPoints") or 0),
                   "blkd": s.get("blocksReceived", 0), "pfd": s.get("foulsDrawn", 0), "clutch_pts": clutch.get(p["personId"], 0)}
            players.append(row)
            if p.get("oncourt") == "1":
                oncourt.append(row["player_id"])
            if mins > 0:
                snap.append({k: row[k] for k in ("player_id", "team", "minutes", "pts", "fgm", "fga", "fg3m", "ftm", "fta", "oreb",
                                                 "dreb", "ast", "stl", "blk", "tov", "blkd", "clutch_pts")})
    tstats = []
    for t, opp in (teams, teams[::-1]):
        ts, os_ = t.get("statistics") or {}, opp.get("statistics") or {}
        tstats.append({"team": t["teamTricode"], "opp_pts_fb": os_.get("pointsFastBreak"), "opp_pts_paint": os_.get("pointsInThePaint"),
                       "opp_tov": os_.get("turnoversTotal"), "dreb": ts.get("reboundsDefensive"), "opp_dreb": os_.get("reboundsDefensive"),
                       "shot_clock_forced": scv.get(opp["teamTricode"], 0)})
    home, away = teams
    for season, tid, gtype in targets:
        if tid != gid:  # the mirror's game row: a copy of the real one under its own season, as a regular game
            cur.execute("""INSERT INTO nba_games (game_id, season, game_type, game_date, tipoff_utc, status, status_text, home_team, away_team,
                                                  home_score, away_score, label)
                           SELECT %s, %s, 'regular', game_date, tipoff_utc, status, status_text, home_team, away_team, home_score, away_score, 'Live test'
                           FROM nba_games WHERE game_id = %s
                           ON CONFLICT (game_id) DO NOTHING""", (tid, season, gid))
        cur.execute("""UPDATE nba_games SET status = %s, status_text = %s, home_score = %s, away_score = %s, updated_at = now()
                       WHERE game_id = %s""", (status, box.get("gameStatusText"), home.get("score"), away.get("score"), tid))
        for r in players:
            cols = ["game_id", "season"] + list(r.keys())
            cur.execute(f"""INSERT INTO nba_player_games ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})
                            ON CONFLICT (game_id, player_id) DO UPDATE SET {', '.join(f'{c} = EXCLUDED.{c}' for c in cols[2:])}, loaded_at = now()""",
                        [tid, season] + list(r.values()))
        for r in tstats:
            cur.execute("""INSERT INTO nba_team_game_stats (game_id, team, season, game_date, opp_pts_fb, opp_pts_paint, opp_tov, dreb, opp_dreb, shot_clock_forced)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT (game_id, team) DO UPDATE SET opp_pts_fb = EXCLUDED.opp_pts_fb, opp_pts_paint = EXCLUDED.opp_pts_paint,
                               opp_tov = EXCLUDED.opp_tov, dreb = EXCLUDED.dreb, opp_dreb = EXCLUDED.opp_dreb,
                               shot_clock_forced = EXCLUDED.shot_clock_forced, loaded_at = now()""",
                        (tid, r["team"], season, game["game_date"], r["opp_pts_fb"], r["opp_pts_paint"], r["opp_tov"], r["dreb"], r["opp_dreb"],
                         r["shot_clock_forced"]))
        if nightly:
            continue
        cur.execute("""INSERT INTO nba_live_state (game_id, status, period, clock, clutch, oncourt, home_score, away_score, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                       ON CONFLICT (game_id) DO UPDATE SET status = EXCLUDED.status, period = EXCLUDED.period, clock = EXCLUDED.clock,
                           clutch = EXCLUDED.clutch, oncourt = EXCLUDED.oncourt, home_score = EXCLUDED.home_score,
                           away_score = EXCLUDED.away_score, updated_at = now()""",
                    (tid, status, box.get("period"), box.get("gameClock"), status == "live" and clutch_time(box, home, away), Json(oncourt),
                     home.get("score"), away.get("score")))
        if status in ("live", "final"):
            cur.execute("""INSERT INTO nba_live_snapshots (game_id, period, clock, status, players) VALUES (%s, %s, %s, %s, %s)""",
                        (tid, box.get("period"), box.get("gameClock"), status, Json(snap)))
    return {"game_id": gid, "status": status, "players": len(players), "clutch": clutch_now, "mirrors": len(targets) - 1}


# Health of the live pull (2026-10-22), for the backup relay on the commissioner's machine (scripts/live_relay.py):
# when the server's own pull keeps failing, the relay fetches the feeds itself and pushes them in (POST /admin/live-push).
HEALTH = {"last_ok": None, "last_error": None, "error": None, "failing_since": None}


def _health(ok: bool, err: str | None = None) -> None:
    now = datetime.now(timezone.utc)
    if ok:
        HEALTH.update(last_ok=now.isoformat(), failing_since=None, error=None)
    else:
        HEALTH.update(last_error=now.isoformat(), error=(err or "")[:300])
        HEALTH["failing_since"] = HEALTH["failing_since"] or now.isoformat()


def pull_today() -> dict:
    """Pull every game of today's scoreboard that has tipped (live, or final within the last pull window)."""
    try:
        board = scoreboard()
    except Exception as e:  # noqa: BLE001 — recorded for the relay, then raised as before
        _health(False, f"{type(e).__name__}: {e}")
        raise
    conn = get_db()
    out = []
    try:
        with conn.cursor() as cur:
            for g in board:
                if g.get("gameStatus") not in (2, 3):
                    continue
                cur.execute("SELECT game_id, season, game_type, game_date, status FROM nba_games WHERE game_id = %s", (g["gameId"],))
                row = cur.fetchone()
                if not row:
                    continue
                if g.get("gameStatus") == 3:
                    cur.execute("SELECT min(pulled_at) AS t FROM nba_live_snapshots WHERE game_id = %s AND status = 'final'", (g["gameId"],))
                    first_final = cur.fetchone()["t"]
                    if first_final and (datetime.now(timezone.utc) - first_final).total_seconds() > 900:
                        continue  # final for 15+ minutes (late stat fixes caught): stop pulling it
                try:
                    out.append(pull_game(cur, dict(row)))
                    conn.commit()
                except Exception as e:  # noqa: BLE001 — one game failing never stops the others (2026-10-22)
                    conn.rollback()
                    import logging
                    logging.getLogger("nba.live").exception("live pull of %s failed", g["gameId"])
                    out.append({"game_id": g["gameId"], "status": "error", "error": f"{type(e).__name__}: {e}"[:500]})
    finally:
        conn.close()
    errs = [g for g in out if g.get("status") == "error"]
    _health(not errs, errs[0]["error"] if errs else None)
    return {"games": out, "any_live": any(g.get("gameStatus") == 2 for g in board),
            "upcoming": any(g.get("gameStatus") == 1 for g in board)}


def next_wait() -> float:
    """Seconds until the live loop should look again, from our schedule (nba_games), without calling the feed:
    a game on now → 30s; a game past its tip time but not started or not final yet → 60s; otherwise sleep until a minute
    before the next tip-off (at most 6 hours, so schedule changes are picked up)."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # only a game that tipped in the last 12 hours: a stale "live" row (2024-25's All-Star Game, from the history
            # load) kept this pulling every 30 seconds around the clock (2026-10-24)
            cur.execute("""SELECT 1 FROM nba_games WHERE status = 'live' AND missing_since IS NULL
                           AND tipoff_utc > now() - interval '12 hours' LIMIT 1""")
            if cur.fetchone():
                return 30.0
            cur.execute("""SELECT 1 FROM nba_games WHERE status = 'scheduled' AND missing_since IS NULL
                           AND tipoff_utc <= now() AND tipoff_utc > now() - interval '6 hours' LIMIT 1""")
            if cur.fetchone():
                return 60.0
            cur.execute("SELECT min(tipoff_utc) AS t FROM nba_games WHERE status = 'scheduled' AND missing_since IS NULL AND tipoff_utc > now()")
            t = cur.fetchone()["t"]
    finally:
        conn.close()
    if not t:
        return 6 * 3600.0
    return max(30.0, min((t - datetime.now(timezone.utc)).total_seconds() - 60, 6 * 3600.0))


def probe() -> dict:
    """Admin check: can this server read the live feed?"""
    res = {}
    for name, path in (("scoreboard", "scoreboard/todaysScoreboard_00.json"), ("boxscore", "boxscore/boxscore_0012600042.json"),
                       ("playbyplay", "playbyplay/playbyplay_0012600042.json")):
        try:
            r = requests.get(f"{BASE}/{path}", headers=HEADERS, timeout=20, allow_redirects=False)
            res[name] = {"status": r.status_code, "ok": r.status_code == 200 and r.text.lstrip().startswith("{")}
        except requests.RequestException as e:
            res[name] = {"status": None, "error": repr(e)[:200]}
    return res
