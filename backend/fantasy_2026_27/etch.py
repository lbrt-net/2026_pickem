"""Lineup history: the live roster vs each week's etched lineup.

- The live roster (fantasy_rosters) is always changeable: Roster moves, adds and drops (later trades) apply to it
  at once. Nothing about it is locked.
- THE ROSTER LOCK RECORD (fantasy_lock_ledger, 2026-10-24): every spot is written there once, at the moment it
  locks, and in the live league the database refuses any change or deletion. Locked spots are read from it alone.
  fantasy_lineups now only holds pins (a not-yet-locked player's spot for this week after a swap with a locked one).
- (History) A week's lineup was etched into fantasy_lineups one entity at a time: when his first game of that week locks
  (5 minutes before tip-off; the replay treats the whole day as played), or when the week ends. An etched row never
  changes (only a future commissioner correction could), so a player dropped after he locked still counts for that
  week, and a player added after his lock only counts from next week.
- Writes happen at locks: the app wakes at every lock moment (5 minutes before each tip-off; nba/scheduler.py →
  etch_league) and saves whoever just locked; etch() also runs before every roster change. Either way only locked
  entities are written, and nothing moved since his lock, so his live spot is the spot he locked in. Reads (week_lineups) combine the etched rows
  with the live roster for whoever isn't etched yet.
- Once etch() runs after a week has ended, the week is closed (fantasy_lineup_weeks): its lineup is the etched rows
  only, so later adds can't leak into it.
- fantasy_rosters.added_asof / added_at (NULL = from the draft) say whether an entity joined before his lock.
- A spot filled by etched entities is full for that week: dropping a locked player and adding someone into his spot
  doesn't give the spot a second scorer — the newcomer starts counting next week.
"""
from datetime import date, datetime, time, timedelta, timezone

from .logic import open_slot
from .weeks import LOCK_MINUTES, league_settings, spot_caps, week_for

REPLAY = "replay"


def started(g: dict, today: date, replay: bool) -> bool:
    """Is this game within 5 minutes of tip-off (or later) as of the league's clock? The replay
    treats a whole day as played."""
    if g["game_date"] < today:
        return True
    if g["game_date"] > today:
        return False
    if replay:
        return True
    return bool(g["tipoff_utc"] and g["tipoff_utc"] - timedelta(minutes=LOCK_MINUTES) <= datetime.now(timezone.utc))


def live_rosters(cur, scenario: str, team_id: str | None = None) -> dict:
    """team id → its live roster entries, in draft order then join order."""
    cur.execute("""
        SELECT r.id AS row_id, r.team_id, r.slot, r.player_id, r.nba_team_id, r.added_asof, r.added_at, r.ir_until,
               COALESCE(p.name, n.name) AS name, COALESCE(fp.position, p.position) AS position, COALESCE(p.nba_team, fp.nba_team) AS nba_team
        FROM fantasy_rosters r
        LEFT JOIN fantasy_players p ON p.id = r.player_id
        LEFT JOIN fantasy_nba_teams n ON n.id = r.nba_team_id
        LEFT JOIN fantasy_leagues lg ON lg.scenario = r.scenario
        LEFT JOIN fantasy_pool fp ON fp.player_id = r.player_id AND fp.season = lg.season
        WHERE r.scenario = %s AND (%s::text IS NULL OR r.team_id = %s)
        ORDER BY r.pick_no NULLS LAST, r.id
    """, (scenario, team_id, team_id))
    out = {}
    for r in cur.fetchall():
        kind = "player" if r["player_id"] else "nba_team"
        out.setdefault(r["team_id"], []).append({
            "id": r["player_id"] or r["nba_team_id"], "kind": kind, "name": r["name"], "slot": r["slot"],
            "position": r["position"] if kind == "player" else "TEAM",
            "nba_team": r["nba_team"] if kind == "player" else r["nba_team_id"], "row_id": r["row_id"],
            "added_asof": r["added_asof"], "added_at": r["added_at"], "ir_until": r["ir_until"]})
    return out


