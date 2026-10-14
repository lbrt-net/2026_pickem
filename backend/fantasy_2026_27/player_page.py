"""The player page (GET /fantasy/2026_27/players/{id}/page): everything the page draws, in one payload.

- Card: name, NBA team, position, bio (data/player_bio.json: height, weight, birth year), career honors
  (data/player_honors.json, counted per season) → card tier: MVP > All-NBA > All-Star > All-Defense > Plain.
- Header and wheel: this season (2026-27) only, blank until he plays (commissioner, 2026-10-14): GP, MPG, MAX (average of his weekly
  best games), AVG (per game), FLOOR (10th-percentile weekly best), CEILING (best weekly best), every game for
  the "Season performance" cloud (weekly bests flagged), and the wheel: fantasy points each group earns in his
  weekly-best games — Scoring (PTS, 3PTM, CLUTCH, FG-, FT-, BLKD), Playmaking (AST, TO), Boards, Stocks.
- Percentiles (all of them, header, wheel and tables): against players with BOTH 10+ games at 10+ MPG AND 250+
  total minutes that season (commissioner, 2026-10-14). Share of qualified players at or below him, 1–99.
  Misses and turnovers are negative fantasy points, so fewer = higher automatically.
- Seasons table: '27 projection (pool PROJ MAX / PROJ AVG) + '26–'23 per-game, by category, in fantasy points and
  box score; last 10 games; next 10 games of his team's schedule.
- Game log per season ('27 = schedule and games so far): every game of his team's, OUT rows for games he missed.
- Availability: today's injury report line + per season, each team game played or missed.
- Fantasy moves: this league's adds, drops, waiver claims and his draft pick.

Season aggregates for every player are computed once per season and kept (past seasons for good, the current one
for 30 minutes); warm() fills them at startup so the first visitor doesn't wait.
"""
import json
import time
from datetime import date
from pathlib import Path

from .logic import score_breakdown
from .projections import shown_max
from .weeks import season_weeks, week_for

SEASONS = ("2022-23", "2023-24", "2024-25", "2025-26", "2026-27")
LIVE = "2026-27"
CATS = ("pts", "fg3m", "clutch_pts", "fgx", "ftx", "blkd", "ast", "tov", "oreb", "dreb", "stl", "blk")
GROUPS = {"Scoring": ("pts", "fg3m", "clutch_pts", "fgx", "ftx", "blkd"), "Playmaking": ("ast", "tov"),
          "Boards": ("oreb", "dreb"), "Stocks": ("stl", "blk")}
WHEEL_ORDER = ("Playmaking", "Stocks", "Boards", "Scoring")  # clockwise from 12 o'clock: TR, BR, BL, TL
TIERS = ("mvp", "allnba", "allstar", "alldef")
DATA = Path(__file__).resolve().parent / "data"
CACHE_SECONDS = 1800

_cache: dict = {}
_extras: dict = {}


def _json(name: str) -> dict:
    if name not in _extras:
        p = DATA / name
        _extras[name] = json.loads(p.read_text()) if p.exists() else {}
    return _extras[name]


def qualified(gp: int, minutes: float) -> bool:
    return gp >= 10 and minutes / gp >= 10 and minutes >= 250


def raw_line(r) -> dict:
    """Box score counts under the same keys as the fantasy breakdown (misses as counts)."""
    return {"pts": r["pts"], "fg3m": r["fg3m"], "clutch_pts": r.get("clutch_pts") or 0, "fgx": r["fga"] - r["fgm"],
            "ftx": r["fta"] - r["ftm"], "blkd": r.get("blkd") or 0, "ast": r["ast"], "tov": r["tov"],
            "oreb": r["oreb"], "dreb": r["dreb"], "stl": r["stl"], "blk": r["blk"]}


