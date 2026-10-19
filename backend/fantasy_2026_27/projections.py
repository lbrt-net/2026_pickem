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
from math import comb, erf

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
    Rookies and new arrivals get one with no stats. The pool's position wins over an older one (2026-10-17: 134
    players kept an older G/F/C here, so seating, lineups and the transaction log disagreed with the pages)."""
    cur.execute("""
        INSERT INTO fantasy_players (id, name, position, nba_team)
        SELECT player_id, name, position, nba_team FROM fantasy_pool WHERE season = %s
        ON CONFLICT (id) DO UPDATE SET position = COALESCE(EXCLUDED.position, fantasy_players.position),
                                       nba_team = COALESCE(EXCLUDED.nba_team, fantasy_players.nba_team)
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


_POOL_CACHE: dict = {}  # season -> (built at, pool): the pool changes a few times a day at most (2026-10-17 speed pass)
POOL_TTL = 120


def clear_cache() -> None:
    _POOL_CACHE.clear()


def pool(cur, season: str | None) -> dict | None:
    """player_id → pool row for the season, or None when the season has no pool (old behavior). Cached 2 minutes (the
    new-player check included); loading projections clears it."""
    import time
    hit = _POOL_CACHE.get(season)
    if hit and time.time() - hit[0] < POOL_TTL:
        return hit[1]
    out = _pool(cur, season)
    _POOL_CACHE[season] = (time.time(), out)
    return out


def _pool(cur, season: str | None) -> dict | None:
    if not is_active(cur, season):
        return None
    detect(cur, season)
    cur.execute("SELECT * FROM fantasy_pool WHERE season = %s", (season,))
    return {r["player_id"]: dict(r) for r in cur.fetchall()}


def pool_for(cur, scenario: str) -> dict | None:
    return pool(cur, league_season(cur, scenario))


def load(cur, season: str, rows: list, source: str = "roster", replace: bool = False) -> dict:
    clear_cache()
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


# Preseason projection → this season's own games (commissioner, 2026-10-18; DECISIONS.md "Weekly projections"): every
# game he PLAYS this season moves 1/14 of the weight onto his own games, all of it after 14 games. Weeks passing don't
# count — a player out injured has no new games, so his projection doesn't move. One rule for every projection that
# blends (the week total, the number under each game, the recap's frozen week).
FULL_SEASON_GAMES = 14


def game_cv(curve: dict | None, season_games: list[float]) -> float:
    """His game-to-game spread as a share of his number: the model's (from its curve: best of 2 − best of 1 =
    0.564 SD), moving onto his own games' spread by games played like the level (5+ games). The weekly number and
    the recap's frozen projection both use this."""
    c = (curve or {}).get("e") or []
    cv = (c[1] - c[0]) / 0.5642 / c[0] if len(c) > 1 and c[0] > 0 else 0.35
    w = season_weight(len(season_games))
    own = sum(season_games) / len(season_games) if season_games else 0.0
    if w and len(season_games) >= 5 and own > 0:
        cv = (1 - w) * cv + w * (sum((x - own) ** 2 for x in season_games) / len(season_games)) ** 0.5 / own
    return cv


def season_weight(games_played: int) -> float:
    return min(1.0, max(0, games_played) / FULL_SEASON_GAMES)


def blend(pre: float | None, season_games: list[float]) -> float | None:
    """Per-game number: the preseason PROJ AVG moving onto his own games this season by games played."""
    if not season_games:
        return pre
    own = sum(season_games) / len(season_games)
    if pre is None:
        return own
    w = season_weight(len(season_games))
    return (1 - w) * pre + w * own


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


def team_game_dates(cur, season: str, weeks: list[dict]) -> dict:
    """NBA team → {fantasy week: [game dates]} (scheduled games with both teams known)."""
    cur.execute("""SELECT game_date, home_team, away_team FROM nba_games WHERE season = %s AND game_type = 'regular'
                   AND missing_since IS NULL AND game_date IS NOT NULL AND home_team IS NOT NULL AND away_team IS NOT NULL""", (season,))
    out: dict = {}
    for g in cur.fetchall():
        w = week_for(weeks, g["game_date"])
        if w:
            for t in (g["home_team"], g["away_team"]):
                out.setdefault(t, {}).setdefault(w["week"], []).append(g["game_date"])
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


def week_best(level: float, cv: float, factors: list[float], avail: dict | None, floor: float | None,
              qs: list[float] | None = None) -> float:
    return week_dist(level, cv, factors, avail, floor, qs)[0]


def week_dist(level: float, cv: float, factors: list[float], avail: dict | None, floor: float | None,
              qs: list[float] | None = None) -> tuple[float, float]:
    """Expected best game of the week when each game has its own number (commissioner, 2026-10-18): game i ~
    Normal(level × factor_i, cv × level × factor_i), played with chance q (a zero-game week with chance `zero`, as
    _games_dist), never below `floor` (his best already this week; 0 if none). Two games of 27.1 and 28.1 beat two of 27.6.
    Returns (expected best, its variance) — the variance is how much his week can still swing (the win chance)."""
    f0 = floor if floor is not None else 0.0
    if not factors or level <= 0:
        return f0, 0.0
    z, q = (avail["zero"], avail["q"]) if avail else (0.0, 1.0)
    qs = qs if qs is not None else [q] * len(factors)  # each game's own chance (lineup._chances), else q for all
    ms = [(level * f, max(cv * level * f, 0.01), qi) for f, qi in zip(factors, qs)]
    hi = max(m + 6 * s for m, s, _ in ms)
    if f0 >= hi:
        return f0, 0.0
    n = 400
    step = (hi - f0) / n
    tail = tail2 = 0.0
    for i in range(n):
        t = f0 + (i + 0.5) * step
        cdf = 1.0
        for m, s, qi in ms:
            cdf *= 1 - qi + qi * 0.5 * (1 + erf((t - m) / (s * 1.4142135623730951)))
        tail += (1 - cdf) * step
        tail2 += 2 * t * (1 - cdf) * step       # E[M²] = f0² + ∫ 2t·P(M > t) dt
    m1, m2 = f0 + tail, f0 * f0 + tail2
    mean = z * f0 + (1 - z) * m1
    return mean, max(0.0, z * f0 * f0 + (1 - z) * m2 - mean * mean)


