"""The nightly box score + play-by-play job (NIGHTLY.md — read it first). Runs inside the app at 4:00 AM Central.

- Which games (real NBA game ids only): every regular-season (and Cup final) game from the last 7 days, every night; each game once more on the
  night it turns 14 days old; plus any older final game of the season that has no raw feed or no player rows.
- Per game: fetch the CDN box score + play-by-play, check them (each team's player points add up to its score, both
  teams have players with minutes, the play-by-play has actions), then write through live.pull_game (one parser for
  live and nightly; upserts, so a rerun changes nothing unless the NBA did) and keep the latest raw feed. A game that
  fails a check writes nothing and is retried the next night. Each load is recorded in nba_game_loads.
- Then the season's shot chart fields (shot_fields.py) from the stored play-by-play, for every player with 50+ shots.
- Only the CDN is used (the server can reach it; stats.nba.com blocks cloud servers).
"""
import logging
import time
from datetime import date, timedelta

import requests
from psycopg2.extras import Json, execute_values

from backend.config import CENTRAL
from backend.db import get_db

from . import live, shot_fields

log = logging.getLogger("nba.nightly")
LOCK_KEY = 872_160_002  # pg advisory lock id (the schedule sync is ...001)
WINDOW_DAYS = 7
LAST_LOOK_DAYS = 14
STATS = ("minutes", "pts", "fgm", "fga", "fg3m", "fta", "ftm", "oreb", "dreb", "ast", "stl", "blk", "tov", "blkd", "pfd", "clutch_pts")


def today_central() -> date:
    from datetime import datetime
    return datetime.now(CENTRAL).date()


def games_to_pull(cur, start: date | None = None, end: date | None = None, today: date | None = None) -> list:
    today = today or today_central()
    if start or end:  # a manual range
        cur.execute("""SELECT game_id, season, game_type, game_date FROM nba_games
                       WHERE game_type IN ('regular', 'cup_final') AND missing_since IS NULL AND game_date BETWEEN %s AND %s
                         AND game_id ~ '^[0-9]{10}$'
                       ORDER BY game_date, game_id""", (start or end, end or start))
        return cur.fetchall()
    cur.execute("""
        SELECT g.game_id, g.season, g.game_type, g.game_date FROM nba_games g
        WHERE g.game_type IN ('regular', 'cup_final') AND g.missing_since IS NULL AND g.game_date < %(today)s
          AND g.game_id ~ '^[0-9]{10}$'  -- real NBA games only (test leagues' practice / mirror games have prefixed ids)
          AND (
              g.game_date >= %(today)s - %(win)s
           OR g.game_date = %(today)s - %(last)s
           OR (g.status = 'final' AND g.season = (SELECT season FROM nba_games WHERE game_date <= %(today)s
                                                  ORDER BY game_date DESC LIMIT 1)
               AND (NOT EXISTS (SELECT 1 FROM nba_live_raw r WHERE r.game_id = g.game_id)
                    OR NOT EXISTS (SELECT 1 FROM nba_player_games p WHERE p.game_id = g.game_id))))
        ORDER BY g.game_date, g.game_id
    """, {"today": today, "win": WINDOW_DAYS, "last": LAST_LOOK_DAYS})
    return cur.fetchall()


def fetch_game(gid: str, tries: int = 3) -> tuple:
    err = None
    for i in range(tries):
        try:
            return live.fetch(f"boxscore/boxscore_{gid}.json"), live.fetch(f"playbyplay/playbyplay_{gid}.json")
        except (requests.RequestException, ValueError) as e:
            err = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"feed unavailable: {err}")


def check(raw_box: dict, raw_pbp: dict) -> list:
    """Problems with a final feed (empty = good to write)."""
    box = raw_box.get("game", {})
    if box.get("gameStatus") != 3:
        return ["not final"]
    out = []
    for side in ("homeTeam", "awayTeam"):
        t = box.get(side, {})
        players = t.get("players", [])
        pts = sum((p.get("statistics") or {}).get("points", 0) for p in players)
        if pts != t.get("score"):
            out.append(f"{t.get('teamTricode')}: player points {pts} ≠ score {t.get('score')}")
        if not any(live._minutes((p.get("statistics") or {}).get("minutes")) > 0 for p in players):
            out.append(f"{t.get('teamTricode')}: no players with minutes")
    if not (raw_pbp or {}).get("game", {}).get("actions"):
        out.append("play-by-play empty")
    return out


def _lines(cur, gid: str) -> dict:
    cur.execute(f"SELECT player_id, {', '.join(STATS)} FROM nba_player_games WHERE game_id = %s", (gid,))
    return {r["player_id"]: tuple(r[c] for c in STATS) for r in cur.fetchall()}


def load_game(cur, game: dict, raw_box: dict, raw_pbp: dict) -> dict:
    """Check and write one game; record it in nba_game_loads. Returns {game_id, ok, changed, problems}."""
    gid = game["game_id"]
    problems = check(raw_box, raw_pbp)
    changed = 0
    if not problems:
        before = _lines(cur, gid)
        live.pull_game(cur, dict(game), raw_box, raw_pbp, nightly=True)
        after = _lines(cur, gid)
        changed = sum(1 for pid, v in after.items() if before.get(pid) != v) if before else 0
    cur.execute("""
        INSERT INTO nba_game_loads (game_id, last_pulled, ok, attempts, changed, problems)
        VALUES (%s, now(), %s, 1, %s, %s)
        ON CONFLICT (game_id) DO UPDATE SET last_pulled = now(), ok = EXCLUDED.ok, attempts = nba_game_loads.attempts + 1,
            changed = nba_game_loads.changed + EXCLUDED.changed, problems = EXCLUDED.problems
    """, (gid, not problems, changed, Json(problems)))
    return {"game_id": gid, "ok": not problems, "changed": changed, "problems": problems}


