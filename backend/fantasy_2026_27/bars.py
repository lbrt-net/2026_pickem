"""Roster's stat bar (GET /team/{id}/bars): for each listed player / NBA team, his typical weekly best game broken down
by scoring category, for one view.

- A week here is a real Mon–Sun calendar week (not a matchup period). Each week's score = his best single game that
  week; the bar = the average of those best games' category points over the weeks he played, and `score` = their
  average total.
- view=actual, window: season = every game of this league season through today; w1 = last week, w4 / w6 = the last
  4 / 6 full weeks — never the week in progress.
- view=<past season> ("2025-26" …): every regular-season game of that season.
- view=proj: the preseason projection (fantasy_pool / fantasy_team_pool PROJ MAX) split by category in the shares of
  his last season's weekly best games (this season's when he has none); no history = total only, no parts.
Uses the league's own scoring rules.
"""
from datetime import timedelta

from .engine import _prev_season, as_of, league
from . import scoring as scoring_mod
from .history import HISTORY_SEASONS

WINDOWS = ("w1", "w4", "w6", "season")
_PLAYER_COLS = "pg.player_id, pg.game_id, g.game_date, pg.pts, pg.fgm, pg.fga, pg.fg3m, pg.ftm, pg.fta, pg.oreb, pg.dreb, pg.ast, pg.stl, pg.blk, pg.tov, pg.blkd, pg.clutch_pts"


def _monday(d):
    return d - timedelta(days=d.weekday())


def _games(cur, season, ids, rules, lo=None, hi=None):
    """{entity id: [(date, total, breakdown)]} — players' box scores (played minutes) and NBA teams' final games."""
    pids = [i for i in ids if not i.isalpha()]
    tris = [i for i in ids if i.isalpha()]
    out = {}
    if pids:
        cur.execute(f"""SELECT {_PLAYER_COLS} FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
                        WHERE pg.season = %s AND g.game_type = 'regular' AND pg.minutes > 0 AND pg.player_id = ANY(%s::text[])
                          AND (%s::date IS NULL OR g.game_date >= %s) AND (%s::date IS NULL OR g.game_date <= %s)""",
                    (season, pids, lo, lo, hi, hi))
        for r in cur.fetchall():
            res = scoring_mod.score_game(rules["player"], scoring_mod.player_line(r))
            out.setdefault(r["player_id"], []).append((r["game_date"], res["total"], res["breakdown"]))
    if tris:
        cur.execute("""SELECT game_id, game_date, home_team, away_team, home_score, away_score FROM nba_games
                       WHERE season = %s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL
                         AND (home_team = ANY(%s::text[]) OR away_team = ANY(%s::text[]))
                         AND (%s::date IS NULL OR game_date >= %s) AND (%s::date IS NULL OR game_date <= %s)""",
                    (season, tris, tris, lo, lo, hi, hi))
        gs = cur.fetchall()
        ex = scoring_mod.team_extras(cur, [g["game_id"] for g in gs])
        for g in gs:
            for t, mine, theirs in ((g["home_team"], g["home_score"], g["away_score"]), (g["away_team"], g["away_score"], g["home_score"])):
                if t in tris and mine is not None:
                    res = scoring_mod.score_game(rules["team"], scoring_mod.team_line(mine, theirs, ex.get((g["game_id"], t))))
                    out.setdefault(t, []).append((g["game_date"], res["total"], res["breakdown"]))
    return out


def _weekly(games):
    """Average of his weekly best games: (score, weeks, {component: points})."""
    best = {}
    for d, total, bd in games:
        k = _monday(d)
        if k not in best or total > best[k][0]:
            best[k] = (total, bd)
    if not best:
        return None, 0, {}
    n = len(best)
    parts = {}
    for _, bd in best.values():
        for c, v in bd.items():
            parts[c] = parts.get(c, 0.0) + v
    return sum(t for t, _ in best.values()) / n, n, {c: v / n for c, v in parts.items()}


def bars(cur, scenario: str, ids: list[str], view: str, window: str = "season") -> dict:
    lg = league(cur, scenario)
    season, today = lg["season"], as_of(lg)
    rules = scoring_mod.league_rules(cur, scenario)
    labels = {**{c["id"]: c["label"] for c in rules["player"]["components"]}, **{c["id"]: c["label"] for c in rules["team"]["components"]}}
    ids = [i for i in dict.fromkeys(ids) if i][:40]
    this_mon = _monday(today)
    if view == "actual":
        if window not in WINDOWS:
            raise ValueError("window must be one of " + ", ".join(WINDOWS))
        lo, hi = {"w1": (this_mon - timedelta(7), this_mon - timedelta(1)),
                  "w4": (this_mon - timedelta(28), this_mon - timedelta(1)), "w6": (this_mon - timedelta(42), this_mon - timedelta(1)),
                  "season": (None, today)}[window]
        stats = {i: _weekly(gs) for i, gs in _games(cur, season, ids, rules, lo, hi).items()}
        label = window
    elif view in HISTORY_SEASONS:
        stats = {i: _weekly(gs) for i, gs in _games(cur, view, ids, rules).items()}
        label = view
    elif view == "proj":
        prev = {i: _weekly(gs) for i, gs in _games(cur, _prev_season(season), ids, rules).items()}
        now = {i: _weekly(gs) for i, gs in _games(cur, season, [i for i in ids if i not in prev], rules, None, today).items()}
        cur.execute("SELECT player_id AS id, proj_max FROM fantasy_pool WHERE season = %s AND player_id = ANY(%s::text[])", (season, ids))
        pm = {r["id"]: r["proj_max"] for r in cur.fetchall()}
        cur.execute("SELECT team AS id, proj_max FROM fantasy_team_pool WHERE season = %s AND team = ANY(%s::text[])", (season, ids))
        pm.update({r["id"]: r["proj_max"] for r in cur.fetchall()})
        stats = {}
        for i in ids:
            if pm.get(i) is None:
                continue
            base = prev.get(i) or now.get(i)
            if base and base[0]:
                k = pm[i] / base[0]
                stats[i] = (pm[i], 0, {c: v * k for c, v in base[2].items()})
            else:
                stats[i] = (pm[i], 0, {})
        label = "proj"
    else:
        raise ValueError("view must be 'actual', 'proj' or one of " + ", ".join(HISTORY_SEASONS))
    out = {}
    for i, (score, n, parts) in stats.items():
        if score is None:
            continue
        ps = [{"label": labels.get(c, c), "points": round(v, 1)} for c, v in parts.items() if c != "blkd" and round(v, 1) != 0]
        ps.sort(key=lambda p: (p["points"] < 0, -abs(p["points"])))
        out[i] = {"score": round(score, 1), "weeks": n, "parts": ps}
    return {"view": label, "season": season, "entities": out}
