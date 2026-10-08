"""Draft pool and projections, per NBA season (fantasy_pool).

- Who's in the pool for a season: the players loaded for it (source "roster": rostered when the pool was
  built), plus anyone who plays a regular-season game that season and isn't in it yet (source "detected",
  added automatically on the next read), plus commissioner additions (source "manual").
- What it holds: PROJ AVG (projected fantasy points per game played), the player's position for that season
  (one of G / F / C), his NBA team, flags, and his weekly-best curve (proj_week: expected best / floor /
  ceiling for 1..10 games in a fantasy week). Blank PROJ AVG is fine: the player is still draftable, he just
  sorts last.
- PROJ MAX: the curve applied to the season's schedule — each fantasy week, his NBA team's game count and his
  availability (availability.py: chance of a zero-game week, else each game with chance q; season-ending injuries
  left out) give the chance he plays 0..n games, and the curve at each count is weighted by it; weeks before a
  current injury's return date are 0; PROJ MAX is the average over the season's weeks (playoff weeks included, fused
  2-week periods as one week). Projections are made once, before the season: apply_schedule runs at load
  time and stores the result (proj_max, proj_weeks); nothing is recomputed during the season.
- Built offline (scripts/projection_study/, rules in PROJECTIONS.md) and loaded with
  scripts/load_projections.py → POST /fantasy/2026_27/admin/pool.
- A season with no pool rows behaves exactly as before (pool = every player in fantasy_players,
  ranked on box-score averages).
"""

from datetime import date
from math import comb

from psycopg2.extras import Json

from .weeks import season_weeks, week_for

COLUMNS = ("player_id", "name", "nba_team", "position", "proj_avg", "proj_lo", "proj_hi", "flags", "proj_week")


def league_season(cur, scenario: str) -> str | None:
    cur.execute("SELECT season FROM fantasy_leagues WHERE scenario = %s", (scenario,))
    r = cur.fetchone()
    return r["season"] if r else None


def is_active(cur, season: str | None) -> bool:
    if not season:
        return False
    cur.execute("SELECT 1 FROM fantasy_pool WHERE season = %s LIMIT 1", (season,))
    return cur.fetchone() is not None


def _ensure_players(cur, season: str) -> None:
    """Every pool player needs a fantasy_players row (rosters, picks and lineups point at it).
    Rookies and new arrivals get one with no stats."""
    cur.execute("""
        INSERT INTO fantasy_players (id, name, position, nba_team)
        SELECT player_id, name, position, nba_team FROM fantasy_pool WHERE season = %s
        ON CONFLICT (id) DO NOTHING
    """, (season,))


def detect(cur, season: str) -> int:
    """Add players who've played a regular-season game this season but aren't in the pool."""
    cur.execute("""
        WITH new AS (
            SELECT DISTINCT ON (g.player_id) g.player_id, g.player_name, g.team
            FROM nba_player_games g
            WHERE g.season = %(s)s AND g.minutes > 0 AND substr(g.game_id, 3, 1) = '2'
              AND NOT EXISTS (SELECT 1 FROM fantasy_pool p WHERE p.season = %(s)s AND p.player_id = g.player_id)
            ORDER BY g.player_id, g.game_id DESC
        ), pos AS (
            SELECT DISTINCT ON (player_id) player_id, position
            FROM nba_player_games WHERE position IS NOT NULL AND player_id IN (SELECT player_id FROM new)
            GROUP BY player_id, position ORDER BY player_id, count(*) DESC
        )
        INSERT INTO fantasy_pool (season, player_id, name, nba_team, position, source)
        SELECT %(s)s, n.player_id, n.player_name, n.team, COALESCE(pos.position, 'F'), 'detected'
        FROM new n LEFT JOIN pos ON pos.player_id = n.player_id
        ON CONFLICT DO NOTHING
    """, {"s": season})
    added = cur.rowcount
    if added:
        _ensure_players(cur, season)
    return added


def pool(cur, season: str | None) -> dict | None:
    """player_id → pool row for the season, or None when the season has no pool (old behavior)."""
    if not is_active(cur, season):
        return None
    detect(cur, season)
    cur.execute("SELECT * FROM fantasy_pool WHERE season = %s", (season,))
    return {r["player_id"]: dict(r) for r in cur.fetchall()}


def pool_for(cur, scenario: str) -> dict | None:
    return pool(cur, league_season(cur, scenario))


