"""The draft list's numbers for one view (GET /players/board): every player's MAX, AVG, GP, MAX low /
MAX high and rank, either projected (the league season's pool) or actual (a past season's history).

- Projected: MAX = PROJ MAX, AVG = PROJ AVG, GP = expected games played scaled to 82; MAX low / high = his projected bad week (p25) / big week (p90)
  averaged over the weeks he has games. NBA teams from fantasy_team_pool. Rank by PROJ MAX (else PROJ AVG), like
  the draft. (Past seasons include NBA teams too: history.py stores them by tricode.)
- A past season ("2025-26" …): TOTAL = his weekly maxes added up over the season, MAX = average weekly max,
  AVG = FP per game, GP = games; MAX low / high = the 25th / 90th percentile of his actual weekly maxes.
  Rank by TOTAL (it rewards the weeks he actually showed up for).
"""
from . import projections
from .history import HISTORY_SEASONS


def _pct(vals: list[float], q: float) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    i = (len(s) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


def _r(v):
    return None if v is None else round(float(v), 1)


def board(cur, scenario: str, view: str) -> dict:
    if view == "proj":
        season = projections.league_season(cur, scenario)
        cur.execute("""SELECT player_id, proj_avg, proj_max, proj_weeks FROM fantasy_pool
                       WHERE season = %s AND (proj_avg IS NOT NULL OR proj_max IS NOT NULL)""", (season,))
        rows = {}
        for r in cur.fetchall():
            wk = [w for w in (r["proj_weeks"] or []) if w.get("games")]
            sched = sum(w.get("games") or 0 for w in (r["proj_weeks"] or []))
            plays = sum(w.get("plays") or 0 for w in (r["proj_weeks"] or []) if w.get("plays") is not None)
            has_plays = any(w.get("plays") is not None for w in (r["proj_weeks"] or []))
            rows[r["player_id"]] = {
                "max": _r(r["proj_max"]), "avg": _r(r["proj_avg"]),
                # expected games played, scaled to a full 82 (the fantasy season stops before the NBA's does)
                "gp": _r(plays / sched * 82) if sched and has_plays else None,
                "max_low": _r(sum(w["p25"] for w in wk) / len(wk)) if wk else None,
                "max_high": _r(sum(w["p90"] for w in wk) / len(wk)) if wk else None,
            }
        # NBA teams: their TEAM projections (fantasy_team_pool), ranked alongside the players
        cur.execute("SELECT team, proj_avg, proj_max, max_low, max_high FROM fantasy_team_pool WHERE season = %s", (season,))
        for r in cur.fetchall():
            rows[r["team"]] = {"max": _r(r["proj_max"]), "avg": _r(r["proj_avg"]), "gp": 82.0,  # an NBA team plays every game
                               "max_low": _r(r["max_low"]), "max_high": _r(r["max_high"])}
        key = lambda pid: rows[pid]["max"] if rows[pid]["max"] is not None else (rows[pid]["avg"] or 0)
    elif view in HISTORY_SEASONS:
        season = view
        cur.execute("SELECT player_id, data FROM fantasy_history WHERE season = %s", (season,))
        rows = {}
        for r in cur.fetchall():
            d = r["data"]
            maxes = [w["max"] for w in d.get("weeks", [])]
            rows[r["player_id"]] = {"total": _r(sum(maxes)), "max": _r(d.get("avg_max")), "avg": _r(d.get("fp_per_game")), "gp": d.get("games"),
                                    "max_low": _r(_pct(maxes, 0.25)), "max_high": _r(_pct(maxes, 0.9))}
        key = lambda pid: rows[pid]["total"] or 0
    else:
        raise ValueError("view must be 'proj' or one of " + ", ".join(HISTORY_SEASONS))
    for n, pid in enumerate(sorted(rows, key=key, reverse=True), 1):
        rows[pid]["rank"] = n
    return {"view": view, "season": season, "players": rows}


def actual(cur, scenario: str, window: str) -> dict:
    """This league season's real numbers so far (GET /players/actual), for one window: season, d14 / d28 (the last
    14 / 28 days up to the league's date) or w6 (the last 6 fantasy weeks that have begun). Per entity: MAX = average
    weekly score over the weeks he played in the window, AVG = FP per game, GP, TOTAL = weekly scores added up,
    weeks = {week no: score} (w6 only). Rank by MAX. NBA teams included, scored by the league's TEAM rules."""
    from datetime import timedelta
    from .engine import as_of, league, weeks_for_league
    from .logic import player_points, team_game_points
    from .scoring import league_rules, team_extras, week_score
    from .weeks import week_for

    lg = league(cur, scenario)
    season, today = lg["season"], as_of(lg)
    weeks = weeks_for_league(cur, lg)
    begun = [w for w in weeks if w["start"] <= today]
    if window == "season":
        start = begun[0]["start"] if begun else today
    elif window in ("d14", "d28"):
        start = today - timedelta(days=(14 if window == "d14" else 28) - 1)
    elif window == "w6":
        start = begun[-6:][0]["start"] if begun else today
    else:
        raise ValueError("window must be season, d14, d28 or w6")
    rules = league_rules(cur, scenario)
    per = {}  # entity id -> {week no: [points]}
    cur.execute("""
        SELECT pg.player_id, g.game_date, pg.pts, pg.fgm, pg.fga, pg.fg3m, pg.ftm, pg.fta, pg.oreb, pg.dreb,
               pg.ast, pg.stl, pg.blk, pg.tov, pg.blkd, pg.clutch_pts
        FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
        WHERE pg.season = %s AND g.game_type = 'regular' AND pg.minutes > 0 AND g.game_date BETWEEN %s AND %s
    """, (season, start, today))
    for r in cur.fetchall():
        w = week_for(weeks, r["game_date"])
        if w:
            per.setdefault(r["player_id"], {}).setdefault(w["week"], []).append(player_points(r, rules))
    cur.execute("""
        SELECT game_id, game_date, home_team, away_team, home_score, away_score FROM nba_games
        WHERE season = %s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL
          AND game_date BETWEEN %s AND %s
    """, (season, start, today))
    tg = cur.fetchall()
    tx = team_extras(cur, [g["game_id"] for g in tg])
    teams = set()
    for g in tg:
        w = week_for(weeks, g["game_date"])
        if not w or g["home_score"] is None:
            continue
        for t, mine, theirs in ((g["home_team"], g["home_score"], g["away_score"]), (g["away_team"], g["away_score"], g["home_score"])):
            teams.add(t)
            per.setdefault(t, {}).setdefault(w["week"], []).append(team_game_points(mine > theirs, mine, theirs, rules, tx.get((g["game_id"], t))))
    rows = {}
    for eid, wk in per.items():
        side = rules["team" if eid in teams else "player"]
        scores = {n: week_score(side, v) or 0.0 for n, v in wk.items()}
        games = [p for v in wk.values() for p in v]
        rows[eid] = {"max": _r(sum(scores.values()) / len(scores)), "avg": _r(sum(games) / len(games)), "gp": len(games),
                     "total": _r(sum(scores.values()))}
        if window == "w6":
            rows[eid]["weeks"] = {str(n): _r(s) for n, s in scores.items()}
    for n, eid in enumerate(sorted(rows, key=lambda e: rows[e]["max"] or 0, reverse=True), 1):
        rows[eid]["rank"] = n
    return {"window": window, "season": season, "as_of": today.isoformat(), "start": start.isoformat(),
            "weeks": [w["week"] for w in begun[-6:]] if window == "w6" else [], "players": rows}
