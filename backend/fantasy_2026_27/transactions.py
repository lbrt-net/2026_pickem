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
from .engine import as_of, kept_results, league, weeks_for_league
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


def checkout(cur, scenario: str, user: dict, team_id: str, adds: list[str], drops: list[str], apply: bool, via: str = "free_agent") -> dict:
    """Check (apply=False) or make (apply=True) one team's adds and drops. Returns the roster after the moves:
    {ok, error, roster: [{id, kind, name, position, nba_team, slot, change: keep | add | drop, moved_from (re-seated to fit)}],
    spots_used, spots_total}."""
    from . import waivers
    _team(cur, scenario, team_id, user)
    if via != "waivers":
        waivers.process(cur, scenario)  # settle any waivers that are up before looking at who's free
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
    from .lineup import ir_lock_week
    week_now = None
    for d in drops:
        if d not in mine:
            raise ValueError("you can only drop your own players")
        if mine[d]["slot"] == "IR" and mine[d].get("ir_until") is not None:
            week_now = ir_lock_week(cur, scenario) if week_now is None else week_now
            if week_now < mine[d]["ir_until"]:  # free to drop once his last IR week is under way
                raise ValueError(f"{mine[d]['name']} is locked on IR through Week {mine[d]['ir_until']}")
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
    if via != "waivers":
        held = waivers.on_waivers(cur, scenario)
        for a in adds:
            if a in held:
                raise ValueError(f"{info[a]['name']} is on waivers — put in a claim instead")

    on_ir = [e for e in roster if e["slot"] == "IR" and e["id"] not in drops]  # IR is extra room: not counted, not reseated
    kept = [e for e in roster if e["id"] not in drops and e["slot"] != "IR"]
    new = [info[a] for a in adds]
    seat = _seat(kept, new, slots) if len(kept) + len(new) <= sum(slots.values()) else None
    order = {t: i for i, t in enumerate(slot_list(settings))}
    after = ([{**{k: e[k] for k in ("id", "kind", "name", "position", "nba_team")}, "slot": (seat or {}).get(e["id"], e["slot"]),
               "change": "keep", "moved_from": e["slot"] if seat and seat[e["id"]] != e["slot"] else None} for e in kept]
             + [{**e, "slot": (seat or {}).get(e["id"]), "change": "add"} for e in new])
    after.sort(key=lambda e: (order.get(e["slot"], 99), e["change"] == "add"))
    after += [{**{k: e[k] for k in ("id", "kind", "name", "position", "nba_team")}, "slot": "IR", "change": "keep"} for e in on_ir]
    dropped = [{**{k: mine[d][k] for k in ("id", "kind", "name", "position", "nba_team", "slot")}, "change": "drop"} for d in drops]
    result = {"ok": seat is not None, "error": None if seat is not None else _why_not(kept + new, slots),
              "roster": after + dropped, "spots_used": len(after) - len(on_ir), "spots_total": sum(slots.values())}
    if not apply or seat is None:
        if apply:
            raise ValueError(result["error"])
        return result

    lg = league(cur, scenario)
    today = as_of(lg)
    weeks = weeks_for_league(cur, lg)
    etch_mod.etch(cur, scenario, lg["season"], weeks, today, team_id)  # history first
    before = etch_mod.week_spots(cur, scenario, lg["season"], weeks, today, team_id)
    by = user.get("discord_id")
    for d in drops:
        real = waivers.was_real(cur, scenario, team_id, mine[d], weeks)
        cur.execute("DELETE FROM fantasy_rosters WHERE id = %s", (mine[d]["row_id"],))
        # every drop is kept (2026-10-27: the old erase took Hit and Run's Jarrett Allen claim with it); a real one also
        # puts him on waivers for 2 days, otherwise (added and dropped before he ever locked in) he's a free agent again
        # and the log hides the pair when the add was a free-agent add (log)
        cur.execute("""INSERT INTO fantasy_transactions (scenario, team_id, kind, entity_id, slot, asof, by_user, undone)
                       VALUES (%s, %s, 'drop', %s, %s, %s, %s, %s)""", (scenario, team_id, d, mine[d]["slot"], today, by, not real))
        if real:
            waivers.put_on_waivers(cur, scenario, d, team_id, today)
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
            cur.execute("""INSERT INTO fantasy_transactions (scenario, team_id, kind, entity_id, slot, asof, by_user, via)
                           VALUES (%s, %s, 'add', %s, %s, %s, %s, %s)""", (scenario, team_id, e["id"], seat[e["id"]], today, by, via))
    except psycopg2.errors.UniqueViolation:
        raise ValueError("someone else just added one of these players")
    if drops:  # gone from the week under way too (a locked one keeps his spot from the lock record)
        cur.execute("DELETE FROM fantasy_lineups WHERE scenario = %s AND team_id = %s AND entity_id = ANY(%s::text[])",
                    (scenario, team_id, drops))
    # 2026-10-26 (Cody: LaMelo dropped, Deni re-seated to G pushed him out of week 2): nobody's spot in the week under
    # way moves; an add takes an open spot this week he can play, else starts next week (etch.week_lineups)
    etch_mod.keep_week(cur, scenario, lg["season"], weeks, today, team_id, before)
    waivers.prune(cur, scenario, team_id, skip=tuple(adds))  # claims this move broke (their drop is gone, no room) are cancelled
    return result


