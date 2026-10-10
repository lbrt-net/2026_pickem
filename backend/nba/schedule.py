"""NBA schedule: fetch the NBA's full-season schedule feed, diff it against
nba_games, and apply the changes.

How moving games are handled:
- Games are keyed by NBA game_id and upserted — a rescheduled game keeps its id,
  so a new date/time is just a field change (logged in nba_game_changes).
- TBD tip times are stored as tipoff_utc NULL + time_tbd; TBD teams (NBA Cup
  knockouts, play-in/playoffs) as NULL tricodes. Filled in on a later sync.
- Postponed / cancelled come from the feed's status and are kept as rows.
- A game missing from the feed is never deleted: it gets missing_since and a
  'removed' change; if it reappears it's 'restored'.
- Safety valve: if the feed has far fewer games than we already store for that
  season, it's treated as a broken/partial feed and nothing is written.
- Fantasy never stores "which week a game is in" — weeks are date ranges and a
  game's week is derived from game_date at read time, so a moved game lands in
  the right week automatically.
"""
import time
from datetime import datetime, timezone

import requests

from backend.db import get_db

FEED_URL = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"
FEED_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.nba.com/",
}
# Patient backoff (see nba_api_tests/CLAUDE_CHECKLIST.md): 30s → 60s → 120s → 120s.
RETRY_WAITS = [30, 60, 120, 120]
# Refuse a feed with fewer than this share of the games we already have for its season.
MIN_FEED_RATIO = 0.9
LOCK_KEY = 872_160_001  # pg advisory lock id for schedule syncs

GAME_TYPES = {"1": "preseason", "2": "regular", "3": "allstar", "4": "playoffs", "5": "playin", "6": "cup_final"}
# Fields whose changes get logged. Scores change every night, so they're stored but not logged.
TRACKED = ("game_date", "tipoff_utc", "time_tbd", "status", "home_team", "away_team")


def fetch_feed() -> dict:
    last = None
    for attempt, wait in enumerate([0] + RETRY_WAITS):
        if wait:
            time.sleep(wait)
        try:
            r = requests.get(FEED_URL, headers=FEED_HEADERS, timeout=30)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            last = e
    raise RuntimeError(f"schedule feed failed after {len(RETRY_WAITS) + 1} attempts: {last}")


def _status(g) -> str:
    text = (g.get("gameStatusText") or "").lower()
    if "cancel" in text:
        return "cancelled"
    # Postponed only when the feed's status text says so ("PPD" / "Postponed"). The postponedStatus field isn't
    # reliable: the 2026-27 feed carries a value on every game, which marked the whole season postponed.
    if "ppd" in text or "postpon" in text:
        return "postponed"
    return {2: "live", 3: "final"}.get(g.get("gameStatus"), "scheduled")


def _team(t) -> str | None:
    t = t or {}
    return t.get("teamTricode") or None if t.get("teamId") else None


def _tipoff(g):
    """(tipoff_utc, time_tbd). The feed marks unknown times with status text 'TBD'."""
    raw = g.get("gameDateTimeUTC") or g.get("gameDateUTC")
    if (g.get("gameStatusText") or "").strip().upper() == "TBD" or not raw:
        return None, True
    return datetime.fromisoformat(raw.replace("Z", "+00:00")), False


def parse_feed(payload: dict) -> tuple[str, list[dict]]:
    """Feed JSON → (season, rows shaped like nba_games)."""
    sched = payload["leagueSchedule"]
    season = sched.get("seasonYear")
    rows = []
    for day in sched.get("gameDates", []):
        for g in day.get("games", []):
            gid = g["gameId"]
            tipoff, tbd = _tipoff(g)
            home, away = g.get("homeTeam") or {}, g.get("awayTeam") or {}
            date_est = (g.get("gameDateEst") or "")[:10] or None
            rows.append({
                "game_id": gid,
                "season": season,
                "game_type": GAME_TYPES.get(gid[2:3], "other"),
                "game_date": date_est,
                "tipoff_utc": tipoff,
                "time_tbd": tbd,
                "status": _status(g),
                "status_text": g.get("gameStatusText"),
                "home_team": _team(home),
                "away_team": _team(away),
                "home_score": home.get("score") if g.get("gameStatus") in (2, 3) else None,
                "away_score": away.get("score") if g.get("gameStatus") in (2, 3) else None,
                "label": g.get("seriesText") or g.get("gameLabel") or None,
            })
    if not season:
        raise ValueError("feed has no leagueSchedule.seasonYear")
    return season, rows


