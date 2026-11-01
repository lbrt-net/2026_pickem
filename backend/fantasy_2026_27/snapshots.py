"""Snapshots the weekly recap needs, which can't be rebuilt later (the injury report and projections get overwritten):

- Win probability, daily: each matchup's chance before that day's games (Improbable win's chart). Taken by the 3 AM
  job; the first snapshot of a day is kept, and none is taken once that day's first game has tipped.
- Projections, weekly: frozen when the week starts (Versus projection). Per entity: the per-game mean — the preseason
  PROJ AVG moving onto his games this season by games played (projections.blend, the site's one rule) — and the
  game-to-game spread. The recap scales it by games actually played: proj_for(mean, sd, games).
"""
from datetime import date, datetime, timedelta, timezone

from . import engine, projections, winprob
from . import scoring as scoring_mod
from .logic import player_points, team_game_points
from .weeks import week_for

C_MAX = [0, 0, 0.564, 0.846, 1.029, 1.163, 1.267, 1.352, 1.424, 1.485, 1.539]  # expected max of N normal draws, in SDs


def init_schema(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fantasy_winprob_daily (
            scenario TEXT NOT NULL,
            week     INTEGER NOT NULL,
            asof     DATE NOT NULL,              -- the league's day; the chance before that day's games
            team_a   TEXT NOT NULL,
            team_b   TEXT NOT NULL,
            p        DOUBLE PRECISION NOT NULL,  -- team a's chance
            taken_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (scenario, week, asof, team_a, team_b)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fantasy_proj_week (
            scenario     TEXT NOT NULL,
            week         INTEGER NOT NULL,
            entity_id    TEXT NOT NULL,          -- player id / NBA team tricode
            pre_avg      DOUBLE PRECISION,       -- preseason PROJ AVG per game
            recent_avg   DOUBLE PRECISION,       -- actual per game over the last 8 weeks
            recent_games INTEGER NOT NULL DEFAULT 0,
            game_mean    DOUBLE PRECISION,       -- the blend
            game_sd      DOUBLE PRECISION,
            taken_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (scenario, week, entity_id)
        )
    """)


blend = projections.blend  # the one blend rule (projections.py)


def proj_for(mean: float | None, sd: float | None, games: int) -> float:
    """Projected weekly score (best game of the week) for the games he actually played: 0 games → 0."""
    if not games or mean is None:
        return 0.0
    return round(mean + (sd or 0.35 * mean) * C_MAX[min(games, len(C_MAX) - 1)], 1)


def _today_started(cur, season: str, today) -> bool:
    cur.execute("""SELECT 1 FROM nba_games WHERE season = %s AND game_date = %s AND tipoff_utc IS NOT NULL
                   AND tipoff_utc <= %s LIMIT 1""", (season, today, datetime.now(timezone.utc)))
    return cur.fetchone() is not None


def take_winprob(cur, scenario: str) -> int:
    lg = engine.league(cur, scenario)
    today = engine.as_of(lg)
    if not lg["sim_date"] and _today_started(cur, lg["season"], today):
        return 0
    wp = winprob.week_probs(cur, scenario)
    if not wp["week"] or wp["week"].get("kind") != "regular":
        return 0
    for m in wp["matchups"]:
        cur.execute("""INSERT INTO fantasy_winprob_daily (scenario, week, asof, team_a, team_b, p) VALUES (%s, %s, %s, %s, %s, %s)
                       ON CONFLICT DO NOTHING""", (scenario, wp["week"]["week"], today, m["a"], m["b"], m["p"]))
    return len(wp["matchups"])


def _report_at(cur, cutoff) -> list[dict]:
    """The injury report as it stood at `cutoff`: today's report with every logged change since undone, newest first.
    The log starts 2026-10-30, so anything earlier reads as the report just before its first entry."""
    cur.execute("SELECT player_id, espn_id, name, team, status, short, injury, return_date, reported_at FROM nba_injuries")
    rep = {r["player_id"] or r["name"]: dict(r) for r in cur.fetchall()}
    cur.execute("SELECT * FROM nba_injury_events WHERE at > %s ORDER BY at DESC, id DESC", (cutoff,))
    for e in cur.fetchall():
        k = e["player_id"] or e["name"]
        if e["kind"] == "listed":
            rep.pop(k, None)
        elif e["kind"] == "cleared" or k not in rep:
            rep[k] = {"player_id": e["player_id"], "espn_id": e["espn_id"], "name": e["name"], "team": e["team"],
                      "status": e["prev_status"], "short": None, "injury": e["injury"], "return_date": e["prev_return"],
                      "reported_at": None}
        else:
            rep[k]["status"], rep[k]["return_date"] = e["prev_status"], e["prev_return"]
    for r in rep.values():
        if r["status"] and not r["short"]:
            r["short"] = "GTD" if r["status"] == "Day-To-Day" else "OUT"
    return [r for r in rep.values() if r["status"]]


def rebuild_winprob(cur, scenario: str, day: date, save: bool = True, detail: dict | None = None) -> list[dict]:
    """A missed day's snapshot, rebuilt (2026-11-01): the league's clock set to the night before (every game through
    then played, that day's still to come), the injury report as it stood at 3 AM Central that day, each team's
    lineup for the week — then put back exactly as it was (savepoint). Never a week's first day (the clock would sit
    in the week before). save: stored like the 3 AM job's (an existing snapshot is kept)."""
    from backend.config import CENTRAL
    from .lineup import week_view
    from .engine import matchup_overrides, week_pairings
    lg = engine.league(cur, scenario)
    w = week_for(engine.weeks_for_league(cur, lg), day)
    if not w or w["kind"] != "regular" or day <= w["start"]:
        raise ValueError(f"{day}: not a regular week's second day or later")
    report = _report_at(cur, datetime.combine(day, datetime.min.time().replace(hour=3), CENTRAL))
    cur.execute("SAVEPOINT rebuild")
    try:
        cur.execute("UPDATE fantasy_leagues SET sim_date = %s WHERE scenario = %s", (day - timedelta(days=1), scenario))
        cur.execute("DELETE FROM nba_injuries")
        for r in report:
            cur.execute("""INSERT INTO nba_injuries (player_id, espn_id, name, team, status, short, injury, return_date, reported_at)
                           VALUES (%(player_id)s, %(espn_id)s, %(name)s, %(team)s, %(status)s, %(short)s, %(injury)s,
                                   %(return_date)s, %(reported_at)s)""", r)
        cur.execute("SELECT id, name FROM fantasy_teams WHERE scenario = %s", (scenario,))
        teams = [dict(t) for t in cur.fetchall()]
        views = {}
        for t in teams:
            v = week_view(cur, scenario, t["id"], w["week"], injuries=True)
            views[t["id"]] = [(e["projected"] or e["week_score"] or 0.0, e.get("proj_var") or 0.0) for e in v["entries"]
                              if e.get("slot") not in ("BENCH", "IR")]
            if detail is not None:
                detail[t["id"]] = [(e["name"], e.get("slot"), e["projected"], e["week_score"], e.get("games_left"),
                                    (e.get("injury") or {}).get("status")) for e in v["entries"]]
        out = [{"a": a["id"], "b": b["id"], "p": round(winprob.formula(views[a["id"]], views[b["id"]]), 3)}
               for a, b in week_pairings(teams, w["week"], matchup_overrides(cur, scenario))]
    finally:
        cur.execute("ROLLBACK TO SAVEPOINT rebuild")
        cur.execute("RELEASE SAVEPOINT rebuild")
    if save:
        for m in out:
            cur.execute("""INSERT INTO fantasy_winprob_daily (scenario, week, asof, team_a, team_b, p) VALUES (%s, %s, %s, %s, %s, %s)
                           ON CONFLICT DO NOTHING""", (scenario, w["week"], day, m["a"], m["b"], m["p"]))
    return out


def drop_misfiled(cur, scenario: str) -> int:
    """Snapshots filed under a week they aren't in (before 2026-11-01 the job took next week's once starters locked)."""
    lg = engine.league(cur, scenario)
    n = 0
    for w in engine.weeks_for_league(cur, lg):
        cur.execute("DELETE FROM fantasy_winprob_daily WHERE scenario = %s AND week = %s AND (asof < %s OR asof > %s)",
                    (scenario, w["week"], w["start"], w["end"]))
        n += cur.rowcount
    return n


def _game_scores(cur, season: str, lo, hi, rules) -> dict:
    """entity id → fantasy points of each game played between lo and hi (players and NBA teams)."""
    out = {}
    cur.execute("""
        SELECT pg.player_id, pg.pts, pg.fgm, pg.fga, pg.fg3m, pg.ftm, pg.fta, pg.oreb, pg.dreb, pg.ast, pg.stl, pg.blk,
               pg.tov, pg.blkd, pg.clutch_pts
        FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
        WHERE pg.season = %s AND g.game_type = 'regular' AND pg.minutes > 0 AND g.game_date BETWEEN %s AND %s
    """, (season, lo, hi))
    for r in cur.fetchall():
        out.setdefault(r["player_id"], []).append(player_points(r, rules))
    cur.execute("""
        SELECT game_id, home_team, away_team, home_score, away_score FROM nba_games
        WHERE season = %s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL AND game_date BETWEEN %s AND %s
    """, (season, lo, hi))
    games = cur.fetchall()
    tx = scoring_mod.team_extras(cur, [g["game_id"] for g in games])
    for g in games:
        for t, mine, theirs in ((g["home_team"], g["home_score"], g["away_score"]), (g["away_team"], g["away_score"], g["home_score"])):
            out.setdefault(t, []).append(team_game_points(mine > theirs, mine, theirs, rules, tx.get((g["game_id"], t))))
    return out


def _spread_scores(cur, season: str, since, before, rules) -> dict:
    """entity id → fantasy points of each game from `since` (the 20-week swing window; None = this season only) up to
    the day before `before`, this season's and last season's (players and NBA teams)."""
    hi = before - timedelta(days=1)
    out = _game_scores(cur, season, since or date(1900, 1, 1), hi, rules)
    if since:
        for k, v in _game_scores(cur, engine._prev_season(season), since, hi, rules).items():
            out[k] = v + out.get(k, [])
    return out


def take_proj(cur, scenario: str) -> int:
    """Freeze this week's projections once, on or after the week's first day (the 3 AM run: before its games)."""
    lg = engine.league(cur, scenario)
    today = engine.as_of(lg)
    weeks = engine.weeks_for_league(cur, lg)
    w = week_for(weeks, today)
    if not w or w.get("kind") != "regular":
        return 0
    cur.execute("SELECT 1 FROM fantasy_proj_week WHERE scenario = %s AND week = %s LIMIT 1", (scenario, w["week"]))
    if cur.fetchone():
        return 0
    season = lg["season"]
    rules = scoring_mod.league_rules(cur, scenario)
    past = [x for x in weeks if x["end"] < w["start"] and x.get("kind") == "regular"][-projections.RECENT_WEEKS:]  # last 4 weeks
    recent = _game_scores(cur, season, past[0]["start"], past[-1]["end"], rules) if past else {}
    spread = _spread_scores(cur, season, projections.spread_since(cur, season, weeks, today), w["start"], rules)
    cur.execute("SELECT player_id AS id, proj_avg, proj_week FROM fantasy_pool WHERE season = %s", (season,))
    rows = cur.fetchall()
    pre = {r["id"]: r["proj_avg"] for r in rows}
    curve = {r["id"]: r["proj_week"] for r in rows}
    cur.execute("SELECT team AS id, proj_avg, proj_week FROM fantasy_team_pool WHERE season = %s", (season,))
    rows = cur.fetchall()
    pre.update({r["id"]: r["proj_avg"] for r in rows})
    curve.update({r["id"]: r["proj_week"] for r in rows})
    n = 0
    for eid in set(pre) | set(recent):
        games = recent.get(eid, [])
        mean = blend(pre.get(eid), games)
        if mean is None:
            continue
        sd = projections.game_cv(curve.get(eid), spread.get(eid, [])) * mean  # his swing: last 20 weeks (projections.game_cv)
        cur.execute("""INSERT INTO fantasy_proj_week (scenario, week, entity_id, pre_avg, recent_avg, recent_games, game_mean, game_sd)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                    (scenario, w["week"], eid, pre.get(eid), (sum(games) / len(games)) if games else None, len(games),
                     round(mean, 3), round(sd, 3)))
        n += 1
    return n


def take_all(cur) -> dict:
    """Both snapshots for every league; each league on its own so one failure doesn't stop the rest."""
    cur.execute("SELECT scenario FROM fantasy_leagues")
    out = {}
    for (scenario,) in [(r["scenario"],) for r in cur.fetchall()]:
        try:
            cur.execute("SAVEPOINT snap")
            out[scenario] = {"winprob": take_winprob(cur, scenario), "proj": take_proj(cur, scenario)}
            cur.execute("RELEASE SAVEPOINT snap")
        except Exception as ex:  # noqa: BLE001 — logged by the caller, the next league still runs
            cur.execute("ROLLBACK TO SAVEPOINT snap")
            out[scenario] = {"error": str(ex)[:200]}
    return out
