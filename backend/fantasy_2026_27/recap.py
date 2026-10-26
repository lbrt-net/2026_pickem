"""The Recap page (DECISIONS.md 2026-10-10): Draft Grades now, Draft Value once Week 1 is over, then each week.

Draft Grades are in fantasy points — the only metric. Points added = a player's projected weekly MAX (PROJ MAX) − the
best player still free at his position after the draft (G / F / C / TM). A team's grade = the plain sum of its starters'.
The yardstick for each pick's color is what that resource usually buys:
- auction: the money actually spent buys points on a curve (worth = min bid + k · points^1.25, k fit on the whole
  draft's spending); "worth" is that price, "usually gets" its inverse. Unspent money is its own ding.
- snake: what pick N normally gets — the Nth-best player by points added.
Frozen when the draft completes (rosters change after; the grades don't), so the page just reads them.
"""
import itertools
import json
from datetime import datetime, timedelta, timezone

from . import engine, etch as etch_mod
from . import scoring as scoring_mod
from .snapshots import proj_for
from . import projections
from . import history
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
    # the PROJ MAX the draft list showed (projections.shown_max), not the raw season column — the raw one counts weeks
    # he's out as zeros, so e.g. Markkanen read 25.7 here against 32.8 on the list and came out "worth $1" (2026-10-17)
    cur.execute("SELECT player_id AS id, name, position AS pos, nba_team, proj_max, proj_weeks FROM fantasy_pool WHERE season = %s", (season,))
    pool = {r["id"]: {"id": r["id"], "kind": "player", "name": r["name"], "pos": r["pos"], "nba_team": r["nba_team"],
                      "proj": projections.shown_max(r["proj_weeks"], r["proj_max"])} for r in cur.fetchall() if r["proj_max"] is not None}
    cur.execute("SELECT t.team AS id, n.name, t.proj_max FROM fantasy_team_pool t LEFT JOIN fantasy_nba_teams n ON n.id = t.team WHERE t.season = %s", (season,))
    for r in cur.fetchall():
        if r["proj_max"] is not None:
            pool[r["id"]] = {"id": r["id"], "kind": "nba_team", "name": r["name"] or r["id"], "pos": "TEAM",
                             "nba_team": r["id"], "proj": r["proj_max"]}
    # the draft as it was made (fantasy_draft_picks) — not today's rosters, which lose drafted players to drops / trades
    from .draft import _picks
    return [{"team_id": r["team_id"], "slot": r["slot"], "id": r["player_id"] or r["nba_team_id"], "pick_no": r["pick_no"], "price": r["price"]}
            for r in _picks(cur, scenario)], pool


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
    cur.execute("SELECT id, name, abbreviation, color, glyph, owner_user_id, logo_updated, picture_url, picture_mode FROM fantasy_teams WHERE scenario = %s", (scenario,))
    from .settings import logo_url
    teams = {}
    for t in cur.fetchall():
        t = dict(t)
        t["logo_url"] = logo_url(t)
        for k in ("logo_updated", "picture_url", "picture_mode"):
            t.pop(k)
        teams[t["id"]] = t
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


# ---------------- weekly recap (canvas "Weekly Report" + "optional awards") ----------------
SLOT_ORDER = {"G": 0, "F": 1, "C": 2, "FLEX": 3, "TEAM": 4}
STARTER = ("G", "F", "C", "FLEX", "TEAM")


