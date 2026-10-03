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
from datetime import date, datetime, timedelta, timezone

DEFAULT_SETTINGS = {
    "league_name": "",  # shown at the top of Home; blank = no name yet
    "playoff_teams": 6,
    "playoff_rounds": [
        {"name": "Quarterfinals", "weeks": 1},
        {"name": "Semifinals", "weeks": 1},
        {"name": "Championship", "weeks": 2},
    ],
    "cutoff_days": 14,
    "fuse_all_star": True,
    "matchup_schedule": "round_robin",  # only option so far
    # Roster: slot type → count. PLAYER = any player, TEAM = an NBA team, FLEX = either,
    # G/F/C = players listed at that position. No bench. Round 1: 3 players + 1 team.
    "roster_slots": {"PLAYER": 3, "TEAM": 1},
    # Team limit: joinable leagues cap members at this; test sandboxes fill up to it with bots. 2–16.
    "team_count": 4,
    # ---- Draft ----
    # linear = same order every round; snake = reverses every round; snake_3rr = snake with a
    # third-round reversal (round 3 repeats round 2's order, then alternates); auction = bidding.
    "draft_type": "snake",
    "pick_seconds": 600,             # pick clock
    "pick_seconds_by_round": [],     # optional per-round clocks, e.g. [120, 120, 60]; rounds past the list use pick_seconds
    "missed_pick": "autopick",       # clock runs out → best available that fits (only option so far)
    "draft_start_at": None,          # ISO time (UTC) the draft starts on its own; None = when the commissioner presses Start
    # Auction (draft_type = auction): budget per team, minimum bid, nomination clock, and the
    # clock each new bid resets to (see draft.py "Auction").
    "auction_budget": 200,
    "auction_min_bid": 1,
    "nomination_seconds": 60,
    "bid_seconds": 15,
}
MATCHUP_SCHEDULES = ("round_robin",)
DRAFT_TYPES = ("linear", "snake", "snake_3rr", "auction")
MISSED_PICK = ("autopick",)
SLOT_TYPES = ("G", "F", "C", "PLAYER", "TEAM", "FLEX")


def normalize_settings(raw: dict | None) -> dict:
    """Stored/submitted settings merged over the defaults and validated (ValueError on bad input)."""
    s = copy.deepcopy(DEFAULT_SETTINGS)
    for k, v in (raw or {}).items():
        if k not in s:
            raise ValueError(f"unknown setting: {k}")
        s[k] = v
    if not isinstance(s["league_name"], str):
        raise ValueError("league_name must be text")
    s["league_name"] = " ".join(s["league_name"].split())[:40]
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
    slots = s["roster_slots"]
    if (not isinstance(slots, dict) or not slots or any(k not in SLOT_TYPES for k in slots)
            or not all(isinstance(v, int) and 0 <= v <= 10 for v in slots.values()) or not 1 <= sum(slots.values()) <= 15):
        raise ValueError(f"roster_slots: counts 0–10 per type {SLOT_TYPES}, 1–15 spots total")
    s["roster_slots"] = {k: v for k, v in slots.items() if v}
    if not isinstance(s["team_count"], int) or not 2 <= s["team_count"] <= 16:
        raise ValueError("team_count must be 2–16")
    if s["draft_type"] not in DRAFT_TYPES:
        raise ValueError(f"draft_type must be one of {DRAFT_TYPES}")
    secs = lambda v: isinstance(v, int) and 10 <= v <= 86400
    if not secs(s["pick_seconds"]):
        raise ValueError("pick_seconds must be 10–86400")
    by_round = s["pick_seconds_by_round"]
    if not isinstance(by_round, list) or len(by_round) > 15 or not all(secs(v) for v in by_round):
        raise ValueError("pick_seconds_by_round: up to 15 rounds, each 10–86400 seconds")
    if s["missed_pick"] not in MISSED_PICK:
        raise ValueError(f"missed_pick must be one of {MISSED_PICK}")
    if s["draft_start_at"] is not None:
        try:
            when = datetime.fromisoformat(str(s["draft_start_at"]).replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("draft_start_at must be an ISO date/time, or null")
        if when.tzinfo is None:
            raise ValueError("draft_start_at needs a time zone (e.g. ...Z)")
        s["draft_start_at"] = when.astimezone(timezone.utc).isoformat()
    a = s
    if not (isinstance(a["auction_budget"], int) and 1 <= a["auction_budget"] <= 10000):
        raise ValueError("auction_budget must be 1–10000")
    if not (isinstance(a["auction_min_bid"], int) and 0 <= a["auction_min_bid"] <= a["auction_budget"]):
        raise ValueError("auction_min_bid must be 0 up to the budget")
    if not (isinstance(a["nomination_seconds"], int) and 5 <= a["nomination_seconds"] <= 600):
        raise ValueError("nomination_seconds must be 5–600")
    if not (isinstance(a["bid_seconds"], int) and 3 <= a["bid_seconds"] <= 120):
        raise ValueError("bid_seconds must be 3–120")
    return s


def round_seconds(settings: dict, rnd: int) -> int:
    """Pick clock for 0-based round `rnd`."""
    by_round = settings["pick_seconds_by_round"]
    return by_round[rnd] if rnd < len(by_round) else settings["pick_seconds"]


def league_settings(cur, scenario: str) -> dict:
    """A league's settings (defaults if the league row or table doesn't exist yet — first boot)."""
    cur.execute("SELECT to_regclass('fantasy_leagues') AS t")
    if cur.fetchone()["t"] is None:
        return normalize_settings(None)
    cur.execute("SELECT settings FROM fantasy_leagues WHERE scenario = %s", (scenario,))
    row = cur.fetchone()
    return normalize_settings(row["settings"] if row else None)


def slot_list(settings: dict) -> list[str]:
    """Roster slots in display order, e.g. ["PLAYER", "PLAYER", "PLAYER", "TEAM"]."""
    order = [t for t in SLOT_TYPES if t in settings["roster_slots"]]
    return [t for t in order for _ in range(settings["roster_slots"][t])]


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
