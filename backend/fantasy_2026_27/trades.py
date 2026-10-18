"""Trades (commissioner, 2026-10-17) — the only way players change teams between two fantasy teams.

- A team proposes: players it gives, players it gets, and any of its own players it drops so its roster stays legal.
- The other team accepts (choosing its own drops, if it needs any), declines, or counters (its own offer back). The proposer can cancel until approved.
- Accepted trades wait for the commissioner: Approve applies it (both rosters re-checked first against who's on them
  now), Reject ends it.
- Drops in a trade happen only when it's approved. IR-locked players can't be traded until his last IR week.
- Legal = the same rule as an add/drop checkout (transactions.py): not over the league's spot count and every player
  has a spot he's eligible for. Everyone in the league sees every trade.
- Applying: history is etched first (like a checkout), traded players move to their new team (re-seated to fit), the
  drops are real drops (logged, onto waivers). Logged as adds / drops "via trade" for each team.
"""
from datetime import datetime, timezone

from psycopg2.extras import Json

from . import etch as etch_mod
from .engine import as_of, league, weeks_for_league
from .transactions import _draft_done, _entities, _seat, _team, _why_not
from .weeks import league_settings

OPEN = ("proposed", "accepted")


def init_schema(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fantasy_trades (
            id          SERIAL PRIMARY KEY,
            scenario    TEXT NOT NULL,
            from_team   TEXT NOT NULL,
            to_team     TEXT NOT NULL,
            give        JSONB NOT NULL,              -- ids from_team sends
            get         JSONB NOT NULL,              -- ids to_team sends
            from_drops  JSONB NOT NULL DEFAULT '[]', -- from_team's own drops to stay legal
            to_drops    JSONB NOT NULL DEFAULT '[]', -- to_team's, chosen when accepting
            status      TEXT NOT NULL,               -- proposed / accepted / approved / declined / countered / cancelled / rejected
            note        TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by  TEXT,
            decided_by  TEXT
        )
    """)


def _roster(cur, scenario, team_id):
    return etch_mod.live_rosters(cur, scenario, team_id).get(team_id, [])


def _side(cur, scenario, slots, roster, out_ids, in_ids, drops):
    """One team's roster after sending out_ids, receiving in_ids and dropping drops: (seat or None, error)."""
    mine = {e["id"]: e for e in roster}
    for i in list(out_ids) + list(drops):
        if i not in mine:
            return None, "a player in this trade is no longer on that team"
    # IR (commissioner, 2026-10-17): a player locked on IR through week N can't be traded or dropped until the next
    # roster lock is the week he's free, i.e. from week N on (locked through week 4: not in week 1; yes once week 4 is under way)
    week_now = None
    for i in list(out_ids) + list(drops):
        e = mine[i]
        if e["slot"] == "IR" and e.get("ir_until") is not None:
            from .lineup import ir_lock_week
            week_now = ir_lock_week(cur, scenario) if week_now is None else week_now
            if week_now < e["ir_until"]:
                return None, f"{e['name']} is locked on IR through Week {e['ir_until']} — tradeable from Week {e['ir_until']}"
    if set(out_ids) & set(drops):
        return None, "the same player is both traded and dropped"
    gone = set(out_ids) | set(drops)
    kept = [e for e in roster if e["id"] not in gone and e["slot"] != "IR"]
    info = _entities(cur, list(in_ids))
    new = [info[i] for i in in_ids if i in info]
    if len(new) != len(in_ids):
        return None, "unknown player in this trade"
    if len(kept) + len(new) > sum(slots.values()):
        return None, _why_not(kept + new, slots)
    seat = _seat(kept, new, slots)
    return (seat, None) if seat is not None else (None, _why_not(kept + new, slots))


def check(cur, scenario, from_team, to_team, give, get, from_drops=(), to_drops=()) -> dict:
    """Both sides' legality: {from: {ok, error}, to: {ok, error}}."""
    slots = league_settings(cur, scenario)["roster_slots"]
    a, ea = _side(cur, scenario, slots, _roster(cur, scenario, from_team), give, get, from_drops)
    b, eb = _side(cur, scenario, slots, _roster(cur, scenario, to_team), get, give, to_drops)
    return {"from": {"ok": a is not None, "error": ea}, "to": {"ok": b is not None, "error": eb}}


def _ids(xs):
    return list(dict.fromkeys(str(x) for x in (xs or []) if x))


def _get(cur, scenario, trade_id):
    cur.execute("SELECT * FROM fantasy_trades WHERE scenario = %s AND id = %s", (scenario, trade_id))
    t = cur.fetchone()
    if not t:
        raise ValueError("no such trade")
    return t


def propose(cur, scenario, user, from_team, to_team, give, get, drops) -> int:
    _team(cur, scenario, from_team, user)
    if not _draft_done(cur, scenario):
        raise ValueError("trades open once the draft is done")
    cur.execute("SELECT 1 FROM fantasy_teams WHERE scenario = %s AND id = %s", (scenario, to_team))
    if not cur.fetchone() or to_team == from_team:
        raise ValueError("pick another team to trade with")
    give, get, drops = _ids(give), _ids(get), _ids(drops)
    if not give and not get:
        raise ValueError("add players to the trade")
    r = check(cur, scenario, from_team, to_team, give, get, drops, ())
    if not r["from"]["ok"]:
        raise ValueError(f"your roster after the trade: {r['from']['error']}")
    if r["to"]["error"] == "a player in this trade is no longer on that team":
        raise ValueError(r["to"]["error"])
    cur.execute("""INSERT INTO fantasy_trades (scenario, from_team, to_team, give, get, from_drops, status, created_by)
                   VALUES (%s, %s, %s, %s, %s, %s, 'proposed', %s) RETURNING id""",
                (scenario, from_team, to_team, Json(give), Json(get), Json(drops), user.get("discord_id")))
    return cur.fetchone()["id"]


def respond(cur, scenario, user, trade_id, action, drops=()) -> None:
    """The other team: accept (with its drops) / decline. The proposer: cancel."""
    t = _get(cur, scenario, trade_id)
    if t["status"] not in OPEN:
        raise ValueError(f"this trade is already {t['status']}")
    if action == "cancel":
        _team(cur, scenario, t["from_team"], user)
        status, extra = "cancelled", {}
    elif action in ("accept", "decline", "counter"):
        _team(cur, scenario, t["to_team"], user)
        if t["status"] != "proposed":
            raise ValueError("this trade was already accepted")
        if action in ("decline", "counter"):  # counter: they answered with their own offer (sent separately)
            status, extra = ("declined" if action == "decline" else "countered"), {}
        else:
            drops = _ids(drops)
            r = check(cur, scenario, t["from_team"], t["to_team"], t["give"], t["get"], t["from_drops"], drops)
            if not r["to"]["ok"]:
                raise ValueError(f"your roster after the trade: {r['to']['error']}")
            if not r["from"]["ok"]:
                raise ValueError(f"their roster after the trade: {r['from']['error']}")
            status, extra = "accepted", {"to_drops": Json(drops)}
    else:
        raise ValueError("unknown action")
    sets = ", ".join([f"{k} = %s" for k in extra] + ["status = %s", "updated_at = now()"])
    cur.execute(f"UPDATE fantasy_trades SET {sets} WHERE id = %s", (*extra.values(), status, t["id"]))


def decide(cur, scenario, user, trade_id, approve: bool) -> None:
    """Commissioner: approve (apply) or reject an accepted trade."""
    if not user.get("is_admin"):
        raise PermissionError("only the commissioner can approve or reject trades")
    t = _get(cur, scenario, trade_id)
    if t["status"] != "accepted":
        raise ValueError("only accepted trades can be approved or rejected")
    if not approve:
        cur.execute("UPDATE fantasy_trades SET status = 'rejected', decided_by = %s, updated_at = now() WHERE id = %s",
                    (user.get("discord_id"), t["id"]))
        return
    slots = league_settings(cur, scenario)["roster_slots"]
    ra, rb = _roster(cur, scenario, t["from_team"]), _roster(cur, scenario, t["to_team"])
    sa, ea = _side(cur, scenario, slots, ra, t["give"], t["get"], t["from_drops"])
    sb, eb = _side(cur, scenario, slots, rb, t["get"], t["give"], t["to_drops"])
    if sa is None or sb is None:
        raise ValueError(f"can't go through now: {ea or eb}")
    _apply(cur, scenario, user, t, ra, rb, sa, sb)
    cur.execute("UPDATE fantasy_trades SET status = 'approved', decided_by = %s, updated_at = now() WHERE id = %s",
                (user.get("discord_id"), t["id"]))


def _apply(cur, scenario, user, t, ra, rb, sa, sb):
    from . import waivers
    lg = league(cur, scenario)
    today, weeks = as_of(lg), weeks_for_league(cur, lg)
    for team in (t["from_team"], t["to_team"]):
        etch_mod.etch(cur, scenario, lg["season"], weeks, today, team)  # history first
    by, now = user.get("discord_id"), datetime.now(timezone.utc)
    rows = {**{e["id"]: e for e in ra}, **{e["id"]: e for e in rb}}
    for team, drops in ((t["from_team"], t["from_drops"]), (t["to_team"], t["to_drops"])):
        for d in drops:  # real drops: logged, onto waivers
            cur.execute("DELETE FROM fantasy_rosters WHERE id = %s", (rows[d]["row_id"],))
            cur.execute("""INSERT INTO fantasy_transactions (scenario, team_id, kind, entity_id, slot, asof, at, by_user)
                           VALUES (%s, %s, 'drop', %s, %s, %s, %s, %s)""", (scenario, team, d, rows[d]["slot"], today, now, by))
            waivers.put_on_waivers(cur, scenario, d, team, today)
    moves = [(i, t["from_team"], t["to_team"], sb) for i in t["give"]] + [(i, t["to_team"], t["from_team"], sa) for i in t["get"]]
    for i, src, dst, seat in moves:
        e = rows[i]
        cur.execute("DELETE FROM fantasy_rosters WHERE id = %s", (e["row_id"],))
        cur.execute("""INSERT INTO fantasy_transactions (scenario, team_id, kind, entity_id, slot, asof, at, by_user, via)
                       VALUES (%s, %s, 'drop', %s, %s, %s, %s, %s, 'trade')""", (scenario, src, i, e["slot"], today, now, by))
    for i, src, dst, seat in moves:
        e = rows[i]
        cur.execute("""INSERT INTO fantasy_rosters (scenario, team_id, slot, player_id, nba_team_id, added_asof, added_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (scenario, dst, seat[i], i if e["kind"] == "player" else None, i if e["kind"] == "nba_team" else None, today, now))
        cur.execute("""INSERT INTO fantasy_transactions (scenario, team_id, kind, entity_id, slot, asof, at, by_user, via)
                       VALUES (%s, %s, 'add', %s, %s, %s, %s, %s, 'trade')""", (scenario, dst, i, seat[i], today, now, by))
    for team, roster, seat in ((t["from_team"], ra, sa), (t["to_team"], rb, sb)):  # everyone staying, re-seated to fit
        for e in roster:
            if e["id"] in seat and e["slot"] != "IR" and seat[e["id"]] != e["slot"]:
                cur.execute("UPDATE fantasy_rosters SET slot = %s WHERE id = %s", (seat[e["id"]], e["row_id"]))


def listing(cur, scenario) -> dict:
    """Every trade in the league, newest first, with names."""
    from .settings import logo_url
    cur.execute("""SELECT id, name, abbreviation, color, glyph, owner_user_id, logo_updated, picture_url, picture_mode
                   FROM fantasy_teams WHERE scenario = %s""", (scenario,))
    teams = {r["id"]: {**{k: r[k] for k in ("id", "name", "abbreviation", "color", "glyph", "owner_user_id")}, "logo_url": logo_url(r)}
             for r in cur.fetchall()}
    cur.execute("SELECT * FROM fantasy_trades WHERE scenario = %s ORDER BY updated_at DESC, id DESC", (scenario,))
    rows = cur.fetchall()
    ids = list({i for r in rows for k in ("give", "get", "from_drops", "to_drops") for i in (r[k] or [])})
    info = _entities(cur, ids)
    ent = lambda xs: [info.get(i, {"id": i, "name": i, "kind": "player"}) for i in (xs or [])]  # noqa: E731
    return {"trades": [{"id": r["id"], "status": r["status"], "from": teams.get(r["from_team"]), "to": teams.get(r["to_team"]),
                        "give": ent(r["give"]), "get": ent(r["get"]), "from_drops": ent(r["from_drops"]), "to_drops": ent(r["to_drops"]),
                        "created_at": r["created_at"].isoformat(), "updated_at": r["updated_at"].isoformat()} for r in rows]}