def _summ(games: list[dict]) -> dict:
    """One player-season from his played games (each: fp, cat, raw, min, week)."""
    gp = len(games)
    mins = sum(g["min"] for g in games)
    bests = {}
    for g in games:
        if g["week"] is not None and (g["week"] not in bests or g["fp"] > bests[g["week"]]["fp"]):
            bests[g["week"]] = g
    ws = sorted(b["fp"] for b in bests.values())
    s = {"gp": gp, "minutes": mins, "mpg": mins / gp, "avg": sum(g["fp"] for g in games) / gp,
         "max": sum(ws) / len(ws) if ws else None, "floor": ws[max(0, int(len(ws) * .1))] if ws else None,
         "ceil": ws[-1] if ws else None,
         "cat": {k: sum(g["cat"].get(k, 0) for g in games) / gp for k in CATS},
         "raw": {k: sum(g["raw"][k] for g in games) / gp for k in CATS}}
    for grp, ks in GROUPS.items():
        s["cat"]["t_" + grp.lower()] = sum(s["cat"][k] for k in ks)
        s["wheel_" + grp] = (sum(sum(b["cat"].get(k, 0) for k in ks) for b in bests.values()) / len(bests)) if bests else None
    s["best_ids"] = {b["game_id"] for b in bests.values()}
    return s


_GAMES_SQL = """
    SELECT pg.*, g.game_date, g.home_team, g.away_team, g.home_score, g.away_score
    FROM nba_player_games pg JOIN nba_games g ON g.game_id = pg.game_id
    WHERE pg.season = %s AND g.game_type = 'regular' AND pg.minutes > 0 {extra}
    ORDER BY g.game_date, g.game_id
"""


def _game(r, weeks) -> dict:
    bd = score_breakdown(r)
    w = week_for(weeks, r["game_date"]) if weeks else None
    home = r["home_team"] == r["team"]
    return {"game_id": r["game_id"], "date": r["game_date"].isoformat(), "team": r["team"], "home": home,
            "opp": r["away_team"] if home else r["home_team"], "week": w["week"] if w else None,
            "min": round(r["minutes"]), "fp": round(sum(bd.values()), 1), "cat": bd, "raw": raw_line(r)}


def season_data(cur, season: str) -> dict:
    """{"weeks", "summ": {pid: season summary}, "qual": [summaries of qualified players]}, cached. Only summaries
    are kept (memory); a player's own games come from player_games."""
    hit = _cache.get(season)
    if hit and (season != LIVE or time.time() - hit[0] < CACHE_SECONDS):  # past seasons never change
        return hit[1]
    weeks = season_weeks(cur, season)
    cur.execute(_GAMES_SQL.format(extra=""), (season,))
    by_player = {}
    for r in cur.fetchall():
        by_player.setdefault(r["player_id"], []).append(_game(r, weeks))
    summ = {}
    for pid, games in by_player.items():
        s = _summ(games)
        s.pop("best_ids")
        summ[pid] = s
    del by_player
    out = {"weeks": weeks, "summ": summ,
           "qual": [s for s in summ.values() if qualified(s["gp"], s["minutes"])]}
    _cache[season] = (time.time(), out)
    return out


def player_games(cur, player_id: str, season: str, weeks) -> dict | None:
    """{"games": [...], "summ": {...}} for one player-season, or None if he didn't play."""
    cur.execute(_GAMES_SQL.format(extra="AND pg.player_id = %s"), (season, player_id))
    games = [_game(r, weeks) for r in cur.fetchall()]
    return {"games": games, "summ": _summ(games)} if games else None


def percentile(qual: list[dict], get, value) -> int | None:
    vals = [v for v in (get(q) for q in qual) if v is not None]
    if value is None or not vals:
        return None
    return max(1, min(99, round(100 * sum(1 for v in vals if v <= value) / len(vals))))


def season_pcts(qual: list[dict], s: dict) -> dict:
    p = {k: percentile(qual, lambda q, k=k: q["cat"][k], s["cat"][k]) for k in s["cat"]}
    for k in ("avg", "max", "floor", "ceil"):
        p[k] = percentile(qual, lambda q, k=k: q[k], s[k])
    for grp in GROUPS:
        p["wheel_" + grp] = percentile(qual, lambda q, g=grp: q["wheel_" + g], s["wheel_" + grp])
    return p


def tier(c: dict) -> str:
    return next((t for t in TIERS if c.get(t)), "plain")


def _height(h: str | None) -> str | None:
    if not h or "-" not in h:
        return h
    ft, inch = h.split("-", 1)
    return f"{ft}'{inch}\""


