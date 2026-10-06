"""Official NBA injury reports, one snapshot per game day, '22 → '26 (2021-22 → 2025-26), via nbainjuries.
Download the PDF → keep its raw text (.txt) + the parsed table (.csv) → delete the PDF
(kept only when parsing fails, so it can be looked at).

    source .venv/bin/activate
    pip install nbainjuries certifi     # + Java: brew install openjdk
    python3 scripts/pull_injury_reports.py

Source is ak-static.cms.nba.com (static PDFs), not stats.nba.com — can run alongside stats pulls.
Game days come from nba-pipeline's schedule parquet (regular season, play-in, playoffs).
Snapshot: 5:30 PM ET (older reports are hourly → 5 PM); falls back to nearby times when missing.
Resumable: skips days already saved. '26 is the validation season — never fit on it.
"""
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

os.environ.setdefault("JAVA_HOME", "/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home")
import certifi  # noqa: E402
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

import pandas as pd  # noqa: E402
import requests  # noqa: E402
from PyPDF2 import PdfReader  # noqa: E402
from nbainjuries import injury  # noqa: E402
from nbainjuries._constants import requestheaders  # noqa: E402
from nbainjuries._util import _gen_filepath  # noqa: E402

PIPE = Path.home() / "PycharmProjects" / "nba-pipeline" / "data" / "raw"
OUT = PIPE / "injury_reports"
SEASONS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
TIMES = [(17, 30), (17, 0), (18, 0), (16, 0), (19, 0), (13, 0), (12, 0)]  # first that exists wins
DELAY = 2


def game_days(season: str) -> list:
    s = pd.read_parquet(PIPE / "schedules" / f"schedule_{season.replace('-', '_')}.parquet")
    s = s[s.game_id.astype(str).str[2].isin(["2", "4", "5"])]
    return sorted(pd.to_datetime(s.game_date).dt.date.unique())


def main():
    for season in SEASONS:
        days = game_days(season)
        d_out = OUT / season
        d_out.mkdir(parents=True, exist_ok=True)
        done = {re.search(r"\d{4}-\d{2}-\d{2}", p.name).group() for p in [*d_out.glob("*.csv"), *d_out.glob("*.missing")]}
        todo = [d for d in days if d.isoformat() not in done]
        print(f"{season}: {len(days)} game days, {len(todo)} to go", flush=True)
        for i, day in enumerate(todo, 1):
            ts = None
            for h, m in TIMES:
                cand = datetime(day.year, day.month, day.day, h, m)
                try:
                    ok = injury.check_reportvalid(cand)
                except ValueError:  # the 2025-12-19 URL-format gap
                    ok = False
                if ok:
                    ts = cand
                    break
                time.sleep(0.5)
            if ts is None:
                (d_out / f"{day.isoformat()}.missing").touch()
                print(f"  [{i}/{len(todo)}] {day}: no report found", flush=True)
                continue
            pdf = Path(_gen_filepath(ts, str(d_out)))
            pdf.write_bytes(requests.get(injury.gen_url(ts), headers=requestheaders, timeout=60).content)
            stem = d_out / pdf.stem
            Path(f"{stem}.txt").write_text("\n\f\n".join(p.extract_text() or "" for p in PdfReader(pdf).pages))
            try:
                df = injury.get_reportdata(ts, local=True, localdir=str(d_out), return_df=True)
                df.to_csv(f"{stem}.csv", index=False)
                pdf.unlink()
                print(f"  [{i}/{len(todo)}] {day} {pdf.stem[-6:]}: {len(df)} rows", flush=True)
            except Exception as e:
                print(f"  [{i}/{len(todo)}] {day}: PARSE FAILED ({type(e).__name__}: {e}) — PDF kept", flush=True)
            time.sleep(DELAY)


if __name__ == "__main__":
    sys.exit(main())
