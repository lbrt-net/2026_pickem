"""Daily NBA schedule sync, run inside the web app (no extra Railway service).

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

from . import schedule

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


def start() -> asyncio.Task | None:
    if os.environ.get("NBA_SYNC_DISABLED") == "1":
        return None
    return asyncio.create_task(run_forever())
