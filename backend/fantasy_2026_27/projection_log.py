"""Projection check (commissioner, 2026-10-19): every pool player's (and NBA team's) weekly projection and 1+ Game %,
saved before the week's first game, then what actually happened once the week is over.

Runs on the server in the 3 AM job (backend/nba/scheduler.py, also on every restart): each run saves the current
week if it isn't saved yet and none of its games has started, and fills in every finished week that's still blank.
The numbers saved are the site's own (lineup.week_view: the weekly number, 1+ Game %, the number under each game),
rostered or not. Shown on /projection-check.
"""
from . import engine
from . import scoring as scoring_mod
from .logic import player_points, team_game_points
from .weeks import week_for


def init_schema(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fantasy_projection_log (
            scenario      TEXT NOT NULL,
            week          INTEGER NOT NULL,
            entity_id     TEXT NOT NULL,
            kind          TEXT NOT NULL,             -- player / nba_team
            name          TEXT,
            nba_team      TEXT,
            team_id       TEXT,                      -- fantasy team he was on when saved (NULL = free agent)
            games         INTEGER,                   -- his NBA team's games that week
            projected     DOUBLE PRECISION,          -- the weekly number (best game, or the sum for a sum week)
            play_prob     DOUBLE PRECISION,          -- 1+ Game %
            game_proj     DOUBLE PRECISION,          -- his per-game number
            proj_var      DOUBLE PRECISION,          -- how much the week could swing (variance)
            saved_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            actual        DOUBLE PRECISION,          -- his week as scored (NULL until filled; NULL = no games played)
            actual_games  INTEGER,                   -- games he played
            filled_at     TIMESTAMPTZ,
            PRIMARY KEY (scenario, week, entity_id)
        )
    """)


def _entities(cur, season: str, scenario: str) -> list[dict]:
    """Every pool player with a projection and every NBA team, as week_view entries (slot BENCH: projection only)."""
    from .etch import live_rosters
    owner = {e["id"]: t for t, es in live_rosters(cur, scenario).items() for e in es}
    cur.execute("""SELECT fp.player_id AS id, COALESCE(p.name, fp.name) AS name, fp.position, fp.nba_team
                   FROM fantasy_pool fp LEFT JOIN fantasy_players p ON p.id = fp.player_id
                   WHERE fp.season = %s AND fp.proj_avg IS NOT NULL AND fp.nba_team IS NOT NULL""", (season,))
    out = [{"id": r["id"], "kind": "player", "name": r["name"], "slot": "BENCH", "position": r["position"],
            "nba_team": r["nba_team"], "_owner": owner.get(r["id"])} for r in cur.fetchall()]
    cur.execute("SELECT id, name FROM fantasy_nba_teams")
    out += [{"id": r["id"], "kind": "nba_team", "name": r["name"], "slot": "BENCH", "position": "TEAM", "nba_team": r["id"],
             "_owner": owner.get(r["id"])} for r in cur.fetchall()]
    return out


def save_week(cur, scenario: str) -> int:
    """Save the current week's projections once, before any of its games has started."""
    from .lineup import week_view
    lg = engine.league(cur, scenario)
    today = engine.as_of(lg)
    weeks = engine.weeks_for_league(cur, lg)
    w = week_for(weeks, today) or next((x for x in weeks if x["start"] > today), None)
    if not w or w.get("kind") != "regular":
        return 0
    cur.execute("SELECT 1 FROM fantasy_projection_log WHERE scenario = %s AND week = %s LIMIT 1", (scenario, w["week"]))
    if cur.fetchone():
        return 0
    cur.execute("""SELECT 1 FROM nba_games WHERE season = %s AND game_type = 'regular' AND game_date BETWEEN %s AND %s
                   AND status IN ('live', 'final') LIMIT 1""", (lg["season"], w["start"], w["end"]))
    if cur.fetchone():  # a game already started: the projections aren't pre-game any more
        return 0
    ents = _entities(cur, lg["season"], scenario)
    owner = {e["id"]: e.pop("_owner") for e in ents}
    n = 0
    for i in range(0, len(ents), 100):
        v = week_view(cur, scenario, "", w["week"], injuries=True, entities=ents[i:i + 100])
        for e in v["entries"]:
            cur.execute("""INSERT INTO fantasy_projection_log (scenario, week, entity_id, kind, name, nba_team, team_id, games,
                                                               projected, play_prob, game_proj, proj_var)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                        (scenario, w["week"], e["id"], e["kind"], e["name"], e["nba_team"], owner.get(e["id"]),
                         len(e["games"]), e["projected"], e["play_prob"], e.get("game_proj"), e.get("proj_var")))
            n += 1
    return n


def fill_weeks(cur, scenario: str) -> int:
    """Fill in what happened for every finished week that's still blank: his week as the league scores it."""
    lg = engine.league(cur, scenario)
    today = engine.as_of(lg)
    weeks = {w["week"]: w for w in engine.weeks_for_league(cur, lg)}
    rules = scoring_mod.league_rules(cur, scenario)
    cur.execute("SELECT DISTINCT week FROM fantasy_projection_log WHERE scenario = %s AND filled_at IS NULL", (scenario,))
    n = 0
    for (wk,) in [(r["week"],) for r in cur.fetchall()]:
        w = weeks.get(wk)
        if not w or w["end"] >= today:
            continue
        cur.execute("""SELECT pg.player_id, pg.pts, pg.fgm, pg.fga, pg.fg3m, pg.ftm, pg.fta, pg.oreb, pg.dreb, pg.ast, pg.stl,
                              pg.blk, pg.tov, pg.blkd, pg.clutch_pts
                       FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
                       WHERE g.season = %s AND g.game_type = 'regular' AND g.game_date BETWEEN %s AND %s AND pg.minutes > 0""",
                    (lg["season"], w["start"], w["end"]))
        got: dict = {}
        for r in cur.fetchall():
            got.setdefault(r["player_id"], []).append(player_points(r, rules))
        cur.execute("""SELECT game_id, home_team, away_team, home_score, away_score FROM nba_games
                       WHERE season = %s AND game_type = 'regular' AND status = 'final' AND game_date BETWEEN %s AND %s""",
                    (lg["season"], w["start"], w["end"]))
        tg = cur.fetchall()
        tx = scoring_mod.team_extras(cur, [g["game_id"] for g in tg])
        for g in tg:
            for t, mine, theirs in ((g["home_team"], g["home_score"], g["away_score"]), (g["away_team"], g["away_score"], g["home_score"])):
                got.setdefault(t, []).append(team_game_points(mine > theirs, mine, theirs, rules, tx.get((g["game_id"], t))))
        cur.execute("SELECT entity_id, kind FROM fantasy_projection_log WHERE scenario = %s AND week = %s", (scenario, wk))
        for r in cur.fetchall():
            vals = got.get(r["entity_id"], [])
            side = rules["team" if r["kind"] == "nba_team" else "player"]
            cur.execute("""UPDATE fantasy_projection_log SET actual = %s, actual_games = %s, filled_at = now()
                           WHERE scenario = %s AND week = %s AND entity_id = %s""",
                        (scoring_mod.week_score(side, vals) if vals else None, len(vals), scenario, wk, r["entity_id"]))
            n += 1
    return n


def run(cur, scenario: str = "live") -> dict:
    return {"saved": save_week(cur, scenario), "filled": fill_weeks(cur, scenario)}


def report(cur, scenario: str, week: int | None = None) -> dict:
    """One week's rows plus the checks: average miss, how wide the misses run, and 1+ Game % against who played."""
    cur.execute("SELECT DISTINCT week FROM fantasy_projection_log WHERE scenario = %s ORDER BY week", (scenario,))
    weeks = [r["week"] for r in cur.fetchall()]
    if not weeks:
        return {"weeks": [], "week": None, "rows": [], "summary": None}
    week = week if week in weeks else weeks[-1]
    cur.execute("""SELECT l.*, t.name AS team_name, t.abbreviation AS team_abbr, t.color AS team_color
                   FROM fantasy_projection_log l LEFT JOIN fantasy_teams t ON t.id = l.team_id AND t.scenario = l.scenario
                   WHERE l.scenario = %s AND l.week = %s ORDER BY l.projected DESC NULLS LAST""", (scenario, week))
    rows = [{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dict(r).items()} for r in cur.fetchall()]
    done = [r for r in rows if r["filled_at"] and r["games"]]
    summary = None
    if done:
        scored = [r for r in done if r["projected"] is not None]
        miss = [(r["actual"] or 0.0) - r["projected"] for r in scored]
        sd_proj = [r["proj_var"] ** 0.5 for r in scored if r["proj_var"]]
        bins = []
        for lo, hi in ((0, 0.5), (0.5, 0.8), (0.8, 0.95), (0.95, 1.01)):
            g = [r for r in done if r["play_prob"] is not None and lo <= r["play_prob"] < hi]
            if g:
                bins.append({"from": lo, "to": min(hi, 1.0), "n": len(g), "said": sum(r["play_prob"] for r in g) / len(g),
                             "played": sum(1 for r in g if r["actual_games"]) / len(g)})
        summary = {"n": len(scored), "avg_miss": sum(miss) / len(miss) if miss else None,
                   "avg_abs_miss": sum(abs(x) for x in miss) / len(miss) if miss else None,
                   "miss_spread": (sum(x * x for x in miss) / len(miss)) ** 0.5 if miss else None,
                   "said_spread": (sum(x * x for x in sd_proj) / len(sd_proj)) ** 0.5 if sd_proj else None,
                   "play_bins": bins}
    return {"weeks": weeks, "week": week, "rows": rows, "summary": summary}
