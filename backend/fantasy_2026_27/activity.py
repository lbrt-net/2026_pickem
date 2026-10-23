"""League activity (Home): the most impactful moves, not the latest ones (DECISIONS.md 2026-10-10).

- Only moves that happened: the Transaction Log already holds only real moves (add-then-drop before any lock leaves
  it); a real drop shows when it's made, an add only once that player has locked into that team's lineup
  (a fantasy_lineups row for the team, that week or later).
- One entry per team per week (lock to lock; "pre" = before Week 1): its net change — a player added and dropped
  inside the same week never appears.
- Impact = the biggest value among the entry's players (not the sum), frozen as of the week the move happened (PROJ
  MAX blended with his actual weeks before it — later games never change it). Every entry halves at the same moment
  — each time a new week starts — so two moves' relative weight never changes: an old move can't jump a newer one or
  vice versa; only new moves slot in. The draft is one entry: its three biggest picks (as of week 0).
- The impact number is only for ranking; it is never sent to the page.
"""
from .engine import as_of, league, weeks_for_league
from . import projections
from .transactions import log as tx_log

TOP = 15            # entries kept (the Home box shows as many of the most important as fit)
ROLE_RANK = 25      # replacement level for a player: the 25th best at his role (G / F / C)
TEAM_RANK = 13      # for an NBA team: the 13th best team


def _values(cur, scenario) -> "callable":
    """importance(entity, week): how much he's worth above a replacement player, as of the start of that week
    (commissioner, 2026-10-23). Value = the site's blend — 25% preseason PROJ MAX + 75% his weekly best over the last
    4 weeks before it, once he has 4+ games there (projections.season_weight), else PROJ MAX. Replacement = the 25th
    best value at his role (G / F / C), or the 13th best NBA team, that same week. Never below 0. Only games before the
    move's week count, so an old move's importance never changes."""
    from .board import actual
    season = projections.league_season(cur, scenario)
    lg = league(cur, scenario)
    weeks = weeks_for_league(cur, lg)
    cur.execute("SELECT player_id AS id, proj_max, proj_weeks, position FROM fantasy_pool WHERE season = %s AND proj_max IS NOT NULL", (season,))
    proj, role = {}, {}
    for r in cur.fetchall():
        proj[r["id"]] = projections.shown_max(r["proj_weeks"], r["proj_max"])
        role[r["id"]] = r["position"]
    cur.execute("SELECT team AS id, proj_max FROM fantasy_team_pool WHERE season = %s AND proj_max IS NOT NULL", (season,))
    for r in cur.fetchall():
        proj[r["id"]], role[r["id"]] = r["proj_max"], "TEAM"
    weekly = {eid: {int(k): v for k, v in row.get("weeks", {}).items()}
              for eid, row in actual(cur, scenario, "season", with_weeks=True)["players"].items()}
    # games played per fantasy week (players: minutes > 0; NBA teams: every final game) — for the 4-games rule
    games: dict = {}
    wk_of = lambda d: next((w["week"] for w in weeks if w["start"] <= d <= w["end"]), None)
    cur.execute("""SELECT pg.player_id AS id, g.game_date FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
                   WHERE pg.season = %s AND g.game_type = 'regular' AND pg.minutes > 0""", (lg["season"],))
    rows = cur.fetchall()
    cur.execute("SELECT home_team, away_team, game_date FROM nba_games WHERE season = %s AND game_type = 'regular' AND status = 'final'", (lg["season"],))
    rows += [{"id": t, "game_date": g["game_date"]} for g in cur.fetchall() for t in (g["home_team"], g["away_team"])]
    for r in rows:
        w = wk_of(r["game_date"])
        if w:
            games.setdefault(r["id"], {}).setdefault(w, 0)
            games[r["id"]][w] += 1

    def value(eid, week):
        p = proj.get(eid)
        window = [k for k in range((week or 0) - projections.RECENT_WEEKS, week or 0)]
        n = sum(games.get(eid, {}).get(k, 0) for k in window)
        ws = [weekly.get(eid, {})[k] for k in window if k in weekly.get(eid, {})]
        w = projections.season_weight(n) if ws else 0.0
        if p is None:
            return sum(ws) / len(ws) if ws else 0.0
        return (1 - w) * p + w * (sum(ws) / len(ws)) if w else p

    repl_cache: dict = {}

    def replacement(week, r):
        if week not in repl_cache:
            by: dict = {}
            for eid in proj:
                by.setdefault(role.get(eid), []).append(value(eid, week))
            repl_cache[week] = {k: (sorted(v, reverse=True)[(TEAM_RANK if k == "TEAM" else ROLE_RANK) - 1]
                                    if len(v) >= (TEAM_RANK if k == "TEAM" else ROLE_RANK) else 0.0) for k, v in by.items()}
        return repl_cache[week].get(r, 0.0)

    def importance(eid, week):
        week = week or 0
        return max(0.0, value(eid, week) - replacement(week, role.get(eid)))
    return importance


