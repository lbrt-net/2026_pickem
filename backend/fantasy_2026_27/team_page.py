"""The NBA team page (GET /fantasy/2026_27/players/{tricode}/page): the player page's shape for a TM-slot entity
(commissioner, 2026-10-15: "build out teams, plain borders"). Same keys as player_page.build so the page and pop-up draw it
with the same code; differences: no bio / honors (tier "plain"), the wheel is replaced by the 7 TEAM scoring parts
(`parts`, percentiles vs the 30 teams), the box-score columns are those parts.

- Team games: every regular-season game, scored by the default TEAM rules (scoring.DEFAULT["team"]; its own score and
  the opponent's plus the defensive stats in nba_team_game_stats).
- Header: this season once it has a game (MAX = average weekly best, AVG per game, the games for the cloud), else the
  projection (fantasy_team_pool through board.py, percentiles vs the other teams, a violin of last season's games
  scaled to the projected average with simulated weekly bests).
"""
import json
import random
import time
from pathlib import Path

from . import scoring as scoring_mod
from .player_page import LIVE, SEASONS, _pctile, _team_games
from .schema import NBA_TEAM_NAMES
from .weeks import season_weeks, week_for

PARTS = [(c["id"], c["label"]) for c in scoring_mod.DEFAULT["team"]["components"]]
COMP = {c["id"]: c for c in scoring_mod.DEFAULT["team"]["components"]}
# the card's wheel: 6 slices (the two points-allowed parts are one), clockwise from 12 o'clock
WHEEL = [("Points allowed", ("under125", "under100")), ("SCV", ("shot_clock",)), ("Fast break", ("fast_break",)),
         ("Paint", ("paint",)), ("Turnovers", ("tov15",)), ("Glass", ("glass",))]
DATA = Path(__file__).resolve().parent / "data" / "team_honors.json"
HONORS = json.loads(DATA.read_text()) if DATA.exists() else {}  # tricode → {champ, finals, conf} (scripts/build_team_honors.py)


def events(c_id: str, pts: float) -> float:
    """How many times a part's event happened in a game (box score mode): SCV = violations forced, <125 = held under
    125 (1/0), the rest = 1 when the bonus hit."""
    c = COMP[c_id]
    if c["type"] == "per_stat":
        return pts / c["points"] if c["points"] else 0.0
    return 1.0 if pts > 0 else 0.0
CACHE_SECONDS = 1800
_cache: dict = {}


def season_games(cur, season: str) -> dict:
    """{tricode: [game dicts]} for a season's final regular-season games, scored by the TEAM rules (cached)."""
    hit = _cache.get(season)
    if hit and (season != LIVE or time.time() - hit[0] < CACHE_SECONDS):
        return hit[1]
    weeks = season_weeks(cur, season)
    cur.execute("""SELECT game_id, game_date, home_team, away_team, home_score, away_score FROM nba_games
                   WHERE season = %s AND game_type = 'regular' AND status = 'final' AND missing_since IS NULL
                   ORDER BY game_date, game_id""", (season,))
    games = cur.fetchall()
    extras = scoring_mod.team_extras(cur, [g["game_id"] for g in games])
    side = scoring_mod.DEFAULT["team"]
    out = {}
    for g in games:
        w = week_for(weeks, g["game_date"]) if weeks else None
        for t, mine, theirs, home in ((g["home_team"], g["home_score"], g["away_score"], True),
                                      (g["away_team"], g["away_score"], g["home_score"], False)):
            if mine is None:
                continue
            sc = scoring_mod.score_game(side, scoring_mod.team_line(mine, theirs, extras.get((g["game_id"], t))))
            out.setdefault(t, []).append({
                "game_id": g["game_id"], "date": g["game_date"].isoformat(), "opp": g["away_team"] if home else g["home_team"],
                "home": home, "week": w["week"] if w else None, "fp": round(sc["total"], 1), "parts": sc["breakdown"],
                "res": f"{'W' if mine > theirs else 'L'} {mine}-{theirs}"})
    _cache[season] = (time.time(), out)
    return out


def summary(games: list) -> dict:
    bests = {}
    for g in games:
        if g["week"] is not None and (g["week"] not in bests or g["fp"] > bests[g["week"]]["fp"]):
            bests[g["week"]] = g
    n = len(games)
    parts = {k: sum(g["parts"].get(k, 0) for g in games) / n for k, _ in PARTS}
    counts = {k: sum(events(k, g["parts"].get(k, 0)) for g in games) for k, _ in PARTS}
    return {"gp": n, "avg": sum(g["fp"] for g in games) / n,
            "max": sum(b["fp"] for b in bests.values()) / len(bests) if bests else None,
            "parts": parts, "counts": counts, "best_ids": {b["game_id"] for b in bests.values()}}


