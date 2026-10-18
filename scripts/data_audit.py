"""Data audit (2026-10-18): every page must agree on the same facts. Read-only; hits the live API like a visitor.

For each fact there is ONE source of truth; every endpoint that shows it is compared against it:

| Fact                                   | Source of truth                         | Compared on                                    |
|----------------------------------------|-----------------------------------------|------------------------------------------------|
| Player position (G / F / C)            | season pool (`/players` pool fields)    | rosters, draft, week views, player page, txns  |
| Player NBA team                        | season pool                             | rosters, draft, week views, player page, txns  |
| PROJ MAX / PROJ AVG                    | board (`/players/board?view=proj`)      | player page header, Draft Grades               |
| Who owns a player / NBA team           | live rosters (`/teams`)                 | `/players`, week views, player page ribbon     |
| Roster spot                            | live rosters                            | week views; spot must fit the position         |
| Fantasy team name / abbreviation / color | `/league/members`                     | `/teams`, draft order, trades                  |
| The draft (who, which team, price)     | permanent draft record (`/draft`)       | Draft Grades, player page "Drafted" line       |

    python3 scripts/data_audit.py            # live league
    python3 scripts/data_audit.py --quick    # skip the per-player page checks
Exit code 1 when anything disagrees (CI / check_site can gate on it).
"""
import json
import ssl
import sys
import urllib.request
from collections import Counter, defaultdict

BASE = "https://lbrt.net/fantasy/2026_27"
SC = "live"
try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa: BLE001
    CTX = ssl.create_default_context()

problems = []


def get(path):
    sep = "&" if "?" in path else "?"
    with urllib.request.urlopen(urllib.request.Request(f"{BASE}/{path}{sep}scenario={SC}", headers={"User-Agent": "data-audit"}),
                                context=CTX, timeout=60) as r:
        return json.loads(r.read())


def bad(area, msg):
    problems.append((area, msg))


