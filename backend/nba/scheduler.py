"""Daily NBA schedule sync and the injury sync (Mondays every 15 min, other days 5 PM), run inside the web app (no extra Railway service).

- Every day at 3:00 AM Central, after the night's games are final.
- On boot, catch up if the last successful sync is over a day old (covers
  deploys/restarts that happened across 3 AM).
- Multiple instances (e.g. old + new container mid-deploy) are safe: the sync
  takes a Postgres advisory lock, so only one runs.
- Set NBA_SYNC_DISABLED=1 to turn it off (local dev).
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta

from backend.config import CENTRAL

from . import injuries, schedule

log = logging.getLogger("nba.scheduler")
SYNC_HOUR = 3  # Central
STARTUP_DELAY = 60  # let the app finish booting first


def seconds_until_next_run(now: datetime | None = None) -> float:
    now = now or datetime.now(CENTRAL)
    target = now.replace(hour=SYNC_HOUR, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


async def _run(trigger: str) -> None:
    result = await asyncio.to_thread(schedule.sync, trigger)
    log.warning("nba schedule sync (%s): %s", trigger, result)
    await _snapshots(trigger)


def take_snapshots() -> dict:
    """The weekly recap's snapshots (fantasy_2026_27/snapshots.py), right after the 3 AM sync: before the day's games."""
    from backend.db import get_db
    from backend.fantasy_2026_27 import snapshots
    conn = get_db()
    try:
        with conn.cursor() as cur:
            out = snapshots.take_all(cur)
        conn.commit()
        return out
    finally:
        conn.close()


async def _snapshots(trigger: str) -> None:
    try:
        log.warning("recap snapshots (%s): %s", trigger, await asyncio.to_thread(take_snapshots))
    except Exception:
        log.exception("recap snapshots failed")


async def run_forever() -> None:
    await asyncio.sleep(STARTUP_DELAY)
    try:
        age = await asyncio.to_thread(schedule.last_success_age_hours)
        if age is None or age > 24:
            await _run("startup")
    except Exception:
        log.exception("nba schedule startup catch-up failed")
    await _snapshots("startup")  # a restart across 3 AM still snapshots the day (kept only before its first game)

    while True:
        await asyncio.sleep(seconds_until_next_run())
        try:
            await _run("daily")
        except Exception:
            log.exception("nba schedule daily sync failed")


# Injuries (injuries.py, ESPN): Mondays often — the fantasy week starts Monday — every 15 minutes 7 AM–11 PM
# Central; the other days once, at 5 PM Central. On boot, catch up if the last good sync is over a day old.
MONDAY_EVERY_MIN, MONDAY_FROM, MONDAY_TO = 15, 7, 23
DAILY_HOUR = 17
_keep: list = []


def next_injury_run(now: datetime | None = None) -> datetime:
    now = now or datetime.now(CENTRAL)
    t = now.replace(second=0, microsecond=0)
    for _ in range(8 * 24 * 4):  # step 15 minutes, at most 8 days ahead
        t += timedelta(minutes=15 - t.minute % 15)
        monday = t.weekday() == 0 and MONDAY_FROM <= t.hour < MONDAY_TO and t.minute % MONDAY_EVERY_MIN == 0
        if t > now and (monday or (t.weekday() != 0 and t.hour == DAILY_HOUR and t.minute == 0)):
            return t
    return now + timedelta(days=1)


async def _injuries(trigger: str) -> None:
    try:
        result = await asyncio.to_thread(injuries.sync, trigger)
        if not result.get("ok"):
            log.warning("nba injury sync failed: %s", result.get("error"))
    except Exception:
        log.exception("nba injury sync failed")


async def injuries_forever() -> None:
    await asyncio.sleep(STARTUP_DELAY)
    age = await asyncio.to_thread(injuries.last_success_age_hours)
    if age is None or age > 24:
        await _injuries("startup")
    while True:
        await asyncio.sleep(max((next_injury_run() - datetime.now(CENTRAL)).total_seconds(), 1))
        await _injuries("scheduled")


# Lineup history (fantasy_2026_27/etch.py): wake at every lock moment — 5 minutes before each tip-off — and save the
# spots of whoever just locked, for the live league and the two sandboxes (the replay test league runs on its own
# clock and saves on roster changes). Checks again at least hourly in case the schedule changed.
LOCK_SCENARIOS = ("live", "test_pre", "test_post")


def etch_locks() -> dict:
    from datetime import timezone
    from backend.db import get_db
    from backend.fantasy_2026_27 import etch
    conn = get_db()
    out, nxt = {}, None
    try:
        with conn.cursor() as cur:
            for sc in LOCK_SCENARIOS:
                try:
                    out[sc] = etch.etch_league(cur, sc)
                    conn.commit()
                    t = etch.next_lock_at(cur, sc, datetime.now(timezone.utc))
                    nxt = t if t and (nxt is None or t < nxt) else nxt
                except ValueError:  # no such league
                    conn.rollback()
    finally:
        conn.close()
    return {"saved": out, "next": nxt}


async def locks_forever() -> None:
    from datetime import timezone
    await asyncio.sleep(STARTUP_DELAY)
    while True:
        try:
            r = await asyncio.to_thread(etch_locks)
            if any(r["saved"].values()):
                log.warning("lineup history saved at lock: %s", r["saved"])
            wait = (r["next"] - datetime.now(timezone.utc)).total_seconds() + 5 if r["next"] else 3600
        except Exception:
            log.exception("lineup history at lock failed")
            wait = 600
        await asyncio.sleep(min(max(wait, 5), 3600))


# Live games (live.py): sleeps until a minute before the next tip-off (from our schedule — no feed calls in between),
# then pulls every 30 seconds while a game is on and every minute while a game past its tip time hasn't started or
# finished; a pull that fails is retried in a minute.
async def live_forever() -> None:
    from . import live
    await asyncio.sleep(STARTUP_DELAY)
    while True:
        try:
            r = await asyncio.to_thread(live.pull_today)
            if r["games"]:
                log.warning("live pull: %s", [(g["game_id"], g["status"]) for g in r["games"]])
            wait = await asyncio.to_thread(live.next_wait)
        except Exception:
            log.exception("live pull failed")
            wait = 60
        await asyncio.sleep(wait)


def start() -> asyncio.Task | None:
    if os.environ.get("NBA_SYNC_DISABLED") == "1":
        return None
    _keep.append(asyncio.create_task(injuries_forever()))  # hold a reference so the task isn't collected
    _keep.append(asyncio.create_task(locks_forever()))
    _keep.append(asyncio.create_task(live_forever()))
    return asyncio.create_task(run_forever())
