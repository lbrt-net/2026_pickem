"""Team rosters week by week: who sits in which spot, moving players, and the weekly lineup lock.

- Spots: G / F / C (players listed at that position), TEAM (an NBA team), FLEX (anyone),
  BENCH (anyone, doesn't score). Same rule as logic.open_slot, minus the "first fit" order.
- Lock (per NBA team): each player locks 5 minutes before his NBA team's first game of the week.
  A move that only involves unlocked players changes this week too; otherwise it applies from
  next week. (The replay treats a whole day as played, so it locks on the game day.)
- History: fantasy_rosters is the current lineup (next week and on). Each week's lineup is saved
  to fantasy_lineups the first time anything changes after that week started, so moving players
  never rewrites a week that's already being played or scored. The results engine reads a week's
  saved lineup when there is one, else the current roster.
"""
from datetime import date, datetime, timedelta, timezone

from .engine import _prev_season, as_of, league, pairings, weeks_for_league
from .logic import SCORING_RULES, SLOT_POSITIONS, player_points, score_breakdown, team_game_points

_LABEL = {k: short for k, short, _ in SCORING_RULES}
from .settings import logo_url
from .weeks import league_settings, slot_list, week_for


def expected_best(scores: list[float], n: int, floor: float | None = None) -> float | None:
    """Projected best single game over `n` games: the expected maximum of n draws from the player's
    own game scores (order statistics), never below `floor` (his best already this week)."""
    if n <= 0 or not scores:
        return floor
    v = sorted(max(x, floor) if floor is not None else x for x in scores)
    m = len(v)
    return sum(x * (((i + 1) / m) ** n - (i / m) ** n) for i, x in enumerate(v))


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
    """Is this game within 5 minutes of tip-off (or later) as of the league's clock? The replay
    treats a whole day as played."""
    if g["game_date"] < today:
        return True
    if g["game_date"] > today:
        return False
    if replay:
        return True
    return bool(g["tipoff_utc"] and g["tipoff_utc"] - timedelta(minutes=5) <= datetime.now(timezone.utc))


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


