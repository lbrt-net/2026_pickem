"""Opponent, home and rest → one game's number (commissioner, 2026-10-18; PROJECTIONS.md "Opponent, home/away and rest").

A player's number for one game = his per-game projection (projections.blend) × this game's factor, from the backtest
'23–'25 → '26 (scripts/projection_study/opp_effect.py, every effect the same direction all four seasons):
  - opponent's defensive rating, pace and net rating (from box scores: possessions = FGA + 0.44·FTA − OREB + TOV, both
    teams averaged, per 48 minutes). Every team starts at the league average (no effect) and moves onto its own games,
    1/14 per game it has played — last season isn't used;
  - home or away, and the opponent playing yesterday: known from the schedule, full effect from day 1.
The factors average 1.0, so they move single games, not a player's level. Players only: an NBA team's score is its own
result, which this study didn't cover.
"""
import time
from datetime import timedelta

from . import projections

DRTG = 0.00886      # per point of opponent defensive rating above average (softer defense → more)
PACE = 0.00870      # per possession of opponent pace above average
NET = -0.00225      # per point of opponent net rating above average (stronger team → blowouts → fewer minutes)
HOME = 0.0296       # home vs away: +half at home, −half away
OPP_B2B = 0.0225    # the opponent played yesterday
B2B_SHARE = 0.173   # how often the opponent is on a back-to-back (so the average game stays 1.0)

_CACHE: dict = {}
TTL = 3600


def _team_games(cur, season: str, upto) -> dict:
    """team -> [(drtg, pace, net)] per game this season up to `upto`, date order."""
    cur.execute("""
        SELECT pg.game_id, g.game_date, pg.team, SUM(pg.pts) AS pts, SUM(pg.fga) AS fga, SUM(pg.fta) AS fta,
               SUM(pg.oreb) AS oreb, SUM(pg.tov) AS tov, SUM(pg.minutes) AS mins
        FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
        WHERE pg.season = %s AND g.game_type = 'regular' AND g.game_date <= %s
        GROUP BY pg.game_id, g.game_date, pg.team
    """, (season, upto))
    by_game: dict = {}
    for r in cur.fetchall():
        by_game.setdefault((r["game_date"], r["game_id"]), []).append(r)
    out: dict = {}
    for _, sides in sorted(by_game.items()):
        if len(sides) != 2:
            continue
        a, b = sides
        poss = sum(float(t["fga"] + 0.44 * t["fta"] - t["oreb"] + t["tov"]) for t in (a, b)) / 2
        if poss <= 0:
            continue
        for t, o in ((a, b), (b, a)):
            pace = poss * 48 / max(float(t["mins"] or 0) / 5, 48)
            out.setdefault(t["team"], []).append((100 * o["pts"] / poss, pace, 100 * (t["pts"] - o["pts"]) / poss))
    return out


def table(cur, season: str, today) -> dict:
    """Everything factor() needs for games after `today`; cached an hour per season / day."""
    key = (season, today)
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    games = _team_games(cur, season, today)
    allg = [x for gs in games.values() for x in gs]
    lg = tuple(sum(x[i] for x in allg) / len(allg) for i in range(3)) if allg else None
    rating = {t: tuple(projections.blend(lg[i], [x[i] for x in gs]) for i in range(3)) for t, gs in games.items()} if lg else {}
    cur.execute("SELECT home_team, away_team, game_date FROM nba_games WHERE season = %s AND game_type = 'regular' "
                "AND missing_since IS NULL", (season,))
    dates: dict = {}
    for g in cur.fetchall():
        for t in (g["home_team"], g["away_team"]):
            dates.setdefault(t, set()).add(g["game_date"])
    tbl = {"rating": rating, "lg": lg, "dates": dates}
    if len(_CACHE) > 20:
        _CACHE.clear()
    _CACHE[key] = (time.time(), tbl)
    return tbl


def factor(tbl: dict | None, opp: str, home: bool, game_date) -> float:
    if not tbl:
        return 1.0
    f = 1.0 + HOME * ((1 if home else 0) - 0.5)
    f += OPP_B2B * ((1 if game_date - timedelta(days=1) in tbl["dates"].get(opp, ()) else 0) - B2B_SHARE)
    r, lg = tbl["rating"].get(opp), tbl["lg"]
    if r and lg:
        f += DRTG * (r[0] - lg[0]) + PACE * (r[1] - lg[1]) + NET * (r[2] - lg[2])
    return f
