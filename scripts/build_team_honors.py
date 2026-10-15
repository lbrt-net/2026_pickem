"""Franchise honors for the team pages' trophy case: NBA titles, Finals trips, conference finals appearances.

    python3 scripts/build_team_honors.py     (system python3 with nba_api; writes backend/fantasy_2026_27/data/team_honors.json)

From TeamYearByYearStats (one call per franchise, all seasons). Titles and Finals: its NBA_FINALS_APPEARANCE column, all
time. Conference finals: seasons a team reached the third round — counted only in the 4-round era (1983-84 on, where it's
unambiguous from playoff wins: 7+ wins through 2001-02 when round 1 was best-of-5, 8+ from 2002-03). The Finals count
includes the conference finals it won.
"""
import json, time
from pathlib import Path

from nba_api.stats.endpoints import TeamYearByYearStats
from nba_api.stats.static import teams

OUT = Path(__file__).resolve().parent.parent / "backend" / "fantasy_2026_27" / "data" / "team_honors.json"
out = {}
for t in teams.get_teams():
    for attempt in range(5):
        try:
            df = TeamYearByYearStats(team_id=t["id"], timeout=60).get_data_frames()[0]
            break
        except Exception as e:
            print(t["abbreviation"], "retry", attempt, e, flush=True)
            time.sleep(20 * (attempt + 1))
    champ = finals = conf = 0
    for r in df.to_dict("records"):
        fa = str(r.get("NBA_FINALS_APPEARANCE") or "")
        start = int(str(r["YEAR"])[:4])
        if fa == "LEAGUE CHAMPION":
            champ += 1
        if fa in ("LEAGUE CHAMPION", "FINALS APPEARANCE"):
            finals += 1
        if start >= 1983 and (r.get("PO_WINS") or 0) >= (7 if start <= 2001 else 8):
            conf += 1
    out[t["abbreviation"]] = {"champ": champ, "finals": finals, "conf": conf}
    print(t["abbreviation"], out[t["abbreviation"]], flush=True)
    time.sleep(1.5)
OUT.write_text(json.dumps(out, indent=0))
