"""Team rosters week by week: who sits in which spot, moving players, and the weekly lineup lock.

- Spots: G / F / C (players listed at that position), TEAM (an NBA team), FLEX (anyone),
  BENCH (anyone, doesn't score). Same rule as logic.open_slot, minus the "first fit" order.
- Lock (like Fantrax): each player locks at his NBA team's first game of the week. A move that
  only involves unlocked players changes this week too; otherwise it applies from next week.
- History: fantasy_rosters is the current lineup (next week and on). Each week's lineup is saved
  to fantasy_lineups the first time anything changes after that week started, so moving players
  never rewrites a week that's already being played or scored. The results engine reads a week's
  saved lineup when there is one, else the current roster.
"""
from datetime import date, datetime, timezone

from .engine import as_of, league, weeks_for_league
from .logic import SLOT_POSITIONS, player_points, team_game_points
from .weeks import league_settings, slot_list, week_for


def eligible(entry: dict, slot: str) -> bool:
    if slot in ("FLEX", "BENCH"):
        return True
    if entry["kind"] == "nba_team":
        return slot == "TEAM"
    return slot in SLOT_POSITIONS and entry.get("position") in SLOT_POSITIONS[slot]


def _roster(cur, scenario: str, team_id: str) -> list[dict]:
    cur.execute("""
        SELECT r.id AS row_id, r.slot, r.player_id, r.nba_team_id, COALESCE(p.name, n.name) AS name,
               p.position, p.nba_team
        FROM fantasy_rosters r
        LEFT JOIN fantasy_players p ON p.id = r.player_id
        LEFT JOIN fantasy_nba_teams n ON n.id = r.nba_team_id
        WHERE r.scenario = %s AND r.team_id = %s ORDER BY r.pick_no NULLS LAST, r.id
    """, (scenario, team_id))
    out = []
    for r in cur.fetchall():
        kind = "player" if r["player_id"] else "nba_team"
        out.append({"id": r["player_id"] or r["nba_team_id"], "kind": kind, "name": r["name"], "slot": r["slot"],
                    "position": r["position"] if kind == "player" else "TEAM",
                    "nba_team": r["nba_team"] if kind == "player" else r["nba_team_id"], "row_id": r["row_id"]})
    return out


def saved_slots(cur, scenario: str) -> dict:
    """(team_id, week) → {entity_id: slot} for every saved weekly lineup in the league."""
    cur.execute("SELECT team_id, week, entity_id, slot FROM fantasy_lineups WHERE scenario = %s", (scenario,))
    out = {}
    for r in cur.fetchall():
        out.setdefault((r["team_id"], r["week"]), {})[r["entity_id"]] = r["slot"]
    return out


def _week_games(cur, season: str, week: dict, tricodes: list[str]) -> dict:
    """tricode → that team's regular-season games in the week, in date order."""
    if not tricodes:
        return {}
    cur.execute("""
        SELECT game_id, game_date, tipoff_utc, status, home_team, away_team, home_score, away_score FROM nba_games
        WHERE season = %s AND game_type = 'regular' AND missing_since IS NULL
          AND game_date BETWEEN %s AND %s AND (home_team = ANY(%s::text[]) OR away_team = ANY(%s::text[]))
        ORDER BY game_date, tipoff_utc NULLS LAST
    """, (season, week["start"], week["end"], tricodes, tricodes))
    out = {}
    for g in cur.fetchall():
        for t in (g["home_team"], g["away_team"]):
            if t in tricodes:
                out.setdefault(t, []).append(g)
    return out


def _started(g: dict, today: date, replay: bool) -> bool:
    """Has this game started as of the league's clock? The replay treats a whole day as played."""
    if g["game_date"] < today:
        return True
    if g["game_date"] > today:
        return False
    if replay:
        return True
    return bool(g["tipoff_utc"] and g["tipoff_utc"] <= datetime.now(timezone.utc))


def _locked(entry: dict, games: dict, today: date, replay: bool) -> bool:
    gs = games.get(entry["nba_team"]) or []
    return bool(gs) and _started(gs[0], today, replay)


