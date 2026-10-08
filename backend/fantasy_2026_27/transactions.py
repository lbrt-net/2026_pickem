"""Adds and drops — the Players page's checkout. No waiver wire: a dropped player goes straight back to the pool.

- One checkout = one team's adds and drops, applied together or not at all, to the live roster, immediately.
- Legal = the roster after the moves isn't over the league's spot count and every entity has a spot he's eligible
  for. Going under is fine. Players already on the team keep their spots when they can; adds take open spots (their
  own position first, then Flex, then Bench); when that doesn't fit, everyone is re-seated (a matching).
- Locks don't stop anything here: etch.py saves the week's history first, so a player dropped after he locked still
  counts this week, and an add counts from his first lock after joining (next week if his spot is etched full).
"""
from datetime import datetime, timezone

import psycopg2

from . import etch as etch_mod
from .engine import as_of, league, weeks_for_league
from .lineup import eligible
from .logic import open_slot
from .weeks import league_settings, slot_list

ORDER = ["G", "F", "C", "TEAM", "FLEX", "BENCH"]


def _team(cur, scenario, team_id, user):
    cur.execute("SELECT id, name, owner_user_id FROM fantasy_teams WHERE scenario = %s AND id = %s", (scenario, team_id))
    team = cur.fetchone()
    if not team:
        raise ValueError("no such team")
    if team["owner_user_id"] != user.get("discord_id") and not user.get("is_admin"):
        raise PermissionError("not your team")
    return team


def _draft_done(cur, scenario) -> bool:
    cur.execute("SELECT status FROM fantasy_drafts WHERE scenario = %s", (scenario,))
    d = cur.fetchone()
    cur.execute("SELECT 1 FROM fantasy_rosters WHERE scenario = %s LIMIT 1", (scenario,))
    has_rosters = cur.fetchone() is not None
    status = d["status"] if d else "not_started"
    return status == "complete" or (status == "not_started" and has_rosters)  # simulated drafts never set a status


def _entities(cur, ids: list[str]) -> dict:
    """id → {id, kind, name, position, nba_team} for players and NBA teams."""
    out = {}
    if not ids:
        return out
    cur.execute("SELECT id, name, position, nba_team FROM fantasy_players WHERE id = ANY(%s::text[])", (ids,))
    for r in cur.fetchall():
        out[r["id"]] = {"id": r["id"], "kind": "player", "name": r["name"], "position": r["position"], "nba_team": r["nba_team"]}
    cur.execute("SELECT id, name FROM fantasy_nba_teams WHERE id = ANY(%s::text[])", (ids,))
    for r in cur.fetchall():
        out[r["id"]] = {"id": r["id"], "kind": "nba_team", "name": r["name"], "position": "TEAM", "nba_team": r["id"]}
    return out


def _seat(kept: list[dict], adds: list[dict], slots: dict) -> dict | None:
    """entity id → slot for everyone after the moves, or None if it can't fit."""
    filled = {}
    for e in kept:
        filled[e["slot"]] = filled.get(e["slot"], 0) + 1
    seat = {e["id"]: e["slot"] for e in kept}
    ok = True
    for e in adds:
        s = open_slot(filled, e, slots)
        if not s:
            ok = False
            break
        seat[e["id"]] = s
        filled[s] = filled.get(s, 0) + 1
    if ok:
        return seat
    # Re-seat everyone: bipartite matching over spot instances, each entity trying his current spot first.
    spots = [t for t in ORDER if t in slots for _ in range(slots[t])]
    people = kept + adds
    prefs = []
    for e in people:
        cand = [i for i, t in enumerate(spots) if eligible(e, t)]
        cand.sort(key=lambda i: (spots[i] != e.get("slot"), ORDER.index(spots[i])))
        prefs.append(cand)
    owner = [None] * len(spots)

    def place(p, seen):
        for i in prefs[p]:
            if i in seen:
                continue
            seen.add(i)
            if owner[i] is None or place(owner[i], seen):
                owner[i] = p
                return True
        return False

    for p in range(len(people)):
        if not place(p, set()):
            return None
    return {people[p]["id"]: spots[i] for i, p in enumerate(owner) if p is not None}


def _why_not(after: list[dict], slots: dict) -> str:
    total = sum(slots.values())
    if len(after) > total:
        return f"{len(after)} players for {total} spots. Drop {len(after) - total} more or remove an add."
    teams = sum(1 for e in after if e["kind"] == "nba_team")
    room = slots.get("TEAM", 0) + slots.get("FLEX", 0) + slots.get("BENCH", 0)
    if teams > room:
        return f"{teams} NBA teams, room for {room}."
    for pos in ("G", "F", "C"):
        n = sum(1 for e in after if eligible(e, pos) and e["kind"] == "player" and not any(eligible(e, p) for p in ("G", "F", "C") if p != pos))
        r = slots.get(pos, 0) + slots.get("FLEX", 0) + slots.get("BENCH", 0)
        if n > r:
            return f"{n} {pos}s, room for {r}."
    return "This roster doesn't fit the league's spots."


