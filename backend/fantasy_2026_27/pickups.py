"""Pickups (2026-11-08, rebuilt the same evening after the commissioner rejected the projection-only version): a Roster
section only winless teams see (0-3 and worse). Simple rules, brief reasons, careful drops.

Every number comes from real games, never the week projection:
  level        FP per game when he plays: this season, early on blended with last season (worth 10 games)
  replacement  the 5th-best healthy free agent's level at his position (3rd-best free NBA team for TEAM)
  week score   level + 1.5 per game over 3 + 0.7 per soft game (opponent in the top 10 for FP allowed per game)
               + half his minutes change (last 14 days vs season, capped ±4); games he's ruled Out of don't count
               (weights from PROJECTIONS.md "Same band, every factor", '22–'26)
Start: a healthy bench player playing real minutes whose week score beats a starter he can replace by 1+.
Add: a free agent who'd count this week (first game not tipped, any waiver ends before it), healthy, playing real
minutes, whose week score beats the weakest starter he can replace by 1+. NBA teams too.
Drop (careful): only someone within 1.5 of replacement when healthy (an injured good player is never a drop), never the
last healthy player at G, F or C. No safe drop → the add isn't shown. A team add drops the current NBA team if it's
near replacement."""
from datetime import datetime, timedelta, timezone

from . import board as board_mod, engine, waivers
from .etch import live_rosters
from .lineup import eligible, week_view
from .logic import player_points

ON = False   # switched on once the commissioner has seen the rebuilt output
STARTER_SLOTS = ("G", "F", "C", "FLEX", "TEAM")
GAIN, NEAR_REPL, SHOW = 1.0, 1.5, 5


def winless(cur, scenario: str, team_id: str) -> bool:
    """No wins or ties after 3+ decided weeks."""
    res = engine.kept_results(cur, scenario)
    row = next((r for r in res.get("standings", []) if r["team"]["id"] == team_id), None)
    return bool(row) and row["w"] == 0 and row.get("t", 0) == 0 and row["l"] >= 3


def counts_this_week(games: list[dict], waiver_until: str | None, now_iso: str) -> bool:
    """Would an add count this week: he has a game, his first one hasn't tipped, and a waiver (if any) ends before it."""
    tips = [g["tipoff"] for g in games or [] if g.get("tipoff")]
    if not tips or min(tips) <= now_iso:
        return False
    return waiver_until is None or waiver_until < min(tips)


def week_score(level: float, games: int, soft: int, min_change: float | None) -> float:
    return level + 1.5 * (games - 3) + 0.7 * soft + 0.5 * max(-4.0, min(4.0, min_change or 0.0))


def blended(avg: float | None, gp: int, last: float | None) -> float | None:
    if avg is None and last is None:
        return None
    if last is None or gp >= 30:
        return avg
    if avg is None:
        return last
    return (gp * avg + 10 * last) / (gp + 10)


def _schedule(cur, season: str, week: dict) -> dict:
    cur.execute("""SELECT game_date, tipoff_utc, home_team, away_team FROM nba_games
                   WHERE season = %s AND game_type = 'regular' AND game_date BETWEEN %s AND %s""",
                (season, week["start"], week["end"]))
    out = {}
    for r in cur.fetchall():
        tip = r["tipoff_utc"].isoformat() if r["tipoff_utc"] else f'{r["game_date"].isoformat()}T23:00:00+00:00'
        for t, o in ((r["home_team"], r["away_team"]), (r["away_team"], r["home_team"])):
            out.setdefault(t, []).append({"date": r["game_date"].isoformat(), "opp": o, "tipoff": tip})
    return out


def _soft_teams(cur, season: str, today, rules) -> list[str]:
    """The 10 teams giving up the most fantasy points per game to players this season."""
    cur.execute("""SELECT pg.game_id, pg.team, g.home_team, g.away_team, pg.pts, pg.fgm, pg.fga, pg.fg3m, pg.ftm, pg.fta,
                          pg.oreb, pg.dreb, pg.ast, pg.stl, pg.blk, pg.tov, pg.blkd, pg.clutch_pts
                   FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
                   WHERE pg.season = %s AND g.game_type = 'regular' AND g.status = 'final' AND pg.minutes > 0
                     AND g.game_date <= %s""", (season, today))
    given = {}
    for r in cur.fetchall():
        opp = r["away_team"] if r["team"] == r["home_team"] else r["home_team"]
        given.setdefault(opp, {}).setdefault(r["game_id"], 0.0)
        given[opp][r["game_id"]] += player_points(r, rules)
    per = {t: sum(v.values()) / len(v) for t, v in given.items() if v}
    return sorted(per, key=lambda t: -per[t])[:10]