def move(cur, scenario: str, user: dict, team_id: str, entity_id: str, to_slot: str, swap_with: str | None = None,
         week_no: int | None = None) -> dict:
    """Move a player into `to_slot`; if it's full, swap with `swap_with` (who must fit the spot
    he's leaving). Owner or commissioner. Returns {"applies": "now" | "next_week"}.
    `week_no` = the week being viewed: on the current week a locked player can't be moved at all."""
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
    if current and week_no == current["week"] and not now_ok:
        raise ValueError("locked for this week — switch to next week to change next week's lineup")

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
        # Forward-looking: once every starter on this team has locked this week, open next week.
        if current and week is current:
            nxt = next((w for w in weeks if w["week"] == current["week"] + 1), None)
            starters = [e for e in _roster(cur, scenario, team_id) if e["slot"] != "BENCH"]
            g = _week_games(cur, season, current, sorted({e["nba_team"] for e in starters if e["nba_team"]}))
            if nxt and starters and all(_locked(e, g, today, replay) or not g.get(e["nba_team"]) for e in starters):
                week = nxt
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
    box_rows = {}  # (player_id, game_id) -> the box score row
    scores = {}  # player id / tricode -> game scores (this season, + last season when thin)
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
                box_rows[(r["player_id"], r["game_id"])] = r
                scores.setdefault(r["player_id"], []).append(p)
                s = sums.setdefault(r["player_id"], [0.0, 0])
                s[0] += p
                s[1] += 1
            else:
                box[(r["player_id"], r["game_id"])] = None  # dressed, didn't play
        season_pts = {k: round(v[0] / v[1], 1) for k, v in sums.items() if v[1]}
        # Projection input: this season's games, topped up with last season's when there are few.
        thin = [pid for pid in pids if len(scores.get(pid, [])) < 10]
        if thin:
            cur.execute("""
                SELECT pg.player_id, pg.pts, pg.fgm, pg.fga, pg.fg3m, pg.ftm, pg.fta, pg.oreb, pg.dreb, pg.ast, pg.stl, pg.blk, pg.tov, pg.blkd
                FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
                WHERE pg.season = %s AND g.game_type = 'regular' AND pg.minutes > 0 AND pg.player_id = ANY(%s::text[])
            """, (_prev_season(season), thin))
            for r in cur.fetchall():
                scores.setdefault(r["player_id"], []).append(player_points(r))

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
                    m = team_game_points(mine > theirs, mine, theirs)
                    scores.setdefault(t, []).append(m)
                    s = tot.setdefault(t, [0.0, 0])
                    s[0] += m
                    s[1] += 1
        season_pts.update({k: round(v[0] / v[1], 1) for k, v in tot.items() if v[1]})
        thin_t = [t for t in tris if len(scores.get(t, [])) < 10]
        if thin_t:
            cur.execute("""
                SELECT home_team, away_team, home_score, away_score FROM nba_games
                WHERE season = %s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL
                  AND (home_team = ANY(%s::text[]) OR away_team = ANY(%s::text[]))
            """, (_prev_season(season), thin_t, thin_t))
            for g in cur.fetchall():
                for t, mine, theirs in ((g["home_team"], g["home_score"], g["away_score"]), (g["away_team"], g["away_score"], g["home_score"])):
                    if t in thin_t:
                        scores.setdefault(t, []).append(team_game_points(mine > theirs, mine, theirs))

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
            gl.append({"game_id": g["game_id"], "date": g["game_date"].isoformat(), "opp": opp, "home": home, "played": played,
                       "points": round(pts, 1) if pts is not None else None})
        vals = [x["points"] for x in gl if x["points"] is not None]
        week_score = (round(sum(vals), 1) if e["kind"] == "nba_team" else round(max(vals), 1)) if vals else None
        remaining = sum(1 for x in gl if not x["played"])
        hist = scores.get(e["id"], [])
        if e["kind"] == "player":
            proj = expected_best(hist, remaining, week_score) if remaining else week_score
            best_game = next((x for x in gl if x["points"] is not None and round(x["points"], 1) == week_score), None)
            r = box_rows.get((e["id"], best_game["game_id"])) if best_game else None
            box_line = (f"{r['pts']} PTS · {r['oreb'] + r['dreb']} REB · {r['ast']} AST"
                        + (f" · {r['stl']} STL" if r["stl"] >= 3 else "") + (f" · {r['blk']} BLK" if r["blk"] >= 3 else "")) if r else None
            # Best game's five biggest fantasy-point categories (either sign), for the matchup page.
            contrib = ([{"label": _LABEL[k], "points": v} for k, v in sorted(score_breakdown(r).items(), key=lambda kv: -abs(kv[1])) if v][:5]
                       if r else [])
            # Same game, every category in rules order (Roster's Points view). BLKD stays out until it's loaded.
            breakdown = {k: v for k, v in score_breakdown(r).items() if k != "blkd"} if r else None
        else:
            avg = sum(hist) / len(hist) if hist else 0.0
            proj = (week_score or 0.0) + avg * remaining if (remaining or week_score is not None) else None
            box_line = None
            contrib = []
            breakdown = None
        out.append({**{k: v for k, v in e.items() if k != "row_id"}, "games": [{k: v for k, v in x.items() if k != "game_id"} for x in gl],
                    "week_score": week_score, "box_line": box_line, "contrib": contrib, "breakdown": breakdown,
                    "games_done": sum(1 for x in gl if x["played"]),
                    "games_today": sum(1 for x in gl if not x["played"] and x["date"] == today.isoformat()),
                    "projected": round(proj, 1) if proj is not None else None, "games_left": remaining,
                    "season_ppg": season_pts.get(e["id"]),
                    # One game's projection (shown under each future game): the average game in the projection input.
                    "game_proj": round(sum(hist) / len(hist), 1) if hist else None,
                    "locked": is_current and _locked(e, games, today, replay)})
    starters = sum(x["week_score"] or 0 for x in out if x["slot"] != "BENCH")
    starters_proj = sum(x["projected"] or 0 for x in out if x["slot"] != "BENCH")
    # When this team's lineup starts locking this week: 5 min before its earliest first game.
    firsts = [gs[0] for t, gs in games.items() if gs and t in {e["nba_team"] for e in roster}]
    first = min(firsts, key=lambda g: (g["game_date"], g["tipoff_utc"] or datetime.max.replace(tzinfo=timezone.utc)), default=None)
    lock = None
    if first:
        lock = {"date": first["game_date"].isoformat(),
                "at": (first["tipoff_utc"] - timedelta(minutes=5)).isoformat() if first["tipoff_utc"] and not replay else None}
    # When rosters league-wide start locking this week: 5 min before the week's first game of any team.
    def first_lock(w):
        if not w:
            return None
        cur.execute("""
            SELECT game_date, tipoff_utc FROM nba_games WHERE season = %s AND game_type = 'regular' AND game_date BETWEEN %s AND %s
            ORDER BY game_date, tipoff_utc NULLS LAST LIMIT 1
        """, (season, w["start"], w["end"]))
        g0 = cur.fetchone()
        return ({"week": w["week"], "date": g0["game_date"].isoformat(),
                 "at": (g0["tipoff_utc"] - timedelta(minutes=5)).isoformat() if g0["tipoff_utc"] and not replay else None} if g0 else None)
    week_lock = first_lock(week)
    # Once this week has started locking, the clock counts to the next week's first lock.
    next_lock = first_lock(next((w for w in weeks if w["week"] == week["week"] + 1), None))
    # This week's opponent (same round-robin as the results engine).
    cur.execute("SELECT id, name, abbreviation, color, glyph, owner_user_id, logo_updated, picture_url FROM fantasy_teams WHERE scenario = %s", (scenario,))
    teams = []
    for t in cur.fetchall():
        t = dict(t)
        t["logo_url"] = logo_url(t)  # uploaded logo, else the owner's picture (TeamIcon falls back to the glyph)
        del t["logo_updated"], t["picture_url"]
        teams.append(t)
    opponent = None
    if week["kind"] == "regular":
        for a, b in pairings(teams, week["week"]):
            if a["id"] == team_id or b["id"] == team_id:
                opponent = b if a["id"] == team_id else a
    return {
        "team_id": team_id, "week": {"week": week["week"], "label": week["label"], "kind": week["kind"],
                                     "start": week["start"].isoformat(), "end": week["end"].isoformat()},
        "current_week": current["week"] if current else None, "as_of": today.isoformat(), "is_current": is_current,
        "weeks": [{"week": w["week"], "label": w["label"], "start": w["start"].isoformat(), "end": w["end"].isoformat()} for w in weeks],
        "roster_slots": settings["roster_slots"], "slot_list": slot_list(settings), "entries": out,
        "starters_score": round(starters, 1), "starters_projected": round(starters_proj, 1), "season": season,
        "lock": lock, "week_lock": week_lock, "next_lock": next_lock, "opponent": opponent, "replay": replay,
    }