def main(quick=False):
    players = {p["id"]: p for p in get("players")}
    pool = {k: p for k, p in players.items() if p.get("in_pool")}
    teams = get("teams")
    members = {t["id"]: t for t in get("league/members")["teams"]}
    draft = get("draft")
    board = get("players/board?view=proj")["players"]
    recap = (get("recap") or {}).get("draft") or {}
    log = get("transactions")
    trades = get("trades").get("trades", [])
    slots = draft["roster_slots"]
    elig = {"G": {"G"}, "F": {"F"}, "C": {"C"}}

    # --- fantasy team identity ------------------------------------------------------------------------------------
    for t in teams:
        m = members.get(t["id"])
        if not m:
            bad("teams", f"{t['name']} is on /teams but not in /league/members")
            continue
        for k in ("name", "abbreviation", "color", "owner_user_id"):
            if t.get(k) != m.get(k):
                bad("teams", f"{t['id']} {k}: /teams {t.get(k)!r} vs members {m.get(k)!r}")
    for t in draft["order"]:
        m = members.get(t["id"])
        if m and t["name"] != m["name"]:
            bad("teams", f"draft order name {t['name']!r} vs members {m['name']!r}")
    for tr in trades:
        for side in ("from", "to"):
            t = tr.get(side) or {}
            m = members.get(t.get("id"))
            if m and (t.get("name") != m["name"] or t.get("color") != m["color"]):
                bad("teams", f"trade {tr['id']} {side} team shows {t.get('name')!r}/{t.get('color')} vs {m['name']!r}/{m['color']}")

    # --- rosters: one team per entity, spots fit, ownership agrees ----------------------------------------------
    owner_of, slot_of = {}, {}
    for t in teams:
        n = Counter(e["slot"] for e in t["roster"] if e["slot"] != "IR")
        for s, c in n.items():
            if c > slots.get(s, 0):
                bad("rosters", f"{t['name']} has {c} in {s} (limit {slots.get(s, 0)})")
        for e in t["roster"]:
            if e["id"] in owner_of:
                bad("rosters", f"{e['name']} is on two rosters: {owner_of[e['id']]} and {t['id']}")
            owner_of[e["id"]], slot_of[e["id"]] = t["id"], e["slot"]
            if e["kind"] == "player":
                truth = pool.get(e["id"], {}).get("position")
                if truth and e.get("position") != truth:
                    bad("positions", f"/teams roster: {e['name']} is {e.get('position')} vs pool {truth}")
                if e.get("nba_team") and pool.get(e["id"]) and e["nba_team"] != pool[e["id"]].get("nba_team"):
                    bad("nba teams", f"/teams roster: {e['name']} on {e['nba_team']} vs pool {pool[e['id']].get('nba_team')}")
                if e["slot"] in elig and truth and truth not in elig[e["slot"]]:
                    bad("rosters", f"{t['name']}: {e['name']} ({truth}) sits in {e['slot']}")
            elif e["slot"] in elig:
                bad("rosters", f"{t['name']}: NBA team {e['name']} sits in {e['slot']}")
    for pid, p in players.items():
        o = p.get("team_id")
        if o and owner_of.get(pid) != o:
            bad("ownership", f"/players says {p['name']} belongs to {o}, rosters say {owner_of.get(pid)}")
        if not o and pid in owner_of:
            bad("ownership", f"/players says {p['name']} is unowned, rosters say {owner_of[pid]}")

    # --- week views: same roster, same positions / teams ----------------------------------------------------------
    for t in teams:
        wk = get(f"team/{t['id']}/week")
        ids = {e["id"] for e in wk.get("entries", []) if e.get("on_roster") is not False}
        live = {e["id"] for e in t["roster"]}
        if wk.get("is_current") and ids and ids != live:
            bad("ownership", f"{t['name']} week view roster differs from /teams: +{sorted(ids - live)} -{sorted(live - ids)}")
        for e in wk.get("entries", []):
            if e.get("kind") == "player" and e["id"] in pool:
                if e.get("position") != pool[e["id"]].get("position"):
                    bad("positions", f"week view {t['name']}: {e['name']} {e.get('position')} vs pool {pool[e['id']].get('position')}")
                if e.get("nba_team") != pool[e["id"]].get("nba_team"):
                    bad("nba teams", f"week view {t['name']}: {e['name']} {e.get('nba_team')} vs pool {pool[e['id']].get('nba_team')}")

    # --- the draft: record vs recap -------------------------------------------------------------------------------
    picks = draft["picks"]
    per_team = Counter(p["team_id"] for p in picks)
    spots = sum(slots.values())
    if draft["status"] == "complete":
        for t in draft["order"]:
            if per_team.get(t["id"], 0) > spots:
                bad("draft", f"{t['name']} has {per_team[t['id']]} picks (roster {spots})")
        for p in picks:
            if p["kind"] == "player" and p["id"] in pool and p.get("position") != pool[p["id"]].get("position"):
                bad("positions", f"draft record: {p['name']} {p.get('position')} vs pool {pool[p['id']].get('position')}")
        rp = {(r["id"], r["team_id"]): r for r in recap.get("picks", [])}
        for p in picks:
            r = rp.get((str(p["id"]), p["team_id"]))
            if not r:
                bad("draft", f"Draft Grades is missing {p['name']} ({p['team_name']})")
            elif r.get("price") != p.get("price"):
                bad("draft", f"Draft Grades price for {p['name']}: {r.get('price')} vs record {p.get('price')}")
        if recap and len(recap.get("picks", [])) != len(picks):
            bad("draft", f"Draft Grades has {len(recap.get('picks', []))} picks, record has {len(picks)}")

    # --- transaction log: positions / teams of players in it --------------------------------------------------------
    for g in log.get("items", []):
        for x in g["adds"] + g["drops"]:
            if x.get("kind") == "player" and x["id"] in pool:
                if x.get("position") != pool[x["id"]].get("position"):
                    bad("positions", f"transaction log: {x['name']} {x.get('position')} vs pool {pool[x['id']].get('position')}")
                if x.get("nba_team") != pool[x["id"]].get("nba_team"):
                    bad("nba teams", f"transaction log: {x['name']} {x.get('nba_team')} vs pool {pool[x['id']].get('nba_team')}")
        m = members.get(g["team_id"])
        if m and g["team_name"] != m["name"]:
            bad("teams", f"transaction log team name {g['team_name']!r} vs {m['name']!r}")

    # --- player pages: position, team, owner, projection, draft line -----------------------------------------------
    if not quick:
        owned = sorted(owner_of)  # every rostered player / team, plus the top of the board
        top = sorted((k for k in board if k.isdigit()), key=lambda k: -(board[k].get("value") or 0))[:40]
        drafted = {str(p["id"]): p for p in picks}
        for pid in sorted(set(owned) | set(top)):
            if not pid.isdigit():
                continue
            pg = get(f"players/{pid}/page")
            pl = pg.get("player", {})
            truth = pool.get(pid, {})
            if truth and pl.get("pos") != truth.get("position"):
                bad("positions", f"player page {pl.get('name')}: {pl.get('pos')} vs pool {truth.get('position')}")
            if truth and pl.get("team") != truth.get("nba_team"):
                bad("nba teams", f"player page {pl.get('name')}: {pl.get('team')} vs pool {truth.get('nba_team')}")
            o = (pl.get("owner") or {}).get("team_id")
            if o != owner_of.get(pid):
                bad("ownership", f"player page {pl.get('name')}: owner {o} vs rosters {owner_of.get(pid)}")
            hdr = pg.get("header") or {}
            if hdr.get("proj") and board.get(pid, {}).get("max") is not None and hdr.get("max") is not None:
                if abs(hdr["max"] - board[pid]["max"]) > 0.15:
                    bad("projections", f"PROJ MAX {pl.get('name')}: player page {hdr['max']} vs board {board[pid]['max']}")
            d = drafted.get(pid)
            mv = [m for m in pg.get("moves", []) if m.get("k") == "draft"]
            if d and not mv:
                bad("draft", f"player page {pl.get('name')}: no Drafted line (drafted by {d['team_name']} for ${d.get('price')})")
            if mv and d and mv[0].get("price") != d.get("price"):
                bad("draft", f"player page {pl.get('name')}: drafted for ${mv[0].get('price')} vs record ${d.get('price')}")

    # --- draft grades projections vs board --------------------------------------------------------------------------
    for r in recap.get("picks", []):
        if r.get("kind") == "player" and r["id"] in board and board[r["id"]].get("max") is not None:
            if abs((r.get("proj") or 0) - board[r["id"]]["max"]) > 0.15:
                bad("projections", f"Draft Grades proj {r['name']}: {r.get('proj')} vs board PROJ MAX {board[r['id']]['max']}")

    by = defaultdict(list)
    for area, msg in problems:
        by[area].append(msg)
    if not problems:
        print("data audit: everything agrees")
        return 0
    print(f"data audit: {len(problems)} disagreement(s)")
    for area, msgs in by.items():
        print(f"\n== {area} ({len(msgs)})")
        for m in msgs[:40]:
            print("  ", m)
        if len(msgs) > 40:
            print(f"   … and {len(msgs) - 40} more")
    return 1


if __name__ == "__main__":
    sys.exit(main(quick="--quick" in sys.argv))
