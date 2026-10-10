"""What each player's weekly score actually was in past seasons (fantasy_history).

A player's weekly score is his best single game in a fantasy week. Weeks are laid out with the league's
default rules (weeks.py): Monday–Sunday, the All-Star week fused with the next one, the season ending at
the tankathon cutoff, the last periods being the playoffs (a 2-week final) — so a fused 2-week period is one
week with one best game, and games after the cutoff don't count. Regular-season games he played
(minutes > 0), league scoring including own shots blocked (nba_player_games.blkd).

Per player-season: games, FP per game, weeks played, average weekly max, the average breakdown of his
best game by scoring category, and his weeks split by how many games he played in them (with the
average max for each). Built from the stored box scores and kept in fantasy_history; rebuild with
POST /fantasy/2026_27/admin/history/build.
"""
from psycopg2.extras import Json

from .logic import SCORING_RULES, score_breakdown
from . import scoring as scoring_mod
from .weeks import season_weeks, week_for

HISTORY_SEASONS = ("2022-23", "2023-24", "2024-25", "2025-26")
CATS = [k for k, _, _ in SCORING_RULES]
TEAM_CATS = [c["id"] for c in scoring_mod.DEFAULT["team"]["components"]]


def build(cur, season: str) -> dict:
    weeks = season_weeks(cur, season)  # the league's default rules
    if not weeks:
        raise ValueError(f"no schedule loaded for {season}")
    cur.execute("""
        SELECT pg.player_id, pg.player_name, pg.team, g.game_date, pg.pts, pg.fgm, pg.fga, pg.fg3m, pg.ftm, pg.fta,
               pg.oreb, pg.dreb, pg.ast, pg.stl, pg.blk, pg.tov, pg.blkd, pg.clutch_pts
        FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
        WHERE pg.season = %s AND g.game_type = 'regular' AND pg.minutes > 0 AND g.game_date BETWEEN %s AND %s
        ORDER BY g.game_date
    """, (season, weeks[0]["start"], weeks[-1]["end"]))
    players = {}  # player_id -> {"name", "team", "weeks": {week: [(fp, breakdown)]}}
    for r in cur.fetchall():
        w = week_for(weeks, r["game_date"])
        if not w:
            continue
        bd = score_breakdown(r)
        p = players.setdefault(r["player_id"], {"name": r["player_name"], "team": r["team"], "weeks": {}})
        p["name"], p["team"] = r["player_name"], r["team"]  # last game's
        p["weeks"].setdefault(w["week"], []).append((round(sum(bd.values()), 1), bd))

    cur.execute("DELETE FROM fantasy_history WHERE season = %s", (season,))
    for pid, p in players.items():
        games = [g for gs in p["weeks"].values() for g in gs]
        bests = {wk: max(gs, key=lambda g: g[0]) for wk, gs in p["weeks"].items()}
        by_games = {}
        for wk, gs in p["weeks"].items():
            b = by_games.setdefault(len(gs), [])
            b.append(bests[wk][0])
        data = {
            "season": season, "team": p["team"], "games": len(games),
            "fp_per_game": round(sum(g[0] for g in games) / len(games), 2),
            "weeks_played": len(bests), "weeks_in_season": len(weeks),
            "avg_max": round(sum(b[0] for b in bests.values()) / len(bests), 2),
            "max_breakdown": {c: round(sum(b[1][c] for b in bests.values()) / len(bests), 2) for c in CATS},
            "by_games": [{"games": n, "weeks": len(v), "avg_max": round(sum(v) / len(v), 2)} for n, v in sorted(by_games.items())],
            "weeks": [{"week": wk, "games": len(p["weeks"][wk]), "max": bests[wk][0]} for wk in sorted(bests)],
        }
        cur.execute("INSERT INTO fantasy_history (season, player_id, name, data) VALUES (%s, %s, %s, %s)",
                    (season, pid, p["name"], Json(data)))
    teams = _build_teams(cur, season, weeks)
    # Stamp which rules this history was scored with, so the check-up (health.py) can say when it's out of date.
    cur.execute("""INSERT INTO fantasy_history_builds (season, version) VALUES (%s, %s)
                   ON CONFLICT (season) DO UPDATE SET version = EXCLUDED.version, built_at = now()""",
                (season, scoring_mod.DEFAULT["version"]))
    return {"season": season, "weeks": len(weeks), "players": len(players), "teams": teams}


