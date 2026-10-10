"""Waivers.

- A drop is real once the player was really on the team: drafted, or locked into one of its weekly lineups
  (etched, etch.py). A real drop puts him on waivers for 2 days — nobody can just add him, not even the team that
  dropped him; teams put in claims instead. An add that's dropped again before any lock wasn't a real move: both
  rows leave the log and he goes straight back to free agents.
- Claims: one per team per player, with an optional player to drop if it wins. When the 2 days are up, the claim
  from the team lowest in the standings (worst record, then fewest points) that still fits its roster wins; the
  rest lose. No claims → he's a free agent.
- Clock: the live league counts 48 hours from the drop; the replay counts 2 days on its own (simulated) date.
- Processing is lazy: process() runs before anything that reads or changes rosters (players list, checkout, claims,
  transaction log), the same way the draft catches up on reads.
"""
from datetime import datetime, timedelta, timezone

from .engine import as_of, league, results

REPLAY = "replay"
WAIVER_DAYS = 2


def _open_sql(scenario: str) -> str:
    return "until_asof > %s" if scenario == REPLAY else "until_at > %s"


def _clock(lg, scenario):
    return as_of(lg) if scenario == REPLAY else datetime.now(timezone.utc)


def was_real(cur, scenario: str, team_id: str, row: dict, weeks: list) -> bool:
    """Was this roster row really the team's: drafted, or etched into a weekly lineup (a week that ended on or after
    he joined — etched rows from an earlier stint don't count)?"""
    if row.get("added_asof") is None:
        return True
    since = [w["week"] for w in weeks if w["end"] >= row["added_asof"]]
    cur.execute("SELECT 1 FROM fantasy_lineups WHERE scenario = %s AND team_id = %s AND entity_id = %s AND week = ANY(%s) LIMIT 1",
                (scenario, team_id, row["id"], since))
    return cur.fetchone() is not None