def checkout(cur, scenario: str, user: dict, team_id: str, adds: list[str], drops: list[str], apply: bool) -> dict:
    """Check (apply=False) or make (apply=True) one team's adds and drops. Returns the roster after the moves:
    {ok, error, roster: [{id, kind, name, position, nba_team, slot, change: keep | add | drop, moved_from (re-seated to fit)}],
    spots_used, spots_total}."""
    _team(cur, scenario, team_id, user)
    if not _draft_done(cur, scenario):
        raise ValueError("adds and drops open once the draft is done")
    adds, drops = list(dict.fromkeys(str(a) for a in adds)), list(dict.fromkeys(str(d) for d in drops))
    if set(adds) & set(drops):
        raise ValueError("the same player is in both adds and drops")
    if not adds and not drops:
        raise ValueError("nothing to do")
    settings = league_settings(cur, scenario)
    slots = settings["roster_slots"]
    roster = etch_mod.live_rosters(cur, scenario, team_id).get(team_id, [])
    mine = {e["id"]: e for e in roster}
    for d in drops:
        if d not in mine:
            raise ValueError("you can only drop your own players")
    info = _entities(cur, adds)
    for a in adds:
        if a not in info:
            raise ValueError(f"unknown player {a}")
    cur.execute("""SELECT r.player_id, r.nba_team_id, t.name FROM fantasy_rosters r JOIN fantasy_teams t ON t.id = r.team_id
                   WHERE r.scenario = %s AND (r.player_id = ANY(%s::text[]) OR r.nba_team_id = ANY(%s::text[]))""",
                (scenario, adds, adds))
    taken = {r["player_id"] or r["nba_team_id"]: r["name"] for r in cur.fetchall()}
    for a in adds:
        if a in taken:
            raise ValueError(f"{info[a]['name']} is on {taken[a]}")

    kept = [e for e in roster if e["id"] not in drops]
    new = [info[a] for a in adds]
    seat = _seat(kept, new, slots) if len(kept) + len(new) <= sum(slots.values()) else None
    order = {t: i for i, t in enumerate(slot_list(settings))}
    after = ([{**{k: e[k] for k in ("id", "kind", "name", "position", "nba_team")}, "slot": (seat or {}).get(e["id"], e["slot"]),
               "change": "keep", "moved_from": e["slot"] if seat and seat[e["id"]] != e["slot"] else None} for e in kept]
             + [{**e, "slot": (seat or {}).get(e["id"]), "change": "add"} for e in new])
    after.sort(key=lambda e: (order.get(e["slot"], 99), e["change"] == "add"))
    dropped = [{**{k: mine[d][k] for k in ("id", "kind", "name", "position", "nba_team", "slot")}, "change": "drop"} for d in drops]
    result = {"ok": seat is not None, "error": None if seat is not None else _why_not(kept + new, slots),
              "roster": after + dropped, "spots_used": len(after), "spots_total": sum(slots.values())}
    if not apply or seat is None:
        if apply:
            raise ValueError(result["error"])
        return result

    lg = league(cur, scenario)
    today = as_of(lg)
    etch_mod.etch(cur, scenario, lg["season"], weeks_for_league(cur, lg), today, team_id)  # history first
    by = user.get("discord_id")
    for d in drops:
        cur.execute("DELETE FROM fantasy_rosters WHERE id = %s", (mine[d]["row_id"],))
        cur.execute("""INSERT INTO fantasy_transactions (scenario, team_id, kind, entity_id, slot, asof, by_user)
                       VALUES (%s, %s, 'drop', %s, %s, %s, %s)""", (scenario, team_id, d, mine[d]["slot"], today, by))
    for e in kept:
        if seat[e["id"]] != e["slot"]:
            cur.execute("UPDATE fantasy_rosters SET slot = %s WHERE id = %s", (seat[e["id"]], e["row_id"]))
    now = datetime.now(timezone.utc)
    try:
        for e in new:
            cur.execute("""INSERT INTO fantasy_rosters (scenario, team_id, slot, player_id, nba_team_id, added_asof, added_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (scenario, team_id, seat[e["id"]], e["id"] if e["kind"] == "player" else None,
                         e["id"] if e["kind"] == "nba_team" else None, today, now))
            cur.execute("""INSERT INTO fantasy_transactions (scenario, team_id, kind, entity_id, slot, asof, by_user)
                           VALUES (%s, %s, 'add', %s, %s, %s, %s)""", (scenario, team_id, e["id"], seat[e["id"]], today, by))
    except psycopg2.errors.UniqueViolation:
        raise ValueError("someone else just added one of these players")
    return result