def week_projection(curve: dict, games_by_week: dict, weeks: list[dict], avail: dict | None = None,
                    out_until: date | None = None, dates_by_week: dict | None = None) -> list[dict]:
    """His projected weekly score for each fantasy week: the curve at the number of games he plays, weighted by the
    chance of playing each number (availability) — 0 games = 0. A week that ends before a known injury's return date
    (out_until, current ESPN report) is 0."""
    out = []
    for w in weeks:
        n = games_by_week.get(w["week"], 0)
        if out_until and w["end"] < out_until:
            n_play = 0
        elif out_until and dates_by_week and w["start"] < out_until:
            # the week he's due back: only its games on or after the return date (2026-10-19)
            n_play = sum(1 for d in dates_by_week.get(w["week"], []) if d >= out_until)
        else:
            n_play = n
        dist = _games_dist(n_play, avail) if n_play else [1.0]
        # games = his team's games; can = the ones he's eligible for (0 before an Out player's return, his return
        # week only the games from that date on); plays = how many he's expected to play
        row = {"week": w["week"], "games": n, "can": n_play, "plays": round(sum(k * p for k, p in enumerate(dist)), 2)}
        for key in ("e", "p25", "p90"):
            c = curve[key]
            row[key] = round(sum(p * c[min(k, len(c)) - 1] for k, p in enumerate(dist) if k), 2)
        # "on" = the same week given he isn't out all of it (only his scattered misses inside it): what the draft list
        # and card show as PROJ MAX / low / high; the plain values (with zero weeks) make the season value
        if n_play:
            don = _games_dist(n_play, {**avail, "zero": 0.0}) if avail else dist
            for key in ("e", "p25", "p90"):
                c = curve[key]
                row[key + "_on"] = round(sum(p * c[min(k, len(c)) - 1] for k, p in enumerate(don) if k), 2)
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
    tdates = team_game_dates(cur, season, weeks)
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
        curve = r["proj_week"]
        wp = week_projection(curve, tg[r["nba_team"]], weeks, curve.get("avail"), out_until.get(r["player_id"]),
                             tdates.get(r["nba_team"]))
        # The curve's availability summary follows the weeks: expected games = the games he's expected to play on this
        # schedule (current injuries and return dates included); the injury-free figure stays as games_healthy.
        if curve.get("avail"):
            av = curve["avail"]
            av.setdefault("games_healthy", av.get("games"))
            av["games"] = round(sum(x["plays"] for x in wp), 1)
        cur.execute("UPDATE fantasy_pool SET proj_max = %s, proj_weeks = %s, proj_week = %s WHERE season = %s AND player_id = %s",
                    (round(sum(x["e"] for x in wp) / len(wp), 2), Json(wp), Json(curve), season, r["player_id"]))
        n += 1
    return {"proj_max": n, "weeks": len(weeks)}


def apply_team_schedule(cur, season: str) -> dict:
    """Same as apply_schedule for NBA teams (fantasy_team_pool): each team with a curve gets its per-week projection
    on the season's schedule (a team plays every game), PROJ MAX = the weeks' average, MAX low / high = the weeks'
    average p25 / p90 over the weeks it has games."""
    weeks = season_weeks(cur, season)
    if not weeks:
        return {"teams": 0, "note": f"no schedule loaded for {season}"}
    tg = team_games(cur, season, weeks)
    cur.execute("SELECT team, proj_week FROM fantasy_team_pool WHERE season = %s AND proj_week IS NOT NULL", (season,))
    n = 0
    for r in cur.fetchall():
        if r["team"] not in tg:
            continue
        wp = week_projection(r["proj_week"], tg[r["team"]], weeks)
        played = [x for x in wp if x["games"]]
        cur.execute("""UPDATE fantasy_team_pool SET proj_weeks = %s, proj_max = %s, max_low = %s, max_high = %s
                       WHERE season = %s AND team = %s""",
                    (Json(wp), round(sum(x["e"] for x in wp) / len(wp), 2),
                     round(sum(x["p25"] for x in played) / len(played), 2) if played else None,
                     round(sum(x["p90"] for x in played) / len(played), 2) if played else None, season, r["team"]))
        n += 1
    return {"teams": n, "weeks": len(weeks)}


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


def shown_max(proj_weeks: list | None, season_max: float | None) -> float | None:
    """The PROJ MAX the site shows (draft list, card, player page): his weeks when he isn't out the whole week (the "on"
    values), leaving out weeks a known injury rules him out of. The season value (proj_max column: zero weeks counted)
    is for ranking and the bid guide only."""
    active = [w for w in (proj_weeks or []) if not (w.get("games") and w.get("plays") == 0)]
    if not active:
        return season_max
    return sum(w.get("e_on", w["e"]) for w in active) / len(active)

