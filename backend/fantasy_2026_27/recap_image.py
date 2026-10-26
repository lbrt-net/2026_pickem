"""A finished week's recap as one desktop picture (commissioner, 2026-10-25): it never half-loads.

The recap is frozen the first time it's made (recap.week_recap), so a picture of it never goes stale. The server opens
its own Recap page in a headless Chromium (Playwright) at desktop width, waits for every photo and font, and saves a
screenshot of the recap into fantasy_recap_images. GET /recap/week/{n} then carries the picture's address and the page
shows it (pannable on a phone); the live page is only used to make the picture (?render=1) and while it doesn't exist.

Only the live league gets a picture. A failed attempt is retried at most every 10 minutes."""
import logging
import os
import threading
import time

from backend.db import get_db

log = logging.getLogger("fantasy.recap_image")
WIDTH = 1280          # desktop viewport; the recap renders alone at 1180 px + padding
SCALE = 2             # sharp on retina screens
QUALITY = 82          # JPEG
RETRY_S = 600
_busy, _tried = set(), {}
_lock = threading.Lock()


def init_schema(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fantasy_recap_images (
            scenario     TEXT NOT NULL,
            week         INTEGER NOT NULL,
            image        BYTEA NOT NULL,
            content_type TEXT NOT NULL,
            width        INTEGER,
            height       INTEGER,
            made_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (scenario, week)
        )
    """)


def stamp(cur, scenario: str, week: int):
    """When the week's picture was made (None = no picture yet)."""
    cur.execute("SELECT made_at, width, height FROM fantasy_recap_images WHERE scenario = %s AND week = %s", (scenario, week))
    return cur.fetchone()


def get(cur, scenario: str, week: int):
    cur.execute("SELECT image, content_type FROM fantasy_recap_images WHERE scenario = %s AND week = %s", (scenario, week))
    return cur.fetchone()


def shoot(week: int, base: str | None = None) -> tuple[bytes, int, int]:
    """Screenshot the Recap page for this week (week 0 = Draft Grades) in its render mode (the recap alone, 1180 px wide).
    Returns (jpeg, css width, css height)."""
    from playwright.sync_api import sync_playwright
    base = base or f"http://127.0.0.1:{os.environ.get('PORT', '8000')}"
    with sync_playwright() as p:
        # channel "chromium" = full headless Chromium; the slim headless shell is refused by the NBA's photo server
        b = p.chromium.launch(channel="chromium", args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            # a normal browser identity: the NBA's photo server refuses headless ones
            pg = b.new_page(viewport={"width": WIDTH, "height": 1000}, device_scale_factor=SCALE,
                            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36")
            tab = "draft" if week == 0 else f"w{week}"
            pg.goto(f"{base}/fantasy/2026_27/recap?tab={tab}&render=1", wait_until="networkidle", timeout=90000)
            pg.wait_for_selector(".rc-render .rc-awards, .rc-render .rw-tc", timeout=60000)
            pg.evaluate("() => document.fonts.ready")
            pg.wait_for_function("() => [...document.images].every(i => i.complete)", timeout=60000)
            el = pg.query_selector(".rc-render")
            box = el.bounding_box()
            img = el.screenshot(type="jpeg", quality=QUALITY)
            return img, round(box["width"]), round(box["height"])
        finally:
            b.close()


def make(scenario: str, week: int) -> bool:
    """Make and save the picture (blocking). False when it failed."""
    try:
        img, w, h = shoot(week)
    except Exception:  # noqa: BLE001 — logged; retried later
        log.exception("recap picture for week %s failed", week)
        return False
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO fantasy_recap_images (scenario, week, image, content_type, width, height)
                           VALUES (%s, %s, %s, 'image/jpeg', %s, %s)
                           ON CONFLICT (scenario, week) DO UPDATE SET image = EXCLUDED.image, width = EXCLUDED.width,
                             height = EXCLUDED.height, made_at = now()""", (scenario, week, img, w, h))
        conn.commit()
    finally:
        conn.close()
    log.warning("recap picture for week %s saved (%d KB, %dx%d)", week, len(img) // 1024, w, h)
    return True


def ensure(scenario: str, week: int) -> None:
    """Start making the picture in the background if it's missing (one at a time, at most every 10 minutes). Only where
    Playwright + Chromium are installed (not the production build — 2026-10-25: installing a browser there made every
    deploy slow); elsewhere the live page shows until a picture is uploaded."""
    if scenario != "live" or os.environ.get("RECAP_IMAGES_DISABLED") == "1":
        return
    try:
        import playwright  # noqa: F401
    except ImportError:
        return
    key = (scenario, week)
    with _lock:
        if key in _busy or time.time() - _tried.get(key, 0) < RETRY_S:
            return
        _busy.add(key)
        _tried[key] = time.time()

    def run():
        try:
            time.sleep(2)  # let the request that asked finish first
            make(scenario, week)
        finally:
            with _lock:
                _busy.discard(key)
    threading.Thread(target=run, daemon=True, name=f"recap-image-{week}").start()
