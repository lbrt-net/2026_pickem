"""Draft room live updates (server-sent events): the server pings every open draft room the moment the draft
changes, and each page then reads GET /draft (its own copy: Rec bids, auto-pick and queue stay private).

One "hub" per league while anyone has the room open:
  - it runs the draft's catch-up whenever a clock runs out (or the warm-up / scheduled start comes), so clocks end
    on time even when nobody clicks, and
  - it pings everyone whenever the draft's fingerprint (status, picks, lot, bids, clocks) changes, whether a click
    (routes call notify()) or a clock caused it.
The pages keep a slow poll as a backup for dropped connections. Single server process (Dockerfile), so in-memory
is enough.
"""
import asyncio
from datetime import datetime, timezone

from starlette.concurrency import run_in_threadpool

from backend.db import get_db

HEARTBEAT_S = 15     # a comment line this often keeps proxies from closing a quiet connection
MAX_SLEEP_S = 10     # the hub re-checks at least this often

_loop: asyncio.AbstractEventLoop | None = None
_subs: dict[str, set[asyncio.Queue]] = {}
_wake: dict[str, asyncio.Event] = {}
_hubs: dict[str, asyncio.Task] = {}


def notify(scenario: str) -> None:
    """Something changed this league's draft (call after the change is committed). Safe from any thread."""
    if _loop and scenario in _wake:
        _loop.call_soon_threadsafe(_wake[scenario].set)


def _tick(scenario: str):
    """Catch the draft up (expired clocks, warm-up, scheduled start) and return (next timed event, fingerprint)."""
    from . import draft
    from .weeks import league_settings
    conn = get_db()
    try:
        with conn.cursor() as cur:
            draft.catch_up(cur, scenario)
            d = draft._row(cur, scenario)
            settings = league_settings(cur, scenario)
            cur.execute("SELECT count(*) AS n FROM fantasy_rosters WHERE scenario = %s", (scenario,))
            made = cur.fetchone()["n"]
            nxt = draft.next_event(d, settings, made)
            fp = repr((d["status"], d["team_order"], d.get("lot"), d.get("lot_deadline"), d.get("nominate_index"),
                       d.get("nominate_deadline"), d.get("clock_started_at"), d.get("warmup_until"), d.get("autopick_teams"),
                       made, settings.get("draft_start_at"), settings.get("draft_type")))
        conn.commit()
        return nxt, fp
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


async def _hub(scenario: str) -> None:
    last = None
    wake = _wake[scenario]
    while _subs.get(scenario):
        wake.clear()
        try:
            nxt, fp = await run_in_threadpool(_tick, scenario)
        except Exception:
            nxt, fp = None, last  # a bad read (e.g. the database restarting): try again shortly
            await asyncio.sleep(1)
        if fp != last:
            last = fp
            for q in list(_subs.get(scenario, ())):
                if q.empty():
                    q.put_nowait("change")
        wait = MAX_SLEEP_S
        if nxt is not None:
            wait = min(MAX_SLEEP_S, max(0.0, (nxt - datetime.now(timezone.utc)).total_seconds() + 0.02))
        try:
            await asyncio.wait_for(wake.wait(), timeout=wait)
        except asyncio.TimeoutError:
            pass
    _hubs.pop(scenario, None)


async def stream(scenario: str):
    """The event stream for one open draft room: 'data: change' whenever the draft changes."""
    global _loop
    _loop = asyncio.get_running_loop()
    q: asyncio.Queue = asyncio.Queue(maxsize=1)
    _subs.setdefault(scenario, set()).add(q)
    _wake.setdefault(scenario, asyncio.Event())
    if scenario not in _hubs:
        _hubs[scenario] = asyncio.create_task(_hub(scenario))
    try:
        yield "retry: 1000\n\n"
        while True:
            try:
                await asyncio.wait_for(q.get(), timeout=HEARTBEAT_S)
                yield "data: change\n\n"
            except asyncio.TimeoutError:
                yield ": ping\n\n"
    finally:
        _subs.get(scenario, set()).discard(q)