def waiver_order(cur, scenario: str) -> dict:
    """The claim order right now (waivers._priority) for the Transaction Log's Waiver order tab: each team's record and
    points for at the period's first lock (the reverse-standings part, frozen for the period — waivers.base_standings)
    and the claims it won since the last reset (why it's at the back)."""
    from . import waivers
    lg = league(cur, scenario)
    now = waivers._clock(lg, scenario)
    per = waivers.period(cur, scenario, now)
    start = per[0]
    res = kept_results(cur, scenario)
    table = {r["team"]["id"]: r for r in waivers.base_standings(res, per[1])}
    won = {}
    if start is not None:
        col = "until_asof" if scenario == waivers.REPLAY else "until_at"
        cur.execute(f"""SELECT w.claimed_by, w.{col} AS at, COALESCE(p.name, n.name) AS name FROM fantasy_waivers w
                        LEFT JOIN fantasy_players p ON p.id = w.entity_id LEFT JOIN fantasy_nba_teams n ON n.id = w.entity_id
                        WHERE w.scenario = %s AND w.status = 'claimed' AND w.{col} >= %s AND w.{col} <= %s ORDER BY w.{col}""",
                    (scenario, start, now))
        for r in cur.fetchall():
            won.setdefault(r["claimed_by"], []).append({"name": r["name"], "at": r["at"].isoformat()})
    cur.execute("SELECT id, name FROM fantasy_teams WHERE scenario = %s", (scenario,))
    names = {r["id"]: r["name"] for r in cur.fetchall()}
    out = []
    for t in waivers._priority(cur, scenario, now, res=res, per=per):
        s = table.get(t) or {}
        out.append({"team_id": t, "team_name": names.get(t, t), "w": s.get("w", 0), "l": s.get("l", 0), "t": s.get("t", 0),
                    "pf": s.get("pf", 0), "won": won.get(t, [])})
    return {"waiver_order": out, "waiver_reset": start.isoformat() if start is not None else None}


def ghosts(rows: list[dict]) -> set:
    """Row ids the log hides (2026-10-27, kept in the table): a free-agent add dropped again before he ever locked in,
    and that drop (Hit and Run: Kel'el Ware → Diabaté → Paul Reed, each gone before a lock). A waiver claim is never
    hidden, nor the drop that undid it. A not-real drop whose add is missing (erased by the old rule) is hidden too."""
    last_add, out = {}, set()
    for r in sorted(rows, key=lambda r: (r["at"], r["id"])):
        k = (r["team_id"], r["entity_id"])
        if r["kind"] == "add":
            last_add[k] = r
        elif r.get("undone"):
            a = last_add.pop(k, None)
            if a is None:
                out.add(r["id"])
            elif a.get("via") not in ("waivers", "trade"):
                out |= {a["id"], r["id"]}
        else:
            last_add.pop(k, None)
    return out


def _join_moves(items: list[dict]) -> list[dict]:
    """Newest-first checkouts → moves: a drop-only checkout and the same team's very next checkout, when that one is
    a free-agent add only (not a claim or trade) in the same week, become one entry at the add's time."""
    nxt, out, used = {}, [], set()
    for i in range(len(items)):  # newest first: nxt = each team's following (newer) checkout
        g = items[i]
        if g["drops"] and not g["adds"] and g["via"] != "trade":
            j = nxt.get(g["team_id"])
            if j is not None and items[j]["adds"] and not items[j]["drops"] and items[j]["via"] is None \
                    and items[j]["week"] == g["week"]:
                items[j] = {**items[j], "drops": g["drops"], "drop_at": g["at"]}
                used.add(i)
        nxt[g["team_id"]] = i
    for i, g in enumerate(items):
        if i not in used:
            out.append(g)
    return out