def _minutes(cur, season: str, today) -> dict:
    since = today - timedelta(days=14)
    cur.execute("""SELECT pg.player_id, pg.team, AVG(pg.minutes) AS mpg,
                          AVG(pg.minutes) FILTER (WHERE g.game_date > %s) AS recent,
                          COUNT(*) FILTER (WHERE g.game_date > %s) AS recent_gp
                   FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
                   WHERE pg.season = %s AND g.game_type = 'regular' AND pg.minutes > 0 AND g.game_date <= %s
                   GROUP BY pg.player_id, pg.team""", (since, since, season, today))
    out = {}
    for r in cur.fetchall():  # a traded player: keep the team he's played for most recently
        o = out.get(r["player_id"])
        if not o or (r["recent_gp"] or 0) > (o["recent_gp"] or 0):
            out[r["player_id"]] = r
    return out


def pickups(cur, scenario: str, team_id: str, week_no: int | None = None, force: bool = False) -> dict:
    if not force and (not ON or not winless(cur, scenario, team_id)):
        return {"show": False}
    from .scoring import league_rules
    lg = engine.league(cur, scenario)
    season, today = lg["season"], engine.as_of(lg)
    mine = week_view(cur, scenario, team_id, week_no, injuries=True)
    week = mine["week"]
    rules = league_rules(cur, scenario)
    now = waivers._clock(lg, scenario)
    now_iso = now.isoformat() if isinstance(now, datetime) else datetime.now(timezone.utc).isoformat()

    sched = _schedule(cur, season, week)
    soft = set(_soft_teams(cur, season, today, rules))
    act = board_mod.actual(cur, scenario, "season")["players"]
    mins = _minutes(cur, season, today)
    cur.execute("SELECT * FROM fantasy_players")
    last = {r["id"]: player_points(r, rules) for r in cur.fetchall() if (r.get("games_played") or 0) >= 10}
    cur.execute("SELECT player_id, status, return_date FROM nba_injuries")
    inj = {r["player_id"]: r for r in cur.fetchall()}
    held = waivers.on_waivers(cur, scenario)
    owned = {e["id"] for es in live_rosters(cur, scenario).values() for e in es}
    cur.execute("""SELECT fp.player_id AS id, COALESCE(p.name, fp.name) AS name, fp.position, fp.nba_team
                   FROM fantasy_pool fp LEFT JOIN fantasy_players p ON p.id = fp.player_id
                   WHERE fp.season = %s AND fp.nba_team IS NOT NULL""", (season,))
    pool = {r["id"]: {**dict(r), "kind": "player"} for r in cur.fetchall()}
    cur.execute("SELECT id, name FROM fantasy_nba_teams")
    pool.update({r["id"]: {"id": r["id"], "name": r["name"], "kind": "nba_team", "position": "TEAM", "nba_team": r["id"]}
                 for r in cur.fetchall()})

    def level(e):
        a = act.get(e["id"]) or {}
        if e["kind"] == "nba_team":
            return a.get("avg")
        return blended(a.get("avg"), a.get("gp") or 0, last.get(e["id"]))

    def games_left(e):
        gs = sched.get(e.get("nba_team"), [])
        r = inj.get(e["id"]) if e["kind"] == "player" else None
        if r and r["status"] == "Out For Season":
            return []
        if r and r["status"] == "Out":
            ret = r["return_date"].isoformat() if r["return_date"] else None
            return [g for g in gs if ret and g["date"] >= ret]
        return gs

    def healthy_now(e):
        if e["kind"] == "nba_team":
            return True
        m = mins.get(e["id"])
        r = inj.get(e["id"])
        return bool(m) and (m["recent_gp"] or 0) >= 2 and (m["recent"] or 0) >= 15 and not (r and r["status"].startswith("Out"))

    def score(e):
        lv = level(e)
        gs = games_left(e)
        if lv is None or not gs:
            return None
        m = mins.get(e["id"]) if e["kind"] == "player" else None
        change = (m["recent"] - m["mpg"]) if m and m["recent"] is not None else 0
        return week_score(lv, len(gs), sum(g["opp"] in soft for g in gs), change)

    def why(e, wait=None):
        """Short facts, one per chip: games, soft opponents, minutes change, teammates out, waivers. No points numbers."""
        gs = games_left(e)
        s = [g["opp"] for g in gs if g["opp"] in soft]
        softs = sorted({f"{o} ×{s.count(o)}" if s.count(o) > 1 else o for o in s})
        r = inj.get(e["id"]) if e["kind"] == "player" else None
        bits = [f"{len(gs)} games"] + ([f'soft: {", ".join(softs)}'] if softs else ["no soft games"])
        if r and r["status"] not in ("Out", "Out For Season"):
            bits.append(r["status"])
        elif r:
            bits.append(f'out until {r["return_date"].strftime("%-m/%-d")}' if r["return_date"] else "out")
        if e["kind"] == "player":
            m = mins.get(e["id"])
            if m and m["recent"] is not None and abs(m["recent"] - m["mpg"]) >= 2:
                bits.append(f'{m["mpg"]:.0f} → {m["recent"]:.0f} min')
            # teammates (20+ mpg) out for most of the week: no return date, or back after its first 3 days
            late = week["start"] + timedelta(days=3)
            out = [pool[i]["name"] for i, r in inj.items() if r["status"].startswith("Out") and i in pool and i != e["id"]
                   and pool[i]["nba_team"] == e.get("nba_team") and ((mins.get(i) or {}).get("mpg") or 0) >= 20
                   and (r["return_date"] is None or r["return_date"] > late)]
            bits += [f"{n} out" for n in out[:2]]
        if wait:
            bits.append(wait)
        return bits

    # replacement level by position, from healthy free agents
    fa = [e for i, e in pool.items() if i not in owned]
    repl = {}
    for pos in ("G", "F", "C", "TEAM"):
        lv = sorted((level(e) for e in fa if e["position"] == pos and level(e) is not None
                     and (e["kind"] == "nba_team" or healthy_now(e))), reverse=True)
        k = 2 if pos == "TEAM" else 4
        repl[pos] = lv[k] if len(lv) > k else (lv[-1] if lv else 0)

    entries = mine["entries"]
    for e in entries:
        if not e.get("nba_team"):
            e["nba_team"] = (pool.get(e["id"]) or {}).get("nba_team")
    starters = [e for e in entries if e["slot"] in STARTER_SLOTS and not e.get("locked")]
    bench = [e for e in entries if e["slot"] == "BENCH" and not e.get("locked")]
    sc = {e["id"]: score(e) for e in entries}

    def slim(e, facts=False):
        """AVG = FP per game, MAX = average weekly best game this season (the Players page's AVG / MAX)."""
        a = act.get(e["id"]) or {}
        out = {"id": e["id"], "kind": e["kind"], "name": e["name"], "position": e.get("position"),
               "nba_team": e.get("nba_team"), "slot": e.get("slot"),
               "avg": round(a["avg"], 1) if a.get("avg") is not None else None,
               "max": round(a["max"], 1) if a.get("max") is not None else None}
        if facts:
            out["facts"] = why(e)
        return out

    def s_or_floor(e):
        v = sc.get(e["id"])
        return -99.0 if v is None else v

    def weakest_for(e):
        opts = [s for s in starters if eligible(e, s["slot"])]
        return min(opts, key=s_or_floor) if opts else None

    starts = []
    for b in sorted(bench, key=s_or_floor, reverse=True):
        if not healthy_now(b) or sc.get(b["id"]) is None:
            continue
        s = weakest_for(b)
        if s and sc[b["id"]] - s_or_floor(s) >= GAIN and all(x["out"]["id"] != s["id"] for x in starts):
            starts.append({"in": slim(b), "out": slim(s, True), "why": why(b)})

    def wait_text(until):
        if not until or "T" not in until:
            return None
        return "waivers until " + datetime.fromisoformat(until).astimezone(timezone(timedelta(hours=-6))).strftime("%a %-I:%M %p")

    def near_repl(e):
        lv = level(e)
        return lv is not None and lv - repl.get(e.get("position"), 0) < NEAR_REPL

    def safe_drop(add):
        """The roster player to drop for this add, or None (near replacement when healthy, keeps G/F/C covered)."""
        if add["kind"] == "nba_team":
            cur_team = next((e for e in entries if e["kind"] == "nba_team" and e["slot"] != "IR"), None)
            if cur_team and near_repl(cur_team):
                return cur_team, ""
        healthy = [e for e in entries if e["kind"] == "player" and e["slot"] != "IR" and healthy_now(e)]
        cands = []
        for e in entries:
            if e["kind"] != "player" or e["slot"] == "IR" or e.get("locked") or not near_repl(e):
                continue
            left = [h for h in healthy if h["id"] != e["id"] and h.get("position") == e.get("position")]
            if add["kind"] == "player" and add.get("position") == e.get("position"):
                left.append(add)
            if left:
                cands.append(e)
        if not cands:
            return None
        d = min(cands, key=lambda e: level(e) - repl.get(e.get("position"), 0))
        return d, ""

    adds = []
    for e in fa:
        if e["kind"] == "player" and (not healthy_now(e) or (act.get(e["id"]) or {}).get("gp", 0) < 3):
            continue
        w = held.get(e["id"])
        until = (w.get("until") or w.get("until_date")) if w else None
        if not counts_this_week(sched.get(e["nba_team"], []), until, now_iso):
            continue
        s_, s = score(e), weakest_for(e)
        if s_ is None or not s or s_ - s_or_floor(s) < GAIN:
            continue
        d = safe_drop(e)
        if not d:
            continue
        adds.append({"in": slim(e), "out": slim(s, True), "drop": slim(d[0], True), "why": why(e, wait_text(until)), "drop_why": d[1],
                     "gain": s_ - s_or_floor(s), "claim": bool(until)})
    adds.sort(key=lambda a: -a["gain"])
    team_adds = [a for a in adds if a["in"]["kind"] == "nba_team"][:1]
    player_adds = [a for a in adds if a["in"]["kind"] == "player"][:SHOW - len(team_adds)]
    out = sorted(player_adds + team_adds, key=lambda a: -a["gain"])

    # depth: one healthy player at a position while another has 3+ → a backup at the thin one, the extra one dropped
    healthy = [e for e in entries if e["kind"] == "player" and e["slot"] != "IR" and healthy_now(e)]
    hurt = [e for e in entries if e["kind"] == "player" and e["slot"] != "IR" and e not in healthy]
    by_pos = {p: [e for e in healthy if e.get("position") == p] for p in ("G", "F", "C")}
    depth = []
    for p, es in by_pos.items():
        if len(es) <= 1:
            names = [e["name"] for e in es] + [f'{e["name"]} (hurt)' for e in hurt if e.get("position") == p]
            depth.append(f'{p}: {", ".join(names) or "nobody"}')
        elif len(es) >= 3:
            depth.append(f'{p}: {", ".join(e["name"] for e in es)}')
    thin = [p for p, es in by_pos.items() if len(es) <= 1]
    extra = [p for p, es in by_pos.items() if len(es) >= 3]
    taken = {a["in"]["id"] for a in out} | {a["drop"]["id"] for a in out}
    for p in thin:
        spare = sorted((e for q in extra for e in by_pos[q] if e["slot"] == "BENCH" and not e.get("locked") and e["id"] not in taken),
                       key=lambda e: level(e) or 0)
        if not spare:
            continue
        best = None
        for e in fa:
            if e["kind"] != "player" or e.get("position") != p or not healthy_now(e) or (act.get(e["id"]) or {}).get("gp", 0) < 3 \
                    or e["id"] in taken:
                continue
            w = held.get(e["id"])
            until = (w.get("until") or w.get("until_date")) if w else None
            now_ok = counts_this_week(sched.get(e["nba_team"], []), until, now_iso)
            lv = (level(e) or 0) + (0 if now_ok else -0.01)
            if best is None or lv > best[0]:
                best = (lv, e, until, now_ok)
        if best:
            lv, e, until, now_ok = best
            bits = why(e, wait_text(until)) + ([] if now_ok else [f'counts from Week {week["week"] + 1}'])
            out.append({"in": slim(e), "out": None, "role": f"Backup {p}", "drop": slim(spare[0], True), "why": bits,
                        "drop_why": f'{{"3rd" if len(by_pos[spare[0]["position"]]) == 3 else "extra"}} healthy {spare[0]["position"]}',
                        "claim": bool(until)})
            taken |= {e["id"], spare[0]["id"]}
    for a in out:
        a.pop("gain", None)
    return {"show": True, "week": week, "depth": depth, "starts": starts, "adds": out}
