"""Every team's week view at once, kept warm (2026-10-21: Matchup took ~2 s — 12 week views one after another, then the
win chance rebuilding them all again).

- Built in parallel (one database connection per worker), so all 12 take about as long as the slowest one.
- Kept: fresh for FRESH seconds; older → the saved one is served at once and rebuilt in the background. A roster
  change (move, add, drop, trade) rebuilds right away, so a manager never sees his week from before his own move.
- One rebuild per roster change (2026-10-29): viewers arriving while it's under way wait for that same build instead
  of each starting all 12 views again.
- One source: GET /week/all (Matchup, Home) and the win chance (winprob.week_probs) read the same views.
"""
import itertools
import threading
import time
from concurrent.futures import ThreadPoolExecutor

FRESH = 10  # live games refresh every 30 s on the page; a 10 s server copy keeps them current
WORKERS = 6
_C: dict = {}           # (scenario, week) -> (built at, roster fingerprint, {team id: view}, build number)
_BUSY: set = set()
_LOCK = threading.Lock()
_SEQ = itertools.count()
_MISS: dict = {}        # (scenario, week) -> (roster fingerprint, threading.Event): the rebuild under way for it


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
    seq = next(_SEQ)
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
        with _LOCK:
            old = _C.get(key)
            if not old or old[3] < seq:  # never replace views begun after these
                _C[key] = (time.time(), fp, views, seq)
        return views
    finally:
        _BUSY.discard(key)


def all_weeks(cur, scenario: str, week_no: int | None = None) -> dict:
    """{team id: week view} for every team (injury report applied)."""
    key = (scenario, week_no)
    hit = _C.get(key)
    fp = _fingerprint(cur, scenario)
    if not hit or hit[1] != fp:
        return single_flight(_MISS, _LOCK, key, fp, lambda: _build(key), lambda: _C.get(key))
    if time.time() - hit[0] >= FRESH:
        with _LOCK:
            if key not in _BUSY:
                _BUSY.add(key)
                threading.Thread(target=_build, args=(key,), daemon=True).start()
    return hit[2]


def single_flight(inflight: dict, lock, key, fp, build, kept):
    """A miss: build once for this key and roster fingerprint; callers arriving meanwhile wait for that build. If it
    failed, or rosters changed again before it read them, the waiter builds its own. kept() = (_, fp, value, ...)."""
    with lock:
        f = inflight.get(key)
        if f and f[0] == fp:
            ev, mine = f[1], False
        else:
            ev, mine = threading.Event(), True
            inflight[key] = (fp, ev)
    if not mine:
        ev.wait()
        hit = kept()
        if hit and hit[1] == fp:
            return hit[2]
        return build()
    try:
        return build()
    finally:
        with lock:
            if inflight.get(key, (None, None))[1] is ev:
                del inflight[key]
        ev.set()


def clear() -> None:
    _C.clear()