def _build_teams(cur, season: str, weeks: list[dict]) -> int:
    """NBA teams' seasons under the default team rules (TEAM draft 6): stored like players' (keyed by tricode),
    MAX = the week's score by the team week mode. Needs nba_team_game_stats for the defensive parts."""
    side = scoring_mod.DEFAULT["team"]
    cur.execute("""
        SELECT game_id, game_date, home_team, away_team, home_score, away_score FROM nba_games
        WHERE season = %s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL
          AND game_date BETWEEN %s AND %s
    """, (season, weeks[0]["start"], weeks[-1]["end"]))
    games = cur.fetchall()
    extras = scoring_mod.team_extras(cur, [g["game_id"] for g in games])
    teams = {}
    for g in games:
        w = week_for(weeks, g["game_date"])
        if not w:
            continue
        for t, mine, theirs in ((g["home_team"], g["home_score"], g["away_score"]), (g["away_team"], g["away_score"], g["home_score"])):
            sc = scoring_mod.score_game(side, scoring_mod.team_line(mine, theirs, extras.get((g["game_id"], t))))
            teams.setdefault(t, {}).setdefault(w["week"], []).append((sc["total"], sc["breakdown"]))
    for t, wks in teams.items():
        games_ = [x for gs in wks.values() for x in gs]
        week_max = {wk: scoring_mod.week_score(side, [x[0] for x in gs]) for wk, gs in wks.items()}
        pick = {wk: (max(gs, key=lambda x: x[0]) if side["week"] == "best_game" else None) for wk, gs in wks.items()}
        by_games = {}
        for wk, gs in wks.items():
            by_games.setdefault(len(gs), []).append(week_max[wk])
        bd_weeks = [pick[wk][1] for wk in wks if pick[wk]] or [x[1] for x in games_]
        data = {
            "season": season, "team": t, "games": len(games_),
            "fp_per_game": round(sum(x[0] for x in games_) / len(games_), 2),
            "weeks_played": len(wks), "weeks_in_season": len(weeks),
            "avg_max": round(sum(week_max.values()) / len(week_max), 2),
            "max_breakdown": {c: round(sum(b.get(c, 0) for b in bd_weeks) / len(bd_weeks), 2) for c in TEAM_CATS},
            "by_games": [{"games": n, "weeks": len(v), "avg_max": round(sum(v) / len(v), 2)} for n, v in sorted(by_games.items())],
            "weeks": [{"week": wk, "games": len(wks[wk]), "max": week_max[wk]} for wk in sorted(wks)],
        }
        cur.execute("INSERT INTO fantasy_history (season, player_id, name, data) VALUES (%s, %s, %s, %s)", (season, t, t, Json(data)))
    return len(teams)


def for_player(cur, player_id: str) -> list[dict]:
    """His seasons, oldest first (only seasons he played in)."""
    cur.execute("SELECT data FROM fantasy_history WHERE player_id = %s ORDER BY season", (player_id,))
    return [r["data"] for r in cur.fetchall()]


def season_summary(cur, season: str) -> dict:
    """player_id → {avg_max, fp_per_game, games, weeks_played} for one season (no week lists)."""
    cur.execute("""
        SELECT player_id, data->'avg_max' AS avg_max, data->'fp_per_game' AS fp_per_game, data->'games' AS games,
               data->'weeks_played' AS weeks_played
        FROM fantasy_history WHERE season = %s
    """, (season,))
    return {r["player_id"]: {k: r[k] for k in ("avg_max", "fp_per_game", "games", "weeks_played")} for r in cur.fetchall()}