def _freeze_started_weeks(cur, scenario: str, team_id: str, roster: list[dict], weeks: list[dict], today: date) -> None:
    """Save the current lineup for every week that has started and has no saved lineup yet."""
    cur.execute("SELECT DISTINCT week FROM fantasy_lineups WHERE scenario = %s AND team_id = %s", (scenario, team_id))
    have = {r["week"] for r in cur.fetchall()}
    for w in weeks:
        if w["start"] <= today and w["week"] not in have:
            for e in roster:
                cur.execute("""INSERT INTO fantasy_lineups (scenario, team_id, week, entity_id, slot) VALUES (%s, %s, %s, %s, %s)
                               ON CONFLICT DO NOTHING""", (scenario, team_id, w["week"], e["id"], e["slot"]))


def move(cur, scenario: str, user: dict, team_id: str, entity_id: str, to_slot: str, swap_with: str | None = None) -> dict:
    """Move a player into `to_slot`; if it's full, swap with `swap_with` (who must fit the spot
    he's leaving). Owner or commissioner. Returns {"applies": "now" | "next_week"}."""
    cur.execute("SELECT owner_user_id FROM fantasy_teams WHERE scenario = %s AND id = %s", (scenario, team_id))
    team = cur.fetchone()
    if not team:
        raise ValueError("no such team")
    if team["owner_user_id"] != user.get("discord_id") and not user.get("is_admin"):
        raise PermissionError("not your team")
    settings = league_settings(cur, scenario)
    if to_slot not in settings["roster_slots"]:
        raise ValueError("this league has no such spot")
    roster = _roster(cur, scenario, team_id)
    by_id = {e["id"]: e for e in roster}
    mover = by_id.get(entity_id)
    if not mover:
        raise ValueError("he isn't on this roster")
    if mover["slot"] == to_slot:
        return {"applies": "now"}
    if not eligible(mover, to_slot):
        raise ValueError(f"{mover['name']} can't play {to_slot}")
    in_slot = [e for e in roster if e["slot"] == to_slot]
    partner = None
    if len(in_slot) >= settings["roster_slots"][to_slot]:
        partner = by_id.get(swap_with) if swap_with else (in_slot[0] if len(in_slot) == 1 else None)
        if not partner or partner["slot"] != to_slot:
            raise ValueError("that spot is full — pick who to swap with")
        if not eligible(partner, mover["slot"]):
            raise ValueError(f"{partner['name']} can't play {mover['slot']}")

    lg = league(cur, scenario)
    today, weeks = as_of(lg), weeks_for_league(cur, lg)
    current = week_for(weeks, today)
    moved = [mover] + ([partner] if partner else [])
    games = _week_games(cur, lg["season"], current, [e["nba_team"] for e in moved]) if current else {}
    now_ok = not current or not any(_locked(e, games, today, scenario == "replay") for e in moved)

    _freeze_started_weeks(cur, scenario, team_id, roster, weeks, today)
    old_slot = mover["slot"]
    cur.execute("UPDATE fantasy_rosters SET slot = %s WHERE id = %s", (to_slot, mover["row_id"]))
    if partner:
        cur.execute("UPDATE fantasy_rosters SET slot = %s WHERE id = %s", (old_slot, partner["row_id"]))
    if current and now_ok:  # nobody involved has played this week yet: this week changes too
        cur.execute("UPDATE fantasy_lineups SET slot = %s WHERE scenario = %s AND team_id = %s AND week = %s AND entity_id = %s",
                    (to_slot, scenario, team_id, current["week"], mover["id"]))
        if partner:
            cur.execute("UPDATE fantasy_lineups SET slot = %s WHERE scenario = %s AND team_id = %s AND week = %s AND entity_id = %s",
                        (old_slot, scenario, team_id, current["week"], partner["id"]))
    return {"applies": "now" if now_ok else "next_week"}


