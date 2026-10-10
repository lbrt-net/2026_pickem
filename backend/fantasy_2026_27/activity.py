"""League activity (Home): the most impactful moves, not the latest ones (DECISIONS.md 2026-10-10).

- Only moves that happened: the Transaction Log already holds only real moves (add-then-drop before any lock leaves
  it); a real drop shows when it's made, an add only once that player has locked into that team's lineup
  (a fantasy_lineups row for the team, that week or later).
- One entry per team per week (lock to lock; "pre" = before Week 1): its net change — a player added and dropped
  inside the same week never appears.
- Impact = the biggest value among the entry's players (not the sum), frozen as of the week the move happened (PROJ
  MAX blended with his actual weeks before it — later games never change it). Every entry halves every 7 days of
  league time at the same rate, so two moves' relative weight never changes: an old move can't jump a newer one or
  vice versa; only new moves slot in. The draft is one entry: its three biggest picks (as of week 0).
- The impact number is only for ranking; it is never sent to the page.
"""
from .engine import as_of, league, weeks_for_league
from . import projections
from .transactions import log as tx_log

TOP = 15            # entries shown
HALF_LIFE = 7.0     # days for impact to halve
BLEND_WEEKS = 6     # finished weeks until a player's value is all actual
RECENT_WEEKS = 4    # actual MAX = average weekly score over his last this-many weeks played


def _values(cur, scenario) -> "callable":
    """value(entity, week): his weekly-MAX value as of the start of that week — PROJ MAX blended toward his actual MAX
    over his last 4 weeks played BEFORE it (1/6 more actual per earlier week, all actual from week 7 on). Only past
    box scores count, so a move's value is frozen once its week starts: later games never re-rank old moves."""
    from .board import actual
    season_pool = projections.pool_for(cur, scenario)
    cur.execute("SELECT player_id AS id, proj_max FROM fantasy_pool WHERE season = %s AND proj_max IS NOT NULL", (season_pool,))
    proj = {r["id"]: r["proj_max"] for r in cur.fetchall()}
    cur.execute("SELECT team AS id, proj_max FROM fantasy_team_pool WHERE season = %s AND proj_max IS NOT NULL", (season_pool,))
    proj.update({r["id"]: r["proj_max"] for r in cur.fetchall()})
    weekly = {eid: {int(k): v for k, v in row.get("weeks", {}).items()}
              for eid, row in actual(cur, scenario, "season", with_weeks=True)["players"].items()}

    def value(eid, week):
        week = week or 0
        blend = min(1.0, max(0, week - 1) / BLEND_WEEKS)
        ws = [v for k, v in sorted(weekly.get(eid, {}).items()) if k < week][-RECENT_WEEKS:]
        p = proj.get(eid)
        if not ws or not blend:
            return p or 0.0
        act = sum(ws) / len(ws)
        return (1 - blend) * (p if p is not None else act) + blend * act
    return value


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
        age = max(0, (today - _date(e["asof"])).days)
        entries.append({**e, "adds": adds, "drops": drops, "_score": impact * 0.5 ** (age / HALF_LIFE)})

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
        age = max(0, (today - at.date()).days) if hasattr(at, "date") else 0
        impact = max((value(p["player_id"] or p["nba_team_id"], 0) for p in top), default=0.0)
        entries.append({"kind": "draft", "at": at.isoformat(), "total": len(picks), "_score": impact * 0.5 ** (age / HALF_LIFE),
                        "top": [{"id": p["player_id"] or p["nba_team_id"], "name": p["name"], "kind": "player" if p["player_id"] else "nba_team",
                                 "position": p.get("position"), "price": p.get("price"), "team_id": p["team_id"], "team_name": team_names.get(p["team_id"])}
                                for p in top]})

    shown = sorted(entries, key=lambda e: e["_score"], reverse=True)[:TOP]
    shown.sort(key=lambda e: e["at"], reverse=True)  # the cut is by impact; the list reads newest first
    for e in shown:
        e.pop("_score", None)
    return {"as_of": today.isoformat(), "current_week": next((w["week"] for w in weeks if w["start"] <= today <= w["end"]), None),
            "entries": shown}


def _date(s):
    from datetime import date
    return date.fromisoformat(s[:10])
