"""Weekly win probability: play the rest of the week out a few thousand times.

Each starter's state:
  current  — what he's already locked in this week (best game so far; None = no game yet)
  left     — games still to play this week
  p_play   — chance he plays each of them (availability; injuries mark games out before this is built)
  games    — optional, instead of left / p_play: [(chance he plays it, opponent factor)] per remaining game; a game in
             progress is (1, factor, points so far, share of his usual minutes left)
  scores   — his own game scores (this season, topped up with last season's while thin) — his range / volatility

One run: every starter gets a form for the week (FORM_SD), plays each remaining game with chance p_play, each game
drawn from his own scores × that form; his week =
his best game (or the sum, for a "sum" side). Team = sum of starters. Win probability = share of runs won (ties ½).
With nothing left to play, it's the actual result. Back-tested on 2025-26: scripts/backtest_winprob.py (WINPROB.md).
"""
import random
import threading
import time

RUNS = 4000
FORM_SD = 0.0    # week-to-week form (minutes, role, health): off until the back-test shows it helps


def _week_value(st: dict, mode: str, rnd: random.Random, form_sd: float) -> float:
    cur = st.get("current")
    scores = st.get("scores") or []
    form = max(0.0, rnd.gauss(1.0, form_sd)) if form_sd else 1.0  # this week's form scales his games still to come
    # each remaining game: (chance he plays it, opponent factor); without a per-game list, `left` games at p_play
    games = st.get("games") or [(st.get("p_play", 1.0), 1.0)] * st.get("left", 0)
    form = form * st.get("scale", 1.0)  # calibrated so his average simulated week = his projected week (lineup._sim_scale)
    draws = []
    for g in games:
        if not scores:
            break
        if len(g) == 4:  # a game in progress: points so far + one of his games × the share of his usual minutes left
            draws.append(g[2] + rnd.choice(scores) * form * g[1] * g[3])
        elif rnd.random() < g[0]:
            draws.append(rnd.choice(scores) * form * g[1])
    if mode == "sum":
        return (cur or 0.0) + sum(draws)
    vals = draws + ([cur] if cur is not None else [])
    return max(vals) if vals else 0.0


def team_total(states: list, rnd: random.Random, form_sd: float = FORM_SD) -> float:
    return sum(_week_value(st, st.get("mode", "best_game"), rnd, form_sd) for st in states)


def _scale(st: dict) -> float:
    from .lineup import _sim_scale
    return _sim_scale(st.get("proj"), st.get("current"), st.get("scores") or [], st.get("games") or [], st.get("mode", "best_game"))


def win_prob(a: list, b: list, runs: int = RUNS, seed: int = 0, form_sd: float = FORM_SD) -> float:
    """P(team a beats team b) from here. a / b = lists of starter states (see module doc)."""
    if not any(st.get("left") or st.get("games") for st in a + b):  # the week is decided
        ta = sum((st.get("current") or 0.0) for st in a)
        tb = sum((st.get("current") or 0.0) for st in b)
        return 1.0 if ta > tb else 0.0 if tb > ta else 0.5
    rnd = random.Random(seed)
    wins = 0.0
    for _ in range(runs):
        ta, tb = team_total(a, rnd, form_sd), team_total(b, rnd, form_sd)
        wins += 1.0 if ta > tb else 0.5 if ta == tb else 0.0
    return wins / runs


def week_probs(cur, scenario: str, week_no: int | None = None) -> dict:
    """Every matchup's win probability for a week (default: the current one), from both teams' week views with the
    injury report applied. {"week", "matchups": [{"a", "b", "p"}]} — p = team a's chance."""
    from .engine import league, matchup_overrides, week_pairings
    from .lineup import week_view
    cur.execute("SELECT id, name FROM fantasy_teams WHERE scenario = %s", (scenario,))
    teams = [dict(t) for t in cur.fetchall()]
    league(cur, scenario)
    views, week = {}, None
    for t in teams:
        v = week_view(cur, scenario, t["id"], week_no, injuries=True, sim=True)
        week = week or v["week"]
        views[t["id"]] = [{**e["_sim"], "scale": _scale(e["_sim"])} for e in v["entries"]
                          if e.get("slot") not in ("BENCH", "IR") and "_sim" in e]
    if not week or week["kind"] != "regular":
        return {"week": week, "matchups": []}
    out = []
    for a, b in week_pairings(teams, week["week"], matchup_overrides(cur, scenario)):
        out.append({"a": a["id"], "b": b["id"], "p": round(win_prob(views[a["id"]], views[b["id"]], seed=week["week"]), 3)})
    return {"week": week, "matchups": out}


# Serving (2026-10-19): building every team's week and simulating takes ~4 s, so the last result is kept. Fresh for a
# minute; older → the saved one is served at once and rebuilt in the background. A lineup / roster change (any move,
# add, drop, trade) rebuilds right away, so a manager never sees the chance from before his own move.
FRESH = 60
_WP: dict = {}            # (scenario, week) -> (built at, roster fingerprint, result)
_BUSY: set = set()
_LOCK = threading.Lock()


def _rosters(cur, scenario: str) -> str:
    cur.execute("""SELECT md5(coalesce(string_agg(team_id || ':' || slot || ':' || coalesce(player_id, nba_team_id), ','
                   ORDER BY team_id, slot, coalesce(player_id, nba_team_id)), '')) AS h FROM fantasy_rosters WHERE scenario = %s""",
                (scenario,))
    return cur.fetchone()["h"]


def _build(key):
    from backend.db import get_db
    conn = get_db()
    try:
        with conn.cursor() as cur:
            fp = _rosters(cur, key[0])
            out = week_probs(cur, *key)
        conn.commit()
        _WP[key] = (time.time(), fp, out)
        return out
    finally:
        conn.close()
        _BUSY.discard(key)


def served(cur, scenario: str, week_no: int | None = None) -> dict:
    key = (scenario, week_no)
    hit = _WP.get(key)
    if not hit or hit[1] != _rosters(cur, scenario):
        return _build(key)
    if time.time() - hit[0] >= FRESH:
        with _LOCK:
            if key not in _BUSY:
                _BUSY.add(key)
                threading.Thread(target=_build, args=(key,), daemon=True).start()
    return hit[2]
