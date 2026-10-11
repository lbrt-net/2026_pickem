"""The Recap page (DECISIONS.md 2026-10-10): Draft Grades now, Draft Value once Week 1 is over, then each week.

Draft Grades are in fantasy points — the only metric. Points added = a player's projected weekly MAX (PROJ MAX) − the
best player still free at his position after the draft (G / F / C / TM). A team's grade = the plain sum of its starters'.
The yardstick for each pick's color is what that resource usually buys:
- auction: the money actually spent buys points on a curve (worth = min bid + k · points^1.25, k fit on the whole
  draft's spending); "worth" is that price, "usually gets" its inverse. Unspent money is its own ding.
- snake: what pick N normally gets — the Nth-best player by points added.
Frozen when the draft completes (rosters change after; the grades don't), so the page just reads them.
"""
import json
from datetime import datetime, timezone

from .weeks import league_settings

CURVE = 1.25
POS = ("G", "F", "C", "TEAM")


def init_schema(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fantasy_recaps (
            scenario TEXT NOT NULL,
            kind     TEXT NOT NULL,            -- draft
            week     INTEGER NOT NULL DEFAULT 0,
            data     JSONB NOT NULL,
            built_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (scenario, kind, week)
        )
    """)


def _entities(cur, scenario: str, season: str) -> tuple[list, dict]:
    """(drafted picks, every pool entity id → {name, pos, nba_team, proj, kind})."""
    cur.execute("SELECT player_id AS id, name, position AS pos, nba_team, proj_max FROM fantasy_pool WHERE season = %s", (season,))
    pool = {r["id"]: {"id": r["id"], "kind": "player", "name": r["name"], "pos": r["pos"], "nba_team": r["nba_team"],
                      "proj": r["proj_max"]} for r in cur.fetchall() if r["proj_max"] is not None}
    cur.execute("SELECT t.team AS id, n.name, t.proj_max FROM fantasy_team_pool t LEFT JOIN fantasy_nba_teams n ON n.id = t.team WHERE t.season = %s", (season,))
    for r in cur.fetchall():
        if r["proj_max"] is not None:
            pool[r["id"]] = {"id": r["id"], "kind": "nba_team", "name": r["name"] or r["id"], "pos": "TEAM",
                             "nba_team": r["id"], "proj": r["proj_max"]}
    cur.execute("""SELECT team_id, slot, COALESCE(player_id, nba_team_id) AS id, pick_no, price FROM fantasy_rosters
                   WHERE scenario = %s AND pick_no IS NOT NULL ORDER BY pick_no""", (scenario,))
    return [dict(r) for r in cur.fetchall()], pool


def build_draft(cur, scenario: str) -> dict | None:
    s = league_settings(cur, scenario)
    cur.execute("SELECT season FROM fantasy_leagues WHERE scenario = %s", (scenario,))
    season = cur.fetchone()["season"]
    picks, pool = _entities(cur, scenario, season)
    picks = [p for p in picks if p["id"] in pool]
    if not picks:
        return None
    drafted = {p["id"] for p in picks}
    repl = {}
    for pos in POS:
        free = sorted((e for e in pool.values() if e["pos"] == pos and e["id"] not in drafted), key=lambda e: -e["proj"])
        if free:
            repl[pos] = {"id": free[0]["id"], "name": free[0]["name"], "kind": free[0]["kind"], "nba_team": free[0]["nba_team"],
                         "proj": round(free[0]["proj"], 1)}
    auction = s.get("draft_type") == "auction" and all(p["price"] is not None for p in picks)
    m = s.get("auction_min_bid", 1)
    rows = []
    for p in picks:
        e = pool[p["id"]]
        pa = round(e["proj"] - repl.get(e["pos"], {"proj": 0})["proj"], 1)
        rows.append({**{k: e[k] for k in ("id", "kind", "name", "pos", "nba_team")}, "team_id": p["team_id"], "slot": p["slot"],
                     "pick_no": p["pick_no"], "price": p["price"], "proj": round(e["proj"], 1), "added": pa})
    if auction:
        pos_pts = sum(max(r["added"], 0) ** CURVE for r in rows)
        k = sum(max(r["price"] - m, 0) for r in rows) / pos_pts if pos_pts else 0
        for r in rows:
            r["worth"] = round(m + k * max(r["added"], 0) ** CURVE)
            usual = ((r["price"] - m) / k) ** (1 / CURVE) if k and r["price"] > m else 0.0
            r["usual"] = round(usual, 1)                       # what this price usually gets, in points added
            r["vs"] = round(r["added"] - usual, 1)             # the color
    else:
        ranked = sorted((max(e["proj"] - repl.get(e["pos"], {"proj": 0})["proj"], -99) for e in pool.values()), reverse=True)
        for r in rows:
            usual = ranked[r["pick_no"] - 1] if r["pick_no"] - 1 < len(ranked) else 0.0
            r["usual"] = round(usual, 1)
            r["vs"] = round(r["added"] - usual, 1)
    cur.execute("SELECT id, name, abbreviation, color, glyph FROM fantasy_teams WHERE scenario = %s", (scenario,))
    teams = {t["id"]: dict(t) for t in cur.fetchall()}
    budget = s.get("auction_budget", 200)
    for tid, t in teams.items():
        mine = [r for r in rows if r["team_id"] == tid]
        t["added"] = round(sum(r["added"] for r in mine if r["slot"] not in ("BENCH", "IR")), 1)
        t["unspent"] = (budget - sum(r["price"] or 0 for r in mine)) if auction else None
        t["top"] = max(mine, key=lambda r: r["proj"])["id"] if mine else None
    order = sorted(teams, key=lambda t: -teams[t]["added"])
    return {"type": "auction" if auction else "snake", "draft_type": s.get("draft_type"), "budget": budget if auction else None,
            "replacement": repl, "teams": [teams[t] for t in order], "picks": rows, "awards": _awards(rows, teams, auction, budget),
            "built_at": datetime.now(timezone.utc).isoformat()}


def _awards(rows: list, teams: dict, auction: bool, budget: int) -> dict:
    top3 = lambda xs, key: sorted(xs, key=key)[:3]
    out = {"worst": top3(rows, lambda r: r["added"])}
    if auction:
        out["best_buy"] = top3(rows, lambda r: -(r["worth"] - r["price"]))
        cheap = [r for r in rows if r["price"] <= budget * 0.10]
        out["best_cheap"] = top3(cheap, lambda r: -r["added"])
        out["overpay"] = top3(rows, lambda r: -(r["price"] - r["worth"]))
    else:
        n = max(r["pick_no"] for r in rows)
        out["best_pick"] = top3(rows, lambda r: -r["vs"])
        out["best_late"] = top3([r for r in rows if r["pick_no"] > n * 2 / 3], lambda r: -r["vs"])
        out["reach"] = top3(rows, lambda r: r["vs"])
    bench = {}
    for r in rows:
        if r["slot"] == "BENCH":
            bench.setdefault(r["team_id"], []).append(r)
    out["bench"] = sorted(({"team_id": t, "added": round(sum(x["added"] for x in b), 1), "players": [x["id"] for x in b]}
                           for t, b in bench.items()), key=lambda x: -x["added"])[:3]
    return {k: ([x["id"] if "id" in x and "team_id" in x and "pick_no" in x else x for x in v]) for k, v in out.items()}


def freeze_draft(cur, scenario: str) -> dict | None:
    data = build_draft(cur, scenario)
    if data:
        cur.execute("""INSERT INTO fantasy_recaps (scenario, kind, week, data) VALUES (%s, 'draft', 0, %s)
                       ON CONFLICT (scenario, kind, week) DO UPDATE SET data = EXCLUDED.data, built_at = now()""",
                    (scenario, json.dumps(data)))
    return data


def recap(cur, scenario: str, preview: bool = False) -> dict:
    """What the Recap page can show. Draft Grades: the frozen copy (made at draft completion; made now if missing);
    a test league can preview from its current rosters. Draft Value and weeks come once Week 1 is over."""
    cur.execute("SELECT status FROM fantasy_drafts WHERE scenario = %s", (scenario,))
    d = cur.fetchone()
    cur.execute("SELECT data FROM fantasy_recaps WHERE scenario = %s AND kind = 'draft' AND week = 0", (scenario,))
    row = cur.fetchone()
    draft = row["data"] if row else None
    if draft is None and d and d["status"] == "complete":
        draft = freeze_draft(cur, scenario)
    if draft is None and preview:
        draft = build_draft(cur, scenario)
    return {"draft": draft, "value": None, "weeks": []}