def _games(cur, season: str, lo, hi, rules: dict) -> dict:
    """entity id → that window's games: {date, pts, bd (scoring parts), team, and for NBA teams the facts}."""
    out = {}
    cur.execute("""
        SELECT pg.player_id, pg.player_name, pg.team, pg.position, g.game_date, pg.pts, pg.fgm, pg.fga, pg.fg3m, pg.ftm, pg.fta,
               pg.oreb, pg.dreb, pg.ast, pg.stl, pg.blk, pg.tov, pg.blkd, pg.clutch_pts
        FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
        WHERE pg.season = %s AND g.game_type = 'regular' AND pg.minutes > 0 AND g.game_date BETWEEN %s AND %s
    """, (season, lo, hi))
    for r in cur.fetchall():
        sg = scoring_mod.score_game(rules["player"], scoring_mod.player_line(r))
        out.setdefault(r["player_id"], []).append({"date": r["game_date"].isoformat(), "pts": sg["total"], "bd": sg["breakdown"],
                                                   "team": r["team"], "name": r["player_name"], "pos": (r["position"] or "")[:1] or None})
    cur.execute("""
        SELECT game_id, game_date, home_team, away_team, home_score, away_score FROM nba_games
        WHERE season = %s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL AND game_date BETWEEN %s AND %s
    """, (season, lo, hi))
    games = cur.fetchall()
    ids = [g["game_id"] for g in games]
    tx = scoring_mod.team_extras(cur, ids)
    raw = {}
    if ids:
        cur.execute("SELECT game_id, team, opp_pts_fb, opp_pts_paint, opp_tov, dreb, opp_dreb, shot_clock_forced FROM nba_team_game_stats WHERE game_id = ANY(%s::text[])", (ids,))
        raw = {(r["game_id"], r["team"]): dict(r) for r in cur.fetchall()}
    for g in games:
        for t, o, mine, theirs in ((g["home_team"], g["away_team"], g["home_score"], g["away_score"]), (g["away_team"], g["home_team"], g["away_score"], g["home_score"])):
            sg = scoring_mod.score_game(rules["team"], scoring_mod.team_line(mine, theirs, tx.get((g["game_id"], t))))
            r = raw.get((g["game_id"], t), {})
            out.setdefault(t, []).append({"date": g["game_date"].isoformat(), "pts": sg["total"], "bd": sg["breakdown"], "team": t,
                                          "facts": {"opp": o, "opp_pts": theirs, "paint": r.get("opp_pts_paint"), "fb": r.get("opp_pts_fb"),
                                                    "tov": r.get("opp_tov"), "dreb": r.get("dreb"), "opp_dreb": r.get("opp_dreb"),
                                                    "scv": r.get("shot_clock_forced")}})
    return out


def _wk(rules: dict, kind: str, gs: list, upto: str | None = None) -> float:
    pts = [g["pts"] for g in gs if upto is None or g["date"] <= upto]
    return scoring_mod.week_score(rules["player" if kind == "player" else "team"], pts) or 0.0


def _best(gs: list):
    return max(gs, key=lambda g: g["pts"], default=None)


def _fits(slot: str, e: dict) -> bool:
    if slot == "TEAM":
        return e["kind"] == "nba_team"
    if e["kind"] == "nba_team":
        return False
    return slot == "FLEX" or (e.get("position") or "") == slot


def _best_lineup(es: list, slots: list) -> float:
    best = 0.0
    for combo in itertools.permutations(es, len(slots)):
        if all(_fits(sl, e) for sl, e in zip(slots, combo)):
            best = max(best, sum(e["score"] for e in combo))
    return round(best, 1)


