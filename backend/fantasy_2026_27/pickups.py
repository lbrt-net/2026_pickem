"""Pickups (2026-11-08, commissioner): a Roster-page section only winless teams see (0-3 and worse) — who to add or
start for one week, from the site's own week projection (lineup.week_view: expected best game with that week's games,
injuries and availability; the same number Roster and Matchup show).

Backtest behind it (PROJECTIONS.md "Bench-tier one-week pickups", '22–'26): for bench-tier players the week's game count
is the big lever (same level: 2 games → 19.5, 4 → 23.6 next week); a player's own swing only reads after a season's
worth of games. The week projection already counts both.

A free agent is listed only if he'd count that week: his first game that week hasn't tipped, and if he's on waivers the
waiver ends before it (a Tuesday clear with a Monday game counts from the next week — Okongwu, Week 4)."""
from datetime import datetime, timezone

from . import engine, waivers
from .etch import live_rosters
from .lineup import eligible, week_view

STARTER_SLOTS = ("G", "F", "C", "FLEX", "TEAM")
CANDIDATES = 90   # free agents projected per request, best by season projection first
SHOW = 6


def winless(cur, scenario: str, team_id: str) -> bool:
    """No wins or ties after 3+ decided weeks."""
    res = engine.kept_results(cur, scenario)
    row = next((r for r in res.get("standings", []) if r["team"]["id"] == team_id), None)
    return bool(row) and row["w"] == 0 and row.get("t", 0) == 0 and row["l"] >= 3


def _free_agents(cur, scenario: str, season: str) -> list[dict]:
    owned = {e["id"] for es in live_rosters(cur, scenario).values() for e in es}
    cur.execute("""SELECT fp.player_id AS id, COALESCE(p.name, fp.name) AS name, fp.position, fp.nba_team, fp.proj_avg
                   FROM fantasy_pool fp LEFT JOIN fantasy_players p ON p.id = fp.player_id
                   WHERE fp.season = %s AND fp.proj_avg IS NOT NULL AND fp.nba_team IS NOT NULL
                   ORDER BY fp.proj_avg DESC""", (season,))
    players = [r for r in cur.fetchall() if r["id"] not in owned][:CANDIDATES]
    out = [{"id": r["id"], "kind": "player", "name": r["name"], "slot": "BENCH", "position": r["position"],
            "nba_team": r["nba_team"]} for r in players]
    cur.execute("SELECT id, name FROM fantasy_nba_teams")
    out += [{"id": r["id"], "kind": "nba_team", "name": r["name"], "slot": "BENCH", "position": "TEAM", "nba_team": r["id"]}
            for r in cur.fetchall() if r["id"] not in owned]
    return out


def counts_this_week(games: list[dict], waiver_until: str | None, now_iso: str) -> bool:
    """Would an add count this week: he has a game, his first one hasn't tipped, and a waiver (if any) ends before it."""
    tips = [g["tipoff"] for g in games or [] if g.get("tipoff")]
    if not tips or min(tips) <= now_iso:
        return False
    return waiver_until is None or waiver_until < min(tips)


def pickups(cur, scenario: str, team_id: str, week_no: int | None = None) -> dict:
    if not winless(cur, scenario, team_id):
        return {"show": False}
    mine = week_view(cur, scenario, team_id, week_no, injuries=True)
    week = mine["week"]
    lg = engine.league(cur, scenario)
    now = waivers._clock(lg, scenario)
    now_iso = now.isoformat() if isinstance(now, datetime) else datetime.now(timezone.utc).isoformat()
    held = waivers.on_waivers(cur, scenario)

    fas = _free_agents(cur, scenario, lg["season"])
    proj = []
    for i in range(0, len(fas), 100):
        proj += week_view(cur, scenario, "", week["week"], injuries=True, entities=fas[i:i + 100])["entries"]

    def counts(e) -> tuple[bool, str | None]:
        """(would count this week, waiver end if he's on waivers)."""
        w = held.get(e["id"])
        until = (w.get("until") or w.get("until_date")) if w else None
        return counts_this_week(e.get("games"), until, now_iso), until

    entries = mine["entries"]
    starters = [e for e in entries if e["slot"] in STARTER_SLOTS and not e.get("locked")]
    bench = [e for e in entries if e["slot"] == "BENCH" and not e.get("locked")]
    pv = lambda e: e.get("projected") or 0

    def slim(e):
        return {"id": e["id"], "kind": e["kind"], "name": e["name"], "position": e.get("position"),
                "nba_team": e.get("nba_team"), "slot": e.get("slot"), "projected": e.get("projected"),
                "games": len(e.get("games") or []), "games_left": e.get("games_left")}

    def weakest_for(e):
        """The lowest-projected starter this player could replace (his position's spot or Flex)."""
        opts = [s for s in starters if eligible(e, s["slot"])]
        return min(opts, key=pv) if opts else None

    # lineup fixes: a bench player projecting above a starter he can replace
    fixes = []
    for b in sorted(bench, key=pv, reverse=True):
        s = weakest_for(b)
        if s and pv(b) > pv(s) + 0.5 and all(f["out"]["id"] != s["id"] for f in fixes):
            fixes.append({"in": slim(b), "out": slim(s), "gain": round(pv(b) - pv(s), 1)})

    adds = []
    for e in proj:
        ok, until = counts(e)
        if not ok:
            continue
        s = weakest_for(e)
        if not s or pv(e) <= pv(s) + 0.5:
            continue
        adds.append({"in": {**slim(e), "waivers_until": until}, "out": slim(s), "gain": round(pv(e) - pv(s), 1)})
    adds.sort(key=lambda a: -a["gain"])

    # who to drop for an add: the lowest-projected non-IR player who isn't locked (an injured player's week is 0, so
    # the season projection breaks ties toward keeping a good player)
    cur.execute("SELECT player_id, proj_avg FROM fantasy_pool WHERE season = %s", (lg["season"],))
    level = {r["player_id"]: r["proj_avg"] or 0 for r in cur.fetchall()}
    droppable = [e for e in entries if e["slot"] != "IR" and not e.get("locked") and e.get("on_roster", True) is not False
                 and e["kind"] == "player"]
    drop = min(droppable, key=lambda e: (level.get(e["id"], 0), pv(e))) if droppable else None
    return {"show": True, "week": week, "fixes": fixes, "adds": adds[:SHOW], "drop": slim(drop) if drop else None}
