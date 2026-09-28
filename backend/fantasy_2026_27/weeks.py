"""Fantasy weeks for a season, derived from the NBA schedule in nba_games.

Rules (user's, from nba-pipeline/fantasy/fantasy_period_defn.py + Fantrax):
- Weeks run Monday–Sunday. Week 1 starts the Monday on/before opening night.
- All-Star break: the All-Star week and the week after are fused into one 2-week period.
- The fantasy season ends at the "tankathon cutoff": last regular-season game
  minus 14 days, rounded back to a Sunday. Games after it don't count.
- Playoffs are the last periods: Quarterfinals (1 week), Semifinals (1 week),
  Championship (2 weeks, Fantrax-style).

Weeks are never stored — a game's week is looked up from its date, so moved
games land in the right week automatically.
"""
from datetime import date, timedelta

PLAYOFF_ROUNDS = [("Quarterfinals", 1), ("Semifinals", 1), ("Championship", 2)]
CUTOFF_DAYS = 14


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _all_star_sunday(game_dates: set[date], all_star_dates: list[date]) -> date | None:
    """The All-Star game's Sunday. Uses the schedule's All-Star games when present;
    otherwise (future schedules list no ASG yet) the Sunday inside the longest
    run of days with no regular-season games between January and March."""
    if all_star_dates:
        d = max(all_star_dates)
        return d + timedelta(days=(6 - d.weekday()) % 7)
    if not game_dates:
        return None
    first, last = min(game_dates), max(game_dates)
    best, run_start, run = None, None, 0
    d = first
    while d <= last:
        if d not in game_dates and d.month in (1, 2, 3):
            run_start = run_start or d
            run += 1
            if run >= 3 and (best is None or run > best[1]):
                best = (run_start, run)
        else:
            run_start, run = None, 0
        d += timedelta(days=1)
    if not best:
        return None
    start, length = best
    for i in range(length):
        day = start + timedelta(days=i)
        if day.weekday() == 6:
            return day
    return None


def build_weeks(game_dates: set[date], all_star_dates: list[date]) -> list[dict]:
    if not game_dates:
        return []
    first, last = min(game_dates), max(game_dates)
    cutoff = last - timedelta(days=CUTOFF_DAYS)
    end = cutoff - timedelta(days=(cutoff.weekday() + 1) % 7)  # back to Sunday

    # Calendar Monday–Sunday weeks, as [start, end] pairs.
    periods, d = [], _monday(first)
    while d <= end:
        periods.append([d, d + timedelta(days=6)])
        d += timedelta(days=7)

    asg = _all_star_sunday(game_dates, all_star_dates)
    asb_start = _monday(asg) if asg else None
    merged = []
    for p in periods:
        if merged and asb_start and merged[-1]["start"] == asb_start and merged[-1]["calendar_weeks"] == 1:
            merged[-1]["end"] = p[1]
            merged[-1]["calendar_weeks"] = 2
            merged[-1]["all_star"] = True
            continue
        merged.append({"start": p[0], "end": p[1], "calendar_weeks": 1, "all_star": False})

    # Playoffs take calendar weeks off the end: 1 + 1 + 2 by default.
    need = sum(n for _, n in PLAYOFF_ROUNDS)
    regular, tail = merged[:-need], merged[-need:]
    playoffs, i = [], 0
    for name, n in PLAYOFF_ROUNDS:
        chunk = tail[i:i + n]
        i += n
        playoffs.append({"start": chunk[0]["start"], "end": chunk[-1]["end"], "calendar_weeks": n, "all_star": False, "round": name})

    out = []
    for n, p in enumerate(regular, start=1):
        label = f"Week {n}" + (" (All-Star break, 2 weeks)" if p["all_star"] else "")
        out.append({**p, "week": n, "kind": "regular", "label": label})
    for j, p in enumerate(playoffs):
        label = p["round"] + (" (2 weeks)" if p["calendar_weeks"] == 2 else "")
        out.append({**p, "week": len(regular) + j + 1, "kind": "playoffs", "label": label})
    return out


def season_weeks(cur, season: str) -> list[dict]:
    cur.execute("""
        SELECT DISTINCT game_date, game_type FROM nba_games
        WHERE season = %s AND missing_since IS NULL AND game_date IS NOT NULL
          AND game_type IN ('regular', 'allstar')
    """, (season,))
    rows = cur.fetchall()
    regular = {r["game_date"] for r in rows if r["game_type"] == "regular"}
    all_star = [r["game_date"] for r in rows if r["game_type"] == "allstar"]
    return build_weeks(regular, all_star)


def week_for(weeks: list[dict], d: date) -> dict | None:
    return next((w for w in weeks if w["start"] <= d <= w["end"]), None)
