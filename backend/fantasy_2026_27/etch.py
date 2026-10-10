"""Lineup history: the live roster vs each week's etched lineup.

- The live roster (fantasy_rosters) is always changeable: Roster moves, adds and drops (later trades) apply to it
  at once. Nothing about it is locked.
- A week's lineup is etched into fantasy_lineups one entity at a time: when his first game of that week locks
  (5 minutes before tip-off; the replay treats the whole day as played), or when the week ends. An etched row never
  changes (only a future commissioner correction could), so a player dropped after he locked still counts for that
  week, and a player added after his lock only counts from next week.
- Writes are lazy: etch() runs before every roster change and saves everyone who locked since the last change.
  Nothing moved in between, so his live spot is the spot he locked in. Reads (week_lineups) combine the etched rows
  with the live roster for whoever isn't etched yet.
- Once etch() runs after a week has ended, the week is closed (fantasy_lineup_weeks): its lineup is the etched rows
  only, so later adds can't leak into it.
- fantasy_rosters.added_asof / added_at (NULL = from the draft) say whether an entity joined before his lock.
- A spot filled by etched entities is full for that week: dropping a locked player and adding someone into his spot
  doesn't give the spot a second scorer — the newcomer starts counting next week.
"""
from datetime import date, datetime, time, timedelta, timezone

from .weeks import league_settings, spot_caps, week_for

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
    return bool(g["tipoff_utc"] and g["tipoff_utc"] - timedelta(minutes=5) <= datetime.now(timezone.utc))


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
    if not weeks or not tricodes:
        return {}
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
    return out


def joined_in_time(e: dict, w: dict, g: dict | None, replay: bool) -> bool:
    """Did this entity join the team before his lock in week w (his first game; the week's end if he has none)?"""
    if e.get("added_asof") is None:  # from the draft
        return True
    if g is None:
        return e["added_asof"] <= w["end"]
    if replay:
        return e["added_asof"] < g["game_date"]
    lock_at = (g["tipoff_utc"] - timedelta(minutes=5) if g["tipoff_utc"]
               else datetime.combine(g["game_date"], time.min, tzinfo=timezone.utc))
    return e["added_at"] < lock_at


def _closed(cur, scenario: str) -> set:
    cur.execute("SELECT team_id, week FROM fantasy_lineup_weeks WHERE scenario = %s", (scenario,))
    return {(r["team_id"], r["week"]) for r in cur.fetchall()}


def etch(cur, scenario: str, season: str, weeks: list[dict], today: date, team_id: str) -> None:
    """Save every entity of this team that has locked (or whose week has ended) and isn't etched yet, then close the
    weeks that are over. Run before any change to the team's live roster."""
    replay = scenario == REPLAY
    begun = [w for w in weeks if w["start"] <= today]
    if not begun:
        return
    closed = _closed(cur, scenario)
    roster = live_rosters(cur, scenario, team_id).get(team_id, [])
    cap = spot_caps(league_settings(cur, scenario))
    cur.execute("SELECT week, entity_id, slot FROM fantasy_lineups WHERE scenario = %s AND team_id = %s", (scenario, team_id))
    have, used = set(), {}
    for r in cur.fetchall():
        have.add((r["week"], r["entity_id"]))
        used[(r["week"], r["slot"])] = used.get((r["week"], r["slot"]), 0) + 1
    fg = first_games(cur, season, begun, sorted({e["nba_team"] for e in roster if e["nba_team"]}))
    for w in begun:
        if (team_id, w["week"]) in closed:
            continue
        over = w["end"] < today
        for e in roster:
            if (w["week"], e["id"]) in have:
                continue
            g = fg.get((e["nba_team"], w["week"]))
            if not joined_in_time(e, w, g, replay):
                continue
            if (over or (g and started(g, today, replay))) and used.get((w["week"], e["slot"]), 0) < cap.get(e["slot"], 0):
                used[(w["week"], e["slot"])] = used.get((w["week"], e["slot"]), 0) + 1
                cur.execute("""INSERT INTO fantasy_lineups (scenario, team_id, week, entity_id, slot) VALUES (%s, %s, %s, %s, %s)
                               ON CONFLICT DO NOTHING""", (scenario, team_id, w["week"], e["id"], e["slot"]))
        if over:
            cur.execute("INSERT INTO fantasy_lineup_weeks (scenario, team_id, week) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                        (scenario, team_id, w["week"]))


def week_lineups(cur, scenario: str, season: str, weeks: list[dict], today: date, team_id: str | None = None) -> dict:
    """(team id, week no) → that week's lineup for every week that has begun: the etched entities (in the spot they
    locked in, even if since dropped), plus — unless the week is closed — live-roster entities not etched yet who
    joined before their lock. Each entry: id, kind, name, slot, position, nba_team, etched, on_roster."""
    replay = scenario == REPLAY
    begun = [w for w in weeks if w["start"] <= today]
    if not begun:
        return {}
    cap = spot_caps(league_settings(cur, scenario))
    live = live_rosters(cur, scenario, team_id)
    closed = _closed(cur, scenario)
    cur.execute("SELECT team_id, week, entity_id, slot FROM fantasy_lineups WHERE scenario = %s AND (%s::text IS NULL OR team_id = %s)",
                (scenario, team_id, team_id))
    etched = {}
    for r in cur.fetchall():
        etched.setdefault((r["team_id"], r["week"]), {})[r["entity_id"]] = r["slot"]
    # Who the etched-but-dropped entities are
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
            entries = []
            for e in mine:  # live order first
                if e["id"] in rows:
                    entries.append({**e, "slot": rows[e["id"]], "etched": True, "on_roster": True})
                elif ((t, w["week"]) not in closed and used.get(e["slot"], 0) < cap.get(e["slot"], 0)
                      and joined_in_time(e, w, fg.get((e["nba_team"], w["week"])), replay)):
                    used[e["slot"]] = used.get(e["slot"], 0) + 1
                    entries.append({**e, "etched": False, "on_roster": True})
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
        cur.execute("DELETE FROM fantasy_lineups WHERE scenario = %s AND week = ANY(%s)", (scenario, open_weeks))
        cur.execute("DELETE FROM fantasy_lineup_weeks WHERE scenario = %s AND week = ANY(%s)", (scenario, open_weeks))