def weekly(cur, scenario: str, week_no: int, preview: bool = False) -> dict | None:
    """One finished regular week's report: results, players of the week, free agents, versus projection, the
    optional awards (each only when it qualifies) and the standings with games behind over the last 8 weeks.
    preview=True (commissioner, never saved): a week still in progress, as if it ended now."""
    lg = engine.league(cur, scenario)
    season, today = lg["season"], engine.as_of(lg)
    weeks = engine.weeks_for_league(cur, lg)
    w = next((x for x in weeks if x["week"] == week_no and x["kind"] == "regular" and (x["end"] < today or (preview and x["start"] <= today))), None)
    if not w:
        return None
    rules = scoring_mod.league_rules(cur, scenario)
    res = engine.results(cur, scenario)
    wk = next(x for x in res["weeks"] if x["week"] == week_no)
    lineups = etch_mod.week_lineups(cur, scenario, season, weeks, today)
    games = _games(cur, season, w["start"], w["end"], rules)
    sat = (w["end"] - timedelta(days=1)).isoformat()
    sun = w["end"].isoformat()
    teams, ents = {}, []
    for m in wk["matchups"]:
        for side in (m["home"], m["away"]):
            t = side["team"]
            teams[t["id"]] = {k: t.get(k) for k in ("id", "name", "abbreviation", "color", "glyph", "owner_user_id", "logo_url")}
            for e in lineups.get((t["id"], week_no), []):
                gs = games.get(e["id"], [])
                b = _best(gs)
                ents.append({"id": e["id"], "kind": e["kind"], "name": e["name"], "slot": e["slot"], "position": e.get("position"),
                             "nba_team": (b or {}).get("team") or e.get("nba_team"), "team_id": t["id"], "score": _wk(rules, e["kind"], gs),
                             "games": len(gs), "sat": _wk(rules, e["kind"], gs, sat), "only_sun": bool(gs) and all(g["date"] == sun for g in gs),
                             "bd": (b or {}).get("bd"), "facts": (b or {}).get("facts"),
                             "days": {g["date"]: round(g["pts"], 1) for g in gs}})  # each game's points by date (the week strip)
    score = {m[k]["team"]["id"]: m[k]["score"] for m in wk["matchups"] for k in ("home", "away")}
    starters = [e for e in ents if e["slot"] in STARTER]
    pairs = [(m["home"]["team"]["id"], m["away"]["team"]["id"]) for m in wk["matchups"]]

    def card(e):
        return {k: e.get(k) for k in ("id", "kind", "name", "position", "nba_team", "team_id", "score", "bd", "facts", "games", "days")}

    # results
    order = sorted(score, key=lambda t: -score[t])
    margins = sorted(({"winner": a if score[a] >= score[b] else b, "loser": b if score[a] >= score[b] else a,
                       "margin": round(abs(score[a] - score[b]), 1)} for a, b in pairs), key=lambda x: -x["margin"])
    faces = {t: [card(e) for e in sorted((e for e in starters if e["team_id"] == t), key=lambda e: SLOT_ORDER.get(e["slot"], 9))] for t in teams}
    # players of the week: best starter at G / F / C / TM (a flex starter competes at his own position)
    potw = []
    for pos in ("G", "F", "C", "TEAM"):
        pool = [e for e in starters if (e["kind"] == "nba_team") == (pos == "TEAM") and (pos == "TEAM" or e.get("position") == pos)]
        if pool:
            potw.append(card(max(pool, key=lambda e: e["score"])))
    # free agents: nobody's at week's end, best 4 by score, only those who beat at least one starter
    owned = {e["id"] for e in ents}
    for es in [v for (tid, wn), v in lineups.items() if wn == week_no]:
        owned |= {e["id"] for e in es}
    low = min((e["score"] for e in starters), default=0)
    fa = []
    for eid, gs in games.items():
        if eid in owned:
            continue
        kind = "nba_team" if gs[0].get("facts") else "player"
        sc = _wk(rules, kind, gs)
        if sc > low:
            b = _best(gs)
            fa.append({"id": eid, "kind": kind, "name": gs[0].get("name") or eid, "position": "TEAM" if kind == "nba_team" else b.get("pos"),
                       "nba_team": b["team"], "team_id": None, "score": sc, "bd": b["bd"], "facts": b.get("facts"), "games": len(gs)})
    fa = sorted(fa, key=lambda x: -x["score"])[:4]
    if fa:
        cur.execute("SELECT player_id, name, position FROM fantasy_pool WHERE season = %s AND player_id = ANY(%s::text[])", (season, [x["id"] for x in fa]))
        meta = {r["player_id"]: r for r in cur.fetchall()}
        for x in fa:
            if x["id"] in meta:
                x["name"], x["position"] = meta[x["id"]]["name"], meta[x["id"]]["position"] or x["position"]
    # versus projection (projections frozen at the week's start; scaled by games played)
    cur.execute("SELECT entity_id, game_mean, game_sd FROM fantasy_proj_week WHERE scenario = %s AND week = %s", (scenario, week_no))
    snap = {r["entity_id"]: r for r in cur.fetchall()}
    vp = []
    for e in starters:
        if e["games"] and e["id"] in snap:
            pr = proj_for(snap[e["id"]]["game_mean"], snap[e["id"]]["game_sd"], e["games"])
            vp.append({**card(e), "proj": pr, "diff": round(e["score"] - pr, 1)})
    versus = {"short": sorted(vp, key=lambda x: x["diff"])[:4], "beat": sorted(vp, key=lambda x: -x["diff"])[:4]} if vp else None
    if versus:
        # each row (2026-10-25): the days his NBA team played (a day he sat = OUT) and where this week ranks among his own
        # weekly scores — the last two seasons plus this one, this week included
        shown = {x["id"]: x for side in versus.values() for x in side}
        first = min((x["start"] for x in weeks if x["kind"] == "regular"), default=w["start"])
        season_games = _games(cur, season, first, w["end"], rules)
        for x in shown.values():
            tg = games.get(x.get("nba_team") or "", [])
            x["team_days"] = sorted({g["date"] for g in tg if g.get("facts")})
            mine = []
            for s_ in sorted(history.for_player(cur, x["id"]), key=lambda s_: s_.get("season", ""))[-2:]:
                mine += [wk_["max"] for wk_ in s_.get("weeks", []) if wk_.get("max") is not None]
            for x_w in weeks:
                if x_w["kind"] == "regular" and x_w["week"] <= week_no:
                    gs = [g for g in season_games.get(x["id"], []) if x_w["start"].isoformat() <= g["date"] <= x_w["end"].isoformat()]
                    if gs:
                        mine.append(_wk(rules, x["kind"], gs))
            if len(mine) >= 5:
                x["pctile"] = round(100 * (sum(1 for v in mine if v < x["score"]) + 0.5 * sum(1 for v in mine if v == x["score"])) / len(mine))
    if versus:
        versus = {"short": [x for x in versus["short"] if x["diff"] < 0], "beat": [x for x in versus["beat"] if x["diff"] > 0]}
    # optional awards
    awards = {}
    slots = [sl for sl in STARTER for _ in range(engine.settings(lg, cur)["roster_slots"].get(sl, 0))]
    lost = []
    for t in teams:
        mine = [e for e in ents if e["team_id"] == t and e["slot"] not in ("IR",)]
        gap = round(_best_lineup(mine, slots) - score[t], 1)
        if gap > 0:
            bench = sorted((e for e in mine if e["slot"] == "BENCH"), key=lambda e: -e["score"])
            sat_e = bench[0] if bench else None
            cands = [e for e in mine if e["slot"] in STARTER and sat_e and _fits(e["slot"], sat_e) and e["score"] < sat_e["score"]]
            lost.append({"team_id": t, "points": gap, "sat": card(sat_e) if sat_e else None,
                         "started": card(min(cands, key=lambda e: e["score"])) if cands else None})
    if lost:
        awards["bench"] = max(lost, key=lambda x: x["points"])
        awards["bench_top"] = sorted(lost, key=lambda x: -x["points"])[:3]  # the card's runners-up (2026-10-25)
    cur.execute("SELECT asof, team_a, team_b, p FROM fantasy_winprob_daily WHERE scenario = %s AND week = %s ORDER BY asof", (scenario, week_no))
    curves = {}
    for r in cur.fetchall():
        curves.setdefault((r["team_a"], r["team_b"]), []).append({"date": r["asof"].isoformat(), "p": r["p"]})
    imp = []
    for (a, b), pts in curves.items():
        if a not in score or b not in score:
            continue
        a_won = score[a] > score[b]
        cur_ = [x["p"] if a_won else 1 - x["p"] for x in pts] + [1.0]
        days = [x["date"] for x in pts]
        lo_i = min(range(len(cur_) - 1), key=lambda i: cur_[i]) if len(cur_) > 1 else None
        if lo_i is not None and cur_[lo_i] < 0.25:
            imp.append({"winner": a if a_won else b, "loser": b if a_won else a, "curve": cur_, "days": days, "low": round(cur_[lo_i], 3),
                        "low_date": days[lo_i]})
    if imp:
        awards["improbable"] = min(imp, key=lambda x: x["low"])
    buzz = []
    for a, b in pairs:
        win, lose = (a, b) if score[a] > score[b] else (b, a)
        ws = round(sum(e["sat"] for e in starters if e["team_id"] == win), 1)
        ls = round(sum(e["sat"] for e in starters if e["team_id"] == lose), 1)
        mine = [e for e in starters if e["team_id"] == win]
        if ws < ls and score[win] > score[lose] and not any(e["only_sun"] for e in mine):
            risers = sorted(({**card(e), "before": e["sat"]} for e in mine if e["score"] > e["sat"]), key=lambda x: -(x["score"] - x["before"]))[:3]
            buzz.append({"winner": win, "loser": lose, "sat": [ws, ls], "final": [score[win], score[lose]], "risers": risers})
    if buzz:
        awards["buzzer"] = max(buzz, key=lambda x: x["sat"][1] - x["sat"][0])
    # pickups (2026-10-25): every add that locked into this week's lineup, made since the last week ended (week 1: since
    # the draft) — a pickup who started ranks ahead of one on the bench, then by his points; the drop made in the same
    # move (if any) is shown with the difference, negative or not
    prev_end = next((x["end"] for x in weeks if x["week"] == week_no - 1), None)
    cur.execute("""SELECT team_id, kind, entity_id, at, asof FROM fantasy_transactions WHERE scenario = %s AND asof <= %s
                   AND (%s::date IS NULL OR asof > %s) AND kind IN ('add', 'drop') ORDER BY at""", (scenario, w["end"], prev_end, prev_end))
    moves = cur.fetchall()
    in_week = {(t, e["id"]) for (t, wn), es in lineups.items() if wn == week_no for e in es}
    slot_in_week = {(t, e["id"]): e["slot"] for (t, wn), es in lineups.items() if wn == week_no for e in es}

    def ent(eid):
        gs = games.get(eid, [])
        kind = "nba_team" if gs and gs[0].get("facts") else "player"
        cur.execute("SELECT name FROM fantasy_players WHERE id = %s", (eid,))
        r = cur.fetchone()
        if not r:
            cur.execute("SELECT name FROM fantasy_nba_teams WHERE id = %s", (eid,))
            r = cur.fetchone()
            kind = "nba_team" if r else kind
        return {"id": eid, "kind": kind, "name": r["name"] if r else eid, "nba_team": (gs[0]["team"] if gs else (eid if kind == "nba_team" else None)),
                "score": _wk(rules, kind, gs)}
    # a period = the time between one week's roster lock and the next: an add and a drop by the same team inside one
    # period are linked (2026-10-25)
    from .lineup import first_lock
    locks = sorted(datetime.fromisoformat(fl["at"]) for fl in (first_lock(cur, season, x) for x in weeks) if fl and fl.get("at"))
    period = lambda t: sum(1 for L in locks if t >= L)
    picks = []
    used = set()  # each drop pairs with one add
    for mv in moves:
        if mv["kind"] != "add" or (mv["team_id"], mv["entity_id"]) not in in_week:
            continue
        ad = ent(mv["entity_id"])
        # the drop it replaced: same team, same period, same kind (player for player, NBA team for NBA team), nearest in time
        cands = [d for d in moves if d["kind"] == "drop" and d["team_id"] == mv["team_id"] and id(d) not in used
                 and period(d["at"]) == period(mv["at"]) and ent(d["entity_id"])["kind"] == ad["kind"]]
        drop = min(cands, key=lambda d: abs((d["at"] - mv["at"]).total_seconds()), default=None)
        if drop:
            used.add(id(drop))
            dr = ent(drop["entity_id"])
        else:
            # no drop: the spot came from moving someone to IR — he replaced that player (Bridges for Dybantsa, George
            # for Butler); a plain open spot doesn't count, any pickup "works" there (2026-10-25)
            ir = next((e for e in lineups.get((mv["team_id"], week_no), []) if e["slot"] == "IR" and ("ir", e["id"]) not in used
                       and ent(e["id"])["kind"] == ad["kind"]), None)
            if not ir:
                continue
            used.add(("ir", ir["id"]))
            dr = {**ent(ir["id"]), "ir": True}  # moved to IR, not dropped
        if ad["score"] <= dr["score"]:
            continue  # a pickup of the week beats who he replaced
        started = slot_in_week.get((mv["team_id"], mv["entity_id"])) in STARTER
        picks.append({"team_id": mv["team_id"], "added": ad, "dropped": dr, "gain": round(ad["score"] - dr["score"], 1) if dr else None,
                      "started": started})
    if picks:
        awards["pickups"] = sorted(picks, key=lambda x: (not x["started"], -x["gain"]))[:3]  # started first, then the gain
    # standings after this week, and games behind each of the last 8 weeks
    rec = {t: {"w": 0, "l": 0, "t": 0, "pf": 0.0, "pa": 0.0} for t in teams}
    hist = []
    for x in res["weeks"]:
        if x["kind"] != "regular" or (x["status"] != "final" and not (preview and x["week"] == week_no)) or x["week"] > week_no:
            continue
        for m in x["matchups"]:
            a, b = m["home"], m["away"]
            for me, op in ((a, b), (b, a)):
                r = rec.setdefault(me["team"]["id"], {"w": 0, "l": 0, "t": 0, "pf": 0.0, "pa": 0.0})
                r["pf"] += me["score"]; r["pa"] += op["score"]
                r["w" if me["score"] > op["score"] else "l" if me["score"] < op["score"] else "t"] += 1
        lead = max(rec.values(), key=lambda r: (r["w"] + r["t"] / 2) - (r["l"] + r["t"] / 2))
        hist.append({"week": x["week"], "gb": {t: ((lead["w"] - r["w"]) + (r["l"] - lead["l"])) / 2 for t, r in rec.items()},
                     "pf": {t: r["pf"] for t, r in rec.items()},
                     "rank": {t: i + 1 for i, t in enumerate(sorted(rec, key=lambda t: (-(rec[t]["w"] + rec[t]["t"] / 2), -rec[t]["pf"])))}})
    standings = [{"team_id": t, "rank": hist[-1]["rank"][t], "prev": hist[-2]["rank"][t] if len(hist) > 1 else None,
                  "w": r["w"], "l": r["l"], "t": r["t"], "pf": round(r["pf"], 1), "pa": round(r["pa"], 1)}
                 for t, r in sorted(rec.items(), key=lambda kv: hist[-1]["rank"][kv[0]])]
    return {"week": week_no, "label": w["label"], "start": w["start"].isoformat(), "end": w["end"].isoformat(), "teams": teams,
            "scores": score, "best": order[0], "worst": order[-1], "biggest": margins[0], "closest": margins[-1], "faces": faces,
            "players": potw, "free_agents": fa, "versus": versus, "awards": awards, "standings": standings, "gb": hist[-8:],
            "labels": {c["id"]: c["label"] for side in ("player", "team") for c in rules[side]["components"]}}