def load(cur, season: str, rows: list, source: str = "roster", replace: bool = False) -> dict:
    """Upsert pool rows. replace=True first removes this season's rows from the same source
    (e.g. a re-run of the projections); detected and manual rows are kept."""
    if source not in ("roster", "manual", "detected"):
        raise ValueError("source must be roster, manual or detected")
    if replace:
        cur.execute("DELETE FROM fantasy_pool WHERE season = %s AND source = %s", (season, source))
    n = 0
    for r in rows:
        if not r.get("player_id") or not r.get("name"):
            continue
        pos = (r.get("position") or "F").strip().upper()[:1]
        if pos not in ("G", "F", "C"):
            pos = "F"
        curve = r.get("proj_week")
        if curve is not None and not (isinstance(curve, dict) and all(isinstance(curve.get(k), list) and curve[k] for k in ("e", "p25", "p90"))):
            raise ValueError(f"proj_week for {r['player_id']} needs e / p25 / p90 lists")
        vals = [str(r["player_id"]), r["name"], r.get("nba_team"), pos] + \
               [None if r.get(k) in (None, "") else float(r[k]) for k in ("proj_avg", "proj_lo", "proj_hi")] + [r.get("flags") or None]
        cur.execute("""
            INSERT INTO fantasy_pool (season, player_id, name, nba_team, position, proj_avg, proj_lo, proj_hi, flags, source, proj_week)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (season, player_id) DO UPDATE SET
              name = EXCLUDED.name, nba_team = EXCLUDED.nba_team, position = EXCLUDED.position,
              proj_avg = EXCLUDED.proj_avg, proj_lo = EXCLUDED.proj_lo, proj_hi = EXCLUDED.proj_hi,
              flags = EXCLUDED.flags, source = EXCLUDED.source, proj_week = EXCLUDED.proj_week, updated_at = now()
        """, (season, *vals, source, Json(curve) if curve else None))
        n += 1
    _ensure_players(cur, season)
    applied = apply_schedule(cur, season)
    cur.execute("SELECT count(*) AS n, count(proj_avg) AS proj FROM fantasy_pool WHERE season = %s", (season,))
    c = cur.fetchone()
    return {"season": season, "loaded": n, "pool": c["n"], "with_proj": c["proj"], **applied}


SEASON_GAMES = 82


def team_games(cur, season: str, weeks: list[dict]) -> dict:
    """NBA team → {fantasy week: regular-season games that week}.

    Before the season, the NBA Cup's December games aren't on the schedule yet: knockout games are placeholders
    with no teams, and the makeup games for teams that don't advance are added once group play ends. So each team
    is short of 82 games, and the shortfall is added to the fantasy week holding the last placeholder (the Cup
    semifinal / final week, where the makeup games are played — in 2025-26 that week still had only 56 team-games). Counts only the weeks inside the fantasy season."""
    cur.execute("""
        SELECT game_date, home_team, away_team FROM nba_games
        WHERE season = %s AND game_type = 'regular' AND missing_since IS NULL AND game_date IS NOT NULL
    """, (season,))
    out, total, placeholder = {}, {}, None
    for g in cur.fetchall():
        if not g["home_team"] or not g["away_team"]:
            placeholder = max(placeholder, g["game_date"]) if placeholder else g["game_date"]
            continue
        for t in (g["home_team"], g["away_team"]):
            total[t] = total.get(t, 0) + 1
            w = week_for(weeks, g["game_date"])
            if w:
                out.setdefault(t, {}).setdefault(w["week"], 0)
                out[t][w["week"]] += 1
    cup = week_for(weeks, placeholder) if placeholder else None
    if cup:
        for t, n in total.items():
            if n < SEASON_GAMES:
                out[t][cup["week"]] = out[t].get(cup["week"], 0) + SEASON_GAMES - n
    return out


def _games_dist(n: int, avail: dict | None) -> list[float]:
    """Chance he plays 0..n of his team's n games in a week. Without availability: all n. With it (availability.py):
    a zero-game week with chance `zero` (injuries cluster), else each game with chance `q`."""
    if not avail:
        return [0.0] * n + [1.0]
    z, q = avail["zero"], avail["q"]
    dist = [(1 - z) * comb(n, k) * q ** k * (1 - q) ** (n - k) for k in range(n + 1)]
    dist[0] += z
    return dist


def week_projection(curve: dict, games_by_week: dict, weeks: list[dict], avail: dict | None = None,
                    out_until: date | None = None) -> list[dict]:
    """His projected weekly score for each fantasy week: the curve at the number of games he plays, weighted by the
    chance of playing each number (availability) — 0 games = 0. A week that ends before a known injury's return date
    (out_until, current ESPN report) is 0."""
    out = []
    for w in weeks:
        n = games_by_week.get(w["week"], 0)
        if out_until and w["end"] < out_until:
            n_play = 0
        else:
            n_play = n
        dist = _games_dist(n_play, avail) if n_play else [1.0]
        row = {"week": w["week"], "games": n, "plays": round(sum(k * p for k, p in enumerate(dist)), 2)}
        for key in ("e", "p25", "p90"):
            c = curve[key]
            row[key] = round(sum(p * c[min(k, len(c)) - 1] for k, p in enumerate(dist) if k), 2)
        out.append(row)
    return out