def activity(cur, scenario: str) -> dict:
    lg = league(cur, scenario)
    weeks = weeks_for_league(cur, lg)
    today = as_of(lg)
    items = tx_log(cur, scenario)["items"]
    cur.execute("SELECT team_id, week, entity_id FROM fantasy_lineups WHERE scenario = %s", (scenario,))
    locked = {}  # (team, entity) -> earliest week he locked in for that team
    for r in cur.fetchall():
        k = (r["team_id"], r["entity_id"])
        locked[k] = min(locked.get(k, r["week"]), r["week"])
    value = _values(cur, scenario)
    # every entry halves at the same moment: when a new week starts (weeks since its week; before the season = 0)
    cw = next((w["week"] for w in weeks if w["start"] <= today <= w["end"]), None)
    if cw is None:
        cw = max((w["week"] for w in weeks if w["end"] < today), default=0)
    fade = lambda week: 0.5 ** max(0, cw - (week or 0))

    # one entry per team per week: net change
    groups = {}
    for g in items:  # newest first
        key = (g["team_id"], g["week"] or 0)
        e = groups.setdefault(key, {"kind": "moves", "team_id": g["team_id"], "team_name": g["team_name"], "week": g["week"],
                                    "week_label": g["week_label"], "at": g["at"], "asof": g["asof"], "via": None, "adds": {}, "drops": {}})
        for p in g["adds"]:
            e["adds"].setdefault(p["id"], {**p, "_via": g["via"]})
        for p in g["drops"]:
            e["drops"].setdefault(p["id"], p)
    entries = []
    for e in groups.values():
        both = set(e["adds"]) & set(e["drops"])  # came and went (or left and came back) inside the week: no change
        wk = e["week"] or 0
        adds = [p for i, p in e["adds"].items() if i not in both and locked.get((e["team_id"], i), -1) >= wk]  # locked in
        drops = [p for i, p in e["drops"].items() if i not in both]
        e["via"] = "waivers" if any(p.get("_via") == "waivers" for p in adds) else None
        adds = [{k: v for k, v in p.items() if k != "_via"} for p in adds]
        if not adds and not drops:
            continue
        impact = max((value(p["id"], e["week"]) for p in adds + drops), default=0.0)  # frozen at its week
        entries.append({**e, "adds": adds, "drops": drops, "_score": impact * fade(e["week"])})

    # the draft: one entry, its three biggest picks
    from .draft import _picks
    picks = _picks(cur, scenario)
    cur.execute("SELECT status, completed_at FROM fantasy_drafts WHERE scenario = %s", (scenario,))
    d = cur.fetchone()
    cur.execute("SELECT id, name FROM fantasy_teams WHERE scenario = %s", (scenario,))
    team_names = {r["id"]: r["name"] for r in cur.fetchall()}
    if picks and d and d["status"] == "complete":
        def val(p):
            return p.get("price") if p.get("price") is not None else value(p["player_id"] or p["nba_team_id"], 0)
        top = sorted(picks, key=val, reverse=True)[:3]
        at = d["completed_at"] or max(p["picked_at"] for p in picks)
        impact = max((value(p["player_id"] or p["nba_team_id"], 0) for p in top), default=0.0)
        entries.append({"kind": "draft", "at": at.isoformat(), "total": len(picks), "_score": impact * fade(0),
                        "top": [{"id": p["player_id"] or p["nba_team_id"], "name": p["name"], "kind": "player" if p["player_id"] else "nba_team",
                                 "position": p.get("position"), "price": p.get("price"), "team_id": p["team_id"], "team_name": team_names.get(p["team_id"])}
                                for p in top]})

    # most important first (2026-10-23): the Home box shows as many as fit, so the cut drops the least important
    shown = sorted(entries, key=lambda e: (e["_score"], e["at"]), reverse=True)[:TOP]
    for e in shown:
        e.pop("_score", None)
    return {"as_of": today.isoformat(), "current_week": next((w["week"] for w in weeks if w["start"] <= today <= w["end"]), None),
            "entries": shown}

