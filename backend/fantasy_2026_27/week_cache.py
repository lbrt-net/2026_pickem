"""Every team's week view at once, kept warm (2026-10-21: Matchup took ~2 s — 12 week views one after another, then the
win chance rebuilding them all again).

- Built in parallel (one database connection per worker), so all 12 take about as long as the slowest one.
- Kept: fresh for FRESH seconds; older → the saved one is served at once and rebuilt in the background. A roster
  change (move, add, drop, trade) rebuilds right away, so a manager never sees his week from before his own move.
- One source: GET /week/all (Matchup, Home) and the win chance (winprob.week_probs) read the same views.
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor

FRESH = 10  # live games refresh every 30 s on the page; a 10 s server copy keeps them current
WORKERS = 6
_C: dict = {}           # (scenario, week) -> (built at, roster fingerprint, {team id: view})
_BUSY: set = set()
_LOCK = threading.Lock()


def _fingerprint(cur, scenario: str) -> str:
    cur.execute("""SELECT md5(coalesce(string_agg(team_id || ':' || slot || ':' || coalesce(player_id, nba_team_id), ','
                   ORDER BY team_id, slot, coalesce(player_id, nba_team_id)), '')) AS h FROM fantasy_rosters WHERE scenario = %s""",
                (scenario,))
    return cur.fetchone()["h"]


def _one(scenario: str, team_id: str, week_no):
    from backend.db import get_db
    from .lineup import week_view
    conn = get_db()
    try:
        with conn.cursor() as cur:
            v = week_view(cur, scenario, team_id, week_no, injuries=True)
        conn.commit()
        return team_id, v
    finally:
        conn.close()


def _build(key) -> dict:
    from backend.db import get_db
    scenario, week_no = key
    try:
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM fantasy_teams WHERE scenario = %s", (scenario,))
                ids = [r["id"] for r in cur.fetchall()]
                fp = _fingerprint(cur, scenario)
            conn.commit()
        finally:
            conn.close()
        with ThreadPoolExecutor(WORKERS) as ex:
            views = dict(ex.map(lambda t: _one(scenario, t, week_no), ids))
        _C[key] = (time.time(), fp, views)
        return views
    finally:
        _BUSY.discard(key)


def all_weeks(cur, scenario: str, week_no: int | None = None) -> dict:
    """{team id: week view} for every team (injury report applied)."""
    key = (scenario, week_no)
    hit = _C.get(key)
    if not hit or hit[1] != _fingerprint(cur, scenario):
        return _build(key)
    if time.time() - hit[0] >= FRESH:
        with _LOCK:
            if key not in _BUSY:
                _BUSY.add(key)
                threading.Thread(target=_build, args=(key,), daemon=True).start()
    return hit[2]


def clear() -> None:
    _C.clear()
