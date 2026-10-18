"""One truth per fact (2026-10-18, after draft night's mismatches). See DATA.md.

A player's position and NBA team live in two tables: the season pool (fantasy_pool — the truth, what every page
shows) and fantasy_players (read by rosters, seating, lineups, the transaction log, trades). `sync` makes the second
match the first, and is run everywhere either can change: app startup, after any pool load / rebuild, and every night.

NBA team: a player traded for real moves to the team of his latest regular-season game this season (the pool keeps
his preseason team otherwise). Position never comes from box scores once the pool exists — the role-based pool
position is the league's (vote, 2026-10-17).
"""
import logging

from ..db import get_db

log = logging.getLogger(__name__)


def sync(cur) -> dict:
    """Pool NBA teams follow real trades; fantasy_players copies the pool's position and NBA team. Returns counts."""
    cur.execute("SELECT max(season) AS s FROM fantasy_pool")
    season = (cur.fetchone() or {}).get("s")
    if not season:
        return {"teams": 0, "players": 0}
    cur.execute("""
        WITH latest AS (
            SELECT DISTINCT ON (g.player_id) g.player_id, g.team
            FROM nba_player_games g JOIN nba_games n ON n.game_id = g.game_id
            WHERE g.season = %s AND n.game_type = 'regular' AND g.minutes > 0 AND g.team IS NOT NULL
            ORDER BY g.player_id, n.game_date DESC, g.game_id DESC
        )
        UPDATE fantasy_pool fp SET nba_team = l.team
        FROM latest l WHERE fp.season = %s AND fp.player_id = l.player_id AND fp.nba_team IS DISTINCT FROM l.team
    """, (season, season))
    moved = cur.rowcount
    cur.execute("""
        UPDATE fantasy_players p SET position = COALESCE(fp.position, p.position), nba_team = COALESCE(fp.nba_team, p.nba_team)
        FROM fantasy_pool fp
        WHERE fp.player_id = p.id AND fp.season = %s
          AND ((fp.position IS NOT NULL AND p.position IS DISTINCT FROM fp.position)
               OR (fp.nba_team IS NOT NULL AND p.nba_team IS DISTINCT FROM fp.nba_team))
    """, (season,))
    out = {"teams": moved, "players": cur.rowcount}
    if moved or out["players"]:
        from . import board, projections
        projections.clear_cache()
        board._BOARD_CACHE.clear()
    return out


def run_sync(why: str) -> dict:
    """sync() in its own transaction (startup, nightly); never raises."""
    try:
        conn = get_db()
        try:
            with conn.cursor() as cur:
                out = sync(cur)
            conn.commit()
        finally:
            conn.close()
        if out["teams"] or out["players"]:
            log.warning("truth sync (%s): %s", why, out)
        return out
    except Exception as e:  # noqa: BLE001 — a sync failure must not take the site down
        log.warning("truth sync (%s) failed: %s", why, e)
        return {"error": str(e)}