def build_shot_fields(cur, season: str) -> int:
    """Rebuild every player's shot chart field for the season from the stored play-by-play (the league map moves
    every night, so everyone is rebuilt)."""
    cur.execute("""SELECT r.payload FROM nba_live_raw r JOIN nba_games g ON g.game_id = r.game_id
                   WHERE r.kind = 'playbyplay' AND g.season = %s AND g.game_type = 'regular'""", (season,))
    shots = [s for r in cur.fetchall() for s in shot_fields.shots_from_pbp(r["payload"])]
    fields = shot_fields.build_all(shots)
    if fields:
        execute_values(cur, """INSERT INTO nba_shot_fields (player_id, season, data) VALUES %s
                               ON CONFLICT (player_id, season) DO UPDATE SET data = EXCLUDED.data, built_at = now()""",
                       [(pid, season, Json(f)) for pid, f in fields.items()])
    return len(fields)


def run(trigger: str = "scheduled", start: date | None = None, end: date | None = None, fetcher=fetch_game) -> dict:
    """One nightly run (or a manual range). Only one at a time across app instances (advisory lock)."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s) AS got", (LOCK_KEY,))
            if not cur.fetchone()["got"]:
                return {"ok": False, "skipped": "another nightly run is going"}
            cur.execute("INSERT INTO nba_sync_runs (kind, trigger) VALUES ('nightly', %s) RETURNING id", (trigger,))
            run_id = cur.fetchone()["id"]
            games = games_to_pull(cur, start, end)
        conn.commit()
        results, seasons = [], set()
        for g in games:
            try:
                raw_box, raw_pbp = fetcher(g["game_id"])
                with conn.cursor() as cur:
                    r = load_game(cur, g, raw_box, raw_pbp)
                conn.commit()
            except Exception as e:  # one bad game never stops the night
                conn.rollback()
                with conn.cursor() as cur:
                    cur.execute("""INSERT INTO nba_game_loads (game_id, last_pulled, ok, attempts, changed, problems)
                                   VALUES (%s, now(), FALSE, 1, 0, %s)
                                   ON CONFLICT (game_id) DO UPDATE SET last_pulled = now(), ok = FALSE,
                                       attempts = nba_game_loads.attempts + 1, problems = EXCLUDED.problems""",
                                (g["game_id"], Json([str(e)[:300]])))
                conn.commit()
                r = {"game_id": g["game_id"], "ok": False, "changed": 0, "problems": [str(e)[:300]]}
            results.append(r)
            if r["ok"]:
                seasons.add(g["season"])
        built = {}
        with conn.cursor() as cur:
            for s in sorted(seasons):
                built[s] = build_shot_fields(cur, s)
        conn.commit()
        failed = [r for r in results if not r["ok"]]
        with conn.cursor() as cur:
            cur.execute("""UPDATE nba_sync_runs SET finished_at = now(), ok = %s, games_seen = %s, changed = %s, error = %s
                           WHERE id = %s""",
                        (not failed, len(results), sum(r["changed"] for r in results),
                         "; ".join(f"{r['game_id']}: {', '.join(r['problems'])}" for r in failed)[:2000] or None, run_id))
        conn.commit()
        out = {"ok": not failed, "run_id": run_id, "games": len(results), "changed": sum(r["changed"] for r in results),
               "failed": failed, "shot_fields": built}
        log.warning("nba nightly (%s): %s", trigger, {k: v for k, v in out.items() if k != "failed"} | {"failed": len(failed)})
        return out
    finally:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(%s)", (LOCK_KEY,))
            conn.commit()
        finally:
            conn.close()


def last_success_age_hours() -> float | None:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT extract(epoch FROM now() - max(finished_at)) / 3600 AS h FROM nba_sync_runs WHERE kind = 'nightly' AND ok")
            h = cur.fetchone()["h"]
    finally:
        conn.close()
    return float(h) if h is not None else None


def status(cur) -> dict:
    """For the check-up: the last run, and games from the window that aren't loaded cleanly."""
    cur.execute("SELECT finished_at, ok, games_seen, changed, error FROM nba_sync_runs WHERE kind = 'nightly' ORDER BY id DESC LIMIT 1")
    last = cur.fetchone()
    cur.execute("""SELECT g.game_id, g.game_date FROM nba_games g LEFT JOIN nba_game_loads l ON l.game_id = g.game_id
                   WHERE g.game_type = 'regular' AND g.status = 'final' AND g.missing_since IS NULL
                     AND g.game_date BETWEEN %s AND %s AND (l.ok IS NOT TRUE)""",
                (today_central() - timedelta(days=WINDOW_DAYS), today_central() - timedelta(days=1)))
    missing = [r["game_id"] for r in cur.fetchall()]
    return {"last": dict(last) if last else None, "missing": missing}
