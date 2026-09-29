"""Fantasy weeks for a season, derived from the NBA schedule in nba_games.

Rules (user's, from nba-pipeline/fantasy/fantasy_period_defn.py + Fantrax), all adjustable per
league by the commissioner through league settings (DEFAULT_SETTINGS are today's rules):
- Weeks run Monday–Sunday. Week 1 starts the Monday on/before opening night.
- All-Star break: the All-Star week and the week after are fused into one 2-week period
  (`fuse_all_star`).
- The fantasy season ends at the "tankathon cutoff": last regular-season game minus
  `cutoff_days` (14), rounded back to a Sunday. Games after it don't count. 0 = run through
  the week of the NBA's last regular-season game.
- Playoffs are the last periods, one per entry in `playoff_rounds` (default Quarterfinals
  1 week, Semifinals 1 week, Championship 2 weeks), for the top `playoff_teams` (6).

Weeks are never stored — a game's week is looked up from its date, so moved
games land in the right week automatically.
"""
import copy
from datetime import date, timedelta

DEFAULT_SETTINGS = {
    "playoff_teams": 6,
    "playoff_rounds": [
        {"name": "Quarterfinals", "weeks": 1},
        {"name": "Semifinals", "weeks": 1},
        {"name": "Championship", "weeks": 2},
    ],
    "cutoff_days": 14,
    "fuse_all_star": True,
    "matchup_schedule": "round_robin",  # only option so far
}
MATCHUP_SCHEDULES = ("round_robin",)


def normalize_settings(raw: dict | None) -> dict:
    """Stored/submitted settings merged over the defaults and validated (ValueError on bad input)."""
    s = copy.deepcopy(DEFAULT_SETTINGS)
    for k, v in (raw or {}).items():
        if k not in s:
            raise ValueError(f"unknown setting: {k}")
        s[k] = v
    if not isinstance(s["playoff_teams"], int) or not 2 <= s["playoff_teams"] <= 32:
        raise ValueError("playoff_teams must be a whole number from 2 to 32")
    rounds = s["playoff_rounds"]
    if not isinstance(rounds, list) or not rounds:
        raise ValueError("playoff_rounds must list at least one round")
    for r in rounds:
        if not isinstance(r, dict) or not str(r.get("name", "")).strip() or not isinstance(r.get("weeks"), int) or not 1 <= r["weeks"] <= 4:
            raise ValueError("each playoff round needs a name and 1–4 weeks")
        r["name"] = str(r["name"]).strip()[:40]
    # A bracket of n rounds holds up to 2^n teams; fewer means the top seeds get byes.
    if not 2 ** (len(rounds) - 1) < s["playoff_teams"] <= 2 ** len(rounds):
        lo, hi = 2 ** (len(rounds) - 1) + 1, 2 ** len(rounds)
        raise ValueError(f"{len(rounds)} playoff rounds fit {lo}–{hi} playoff teams")
    if not isinstance(s["cutoff_days"], int) or not 0 <= s["cutoff_days"] <= 60:
        raise ValueError("cutoff_days must be 0–60")
    if not isinstance(s["fuse_all_star"], bool):
        raise ValueError("fuse_all_star must be true or false")
    if s["matchup_schedule"] not in MATCHUP_SCHEDULES:
        raise ValueError(f"matchup_schedule must be one of {MATCHUP_SCHEDULES}")
    return s


def playoff_byes(settings: dict) -> int:
    return 2 ** len(settings["playoff_rounds"]) - settings["playoff_teams"]


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


def build_weeks(game_dates: set[date], all_star_dates: list[date], settings: dict | None = None) -> list[dict]:
    s = normalize_settings(settings)
    if not game_dates:
        return []
    first, last = min(game_dates), max(game_dates)
    if s["cutoff_days"]:
        cutoff = last - timedelta(days=s["cutoff_days"])
        end = cutoff - timedelta(days=(cutoff.weekday() + 1) % 7)  # back to Sunday
    else:
        end = last + timedelta(days=(6 - last.weekday()) % 7)      # Sunday of the last game's week

    # Calendar Monday–Sunday weeks, as [start, end] pairs.
    periods, d = [], _monday(first)
    while d <= end:
        periods.append([d, d + timedelta(days=6)])
        d += timedelta(days=7)

    asg = _all_star_sunday(game_dates, all_star_dates) if s["fuse_all_star"] else None
    asb_start = _monday(asg) if asg else None
    merged = []
    for p in periods:
        if merged and asb_start and merged[-1]["start"] == asb_start and merged[-1]["calendar_weeks"] == 1:
            merged[-1]["end"] = p[1]
            merged[-1]["calendar_weeks"] = 2
            merged[-1]["all_star"] = True
            continue
        merged.append({"start": p[0], "end": p[1], "calendar_weeks": 1, "all_star": False})

    # Playoffs take calendar weeks off the end, one chunk per round.
    rounds = s["playoff_rounds"]
    need = sum(r["weeks"] for r in rounds)
    if need >= len(merged):
        raise ValueError(f"playoffs need {need} weeks but the season only has {len(merged)}")
    regular, tail = merged[:-need], merged[-need:]
    playoffs, i = [], 0
    for r in rounds:
        chunk = tail[i:i + r["weeks"]]
        i += r["weeks"]
        playoffs.append({"start": chunk[0]["start"], "end": chunk[-1]["end"], "calendar_weeks": r["weeks"],
                         "all_star": any(c["all_star"] for c in chunk), "round": r["name"]})

    out = []
    for n, p in enumerate(regular, start=1):
        label = f"Week {n}" + (" (All-Star break, 2 weeks)" if p["all_star"] else "")
        out.append({**p, "week": n, "kind": "regular", "label": label})
    for j, p in enumerate(playoffs):
        label = p["round"] + (f" ({p['calendar_weeks']} weeks)" if p["calendar_weeks"] > 1 else "")
        out.append({**p, "week": len(regular) + j + 1, "kind": "playoffs", "label": label})
    return out


def season_weeks(cur, season: str, settings: dict | None = None) -> list[dict]:
    cur.execute("""
        SELECT DISTINCT game_date, game_type FROM nba_games
        WHERE season = %s AND missing_since IS NULL AND game_date IS NOT NULL
          AND game_type IN ('regular', 'allstar')
    """, (season,))
    rows = cur.fetchall()
    regular = {r["game_date"] for r in rows if r["game_type"] == "regular"}
    all_star = [r["game_date"] for r in rows if r["game_type"] == "allstar"]
    return build_weeks(regular, all_star, settings)


def week_for(weeks: list[dict], d: date) -> dict | None:
    return next((w for w in weeks if w["start"] <= d <= w["end"]), None)
