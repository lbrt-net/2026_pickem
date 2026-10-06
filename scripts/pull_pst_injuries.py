"""Injury history from prosportstransactions.com (IL moves + missed games due to injury),
2000-08-01 → 2026-07-31, for the durability study. The site sits behind Cloudflare, which loops
forever on a Chrome that Playwright launched. So you start Chrome yourself, pass the check by hand,
and this script attaches to that Chrome over its debugging port.

    # 1. quit any Chrome this script opened, then start your own (separate profile, debug port):
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir="$HOME/.pst_chrome_profile"
    # 2. in that window, open the search URL below and pass the Cloudflare check until you see the table
    # 3. in another terminal:
    source .venv/bin/activate
    python3 scripts/pull_pst_injuries.py

- If Cloudflare comes back mid-run, pass it in the window; the script waits up to 5 minutes.
- Resumable: rows go to the CSV page by page, and finished pages are listed in a .done file.
  Stop with Ctrl-C any time and re-run to continue.

Output: ~/PycharmProjects/nba-pipeline/data/raw/prosportstransactions/injuries_2000_2026.csv
  columns: start (page offset), date, team, acquired, relinquished, notes
  acquired = returned from IL / to lineup; relinquished = placed on IL / out; notes = the injury text.
'26 rows are in the file but are the validation season — filter them out of any fitting.
"""
import csv
import random
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = ("https://prosportstransactions.com/basketball/Search/SearchResults.php?Player=&Team="
       "&BeginDate=2000-08-01&EndDate=2026-07-31&ILChkBx=yes&InjuriesChkBx=yes&Submit=Search&start={}")
LAST_START = 67125  # page 2686, per the site on 2026-10-06
OUT = Path.home() / "PycharmProjects" / "nba-pipeline" / "data" / "raw" / "prosportstransactions" / "injuries_2000_2026.csv"
DONE = OUT.with_suffix(".done")
CDP = "http://localhost:9222"
DELAY = (10.0, 20.0)  # seconds between pages, random in this range


def read_rows(page) -> list[list[str]] | None:
    """The results table's data rows (5 cells each), or None if the table isn't there."""
    rows = page.eval_on_selector_all(
        "table tr",
        "trs => trs.map(tr => Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim()))")
    data = [r for r in rows if len(r) == 5 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", r[0])]  # drops header + pager row
    has_header = any(len(r) == 5 and r[0] == "Date" for r in rows)
    return data if has_header else None


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    done = set(DONE.read_text().split()) if DONE.exists() else set()
    # newest first: the recent seasons matter most if Cloudflare cuts the run short
    todo = [s for s in range(LAST_START, -1, -25) if str(s) not in done]
    print(f"{len(done)} pages done, {len(todo)} to go")
    new_file = not OUT.exists()

    with sync_playwright() as p, OUT.open("a", newline="") as f, DONE.open("a") as d:
        w = csv.writer(f)
        if new_file:
            w.writerow(["start", "date", "team", "acquired", "relinquished", "notes"])
        try:
            browser = p.chromium.connect_over_cdp(CDP)
        except Exception:
            raise SystemExit("No Chrome on port 9222 — start it with the command at the top of this file.")
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for i, start in enumerate(todo, 1):
            page.goto(URL.format(start), wait_until="domcontentloaded", timeout=120_000)
            rows, warned = None, False
            for _ in range(150):  # up to ~5 min for a Cloudflare check / slow load
                rows = read_rows(page)
                if rows is not None:
                    break
                if not warned and "Just a moment" in page.title():
                    print("  Cloudflare check — pass it in the Chrome window")
                    warned = True
                time.sleep(2)
            if rows is None:
                raise SystemExit(f"no results table at start={start}; stopping (re-run to resume)")
            for r in rows:
                w.writerow([start, *r])
            f.flush()
            d.write(f"{start}\n")
            d.flush()
            print(f"[{i}/{len(todo)}] start={start}: {len(rows)} rows, {rows[0][0] if rows else '-'}")
            time.sleep(random.uniform(*DELAY))
    print("done:", OUT)


if __name__ == "__main__":
    main()