def log(cur, scenario: str) -> dict:
    """The league's adds and drops, newest first: when (and the league date / fantasy week it fell in), the team, who
    made it (owner or commissioner), and the players. One entry per move (2026-10-27): a checkout (same team, same
    moment), and a drop on its own joined with the same team's next checkout when that one only adds, in the same week
    — the drop opened the spot the add filled ("drop_at" = the drop's time, "at" = the add's)."""
    from . import waivers
    waivers.process(cur, scenario)
    lg = league(cur, scenario)
    weeks = weeks_for_league(cur, lg)
    cur.execute("""
        SELECT x.id, x.team_id, x.kind, x.entity_id, x.slot, x.asof, x.at, x.by_user, x.via, x.undone,
               t.name AS team_name, t.owner_user_id, COALESCE(p.name, n.name) AS name, p.position, p.nba_team
        FROM fantasy_transactions x
        JOIN fantasy_teams t ON t.id = x.team_id AND t.scenario = x.scenario
        LEFT JOIN fantasy_players p ON p.id = x.entity_id
        LEFT JOIN fantasy_nba_teams n ON n.id = x.entity_id
        WHERE x.scenario = %s ORDER BY x.at DESC, x.id
    """, (scenario,))
    rows = cur.fetchall()
    hidden = ghosts(rows)
    groups, order = {}, []
    for r in rows:
        if r["id"] in hidden:
            continue
        key = (r["team_id"], r["at"])
        if key not in groups:
            w = next((w for w in weeks if w["start"] <= r["asof"] <= w["end"]), None)
            groups[key] = {"at": r["at"].isoformat(), "asof": r["asof"].isoformat(), "week": w["week"] if w else None,
                           "week_label": w["label"] if w else None, "team_id": r["team_id"], "team_name": r["team_name"],
                           "by": "owner" if not r["by_user"] or r["by_user"] == r["owner_user_id"] else "commissioner",
                           "via": None,
                           "adds": [], "drops": []}
            order.append(key)
        if r["kind"] == "add" and r["via"] == "waivers":
            groups[key]["via"] = "waivers"
        if r["via"] == "trade":  # trades.py: the players each team got (adds) and sent (drops)
            groups[key]["via"] = "trade"
        kind = "player" if r["position"] is not None or r["nba_team"] is not None else "nba_team"
        groups[key]["adds" if r["kind"] == "add" else "drops"].append(
            {"id": r["entity_id"], "name": r["name"], "kind": kind, "position": r["position"] if kind == "player" else "TEAM",
             "nba_team": r["nba_team"] if kind == "player" else r["entity_id"], "slot": r["slot"],
             # how this one player moved (2026-10-29): 'waivers' (a claim he was won on), 'trade' (got or sent in a
             # trade), None (a free-agent add / a plain drop)
             "via": r["via"] if r["via"] in ("waivers", "trade") else None})
    items = _join_moves([groups[k] for k in order])
    return {"items": items, "injuries": injury_log(cur, scenario, weeks), **waiver_order(cur, scenario), "adds": sum(len(g["adds"]) for g in items), "drops": sum(len(g["drops"]) for g in items),
            "weeks": [{"week": w["week"], "label": w["label"], "start": w["start"].isoformat(), "end": w["end"].isoformat()} for w in weeks]}


def injury_log(cur, scenario: str, weeks: list[dict]) -> list[dict]:
    """Injury updates (2026-10-30): every change the injury sync logged (nba_injury_events) for players in the pool,
    newest first by when ESPN posted it (shown: ESPN's time, else our sync's for cleared), with the fantasy team that has him now (None = free agent) and the fantasy week it fell in. Each
    carries his status now (current); minutes and FP per game this season (mpg_now / avg_now, gp_now games of his
    team's team_games so far) and over the 2 seasons before it (mpg2 / avg2; None = no games), for the page's filters
    (under 15 MPG hidden by default unless he's at 15+ over the 2 before — a regular who's missing now stays on); his
    projection (proj_mpg / proj_avg: what to show when he hasn't played this season — under 4 recent games the live
    blend is the preseason number); games missed in a row up to the change (missed) and team games before his return
    date (will_miss; Out only, None = no date)."""
    season = past_season(0)
    cur.execute("""
        SELECT e.id, e.player_id, e.kind, e.status, e.prev_status, e.injury, e.return_date, e.prev_return, e.comment,
               COALESCE(e.reported_at, e.at) AS at, e.at AS synced_at,
               (COALESCE(e.reported_at, e.at) AT TIME ZONE 'America/Chicago')::date AS asof, p.name, p.position, p.nba_team,
               r.team_id, t.name AS team_name, fp.proj_avg, (fp.proj_line->>'mpg')::float AS proj_mpg,
               (SELECT i.status FROM nba_injuries i WHERE i.player_id = e.player_id LIMIT 1) AS current
        FROM nba_injury_events e
        JOIN fantasy_players p ON p.id = e.player_id
        LEFT JOIN fantasy_pool fp ON fp.season = %s AND fp.player_id = e.player_id
        LEFT JOIN fantasy_rosters r ON r.scenario = %s AND r.player_id = e.player_id
        LEFT JOIN fantasy_teams t ON t.id = r.team_id AND t.scenario = r.scenario
        ORDER BY COALESCE(e.reported_at, e.at) DESC, e.id DESC LIMIT 1000
    """, (season, scenario))
    rows = cur.fetchall()
    if not rows:
        return []
    prev = per_game(cur, [past_season(1), past_season(2)], "2")
    now = per_game(cur, [season], "_now")
    games = _team_games(cur, season, {r["nba_team"] for r in rows if r["nba_team"]})
    played = _played(cur, season, {r["player_id"] for r in rows})
    out = []
    for r in rows:
        w = next((w for w in weeks if w["start"] <= r["asof"] <= w["end"]), None)
        tg = games.get(r["nba_team"], [])
        out.append({"id": r["id"], "at": r["at"].isoformat(), "synced_at": r["synced_at"].isoformat(), "week": w["week"] if w else None,
                    "week_label": w["label"] if w else None, "team_id": r["team_id"], "team_name": r["team_name"],
                    "kind": r["kind"], "status": r["status"], "prev_status": r["prev_status"], "injury": r["injury"],
                    "return_date": r["return_date"].isoformat() if r["return_date"] else None,
                    "prev_return": r["prev_return"].isoformat() if r["prev_return"] else None, "comment": r["comment"],
                    "current": r["current"],
                    **prev.get(r["player_id"], {"mpg2": None, "avg2": None, "gp2": 0}),
                    **now.get(r["player_id"], {"mpg_now": None, "avg_now": None, "gp_now": 0}),
                    "team_games": sum(1 for g in tg if g[2]),
                    "proj_mpg": round(r["proj_mpg"], 1) if r["proj_mpg"] is not None else None,
                    "proj_avg": round(r["proj_avg"], 1) if r["proj_avg"] is not None else None,
                    **_missed(tg, played.get(r["player_id"], set()), r),
                    "player": {"id": r["player_id"], "name": r["name"], "kind": "player", "position": r["position"],
                               "nba_team": r["nba_team"]}})
    return out

