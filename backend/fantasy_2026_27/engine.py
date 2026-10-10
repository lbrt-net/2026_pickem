"""League engine: a sandbox's clock, and weekly results computed from real box scores.

- Every sandbox is a league row (fantasy_leagues): an NBA season + sim_date. sim_date NULL
  means "today" (the live league). The replay sandbox replays 2025-26 with a date an admin moves.
- Nothing after the league's as-of date is ever read, so a replay can't see the future.
- Weekly scores (FANTASY_SCORING.md): a player's week = his single best game that week;
  an NBA team slot's week = its point margin totaled over the week's games. A fantasy team's
  week = the sum over its roster. Regular-season matchups are a round-robin (same pairing
  rule as the frontend's weekPairings), so both sides agree on who plays whom.
- Rosters: a week's lineup comes from etch.py — entities etched when they locked (they still count after
  being dropped), plus live-roster entities not etched yet who joined before their lock.
- Playoff weeks are listed but their matchups aren't built yet.
"""
from datetime import date, datetime, timedelta, timezone

from psycopg2.extras import Json

from . import etch as etch_mod
from .logic import player_points, team_game_points
from .scoring import league_rules, team_extras, week_score
from .weeks import DEFAULT_SETTINGS, LOCK_MINUTES, normalize_settings, season_weeks, week_for

REPLAY = "replay"
# Settings that shape the draft: locked once it has started (save_settings).
DRAFT_LOCKED = ("roster_slots", "team_count", "draft_type", "pick_seconds", "pick_seconds_by_round", "missed_pick",
                "draft_start_at", "auction_budget", "auction_min_bid", "nomination_seconds", "bid_seconds")