def put_on_waivers(cur, scenario: str, entity_id: str, team_id: str, today) -> None:
    now = datetime.now(timezone.utc)
    cur.execute("UPDATE fantasy_waivers SET status = 'cleared' WHERE scenario = %s AND entity_id = %s AND status = 'open'", (scenario, entity_id))
    cur.execute("""INSERT INTO fantasy_waivers (scenario, entity_id, from_team, dropped_at, until_at, until_asof)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (scenario, entity_id, team_id, now, now + timedelta(days=WAIVER_DAYS), today + timedelta(days=WAIVER_DAYS)))


def on_waivers(cur, scenario: str) -> dict:
    """entity id → {waiver_id, until (ISO, live) / until_date (replay), from_team} for players on waivers now."""
    lg = league(cur, scenario)
    cur.execute(f"SELECT id, entity_id, from_team, until_at, until_asof FROM fantasy_waivers WHERE scenario = %s AND status = 'open' AND {_open_sql(scenario)}",
                (scenario, _clock(lg, scenario)))
    return {r["entity_id"]: {"waiver_id": r["id"], "from_team": r["from_team"],
                             "until": r["until_at"].isoformat() if scenario != REPLAY else None,
                             "until_date": r["until_asof"].isoformat()} for r in cur.fetchall()}


def _priority(cur, scenario: str) -> list:
    """Team ids, first claim first: worst record, then fewest points for (reverse standings)."""
    table = results(cur, scenario)["standings"]
    rows = sorted(table, key=lambda r: ((r["w"] + r["t"] / 2), r["pf"]))
    out = [r["team"]["id"] for r in rows]
    cur.execute("SELECT id FROM fantasy_teams WHERE scenario = %s ORDER BY name", (scenario,))
    return out + [r["id"] for r in cur.fetchall() if r["id"] not in out]


def process(cur, scenario: str) -> int:
    """Settle every waiver whose 2 days are up. Returns how many were settled."""
    from . import transactions
    lg = league(cur, scenario)
    done = "until_asof <= %s" if scenario == REPLAY else "until_at <= %s"
    cur.execute(f"SELECT * FROM fantasy_waivers WHERE scenario = %s AND status = 'open' AND {done} ORDER BY until_at FOR UPDATE",
                (scenario, _clock(lg, scenario)))
    due = cur.fetchall()
    if not due:
        return 0
    order = None
    for w in due:
        cur.execute("SELECT * FROM fantasy_claims WHERE waiver_id = %s AND status = 'pending'", (w["id"],))
        claims = cur.fetchall()
        winner = None
        if claims:
            order = order or _priority(cur, scenario)
            rank = {t: i for i, t in enumerate(order)}
            for c in sorted(claims, key=lambda c: (rank.get(c["team_id"], 99), c["created_at"])):
                try:
                    cur.execute("SAVEPOINT claim")
                    transactions.checkout(cur, scenario, {"is_admin": True}, c["team_id"], [w["entity_id"]],
                                          [c["drop_id"]] if c["drop_id"] else [], apply=True, via="waivers")
                    cur.execute("RELEASE SAVEPOINT claim")
                    winner = c
                    break
                except ValueError as e:  # doesn't fit any more (roster changed): next claim
                    cur.execute("ROLLBACK TO SAVEPOINT claim")
                    cur.execute("UPDATE fantasy_claims SET status = 'failed', note = %s WHERE id = %s", (str(e)[:200], c["id"]))
            for c in claims:
                if winner and c["id"] == winner["id"]:
                    cur.execute("UPDATE fantasy_claims SET status = 'won' WHERE id = %s", (c["id"],))
                else:
                    cur.execute("UPDATE fantasy_claims SET status = 'lost' WHERE id = %s AND status = 'pending'", (c["id"],))
        cur.execute("UPDATE fantasy_waivers SET status = %s, claimed_by = %s WHERE id = %s",
                    ("claimed" if winner else "cleared", winner["team_id"] if winner else None, w["id"]))
    return len(due)


def _team(cur, scenario, team_id, user):
    cur.execute("SELECT id, owner_user_id FROM fantasy_teams WHERE scenario = %s AND id = %s", (scenario, team_id))
    t = cur.fetchone()
    if not t:
        raise ValueError("no such team")
    if t["owner_user_id"] != user.get("discord_id") and not user.get("is_admin"):
        raise PermissionError("not your team")


def claim(cur, scenario: str, user: dict, team_id: str, entity_id: str, drop_id: str | None) -> dict:
    """Put in (or replace) this team's claim on a player on waivers, with an optional drop if it wins.
    Checked now against the roster (the same check runs again when it's settled)."""
    from . import transactions
    _team(cur, scenario, team_id, user)
    if not transactions._draft_done(cur, scenario):
        raise ValueError("adds and drops open once the draft is done")
    process(cur, scenario)
    w = on_waivers(cur, scenario).get(entity_id)
    if not w:
        raise ValueError("he isn't on waivers — add him as a free agent")
    preview = transactions.checkout(cur, scenario, user, team_id, [entity_id], [drop_id] if drop_id else [], apply=False, via="waivers")
    if not preview["ok"]:
        raise ValueError(preview["error"])
    cur.execute("DELETE FROM fantasy_claims WHERE waiver_id = %s AND team_id = %s AND status = 'pending'", (w["waiver_id"], team_id))
    cur.execute("""INSERT INTO fantasy_claims (scenario, waiver_id, team_id, entity_id, drop_id, by_user)
                   VALUES (%s, %s, %s, %s, %s, %s)""", (scenario, w["waiver_id"], team_id, entity_id, drop_id, user.get("discord_id")))
    return claims_for(cur, scenario, team_id)


def cancel(cur, scenario: str, user: dict, team_id: str, claim_id: int) -> dict:
    _team(cur, scenario, team_id, user)
    cur.execute("DELETE FROM fantasy_claims WHERE scenario = %s AND team_id = %s AND id = %s AND status = 'pending'", (scenario, team_id, claim_id))
    return claims_for(cur, scenario, team_id)


def claims_for(cur, scenario: str, team_id: str) -> dict:
    """This team's pending claims (private) and its place in the claim order."""
    cur.execute("""
        SELECT c.id, c.entity_id, c.drop_id, c.created_at, w.until_at, w.until_asof,
               COALESCE(p.name, n.name) AS name, COALESCE(dp.name, dn.name) AS drop_name
        FROM fantasy_claims c JOIN fantasy_waivers w ON w.id = c.waiver_id
        LEFT JOIN fantasy_players p ON p.id = c.entity_id LEFT JOIN fantasy_nba_teams n ON n.id = c.entity_id
        LEFT JOIN fantasy_players dp ON dp.id = c.drop_id LEFT JOIN fantasy_nba_teams dn ON dn.id = c.drop_id
        WHERE c.scenario = %s AND c.team_id = %s AND c.status = 'pending' ORDER BY w.until_at
    """, (scenario, team_id))
    rows = [{"id": r["id"], "entity_id": r["entity_id"], "name": r["name"], "drop_id": r["drop_id"], "drop_name": r["drop_name"],
             "until": r["until_at"].isoformat() if scenario != REPLAY else None, "until_date": r["until_asof"].isoformat()}
            for r in cur.fetchall()]
    order = _priority(cur, scenario)
    return {"claims": rows, "priority": order.index(team_id) + 1 if team_id in order else None, "teams": len(order)}