def apply_schedule(cur, season: str) -> dict:
    """Once, at load time: every pool player with a curve gets PROJ MAX and his per-week projection from the
    season's schedule as it stands (league default week rules), his availability (how many of each week's games he
    plays; season-ending injuries left out) and any injury he's out with right now."""
    weeks = season_weeks(cur, season)
    if not weeks:
        return {"proj_max": 0, "note": f"no schedule loaded for {season}"}
    tg = team_games(cur, season, weeks)
    # known injuries right now (nba_injuries, ESPN): Out with a return date → weeks before it are 0
    cur.execute("""SELECT player_id, return_date FROM nba_injuries
                   WHERE status IN ('Out', 'Out For Season', 'Suspension') AND return_date IS NOT NULL AND player_id IS NOT NULL""")
    out_until = {r["player_id"]: r["return_date"] for r in cur.fetchall()}
    cur.execute("SELECT player_id, nba_team, proj_week FROM fantasy_pool WHERE season = %s AND proj_week IS NOT NULL", (season,))
    n = 0
    for r in cur.fetchall():
        if r["nba_team"] not in tg:  # no NBA team (unsigned): no schedule, no PROJ MAX
            cur.execute("UPDATE fantasy_pool SET proj_max = NULL, proj_weeks = NULL WHERE season = %s AND player_id = %s", (season, r["player_id"]))
            continue
        wp = week_projection(r["proj_week"], tg[r["nba_team"]], weeks, r["proj_week"].get("avail"), out_until.get(r["player_id"]))
        cur.execute("UPDATE fantasy_pool SET proj_max = %s, proj_weeks = %s WHERE season = %s AND player_id = %s",
                    (round(sum(x["e"] for x in wp) / len(wp), 2), Json(wp), season, r["player_id"]))
        n += 1
    return {"proj_max": n, "weeks": len(weeks)}


def record_build(cur, season: str, side: str, rules_side: dict) -> str:
    """Remember which ruleset ("player" or "team") the projections just loaded were built for."""
    from . import scoring
    v = scoring.side_version(rules_side)
    cur.execute("""
        INSERT INTO fantasy_proj_builds (season, side, rules, version) VALUES (%s, %s, %s, %s)
        ON CONFLICT (season, side) DO UPDATE SET rules = EXCLUDED.rules, version = EXCLUDED.version, loaded_at = now()
    """, (season, side, Json(rules_side), v))
    return v


def build_status(cur, scenario: str) -> dict | None:
    """Per side: are the loaded projections built for the league's current scoring rules?
    {"player": {"version", "built_for", "loaded_at", "stale", "changes": [plain words]}, "team": {...}}; a side with
    projections loaded but no record (loaded before records existed) has built_for None and stale True."""
    from . import scoring
    season = league_season(cur, scenario)
    if not season:
        return None
    rules = scoring.league_rules(cur, scenario)
    cur.execute("SELECT side, rules, version, loaded_at FROM fantasy_proj_builds WHERE season = %s", (season,))
    built = {r["side"]: r for r in cur.fetchall()}
    cur.execute("SELECT EXISTS (SELECT 1 FROM fantasy_pool WHERE season = %(s)s AND proj_avg IS NOT NULL) AS player, "
                "EXISTS (SELECT 1 FROM fantasy_team_pool WHERE season = %(s)s AND proj_max IS NOT NULL) AS team", {"s": season})
    has = cur.fetchone()
    out = {}
    for side in ("player", "team"):
        if not has[side]:
            out[side] = None
            continue
        now, b = scoring.side_version(rules[side]), built.get(side)
        out[side] = {"version": now, "built_for": b["version"] if b else None,
                     "loaded_at": b["loaded_at"].isoformat() if b else None,
                     "stale": not b or b["version"] != now,
                     "changes": scoring.changes(b["rules"], rules[side]) if b and b["version"] != now else []}
    return {"season": season, **out}


def by_games(proj_weeks: list[dict]) -> list[dict]:
    """His season's weeks split by game count: how many, and the projected max in each."""
    groups = {}
    for w in proj_weeks or []:
        groups.setdefault(w["games"], []).append(w["e"])
    return [{"games": g, "weeks": len(v), "avg_max": round(sum(v) / len(v), 2)} for g, v in sorted(groups.items())]