def _team_games(cur, season: str, team: str) -> list[dict]:
    cur.execute("""
        SELECT game_id, game_date, status, home_team, away_team, home_score, away_score FROM nba_games
        WHERE season = %s AND game_type = 'regular' AND missing_since IS NULL AND (home_team = %s OR away_team = %s)
        ORDER BY game_date, game_id
    """, (season, team, team))
    return cur.fetchall()


def _box_rows(cur, player_id: str, season: str) -> dict:
    """game_id → his box score row (including DNP rows with a reason)."""
    cur.execute("SELECT game_id, team, minutes, dnp_reason FROM nba_player_games WHERE player_id = %s AND season = %s",
                (player_id, season))
    return {r["game_id"]: r for r in cur.fetchall()}


def _stints(games: list[dict]) -> list[tuple]:
    """[(team, first date, last date)] in order, from the games he played."""
    out = []
    for g in games:
        if out and out[-1][0] == g["team"]:
            out[-1][2] = g["date"]
        else:
            out.append([g["team"], g["date"], g["date"]])
    return out


def season_log(cur, player_id: str, season: str, pg: dict, weeks: list[dict]) -> list[dict]:
    """Every game of his team's that season (the team of each stint); played rows carry the line, missed rows the
    reason. Before his first game / after his last, the first / last stint's team."""
    played = {g["game_id"]: g for g in pg["games"]}
    games = pg["games"]
    best = pg["summ"]["best_ids"]
    stints = _stints(games)
    if not stints:
        return []
    box = _box_rows(cur, player_id, season)
    rows = []
    for i, (team, first, last) in enumerate(stints):
        lo = first if i else "0000"
        hi = stints[i + 1][1] if i + 1 < len(stints) else "9999"
        for g in _team_games(cur, season, team):
            d = g["game_date"].isoformat()
            if not lo <= d < hi:
                continue
            if g["game_id"] in played and played[g["game_id"]]["team"] != team:
                continue
            home = g["home_team"] == team
            w = week_for(weeks, g["game_date"]) if weeks else None
            row = {"date": d, "opp": g["away_team"] if home else g["home_team"], "home": home, "week": w["week"] if w else None}
            if g["status"] == "final" and g["home_score"] is not None:
                mine, theirs = (g["home_score"], g["away_score"]) if home else (g["away_score"], g["home_score"])
                row["res"] = f"{'W' if mine > theirs else 'L'} {mine}-{theirs}"
            if g["game_id"] in played:
                p = played[g["game_id"]]
                row.update(min=p["min"], fp=p["fp"], cat=p["cat"], raw=p["raw"], best=g["game_id"] in best)
            elif g["status"] == "final":
                b = box.get(g["game_id"])
                row["out"] = (b["dnp_reason"] if b and b["dnp_reason"] else "Did not play").replace("DNP - ", "")
            elif g["status"] in ("postponed", "cancelled"):
                row["out"] = g["status"].capitalize()
            else:
                row["up"] = 1
            rows.append(row)
    rows.sort(key=lambda r: r["date"])
    return rows


def _moves(cur, scenario: str, player_id: str) -> list[dict]:
    """His fantasy moves in this league, newest first: draft pick, adds (waiver claims marked), drops."""
    cur.execute("""
        SELECT x.kind, x.via, x.at, x.asof, t.name AS team_name, t.abbreviation, t.color
        FROM fantasy_transactions x JOIN fantasy_teams t ON t.id = x.team_id AND t.scenario = x.scenario
        WHERE x.scenario = %s AND x.entity_id = %s ORDER BY x.at DESC, x.id
    """, (scenario, player_id))
    out = [{"d": r["asof"].isoformat(), "k": "claim" if r["kind"] == "add" and r["via"] == "waivers" else r["kind"],
            "team": [r["abbreviation"] or r["team_name"][:4].upper(), r["color"] or "#52637b"], "team_name": r["team_name"]}
           for r in cur.fetchall()]
    # his draft pick (a drafted player still on the drafting team keeps his pick number on the roster row)
    cur.execute("""
        SELECT r.*, t.name AS team_name, t.abbreviation, t.color, d.completed_at, d.started_at
        FROM fantasy_rosters r JOIN fantasy_teams t ON t.id = r.team_id
        LEFT JOIN fantasy_drafts d ON d.scenario = r.scenario
        WHERE r.scenario = %s AND r.player_id = %s AND r.pick_no IS NOT NULL
    """, (scenario, player_id))
    for r in cur.fetchall():
        when = r.get("completed_at") or r.get("started_at")
        out.append({"d": when.date().isoformat() if when else None, "k": "draft", "pick": r["pick_no"], "price": r.get("price"),
                    "team": [r["abbreviation"] or r["team_name"][:4].upper(), r["color"] or "#52637b"],
                    "team_name": r["team_name"]})
    return out