def build(cur, scenario: str, tri: str, owner: dict | None, on_waivers: bool, proj_board: dict | None) -> dict | None:
    tri = tri.upper()
    if tri not in NBA_TEAM_NAMES:
        return None
    sg = {s: season_games(cur, s) for s in SEASONS}
    summ = {s: {t: summary(gs) for t, gs in sg[s].items()} for s in SEASONS}

    def wheel(s: str) -> list:
        """6 slices: points per game in each, percentile vs the 30 teams that season."""
        val = lambda x, ks: sum(x["parts"][k] for k in ks)
        others = list(summ[s].values())
        return [{"k": name, "v": round(val(summ[s][tri], ks), 2), "p": _pctile([val(o, ks) for o in others], val(summ[s][tri], ks)) or 1,
                 "season": s} for name, ks in WHEEL]

    def pcts(s: str, me: dict) -> dict:
        others = list(summ[s].values())
        p = {k: _pctile([o[k] for o in others], me[k]) for k in ("max", "avg")}
        p.update({k: _pctile([o["parts"][k] for o in others], me["parts"][k]) for k, _ in PARTS})
        return p

    header, parts, wheel6 = None, None, None
    if tri in summ[LIVE]:
        wheel6 = wheel(LIVE)
        s, gs = summ[LIVE][tri], sg[LIVE][tri]
        pc = pcts(LIVE, s)
        header = {"season": LIVE, "gp": s["gp"], "max": s["max"], "avg": s["avg"], "pct": {k: pc[k] for k in ("max", "avg")},
                  "games": [[g["fp"], 1 if g["game_id"] in s["best_ids"] else 0] for g in gs]}
        parts = [{"k": k, "l": l, "v": round(s["parts"][k], 2), "p": pc[k]} for k, l in PARTS]
    elif proj_board and tri in proj_board:
        me = proj_board[tri]
        teams = [v for k, v in proj_board.items() if k in NBA_TEAM_NAMES]
        pct = {k: _pctile([o.get(src) for o in teams], me.get(src)) for k, src in (("max", "max"), ("avg", "avg"))}
        last = next((s for s in reversed(SEASONS) if s != LIVE and tri in sg[s]), None)
        rng = random.Random(sum(map(ord, tri)))
        dist = []
        if last and me.get("avg") is not None:
            base = summ[last][tri]["avg"]
            dist = [round(g["fp"] * me["avg"] / base, 1) for g in sg[last][tri]] if base else []
        cur.execute("SELECT proj_weeks FROM fantasy_team_pool WHERE team = %s ORDER BY season DESC LIMIT 1", (tri,))
        r = cur.fetchone()
        weeks = [w for w in ((r or {}).get("proj_weeks") or []) if w.get("games")]
        sim = []
        if dist and weeks:
            for _ in range(400 // len(weeks) + 1):
                for w in weeks:
                    sim.append(max(rng.choice(dist) for _ in range(w["games"])))
            rng.shuffle(sim)
            sim = sorted(round(x, 1) for x in sim[:400])
        header = {"season": LIVE, "proj": True, "gp": 0, "max": me.get("max"), "avg": me.get("avg"), "pct": pct,
                  "games": [], "dist": dist, "sim": sim}
        if last:
            wheel6 = wheel(last)
            pc = pcts(last, summ[last][tri])
            parts = [{"k": k, "l": l, "v": round(summ[last][tri]["parts"][k], 2), "p": pc[k], "season": last} for k, l in PARTS]

    # its 2026-27 projection goes to the pop-up's small table, not the Seasons section (2026-10-20, as player pages)
    proj_row = {"season": "'27", "proj": True, "team": tri, "max": (proj_board or {}).get(tri, {}).get("max"),
                "avg": (proj_board or {}).get(tri, {}).get("avg")}
    seasons = []
    for s in reversed(SEASONS):
        if tri in summ[s]:
            x = summ[s][tri]
            seasons.append({"season": "'" + s[-2:], "team": tri, "gp": x["gp"], "max": x["max"], "avg": x["avg"],
                            "parts": x["parts"], "counts": x["counts"], "pct": pcts(s, x)})

    # game log per season (every final game; '27 adds the schedule ahead)
    glog = {}
    for s in reversed(SEASONS):
        rows = [{k: g[k] for k in ("date", "opp", "home", "week", "fp", "parts", "res")}
                | {"best": g["game_id"] in summ[s][tri]["best_ids"], "counts": {k: events(k, g["parts"].get(k, 0)) for k, _ in PARTS}}
                for g in sg[s].get(tri, [])]
        if s == LIVE:
            weeks = season_weeks(cur, LIVE)
            played = {r["date"] for r in rows}
            for g in _team_games(cur, LIVE, tri):
                d = g["game_date"].isoformat()
                if d in played or g["status"] in ("final", "postponed", "cancelled"):
                    continue
                home = g["home_team"] == tri
                rows.append({"date": d, "opp": g["away_team"] if home else g["home_team"], "home": home, "up": 1,
                             "week": (week_for(weeks, g["game_date"]) or {}).get("week") if weeks else None})
            rows.sort(key=lambda r: r["date"])
        if rows:
            glog[s] = rows
    recent = [r for s in SEASONS for r in glog.get(s, []) if "fp" in r][-10:]
    nxt = [r for r in glog.get(LIVE, []) if r.get("up")][:10]
    counts = {}
    for r in glog.get(LIVE, []):
        if r.get("week") is not None:
            counts[r["week"]] = counts.get(r["week"], 0) + 1
    for r in nxt:
        r["wn"] = counts.get(r["week"])

    from .player_page import _moves  # the same list as player pages: adds / drops / claims + the draft pick (DATA.md)
    moves = _moves(cur, scenario, tri)
    ribbon = owner["abbreviation"] if owner and owner.get("abbreviation") else ("WW" if on_waivers else "FA")
    hon = HONORS.get(tri, {})
    return {"player": {"id": tri, "kind": "team", "name": NBA_TEAM_NAMES[tri], "team": tri, "pos": "TM", "tier": "plain",
                       "c": {k: v for k, v in (("champ", hon.get("champ")), ("finals", hon.get("finals"))) if v},
                       "ribbon": ribbon, "owner": owner, "in_pool": True},
            "header": header, "parts": parts, "wheel": wheel6, "part_labels": PARTS, "seasons": seasons, "proj_row": proj_row, "recent": recent, "next": nxt,
            "glog": glog, "status": None, "hist": [], "moves": moves}
