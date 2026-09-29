"""League engine: a sandbox's clock, and weekly results computed from real box scores.

- Every sandbox is a league row (fantasy_leagues): an NBA season + sim_date. sim_date NULL
  means "today" (the live league). The replay sandbox replays 2025-26 with a date an admin moves.
- Nothing after the league's as-of date is ever read, so a replay can't see the future.
- Weekly scores (FANTASY_SCORING.md): a player's week = his single best game that week;
  an NBA team slot's week = its point margin totaled over the week's games. A fantasy team's
  week = the sum over its roster. Regular-season matchups are a round-robin (same pairing
  rule as the frontend's weekPairings), so both sides agree on who plays whom.
- Rosters are the sandbox's current rosters for every week — there's no transaction history
  yet (adds/drops/trades will need roster-by-date later).
- Playoff weeks are listed but their matchups aren't built yet.
"""
from datetime import date, timedelta

from psycopg2.extras import Json

from .logic import player_points, simulate_draft, team_game_points
from .weeks import DEFAULT_SETTINGS, normalize_settings, season_weeks, week_for

REPLAY = "replay"


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


def set_clock(cur, scenario: str, sim_date: date | None) -> None:
    if scenario != REPLAY:
        raise ValueError("only the replay sandbox has a movable clock")
    cur.execute("UPDATE fantasy_leagues SET sim_date = %s, updated_at = now() WHERE scenario = %s", (sim_date, scenario))


def reset_replay(cur) -> dict:
    """Fresh replay: re-draft ranked on the season before the replayed one (no peeking),
    clock set to the day before the first fantasy week."""
    lg = league(cur, REPLAY)
    season = lg["season"]
    weeks = weeks_for_league(cur, lg)
    if not weeks:
        raise ValueError(f"no schedule loaded for {season}")
    prior = _prev_season(season)

    # Rank by last season's average fantasy points (one scoring function: player_points).
    cur.execute("""
        SELECT player_id, pts, fgm, fga, fg3m, ftm, fta, oreb, dreb, ast, stl, blk, tov, blkd
        FROM nba_player_games WHERE season = %s AND minutes > 0 AND substr(game_id, 3, 1) = '2'
    """, (prior,))
    sums, counts = {}, {}
    for r in cur.fetchall():
        sums[r["player_id"]] = sums.get(r["player_id"], 0) + player_points(r)
        counts[r["player_id"]] = counts.get(r["player_id"], 0) + 1
    rank = {pid: sums[pid] / counts[pid] for pid in sums}
    for team, margin in _team_margins(cur, prior).items():
        rank[team] = margin

    cur.execute("DELETE FROM fantasy_rosters WHERE scenario = %s", (REPLAY,))
    simulate_draft(cur, REPLAY, rank_points=rank)
    start = weeks[0]["start"] - timedelta(days=1)
    set_clock(cur, REPLAY, start)
    return {"season": season, "drafted_on": prior, "sim_date": start.isoformat()}


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


def results(cur, scenario: str) -> dict:
    """Every week up to the league's as-of date: matchups with each slot's weekly score, plus standings."""
    lg = league(cur, scenario)
    season, today = lg["season"], as_of(lg)
    weeks = weeks_for_league(cur, lg)

    cur.execute("SELECT id, name, abbreviation, color, owner_user_id FROM fantasy_teams WHERE scenario = %s", (scenario,))
    teams = {t["id"]: dict(t) for t in cur.fetchall()}
    cur.execute("""
        SELECT r.team_id, r.slot, r.player_id, r.nba_team_id, COALESCE(p.name, n.name) AS name
        FROM fantasy_rosters r
        LEFT JOIN fantasy_players p ON p.id = r.player_id
        LEFT JOIN fantasy_nba_teams n ON n.id = r.nba_team_id
        WHERE r.scenario = %s ORDER BY r.id
    """, (scenario,))
    roster = {tid: [] for tid in teams}
    for r in cur.fetchall():
        roster[r["team_id"]].append({"id": r["player_id"] or r["nba_team_id"], "kind": "player" if r["player_id"] else "nba_team",
                                     "name": r["name"], "slot": r["slot"]})
    player_ids = [e["id"] for es in roster.values() for e in es if e["kind"] == "player"]
    team_ids = [e["id"] for es in roster.values() for e in es if e["kind"] == "nba_team"]

    # Best game per player per week (regular season, played, on or before as-of).
    best = {}  # (player_id, week) -> {points, date}
    if player_ids:
        cur.execute("""
            SELECT pg.player_id, g.game_date, pg.pts, pg.fgm, pg.fga, pg.fg3m, pg.ftm, pg.fta, pg.oreb, pg.dreb,
                   pg.ast, pg.stl, pg.blk, pg.tov, pg.blkd
            FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
            WHERE pg.season = %s AND g.game_type = 'regular' AND pg.minutes > 0
              AND g.game_date <= %s AND pg.player_id = ANY(%s::text[])
        """, (season, today, player_ids))
        for r in cur.fetchall():
            w = week_for(weeks, r["game_date"])
            if not w:
                continue
            pts = player_points(r)
            key = (r["player_id"], w["week"])
            if key not in best or pts > best[key]["points"]:
                best[key] = {"points": pts, "date": r["game_date"].isoformat()}

    # Point margin totaled per NBA team per week.
    margin = {}  # (tricode, week) -> {points, games}
    if team_ids:
        cur.execute("""
            SELECT game_date, home_team, away_team, home_score, away_score FROM nba_games
            WHERE season = %s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL
              AND game_date <= %s AND (home_team = ANY(%s::text[]) OR away_team = ANY(%s::text[]))
        """, (season, today, team_ids, team_ids))
        for g in cur.fetchall():
            w = week_for(weeks, g["game_date"])
            if not w:
                continue
            for t, mine, theirs in ((g["home_team"], g["home_score"], g["away_score"]),
                                    (g["away_team"], g["away_score"], g["home_score"])):
                if t in team_ids:
                    m = margin.setdefault((t, w["week"]), {"points": 0.0, "games": 0})
                    m["points"] += team_game_points(mine > theirs, mine, theirs)
                    m["games"] += 1

    def side(team, week):
        slots = []
        for e in roster[team["id"]]:
            if e["kind"] == "player":
                b = best.get((e["id"], week))
                slots.append({**e, "score": b["points"] if b else 0.0, "best_game_date": b["date"] if b else None})
            else:
                m = margin.get((e["id"], week))
                slots.append({**e, "score": round(m["points"], 1) if m else 0.0, "games": m["games"] if m else 0})
        return {"team": team, "score": round(sum(s["score"] for s in slots), 1), "slots": slots}

    standings = {tid: {"team": t, "w": 0, "l": 0, "t": 0, "pf": 0.0, "pa": 0.0} for tid, t in teams.items()}
    out_weeks = []
    for w in weeks:
        if w["start"] > today:
            break
        status = "final" if w["end"] < today else "in_progress"
        entry = {"week": w["week"], "label": w["label"], "kind": w["kind"], "start": w["start"].isoformat(),
                 "end": w["end"].isoformat(), "status": status, "matchups": []}
        if w["kind"] == "regular":
            for a, b in pairings(list(teams.values()), w["week"]):
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
        "season_start": weeks[0]["start"].isoformat() if weeks else None,
        "season_end": weeks[-1]["end"].isoformat() if weeks else None,
        "weeks": out_weeks, "standings": table, "settings": settings(lg),
    }