def build(cur, scenario: str, player_id: str, pool_row: dict | None, owner: dict | None, on_waivers: bool) -> dict | None:
    sds = {s: season_data(cur, s) for s in SEASONS}
    mine = {s: player_games(cur, player_id, s, sds[s]["weeks"]) for s in SEASONS if player_id in sds[s]["summ"]}
    played_in = [s for s in SEASONS if mine.get(s)]
    if not pool_row and not played_in:
        return None
    last = mine[played_in[-1]]["games"][-1] if played_in else None
    name = pool_row["name"] if pool_row else None
    if not name:
        cur.execute("SELECT player_name FROM nba_player_games WHERE player_id = %s ORDER BY game_id DESC LIMIT 1", (player_id,))
        r = cur.fetchone()
        name = r["player_name"] if r else player_id
    team = (pool_row or {}).get("nba_team") or (last["team"] if last else None)
    pos = (pool_row or {}).get("position") or "F"
    bio = _json("player_bio.json").get(player_id, {})
    honors = _json("player_honors.json").get(player_id, {})
    age_now = (2026 - bio["born"]) if bio.get("born") else None  # age during the 2026-27 season (born that year, roughly)

    now = LIVE if LIVE in played_in else None  # header + wheel: this season only (blank until he plays)
    header = None
    if now:
        sd = sds[now]
        p = mine[now]
        s, pc = p["summ"], season_pcts(sd["qual"], p["summ"])
        header = {"season": now, "gp": s["gp"], "mpg": round(s["mpg"], 1),
                  "max": s["max"], "avg": s["avg"], "floor": s["floor"], "ceil": s["ceil"],
                  "pct": {k: pc[k] for k in ("max", "avg", "floor", "ceil")},
                  "games": [[g["fp"], 1 if g["game_id"] in s["best_ids"] else 0] for g in p["games"]],
                  "wheel": [{"k": k, "v": round(s["wheel_" + k], 1) if s["wheel_" + k] is not None else None,
                             "p": pc["wheel_" + k] or 1} for k in WHEEL_ORDER],
                  "qualified": len(sd["qual"])}

    seasons = [{"season": "'27", "proj": True, "team": team,
                "max": shown_max((pool_row or {}).get("proj_weeks"), (pool_row or {}).get("proj_max")),
                "avg": (pool_row or {}).get("proj_avg")}]
    for s_name in reversed(played_in):
        if s_name == LIVE:
            continue
        p = mine[s_name]
        s = p["summ"]
        seasons.append({"season": "'" + s_name[-2:], "team": p["games"][-1]["team"], "gp": s["gp"], "mpg": s["mpg"],
                        "max": s["max"], "avg": s["avg"], "cat": s["cat"], "raw": s["raw"],
                        "pct": season_pcts(sds[s_name]["qual"], s),
                        "age": (int(s_name[:4]) + 1 - bio["born"] - 1) if bio.get("born") else None})
    if LIVE in played_in:  # this season's actual line sits under the projection
        p = mine[LIVE]
        s = p["summ"]
        seasons.insert(1, {"season": "'" + LIVE[-2:], "team": p["games"][-1]["team"], "gp": s["gp"], "mpg": s["mpg"], "max": s["max"],
                           "avg": s["avg"], "cat": s["cat"], "raw": s["raw"], "pct": season_pcts(sds[LIVE]["qual"], s),
                           "age": age_now})

    # last 10 played games, oldest → newest
    allg = []
    for s_name in played_in:
        best = mine[s_name]["summ"]["best_ids"]
        allg += [{**{k: g[k] for k in ("date", "opp", "home", "week", "min", "fp", "cat", "raw")},
                  "best": g["game_id"] in best} for g in mine[s_name]["games"]]
    recent = allg[-10:]

    # next 10 games of his team's schedule, with each week's game count
    live_weeks = sds[LIVE]["weeks"]
    nxt = []
    if team:
        sched = [g for g in _team_games(cur, LIVE, team) if g["status"] not in ("final", "postponed", "cancelled")
                 and g["game_date"] >= date.today()]
        per_week = {}
        for g in _team_games(cur, LIVE, team):
            w = week_for(live_weeks, g["game_date"]) if live_weeks else None
            if w and g["status"] not in ("postponed", "cancelled"):
                per_week[w["week"]] = per_week.get(w["week"], 0) + 1
        for g in sched[:10]:
            home = g["home_team"] == team
            w = week_for(live_weeks, g["game_date"]) if live_weeks else None
            nxt.append({"date": g["game_date"].isoformat(), "opp": g["away_team"] if home else g["home_team"], "home": home,
                        "week": w["week"] if w else None, "wn": per_week.get(w["week"]) if w else None})

    # game logs: '27 = his team's schedule (and any games so far), past seasons = every team game
    glog = {}
    for s_name in reversed(SEASONS):
        if s_name == LIVE:
            if LIVE in played_in:
                glog[LIVE] = season_log(cur, player_id, LIVE, mine[LIVE], live_weeks)
            elif team:
                glog[LIVE] = [{"date": g["game_date"].isoformat(), "opp": g["away_team"] if g["home_team"] == team else g["home_team"],
                               "home": g["home_team"] == team, "up": 1,
                               "week": (week_for(live_weeks, g["game_date"]) or {}).get("week") if live_weeks else None}
                              for g in _team_games(cur, LIVE, team)]
        elif s_name in played_in:
            glog[s_name] = season_log(cur, player_id, s_name, mine[s_name], sds[s_name]["weeks"])

    # availability: per season, each team game played / missed (regular season, games already played)
    hist = []
    for s_name in reversed(SEASONS):
        rows = [r for r in glog.get(s_name, []) if not r.get("up")]
        if not rows:
            continue
        hist.append({"season": s_name, "missed": sum(1 for r in rows if "out" in r),
                     "games": [{"d": r["date"], "p": 0 if "out" in r else 1, "o": r["opp"], "fp": r.get("fp", 0),
                                "r": r.get("out")} for r in rows]})
    cur.execute("SELECT status, injury, return_date, comment FROM nba_injuries WHERE player_id = %s LIMIT 1", (player_id,))
    inj = cur.fetchone()
    status = {"status": inj["status"], "injury": inj["injury"],
              "return_date": inj["return_date"].isoformat() if inj["return_date"] else None} if inj else None

    ribbon = owner["abbreviation"] if owner and owner.get("abbreviation") else ("WW" if on_waivers else "FA")
    return {
        "player": {"id": player_id, "name": name, "team": team, "pos": pos, "ht": _height(bio.get("ht")), "wt": bio.get("wt"),
                   "age": age_now, "c": honors, "tier": tier(honors), "in_pool": bool(pool_row),
                   "owner": owner, "ribbon": ribbon},
        "header": header, "seasons": seasons, "recent": recent, "next": nxt, "glog": glog,
        "status": status, "hist": hist, "moves": _moves(cur, scenario, player_id),
    }


# ---- Extras: the shot chart. Fields are computed offline (scripts/build_shot_fields.py, the pipeline chart's method) and
# stored per player-season in nba_shot_fields; the page lights its bulbs from them.
def shots(cur, player_id: str) -> dict:
    """{season: field data} for every season with his shot chart built, newest first."""
    cur.execute("SELECT season, data FROM nba_shot_fields WHERE player_id = %s ORDER BY season DESC", (player_id,))
    return {r["season"]: r["data"] for r in cur.fetchall()}


def warm() -> None:
    """Fill the season caches (run in a background thread at startup)."""
    from backend.db import get_db
    conn = get_db()
    try:
        with conn.cursor() as cur:
            for s in SEASONS:
                season_data(cur, s)
    finally:
        conn.close()