def week_view(cur, scenario: str, team_id: str, week_no: int | None = None) -> dict:
    """One team's lineup for one week: each spot's player, his games that week (opponent, date,
    played or not, fantasy points / margin), best game, season points per game, and the lock."""
    lg = league(cur, scenario)
    season, today = lg["season"], as_of(lg)
    replay = scenario == "replay"
    weeks = weeks_for_league(cur, lg)
    current = week_for(weeks, today)
    if week_no is None:
        week = current or (weeks[0] if weeks and today < weeks[0]["start"] else (weeks[-1] if weeks else None))
    else:
        week = next((w for w in weeks if w["week"] == week_no), None)
    if not week:
        raise ValueError("no such week")
    settings = league_settings(cur, scenario)
    roster = _roster(cur, scenario, team_id)
    saved = saved_slots(cur, scenario).get((team_id, week["week"]))
    if saved:
        for e in roster:
            e["slot"] = saved.get(e["id"], e["slot"])
    is_current = bool(current and current["week"] == week["week"])
    games = _week_games(cur, season, week, sorted({e["nba_team"] for e in roster if e["nba_team"]}))

    pids = [e["id"] for e in roster if e["kind"] == "player"]
    box = {}  # (player_id, game_id) -> points
    season_pts = {}
    if pids:
        cur.execute("""
            SELECT pg.player_id, pg.game_id, g.game_date, pg.pts, pg.fgm, pg.fga, pg.fg3m, pg.ftm, pg.fta, pg.oreb, pg.dreb,
                   pg.ast, pg.stl, pg.blk, pg.tov, pg.blkd, pg.minutes
            FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
            WHERE pg.season = %s AND g.game_type = 'regular' AND g.game_date <= %s AND pg.player_id = ANY(%s::text[])
        """, (season, today, pids))
        sums = {}
        for r in cur.fetchall():
            if r["minutes"] > 0:
                p = player_points(r)
                box[(r["player_id"], r["game_id"])] = p
                s = sums.setdefault(r["player_id"], [0.0, 0])
                s[0] += p
                s[1] += 1
            else:
                box[(r["player_id"], r["game_id"])] = None  # dressed, didn't play
        season_pts = {k: round(v[0] / v[1], 1) for k, v in sums.items() if v[1]}

    tris = [e["id"] for e in roster if e["kind"] == "nba_team"]
    if tris:
        cur.execute("""
            SELECT home_team, away_team, home_score, away_score FROM nba_games
            WHERE season = %s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL AND game_date <= %s
              AND (home_team = ANY(%s::text[]) OR away_team = ANY(%s::text[]))
        """, (season, today, tris, tris))
        tot = {}
        for g in cur.fetchall():
            for t, mine, theirs in ((g["home_team"], g["home_score"], g["away_score"]), (g["away_team"], g["away_score"], g["home_score"])):
                if t in tris:
                    s = tot.setdefault(t, [0.0, 0])
                    s[0] += team_game_points(mine > theirs, mine, theirs)
                    s[1] += 1
        season_pts.update({k: round(v[0] / v[1], 1) for k, v in tot.items() if v[1]})

    out = []
    for e in roster:
        gl = []
        for g in games.get(e["nba_team"], []):
            home = g["home_team"] == e["nba_team"]
            opp = g["away_team"] if home else g["home_team"]
            played = g["game_date"] <= today and g["status"] == "final" if not replay else g["game_date"] <= today
            pts = None
            if played:
                if e["kind"] == "player":
                    pts = box.get((e["id"], g["game_id"]))
                elif g["home_score"] is not None:
                    mine, theirs = (g["home_score"], g["away_score"]) if home else (g["away_score"], g["home_score"])
                    pts = team_game_points(mine > theirs, mine, theirs)
            gl.append({"date": g["game_date"].isoformat(), "opp": opp, "home": home, "played": played,
                       "points": round(pts, 1) if pts is not None else None})
        vals = [x["points"] for x in gl if x["points"] is not None]
        week_score = (round(sum(vals), 1) if e["kind"] == "nba_team" else round(max(vals), 1)) if vals else None
        out.append({**{k: v for k, v in e.items() if k != "row_id"}, "games": gl, "week_score": week_score,
                    "season_ppg": season_pts.get(e["id"]),
                    "locked": is_current and _locked(e, games, today, replay)})
    starters = sum(x["week_score"] or 0 for x in out if x["slot"] != "BENCH")
    return {
        "team_id": team_id, "week": {"week": week["week"], "label": week["label"], "kind": week["kind"],
                                     "start": week["start"].isoformat(), "end": week["end"].isoformat()},
        "current_week": current["week"] if current else None, "as_of": today.isoformat(), "is_current": is_current,
        "weeks": [{"week": w["week"], "label": w["label"], "start": w["start"].isoformat(), "end": w["end"].isoformat()} for w in weeks],
        "roster_slots": settings["roster_slots"], "slot_list": slot_list(settings), "entries": out,
        "starters_score": round(starters, 1), "season": season,
    }
