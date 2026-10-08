"""Current NBA injury status — present state only, no history.

- Source: ESPN's public injury feed (one JSON with every listed player; the NBA's official report PDF is blocked
  from servers). Statuses there: "Out", "Day-To-Day" (+ "Out For Season", "Suspension" when they occur).
- Synced every 30 minutes inside the app (scheduler.py). Each sync replaces the whole table: a player who drops off
  the feed is healthy again.
- Each row is matched to our NBA player id by name (accents, punctuation and Jr./III ignored) and team; a row that
  doesn't match keeps player_id NULL (still listed, by name).
"""
import re
import time
import unicodedata

import requests

from backend.db import get_db

FEED_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/126.0 Safari/537.36"}
RETRY_WAITS = [30, 60, 120]
# ESPN uses a few team abbreviations that differ from the NBA's tricodes
ESPN_TEAM = {"GS": "GSW", "NO": "NOP", "NY": "NYK", "SA": "SAS", "UTAH": "UTA", "WSH": "WAS", "PHO": "PHX", "BKN": "BKN"}
SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b")


def name_key(name: str) -> str:
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    s = SUFFIX.sub("", re.sub(r"[^a-z ]", "", s.replace("-", " ")))
    return " ".join(s.split())


def fetch() -> dict:
    last = None
    for wait in [0] + RETRY_WAITS:
        if wait:
            time.sleep(wait)
        try:
            r = requests.get(FEED_URL, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            last = e
    raise RuntimeError(f"injury feed failed: {last}")


def parse(payload: dict) -> list[dict]:
    out = []
    for team in payload.get("injuries") or []:
        for i in team.get("injuries") or []:
            a, d = i.get("athlete") or {}, i.get("details") or {}
            abbr = ((a.get("team") or {}).get("abbreviation") or "").upper()
            injury = " ".join(x for x in (d.get("side") if d.get("side") not in (None, "Not Specified") else None,
                                          d.get("type"), d.get("detail")) if x)
            out.append({
                "espn_id": str(i.get("id") or a.get("id") or ""), "name": a.get("displayName"),
                "team": ESPN_TEAM.get(abbr, abbr) or None, "team_name": team.get("displayName"),
                "status": i.get("status"),                                           # Out / Day-To-Day / ...
                "short": ((d.get("fantasyStatus") or {}).get("abbreviation")),       # OUT / GTD / ...
                "injury": injury or None, "return_date": d.get("returnDate"),
                "comment": i.get("shortComment"), "reported_at": i.get("date"),
            })
    return out


def _players(cur) -> dict:
    """name key → [(player_id, team)] from everyone we know: this season's pool and box scores."""
    cur.execute("""
        SELECT id AS player_id, name, nba_team AS team FROM fantasy_players
        UNION
        SELECT DISTINCT ON (player_id) player_id, player_name, team FROM nba_player_games ORDER BY player_id, team
    """)
    idx = {}
    for r in cur.fetchall():
        idx.setdefault(name_key(r["name"]), []).append((r["player_id"], r["team"]))
    return idx


def match(rows: list[dict], idx: dict) -> None:
    for r in rows:
        cands = {pid: t for pid, t in idx.get(name_key(r["name"]), [])}
        same_team = [pid for pid, t in cands.items() if t == r["team"]]
        r["player_id"] = same_team[0] if len(same_team) == 1 else (next(iter(cands)) if len(cands) == 1 else None)


def sync(trigger: str = "scheduled", payload: dict | None = None) -> dict:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO nba_sync_runs (kind, trigger) VALUES ('injuries', %s) RETURNING id", (trigger,))
            run_id = cur.fetchone()["id"]
            conn.commit()
            try:
                rows = parse(payload if payload is not None else fetch())
                if payload is None and not rows:
                    raise RuntimeError("feed returned no injuries — keeping the last list")
                match(rows, _players(cur))
                cur.execute("DELETE FROM nba_injuries")
                for r in rows:
                    cur.execute("""
                        INSERT INTO nba_injuries (player_id, espn_id, name, team, status, short, injury, return_date,
                                                  comment, reported_at)
                        VALUES (%(player_id)s, %(espn_id)s, %(name)s, %(team)s, %(status)s, %(short)s, %(injury)s,
                                %(return_date)s, %(comment)s, %(reported_at)s)
                    """, r)
                matched = sum(1 for r in rows if r["player_id"])
                cur.execute("UPDATE nba_sync_runs SET finished_at = now(), ok = TRUE, games_seen = %s, added = %s WHERE id = %s",
                            (len(rows), matched, run_id))
                conn.commit()
                return {"ok": True, "listed": len(rows), "matched": matched,
                        "unmatched": [r["name"] for r in rows if not r["player_id"]]}
            except Exception as e:
                conn.rollback()
                cur.execute("UPDATE nba_sync_runs SET finished_at = now(), ok = FALSE, error = %s WHERE id = %s", (str(e)[:500], run_id))
                conn.commit()
                return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def current(cur, player_id: str | None = None) -> list[dict]:
    q = "SELECT player_id, name, team, status, short, injury, return_date, comment, reported_at, synced_at FROM nba_injuries"
    cur.execute(q + (" WHERE player_id = %s" if player_id else "") + " ORDER BY team, name", (player_id,) if player_id else None)
    return [{**r, "return_date": r["return_date"].isoformat() if r["return_date"] else None,
             "reported_at": r["reported_at"].isoformat() if r["reported_at"] else None,
             "synced_at": r["synced_at"].isoformat()} for r in cur.fetchall()]