def first_games(cur, season: str, weeks: list[dict], tricodes: list[str]) -> dict:
    """(tricode, week no) → that NBA team's first regular-season game of the week."""
    if not weeks:
        return {}
    tricodes = tricodes or [""]
    cur.execute("""
        SELECT game_date, tipoff_utc, home_team, away_team FROM nba_games
        WHERE season = %s AND game_type = 'regular' AND missing_since IS NULL AND game_date BETWEEN %s AND %s
          AND (home_team = ANY(%s::text[]) OR away_team = ANY(%s::text[]))
        ORDER BY game_date, tipoff_utc NULLS LAST
    """, (season, weeks[0]["start"], weeks[-1]["end"], tricodes, tricodes))
    out = {}
    for g in cur.fetchall():
        w = week_for(weeks, g["game_date"])
        if w:
            for t in (g["home_team"], g["away_team"]):
                if t in tricodes:
                    out.setdefault((t, w["week"]), g)
    # ("*", week): the week's last first game — the latest tip-off among every NBA team's first game of the week. A spot
    # with no game that week (an empty spot, a player whose team doesn't play) locks then: after it, no pickup can
    # still play that week (commissioner, 2026-10-24)
    cur.execute("""
        SELECT DISTINCT ON (t, game_date, tipoff_utc) t, game_date, tipoff_utc FROM (
            SELECT home_team AS t, game_date, tipoff_utc FROM nba_games WHERE season = %s AND game_type = 'regular'
              AND missing_since IS NULL AND game_date BETWEEN %s AND %s
            UNION ALL
            SELECT away_team, game_date, tipoff_utc FROM nba_games WHERE season = %s AND game_type = 'regular'
              AND missing_since IS NULL AND game_date BETWEEN %s AND %s) x
        ORDER BY t, game_date, tipoff_utc NULLS LAST
    """, (season, weeks[0]["start"], weeks[-1]["end"], season, weeks[0]["start"], weeks[-1]["end"]))
    firsts = {}
    for g in cur.fetchall():
        w = week_for(weeks, g["game_date"])
        if w and g["t"] and (g["t"], w["week"]) not in firsts:
            firsts[(g["t"], w["week"])] = g
    for (t, wk), g in firsts.items():
        cur_last = out.get(("*", wk))
        key = lambda x: (x["game_date"], x["tipoff_utc"] or datetime.max.replace(tzinfo=timezone.utc))
        if cur_last is None or key(g) > key(cur_last):
            out[("*", wk)] = {"game_date": g["game_date"], "tipoff_utc": g["tipoff_utc"]}
    return out


def game_for(fg: dict, tricode: str | None, week: int) -> dict | None:
    """The game a spot locks at in a week: its NBA team's first game; no game that week → the week's last first game."""
    return fg.get((tricode, week)) or fg.get(("*", week))


def joined_in_time(e: dict, w: dict, g: dict | None, replay: bool) -> bool:
    """Did this entity join the team before his lock in week w (his first game; the week's end if he has none)?"""
    if e.get("added_asof") is None:  # from the draft
        return True
    if g is None:
        return e["added_asof"] <= w["end"]
    if replay:
        return e["added_asof"] < g["game_date"]
    lock_at = (g["tipoff_utc"] - timedelta(minutes=LOCK_MINUTES) if g["tipoff_utc"]
               else datetime.combine(g["game_date"], time.min, tzinfo=timezone.utc))
    return e["added_at"] < lock_at


def _closed(cur, scenario: str) -> set:
    cur.execute("SELECT team_id, week FROM fantasy_lineup_weeks WHERE scenario = %s", (scenario,))
    return {(r["team_id"], r["week"]) for r in cur.fetchall()}


def lock_moment(g: dict | None, w: dict) -> datetime:
    """When a spot locks: 5 minutes before its player's first game of the week (the replay: that day); no game that
    week → the end of the week."""
    if g is None:
        return datetime.combine(w["end"] + timedelta(days=1), time.min, tzinfo=timezone.utc)
    if g["tipoff_utc"]:
        return g["tipoff_utc"] - timedelta(minutes=LOCK_MINUTES)
    return datetime.combine(g["game_date"], time.min, tzinfo=timezone.utc)


def ledger(cur, scenario: str, team_id: str | None = None) -> dict:
    """(team, week) → {entity id: slot}: THE ROSTER LOCK RECORD (fantasy_lock_ledger) — every spot that has locked."""
    cur.execute("""SELECT team_id, week, entity_id, slot FROM fantasy_lock_ledger
                   WHERE scenario = %s AND (%s::text IS NULL OR team_id = %s) ORDER BY week, slot, spot_no""",
                (scenario, team_id, team_id))
    out = {}
    for r in cur.fetchall():
        out.setdefault((r["team_id"], r["week"]), {})[r["entity_id"]] = r["slot"]
    return out


