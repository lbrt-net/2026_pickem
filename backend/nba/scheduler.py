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


async def run_forever() -> None:
    await asyncio.sleep(STARTUP_DELAY)
    try:
        age = await asyncio.to_thread(schedule.last_success_age_hours)
        if age is None or age > 24:
            await _run("startup")
    except Exception:
        log.exception("nba schedule startup catch-up failed")

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


def start() -> asyncio.Task | None:
    if os.environ.get("NBA_SYNC_DISABLED") == "1":
        return None
    _keep.append(asyncio.create_task(injuries_forever()))  # hold a reference so the task isn't collected
    return asyncio.create_task(run_forever())