def draft_value(cur, scenario: str, draft: dict | None) -> dict | None:
    """Draft Value (after Week 1): each pick's actual points added a week — his weekly scores while he was the drafting
    team's, minus the draft's replacement player's over the same weeks — next to the draft-day projection. A dropped
    pick counts only through the week he left; the dropped pick who did most since is the "biggest regret"."""
    if not draft:
        return None
    lg = engine.league(cur, scenario)
    season, today = lg["season"], engine.as_of(lg)
    weeks = [w for w in engine.weeks_for_league(cur, lg) if w["kind"] == "regular" and w["end"] < today]
    if not weeks:
        return None
    rules = scoring_mod.league_rules(cur, scenario)
    lineups = etch_mod.week_lineups(cur, scenario, season, engine.weeks_for_league(cur, lg), today)
    games = _games(cur, season, weeks[0]["start"], weeks[-1]["end"], rules)
    def weekly_scores(eid, kind):
        out = {}
        for w in weeks:
            gs = [g for g in games.get(eid, []) if w["start"].isoformat() <= g["date"] <= w["end"].isoformat()]
            out[w["week"]] = _wk(rules, kind, gs)
        return out
    repl = {pos: (r, weekly_scores(r["id"], r["kind"])) for pos, r in draft["replacement"].items()}
    rows, regret = [], []
    for p in draft["picks"]:
        mine = [w["week"] for w in weeks if any(e["id"] == p["id"] for e in lineups.get((p["team_id"], w["week"]), []))]
        ws = weekly_scores(p["id"], p["kind"])
        r = repl.get(p["pos"])
        if mine:
            avg = sum(ws[x] for x in mine) / len(mine)
            ravg = sum(r[1][x] for x in mine) / len(mine) if r else 0
            actual = round(avg - ravg, 1)
        else:
            actual = None
        left = None if len(mine) == len(weeks) else (max(mine) if mine else 0)
        rows.append({**{k: p[k] for k in ("id", "kind", "name", "pos", "nba_team", "team_id", "slot", "price", "pick_no", "added")},
                     "actual": actual, "weeks": len(mine), "left_week": left})
        if left is not None:
            after = [ws[w["week"]] for w in weeks if w["week"] > left]
            if after:
                regret.append({"id": p["id"], "team_id": p["team_id"], "left_week": left, "since": round(sum(after), 1), "weeks_since": len(after)})
    by_team = {}
    for r_ in rows:
        if r_["slot"] not in ("BENCH", "IR") and r_["actual"] is not None:
            by_team[r_["team_id"]] = round(by_team.get(r_["team_id"], 0) + r_["actual"], 1)
    teams = [{**t, "actual": by_team.get(t["id"], 0.0)} for t in draft["teams"]]
    teams.sort(key=lambda t: -t["actual"])
    return {"type": draft["type"], "through": weeks[-1]["week"], "teams": teams, "picks": rows,
            "regret": max(regret, key=lambda x: x["since"]) if regret else None}