def _write_lock(cur, scenario: str, team_id: str, week: int, e: dict, slot: str, locked_at: datetime, cap: dict) -> bool:
    """Write one locked spot to the lock record: the first free spot of that kind. A full spot kind can't take
    anyone (False). Never changes an existing row — the database refuses that anyway."""
    cur.execute("SELECT spot_no FROM fantasy_lock_ledger WHERE scenario = %s AND team_id = %s AND week = %s AND slot = %s",
                (scenario, team_id, week, slot))
    taken = {r["spot_no"] for r in cur.fetchall()}
    free = next((i for i in range(cap.get(slot, 0)) if i not in taken), None)
    if free is None:
        return False
    cur.execute("""INSERT INTO fantasy_lock_ledger (scenario, team_id, week, slot, spot_no, entity_id, entity_kind, locked_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                (scenario, team_id, week, slot, free, e["id"], e["kind"], locked_at))
    return cur.rowcount == 1


def etch(cur, scenario: str, season: str, weeks: list[dict], today: date, team_id: str) -> None:
    """Lock every spot of this team whose moment has come (its player's first game of the week started — IR spots
    the same — or the week ended): write it to the lock record, once, for good. Then close the weeks that are over.
    Runs at every lock moment (scheduler) and before any change to the team's roster or lineup.

    fantasy_lineups holds pins only: the spot a not-yet-locked player keeps this week when a swap with a locked player
    moved him for next week. At his lock, the pin (else his roster spot) is what gets written."""
    replay = scenario == REPLAY
    begun = [w for w in weeks if w["start"] <= today]
    if not begun:
        return
    closed = _closed(cur, scenario)
    roster = live_rosters(cur, scenario, team_id).get(team_id, [])
    cap = spot_caps(league_settings(cur, scenario))
    locked = ledger(cur, scenario, team_id)
    cur.execute("SELECT week, entity_id, slot FROM fantasy_lineups WHERE scenario = %s AND team_id = %s", (scenario, team_id))
    pins = {(r["week"], r["entity_id"]): r["slot"] for r in cur.fetchall()}
    fg = first_games(cur, season, begun, sorted({e["nba_team"] for e in roster if e["nba_team"]}))
    spots = week_lineups(cur, scenario, season, weeks, today, team_id)  # the spot he locks in = his spot in that week
    for w in begun:
        if (team_id, w["week"]) in closed:
            continue
        over = w["end"] < today
        mine = locked.get((team_id, w["week"]), {})
        here = {x["id"]: x["slot"] for x in spots.get((team_id, w["week"]), []) if not x["etched"]}
        for e in roster:
            key = (w["week"], e["id"])
            g = game_for(fg, e["nba_team"], w["week"])
            if not joined_in_time(e, w, g, replay):
                # joined after his lock: never in this week. A pin for him is a mistake (a swap used to write one —
                # 2026-10-24, Ty Jerome over James Harden): remove it
                if key in pins:
                    cur.execute("DELETE FROM fantasy_lineups WHERE scenario = %s AND team_id = %s AND week = %s AND entity_id = %s",
                                (scenario, team_id, w["week"], e["id"]))
                continue
            if e["id"] in mine or not (over or (g and started(g, today, replay))):
                continue
            slot = here.get(e["id"])
            if not slot:  # no spot this week (every one he can play is taken): starts next week
                continue
            if _write_lock(cur, scenario, team_id, w["week"], e, slot, lock_moment(g, w), cap):
                mine[e["id"]] = slot
        if over:
            cur.execute("INSERT INTO fantasy_lineup_weeks (scenario, team_id, week) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                        (scenario, team_id, w["week"]))


def week_spots(cur, scenario: str, season: str, weeks: list[dict], today: date, team_id: str) -> tuple:
    """(current week no, {id: this week's spot}) for the team's players not locked yet; (None, {}) between weeks."""
    w = week_for(weeks, today)
    if not w:
        return None, {}
    wl = week_lineups(cur, scenario, season, weeks, today, team_id).get((team_id, w["week"]), [])
    return w["week"], {e["id"]: e["slot"] for e in wl if not e["etched"] and e["on_roster"]}


def keep_week(cur, scenario: str, season: str, weeks: list[dict], today: date, team_id: str, before: tuple,
              skip=()) -> None:
    """After a roster change (2026-10-26): nobody not locked yet changes spot in the week under way unless that move
    was made for this week (skip). Pins everyone whose spot this week would otherwise change. Week 3 on = the roster."""
    wk, was = before
    if wk is None:
        return
    _, now = week_spots(cur, scenario, season, weeks, today, team_id)
    for eid, slot in was.items():
        if eid in skip or now.get(eid) == slot or eid not in now and not _on_roster(cur, scenario, team_id, eid):
            continue
        cur.execute("""INSERT INTO fantasy_lineups (scenario, team_id, week, entity_id, slot) VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (scenario, team_id, week, entity_id) DO UPDATE SET slot = EXCLUDED.slot""",
                    (scenario, team_id, wk, eid, slot))


def _on_roster(cur, scenario: str, team_id: str, eid: str) -> bool:
    cur.execute("SELECT 1 FROM fantasy_rosters WHERE scenario = %s AND team_id = %s AND (player_id = %s OR nba_team_id = %s)",
                (scenario, team_id, eid, eid))
    return cur.fetchone() is not None


def backfill_ledger(cur, scenario: str) -> int:
    """One time (2026-10-24): the lock record starts from the spots already locked in fantasy_lineups — only rows whose
    player had locked (game started / week over) and joined before his lock, in their order, within the spot counts."""
    from .engine import as_of, league, weeks_for_league
    cur.execute("SELECT 1 FROM fantasy_lock_ledger WHERE scenario = %s LIMIT 1", (scenario,))
    if cur.fetchone():
        return 0
    lg = league(cur, scenario)
    weeks, today = weeks_for_league(cur, lg), as_of(lg)
    replay = scenario == REPLAY
    begun = [w for w in weeks if w["start"] <= today]
    cap = spot_caps(league_settings(cur, scenario))
    live = live_rosters(cur, scenario)
    cur.execute("SELECT team_id, week, entity_id, slot FROM fantasy_lineups WHERE scenario = %s ORDER BY team_id, week, ctid", (scenario,))
    rows = cur.fetchall()
    ids = sorted({r["entity_id"] for r in rows})
    who = {}
    if ids:
        cur.execute("SELECT id, nba_team FROM fantasy_players WHERE id = ANY(%s::text[])", (ids,))
        who.update({r["id"]: {"id": r["id"], "kind": "player", "nba_team": r["nba_team"]} for r in cur.fetchall()})
        cur.execute("SELECT id FROM fantasy_nba_teams WHERE id = ANY(%s::text[])", (ids,))
        who.update({r["id"]: {"id": r["id"], "kind": "nba_team", "nba_team": r["id"]} for r in cur.fetchall()})
    fg = first_games(cur, lg["season"], begun, sorted({x["nba_team"] for x in who.values() if x["nba_team"]}))
    n = 0
    for r in rows:
        w = next((x for x in begun if x["week"] == r["week"]), None)
        e = next((x for x in live.get(r["team_id"], []) if x["id"] == r["entity_id"]), None) or who.get(r["entity_id"])
        if not w or not e:
            continue
        g = game_for(fg, e["nba_team"], w["week"])
        if not (w["end"] < today or (g and started(g, today, replay))):
            continue  # a pin for a player who hasn't locked yet: not a locked spot
        if not joined_in_time(e, w, g, replay):
            continue  # joined after his lock: never was in this week
        n += _write_lock(cur, scenario, r["team_id"], w["week"], e, r["slot"], lock_moment(g, w), cap)
    return n


def etch_league(cur, scenario: str) -> int:
    """Run etch() for every team of a league (the lock-time job). Returns how many lineup rows were written."""
    from .engine import as_of, league, weeks_for_league
    lg = league(cur, scenario)
    weeks, today = weeks_for_league(cur, lg), as_of(lg)
    backfill_ledger(cur, scenario)
    cur.execute("SELECT count(*) AS n FROM fantasy_lock_ledger WHERE scenario = %s", (scenario,))
    before = cur.fetchone()["n"]
    cur.execute("SELECT id FROM fantasy_teams WHERE scenario = %s", (scenario,))
    for t in [r["id"] for r in cur.fetchall()]:
        etch(cur, scenario, lg["season"], weeks, today, t)
    cur.execute("SELECT count(*) AS n FROM fantasy_lock_ledger WHERE scenario = %s", (scenario,))
    return cur.fetchone()["n"] - before


def next_lock_at(cur, scenario: str, now: datetime) -> datetime | None:
    """The next lock moment after `now`: 5 minutes before the next tip-off of the league's season."""
    from .engine import league
    lg = league(cur, scenario)
    cur.execute("""SELECT min(tipoff_utc) AS t FROM nba_games WHERE season = %s AND game_type = 'regular' AND missing_since IS NULL
                   AND tipoff_utc - %s > %s""", (lg["season"], timedelta(minutes=LOCK_MINUTES), now))
    t = cur.fetchone()["t"]
    return t - timedelta(minutes=LOCK_MINUTES) if t else None


def week_lineups(cur, scenario: str, season: str, weeks: list[dict], today: date, team_id: str | None = None) -> dict:
    """(team id, week no) → that week's lineup for every week that has begun. Locked spots come from THE ROSTER LOCK
    RECORD only (in the spot they locked in, even if since dropped); unless the week is closed, roster players not
    locked yet who joined before their lock fill the spots still open (a pin keeps a player's spot for this week).
    Each entry: id, kind, name, slot, position, nba_team, etched (= locked), on_roster."""
    replay = scenario == REPLAY
    begun = [w for w in weeks if w["start"] <= today]
    if not begun:
        return {}
    cap = spot_caps(league_settings(cur, scenario))
    live = live_rosters(cur, scenario, team_id)
    closed = _closed(cur, scenario)
    etched = ledger(cur, scenario, team_id)
    cur.execute("SELECT team_id, week, entity_id, slot FROM fantasy_lineups WHERE scenario = %s AND (%s::text IS NULL OR team_id = %s)",
                (scenario, team_id, team_id))
    pins = {(r["team_id"], r["week"], r["entity_id"]): r["slot"] for r in cur.fetchall()}
    # Who the locked-but-dropped entities are
    known = {e["id"]: e for es in live.values() for e in es}
    missing = sorted({eid for rows in etched.values() for eid in rows} - set(known))
    info = {}
    if missing:
        cur.execute("SELECT id, name, position, nba_team FROM fantasy_players WHERE id = ANY(%s::text[])", (missing,))
        info.update({r["id"]: {"id": r["id"], "kind": "player", "name": r["name"], "position": r["position"], "nba_team": r["nba_team"]}
                     for r in cur.fetchall()})
        cur.execute("SELECT id, name FROM fantasy_nba_teams WHERE id = ANY(%s::text[])", (missing,))
        info.update({r["id"]: {"id": r["id"], "kind": "nba_team", "name": r["name"], "position": "TEAM", "nba_team": r["id"]}
                     for r in cur.fetchall()})
    fg = first_games(cur, season, begun, sorted({e["nba_team"] for e in known.values() if e["nba_team"]}))
    teams = set(live) | {t for t, _ in etched}
    out = {}
    for t in teams:
        mine = live.get(t, [])
        mine_ids = {e["id"] for e in mine}
        for w in begun:
            rows = etched.get((t, w["week"]), {})
            used = {}
            for slot in rows.values():
                used[slot] = used.get(slot, 0) + 1
            entries = [{**e, "slot": rows[e["id"]], "etched": True, "on_roster": True} for e in mine if e["id"] in rows]
            # not locked yet (2026-10-26, Deni / LaMelo): this week's spot = his pin, else his roster spot, else an open
            # spot he can play (own position, Flex, Bench) — a roster change never pushes him out of the week under way
            free = [] if (t, w["week"]) in closed else [
                e for e in mine if e["id"] not in rows and joined_in_time(e, w, game_for(fg, e["nba_team"], w["week"]), replay)]
            pinned = [e for e in free if (t, w["week"], e["id"]) in pins]
            rest = [e for e in free if (t, w["week"], e["id"]) not in pins]
            placed = set()
            for group, spot_of in ((pinned, lambda e: pins[(t, w["week"], e["id"])]), (rest, lambda e: e["slot"]),
                                   (rest, lambda e: open_slot(used, e, cap) if e["slot"] != "IR" else None)):
                for e in group:
                    slot = spot_of(e)
                    if e["id"] in placed or not slot or used.get(slot, 0) >= cap.get(slot, 0):
                        continue
                    used[slot] = used.get(slot, 0) + 1
                    placed.add(e["id"])
                    entries.append({**e, "slot": slot, "etched": False, "on_roster": True})
            for eid, slot in rows.items():
                who = None if eid in mine_ids else (known.get(eid) or info.get(eid))  # dropped since (maybe on another team now)
                if who:
                    entries.append({**who, "slot": slot, "etched": True, "on_roster": False})
            out[(t, w["week"])] = [{k: v for k, v in x.items() if k not in ("row_id", "added_asof", "added_at")} for x in entries]
    return out


def rewind(cur, scenario: str, weeks: list[dict], new_today: date) -> None:
    """The replay clock moved back: forget what was etched for weeks that haven't ended as of the new date."""
    open_weeks = [w["week"] for w in weeks if w["end"] >= new_today]
    if open_weeks:
        cur.execute("DELETE FROM fantasy_lock_ledger WHERE scenario = %s AND week = ANY(%s)", (scenario, open_weeks))  # live refuses
        cur.execute("DELETE FROM fantasy_lineups WHERE scenario = %s AND week = ANY(%s)", (scenario, open_weeks))
        cur.execute("DELETE FROM fantasy_lineup_weeks WHERE scenario = %s AND week = ANY(%s)", (scenario, open_weeks))