def past_season(k: int) -> str:
    """The season k years before this one ('2026-27' → k=1 '2025-26')."""
    from .player_page import LIVE
    y = int(LIVE[:4]) - k
    return f"{y}-{str(y + 1)[2:]}"


def per_game(cur, seasons: list[str], suffix: str) -> dict:
    """player id → {"mpg<suffix>", "avg<suffix>"}: minutes and fantasy points per game played over these seasons, all
    games pooled (regular season; the player page's cached season summaries)."""
    from .player_page import season_data
    tot = {}
    for season in seasons:
        for pid, sm in season_data(cur, season)["summ"].items():
            t = tot.setdefault(pid, [0, 0.0, 0.0])
            t[0] += sm["gp"]; t[1] += sm["minutes"]; t[2] += sm["avg"] * sm["gp"]
    return {pid: {"mpg" + suffix: round(m / g, 1), "avg" + suffix: round(f / g, 1), "gp" + suffix: g}
            for pid, (g, m, f) in tot.items() if g}


def _team_games(cur, season: str, teams: set) -> dict:
    """NBA team → [(date, game_id, final)] for the season's regular-season games, in order."""
    cur.execute("""SELECT game_id, game_date, status, home_team, away_team FROM nba_games
                   WHERE season = %s AND game_type = 'regular' AND missing_since IS NULL AND game_date IS NOT NULL
                     AND (home_team = ANY(%s) OR away_team = ANY(%s)) ORDER BY game_date, game_id""",
                (season, list(teams), list(teams)))
    out = {}
    for g in cur.fetchall():
        for t in (g["home_team"], g["away_team"]):
            if t in teams:
                out.setdefault(t, []).append((g["game_date"], g["game_id"], g["status"] == "final"))
    return out


def _played(cur, season: str, ids: set) -> dict:
    cur.execute("SELECT player_id, game_id FROM nba_player_games WHERE season = %s AND minutes > 0 AND player_id = ANY(%s)",
                (season, list(ids)))
    out = {}
    for r in cur.fetchall():
        out.setdefault(r["player_id"], set()).add(r["game_id"])
    return out


def _missed(games: list, played: set, r) -> dict:
    """missed: his team's final games before the change's day that he sat, counting back until one he played (this
    season). will_miss: team games from that day until his return date while he's Out (the rest of the season when
    out for the season); None for Day-To-Day, cleared, or no return date."""
    day = r["asof"]
    missed = 0
    for _, gid, _ in reversed([g for g in games if g[0] < day and g[2]]):
        if gid in played:
            break
        missed += 1
    will = None
    if r["status"] == "Out For Season":
        will = sum(1 for d, _, _ in games if d >= day)
    elif r["status"] in ("Out", "Suspension") and r["return_date"]:
        will = sum(1 for d, _, _ in games if day <= d < r["return_date"])
    return {"missed": missed, "will_miss": will}