def league(cur, scenario: str) -> dict:
    cur.execute("SELECT * FROM fantasy_leagues WHERE scenario = %s", (scenario,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"no league for scenario {scenario}")
    return dict(row)


def as_of(lg: dict) -> date:
    return lg["sim_date"] or date.today()


def settings(lg: dict) -> dict:
    """The league's commissioner settings, defaults filled in."""
    return normalize_settings(lg.get("settings") or {})


def weeks_for_league(cur, lg: dict) -> list[dict]:
    return season_weeks(cur, lg["season"], settings(lg))


def save_settings(cur, scenario: str, changes: dict) -> dict:
    """Merge commissioner changes into a league's settings, validate, and check the season still
    fits (e.g. enough weeks for the playoff rounds). Raises ValueError; nothing saved on error."""
    lg = league(cur, scenario)
    # Once the draft has started, the settings that shape it are locked (reset the draft first),
    # so a finished draft never turns into "16 of 28 picks".
    cur.execute("SELECT status FROM fantasy_drafts WHERE scenario = %s", (scenario,))
    row = cur.fetchone()
    cur.execute("SELECT 1 FROM fantasy_rosters WHERE scenario = %s LIMIT 1", (scenario,))
    drafted = (row and row["status"] != "not_started") or cur.fetchone() is not None
    current = normalize_settings(lg.get("settings") or {})
    touched = [k for k in DRAFT_LOCKED if k in changes and changes[k] != current.get(k)]
    if drafted and touched:
        raise ValueError(f"the draft has started — reset it to change {', '.join(touched)}")
    stored = {**(lg.get("settings") or {}), **changes}
    new = normalize_settings(stored)
    season_weeks(cur, lg["season"], new)  # raises if the playoffs don't fit this season
    overrides = {k: v for k, v in new.items() if v != DEFAULT_SETTINGS[k]}
    cur.execute("UPDATE fantasy_leagues SET settings = %s, updated_at = now() WHERE scenario = %s",
                (Json(overrides), scenario))
    return new


def _prev_season(season: str) -> str:
    y = int(season[:4]) - 1
    return f"{y}-{str(y + 1)[2:]}"


def pairings(teams: list[dict], week: int) -> list[tuple]:
    """Round-robin by the circle method, teams sorted by name — mirrors data.js weekPairings."""
    ids = sorted(teams, key=lambda t: t["name"].lower())
    if len(ids) % 2:
        ids.append(None)
    n = len(ids)
    if n < 2:
        return []
    rest = ids[1:]
    r = (week - 1) % (n - 1)
    rot = [ids[0]] + [rest[(i + r) % len(rest)] for i in range(len(rest))]
    return [(rot[i], rot[n - 1 - i]) for i in range(n // 2) if rot[i] and rot[n - 1 - i]]


def matchup_overrides(cur, scenario: str) -> dict:
    """The commissioner's hand-set weeks: {week number: [(team_id, team_id), ...]}."""
    cur.execute("SELECT matchups FROM fantasy_leagues WHERE scenario = %s", (scenario,))
    r = cur.fetchone()
    return {int(k): [tuple(p) for p in v] for k, v in ((r and r["matchups"]) or {}).items()}


def week_pairings(teams: list[dict], week: int, overrides: dict) -> list[tuple]:
    """A week's matchups: the commissioner's pairs if he set that week, else the round robin."""
    if week in overrides:
        by_id = {t["id"]: t for t in teams}
        return [(by_id[a], by_id[b]) for a, b in overrides[week] if a in by_id and b in by_id]
    return pairings(teams, week)


def set_matchups(cur, scenario: str, week: int, pairs: list | None, team_ids: set) -> None:
    """Set one week's matchups by hand (pairs of team ids), or put it back on the round robin (pairs=None).
    Each team plays at most once; a team left out has no game that week."""
    cur.execute("SELECT matchups FROM fantasy_leagues WHERE scenario = %s", (scenario,))
    current = dict((cur.fetchone() or {}).get("matchups") or {})
    if pairs is None:
        current.pop(str(week), None)
    else:
        seen = set()
        for pr in pairs:
            if not isinstance(pr, (list, tuple)) or len(pr) != 2 or pr[0] == pr[1]:
                raise ValueError("each matchup is two different teams")
            for t in pr:
                if t not in team_ids:
                    raise ValueError("unknown team")
                if t in seen:
                    raise ValueError("a team can only play once a week")
                seen.add(t)
        current[str(week)] = [list(pr) for pr in pairs]
    cur.execute("UPDATE fantasy_leagues SET matchups = %s, updated_at = now() WHERE scenario = %s", (Json(current) if current else None, scenario))


def set_clock(cur, scenario: str, sim_date: date | None) -> None:
    if scenario != REPLAY:
        raise ValueError("only the replay sandbox has a movable clock")
    lg = league(cur, scenario)
    new_today = sim_date or date.today()
    if new_today < as_of(lg):  # moving back: weeks not over yet as of the new date get re-etched as they lock again
        etch_mod.rewind(cur, scenario, weeks_for_league(cur, lg), new_today)
    cur.execute("UPDATE fantasy_leagues SET sim_date = %s, updated_at = now() WHERE scenario = %s", (sim_date, scenario))


def reset_replay(cur) -> dict:
    """Fresh replay: empty rosters and a not-started draft (draft it in the Draft Room with the
    Replay sandbox selected — rankings use the prior season), clock back to the day before
    the first fantasy week."""
    lg = league(cur, REPLAY)
    weeks = weeks_for_league(cur, lg)
    if not weeks:
        raise ValueError(f"no schedule loaded for {lg['season']}")
    from . import draft  # local import: draft is a sibling module that doesn't import engine
    draft.reset(cur, REPLAY)  # empty rosters, draft not started, saved order kept
    start = weeks[0]["start"] - timedelta(days=1)
    set_clock(cur, REPLAY, start)
    return {"season": lg["season"], "sim_date": start.isoformat(), "draft": "not_started"}


def _team_margins(cur, season: str) -> dict:
    cur.execute("""
        SELECT home_team, away_team, home_score, away_score FROM nba_games
        WHERE season = %s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL
    """, (season,))
    tot, n = {}, {}
    for g in cur.fetchall():
        for team, m in ((g["home_team"], g["home_score"] - g["away_score"]), (g["away_team"], g["away_score"] - g["home_score"])):
            tot[team] = tot.get(team, 0) + m
            n[team] = n.get(team, 0) + 1
    return {t: tot[t] / n[t] for t in tot}


def home_week(cur, season: str, weeks: list[dict], today: date, replay: bool):
    """The league-wide current week (Home): week N until 5 min before week N+1's first game.
    The replay plays whole days, so a week starts on its first day."""
    if not weeks:
        return None
    started = [w for w in weeks if w["start"] <= today]
    if not started:
        return weeks[0]["week"]
    w = started[-1]
    if replay or w is weeks[0]:
        return w["week"]
    cur.execute("SELECT MIN(tipoff_utc) AS t FROM nba_games WHERE season = %s AND game_type = 'regular' AND game_date BETWEEN %s AND %s",
                (season, w["start"], w["end"]))
    first = cur.fetchone()["t"]
    if first and datetime.now(timezone.utc) < first - timedelta(minutes=LOCK_MINUTES):
        return started[-2]["week"]
    return w["week"]


def results(cur, scenario: str) -> dict:
    """Every week up to the league's as-of date: matchups with each slot's weekly score, plus standings."""
    lg = league(cur, scenario)
    season, today = lg["season"], as_of(lg)
    weeks = weeks_for_league(cur, lg)

    cur.execute("""
        SELECT t.id, t.name, t.abbreviation, t.color, t.glyph, t.owner_user_id, u.username AS owner_name
        FROM fantasy_teams t LEFT JOIN users u ON u.discord_id = t.owner_user_id WHERE t.scenario = %s
    """, (scenario,))
    teams = {t["id"]: dict(t) for t in cur.fetchall()}
    # Each begun week's lineup per team: etched entities (even if dropped since) + live ones not etched yet (etch.py).
    lineups = etch_mod.week_lineups(cur, scenario, season, weeks, today)
    every = {e["id"]: e for es in lineups.values() for e in es}
    player_ids = sorted(eid for eid, e in every.items() if e["kind"] == "player")
    team_ids = sorted(eid for eid, e in every.items() if e["kind"] == "nba_team")

    # Every game's fantasy points per entity per week, under the league's rulesets; the weekly score comes from
    # the ruleset's week mode (today: players = best game, NBA teams = sum).
    rules = league_rules(cur, scenario)
    overrides = matchup_overrides(cur, scenario)
    games_wk = {}  # (entity id, week) -> [(points, date)]
    if player_ids:
        cur.execute("""
            SELECT pg.player_id, g.game_date, pg.pts, pg.fgm, pg.fga, pg.fg3m, pg.ftm, pg.fta, pg.oreb, pg.dreb,
                   pg.ast, pg.stl, pg.blk, pg.tov, pg.blkd, pg.clutch_pts
            FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
            WHERE pg.season = %s AND g.game_type = 'regular' AND pg.minutes > 0
              AND g.game_date <= %s AND pg.player_id = ANY(%s::text[])
        """, (season, today, player_ids))
        for r in cur.fetchall():
            w = week_for(weeks, r["game_date"])
            if w:
                games_wk.setdefault((r["player_id"], w["week"]), []).append((player_points(r, rules), r["game_date"].isoformat()))
    if team_ids:
        cur.execute("""
            SELECT game_id, game_date, home_team, away_team, home_score, away_score FROM nba_games
            WHERE season = %s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL
              AND game_date <= %s AND (home_team = ANY(%s::text[]) OR away_team = ANY(%s::text[]))
        """, (season, today, team_ids, team_ids))
        tgames = cur.fetchall()
        extras = team_extras(cur, [g["game_id"] for g in tgames])
        for g in tgames:
            w = week_for(weeks, g["game_date"])
            if not w:
                continue
            for t, mine, theirs in ((g["home_team"], g["home_score"], g["away_score"]),
                                    (g["away_team"], g["away_score"], g["home_score"])):
                if t in team_ids:
                    pts = team_game_points(mine > theirs, mine, theirs, rules, extras.get((g["game_id"], t)))
                    games_wk.setdefault((t, w["week"]), []).append((pts, g["game_date"].isoformat()))

    def side(team, week):
        slots = []
        for e in lineups.get((team["id"], week), []):
            e = {k: e[k] for k in ("id", "kind", "name", "slot")}
            gs = games_wk.get((e["id"], week), [])
            score = week_score(rules["player" if e["kind"] == "player" else "team"], [p for p, _ in gs]) or 0.0
            if e["kind"] == "player":
                best = max(gs, key=lambda g: g[0], default=None)
                slots.append({**e, "score": score, "best_game_date": best[1] if best else None})
            else:
                slots.append({**e, "score": score, "games": len(gs)})
        # Bench and IR spots are shown but don't count toward the team's score.
        return {"team": team, "score": round(sum(s["score"] for s in slots if s.get("slot") not in ("BENCH", "IR")), 1), "slots": slots}

    standings = {tid: {"team": t, "w": 0, "l": 0, "t": 0, "pf": 0.0, "pa": 0.0} for tid, t in teams.items()}
    out_weeks = []
    for w in weeks:
        if w["start"] > today:
            break
        status = "final" if w["end"] < today else "in_progress"
        entry = {"week": w["week"], "label": w["label"], "kind": w["kind"], "start": w["start"].isoformat(),
                 "end": w["end"].isoformat(), "status": status, "matchups": []}
        if w["kind"] == "regular":
            for a, b in week_pairings(list(teams.values()), w["week"], overrides):
                sa, sb = side(a, w["week"]), side(b, w["week"])
                entry["matchups"].append({"home": sa, "away": sb})
                if status == "final":
                    ra, rb = standings[a["id"]], standings[b["id"]]
                    ra["pf"] += sa["score"]; ra["pa"] += sb["score"]; rb["pf"] += sb["score"]; rb["pa"] += sa["score"]
                    if sa["score"] > sb["score"]:
                        ra["w"] += 1; rb["l"] += 1
                    elif sb["score"] > sa["score"]:
                        rb["w"] += 1; ra["l"] += 1
                    else:
                        ra["t"] += 1; rb["t"] += 1
        out_weeks.append(entry)

    table = sorted(standings.values(), key=lambda r: (-(r["w"] + r["t"] / 2), -r["pf"]))
    for r in table:
        r["pf"], r["pa"] = round(r["pf"], 1), round(r["pa"], 1)
    current = week_for(weeks, today)
    return {
        "scenario": scenario, "season": season, "as_of": today.isoformat(), "sim_date": lg["sim_date"].isoformat() if lg["sim_date"] else None,
        "current_week": current["week"] if current else None,
        "home_week": home_week(cur, season, weeks, today, scenario == REPLAY),
        "season_start": weeks[0]["start"].isoformat() if weeks else None,
        "season_end": weeks[-1]["end"].isoformat() if weeks else None,
        "weeks": out_weeks, "standings": table, "settings": settings(lg),
    }