def week_ready(cur, lg: dict, w: dict) -> bool:
    """When a week's recap can be made (2026-10-25): once every NBA game of the week is final (Best free agents needs all of
    them, not just the fantasy teams' games), or at 2 AM Central the Monday after if some game still isn't marked final.
    A league on a sim date: once the week is over."""
    today = engine.as_of(lg)
    if w["start"] > today:
        return False
    if lg.get("sim_date"):
        return w["end"] < today
    from backend.config import CENTRAL
    now = datetime.now(CENTRAL)
    if now >= datetime.combine(w["end"] + timedelta(days=1), datetime.min.time().replace(hour=2), tzinfo=CENTRAL):
        return True
    cur.execute("""SELECT count(*) AS n, count(*) FILTER (WHERE status <> 'final') AS open FROM nba_games
                   WHERE season = %s AND game_type = 'regular' AND missing_since IS NULL AND game_date BETWEEN %s AND %s""",
                (lg["season"], w["start"], w["end"]))
    r = cur.fetchone()
    return bool(r["n"]) and r["open"] == 0 and today >= w["end"]


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
    lg = engine.league(cur, scenario)
    today = engine.as_of(lg)
    done = [w for w in engine.weeks_for_league(cur, lg) if w["kind"] == "regular" and week_ready(cur, lg, w)]
    return {"draft": draft, "value": draft_value(cur, scenario, draft) if done else None,
            "weeks": [{"week": w["week"], "label": w["label"]} for w in done]}


def week_recap(cur, scenario: str, week_no: int) -> dict | None:
    """A finished week's report; frozen the first time it's built (stat corrections after don't rewrite it)."""
    cur.execute("SELECT data FROM fantasy_recaps WHERE scenario = %s AND kind = 'week' AND week = %s", (scenario, week_no))
    row = cur.fetchone()
    if row:
        return row["data"]
    lg = engine.league(cur, scenario)
    w = next((x for x in engine.weeks_for_league(cur, lg) if x["week"] == week_no and x["kind"] == "regular"), None)
    if not w or not week_ready(cur, lg, w):
        return None
    data = weekly(cur, scenario, week_no, preview=w["end"] >= engine.as_of(lg))  # every game final before midnight: made then
    if data:
        cur.execute("""INSERT INTO fantasy_recaps (scenario, kind, week, data) VALUES (%s, 'week', %s, %s) ON CONFLICT DO NOTHING""",
                    (scenario, week_no, json.dumps(data)))
    return data