def _norm(v):
    """Comparable string form, so DB values and parsed values diff cleanly."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc).isoformat()
    return str(v)


def rows_from_history(games: list[dict]) -> list[dict]:
    """Rows posted by scripts/load_historical_schedules.py (already in nba_games shape,
    minus game_type/season) → validated nba_games rows."""
    rows = []
    for g in games:
        gid = str(g["game_id"])
        tip = g.get("tipoff_utc")
        rows.append({
            "game_id": gid,
            "game_type": GAME_TYPES.get(gid[2:3], "other"),
            "game_date": g.get("game_date"),
            "tipoff_utc": datetime.fromisoformat(tip.replace("Z", "+00:00")) if tip else None,
            "time_tbd": not tip,
            "status": g.get("status") if g.get("status") in ("scheduled", "live", "final", "postponed", "cancelled") else "scheduled",
            "status_text": g.get("status_text"),
            "home_team": g.get("home_team") or None,
            "away_team": g.get("away_team") or None,
            "home_score": g.get("home_score"),
            "away_score": g.get("away_score"),
            "label": g.get("label") or None,
        })
    return rows


def apply_feed(cur, payload: dict, run_id: int) -> dict:
    season, rows = parse_feed(payload)
    return apply_rows(cur, season, rows, run_id)


def apply_rows(cur, season: str, rows: list[dict], run_id: int) -> dict:
    for r in rows:
        r["season"] = season
    cur.execute("SELECT * FROM nba_games WHERE season = %s", (season,))
    existing = {r["game_id"]: r for r in cur.fetchall()}
    active = [gid for gid, r in existing.items() if r["missing_since"] is None]

    if active and len(rows) < MIN_FEED_RATIO * len(active):
        raise RuntimeError(f"feed looks partial: {len(rows)} games vs {len(active)} stored for {season}; nothing written")

    counts = {"games_seen": len(rows), "added": 0, "changed": 0, "removed": 0, "restored": 0}
    log = lambda gid, kind, field=None, old=None, new=None: cur.execute(
        "INSERT INTO nba_game_changes (run_id, game_id, kind, field, old_value, new_value) VALUES (%s,%s,%s,%s,%s,%s)",
        (run_id, gid, kind, field, _norm(old), _norm(new)))

    seen = set()
    for row in rows:
        gid = row["game_id"]
        seen.add(gid)
        old = existing.get(gid)
        cols = [k for k in row if k != "game_id"]
        if old is None:
            cur.execute(
                f"INSERT INTO nba_games (game_id, {', '.join(cols)}) VALUES (%s, {', '.join(['%s'] * len(cols))})",
                [gid] + [row[c] for c in cols])
            log(gid, "added")
            counts["added"] += 1
            continue

        diffs = [f for f in TRACKED if _norm(old[f]) != _norm(row[f])]
        for f in diffs:
            log(gid, "changed", f, old[f], row[f])
        if diffs:
            counts["changed"] += 1
        if old["missing_since"] is not None:
            log(gid, "restored")
            counts["restored"] += 1
        cur.execute(
            f"UPDATE nba_games SET {', '.join(f'{c} = %s' for c in cols)}, last_seen_at = now(), missing_since = NULL"
            f"{', updated_at = now()' if diffs or old['missing_since'] else ''} WHERE game_id = %s",
            [row[c] for c in cols] + [gid])

    for gid in active:
        if gid not in seen:
            cur.execute("UPDATE nba_games SET missing_since = now(), updated_at = now() WHERE game_id = %s", (gid,))
            log(gid, "removed")
            counts["removed"] += 1
    return counts


def sync(trigger: str, payload: dict | None = None, history: dict | None = None) -> dict:
    """Run one schedule sync: fetch the live feed, or apply a given feed payload,
    or apply a historical season ({"season": "2024-25", "games": [...]}).
    Only one sync runs at a time across every app instance (advisory lock)."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s) AS got", (LOCK_KEY,))
            if not cur.fetchone()["got"]:
                return {"ok": False, "skipped": "another schedule sync is running"}
            cur.execute("INSERT INTO nba_sync_runs (kind, trigger) VALUES ('schedule', %s) RETURNING id", (trigger,))
            run_id = cur.fetchone()["id"]
        conn.commit()

        try:
            with conn.cursor() as cur:
                if history is not None:
                    counts = apply_rows(cur, history["season"], rows_from_history(history["games"]), run_id)
                else:
                    counts = apply_feed(cur, payload if payload is not None else fetch_feed(), run_id)
                cur.execute("""
                    UPDATE nba_sync_runs SET finished_at = now(), ok = TRUE, games_seen = %(games_seen)s,
                        added = %(added)s, changed = %(changed)s, removed = %(removed)s, restored = %(restored)s
                    WHERE id = %(id)s
                """, {**counts, "id": run_id})
            conn.commit()
            return {"ok": True, "run_id": run_id, **counts}
        except Exception as e:
            conn.rollback()  # all-or-nothing: a failed sync leaves the schedule untouched
            with conn.cursor() as cur:
                cur.execute("UPDATE nba_sync_runs SET finished_at = now(), ok = FALSE, error = %s WHERE id = %s",
                            (str(e)[:2000], run_id))
            conn.commit()
            return {"ok": False, "run_id": run_id, "error": str(e)}
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
            cur.execute("""
                SELECT EXTRACT(EPOCH FROM now() - max(finished_at)) / 3600 AS h
                FROM nba_sync_runs WHERE kind = 'schedule' AND ok
            """)
            h = cur.fetchone()["h"]
    finally:
        conn.close()
    return float(h) if h is not None else None
