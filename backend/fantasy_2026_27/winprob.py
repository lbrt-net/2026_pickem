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


def formula(a: list, b: list) -> float:
    """Team a's chance from the projections themselves (2026-10-19): each starter's projected week and how much it can
    still swing (its variance, from the same per-game numbers, chances and spread — lineup.proj_var). Margin = a's
    total − b's; spread = √(sum of every starter's variance); chance = normal curve. Nothing left to play → the result."""
    from math import erf, sqrt
    d = sum(p for p, _ in a) - sum(p for p, _ in b)
    v = sum(x for _, x in a) + sum(x for _, x in b)
    if v <= 1e-9:
        return 1.0 if d > 0 else 0.0 if d < 0 else 0.5
    return 0.5 * (1 + erf(d / sqrt(2 * v)))


def week_probs(cur, scenario: str, week_no: int | None = None) -> dict:
    """Every matchup's win probability for a week (default: the current one), from both teams' week views with the
    injury report applied. {"week", "matchups": [{"a", "b", "p"}]} — p = team a's chance."""
    from .engine import league, matchup_overrides, week_pairings
    from .week_cache import all_weeks
    cur.execute("SELECT id, name FROM fantasy_teams WHERE scenario = %s", (scenario,))
    teams = [dict(t) for t in cur.fetchall()]
    league(cur, scenario)
    views, week = {}, None
    for tid, v in all_weeks(cur, scenario, week_no).items():  # the same views Matchup / Home show (week_cache)
        week = week or v["week"]
        views[tid] = [(e["projected"] or e["week_score"] or 0.0, e.get("proj_var") or 0.0) for e in v["entries"]
                      if e.get("slot") not in ("BENCH", "IR")]
    if not week or week["kind"] != "regular":
        return {"week": week, "matchups": []}
    out = []
    for a, b in week_pairings(teams, week["week"], matchup_overrides(cur, scenario)):
        out.append({"a": a["id"], "b": b["id"], "p": round(formula(views[a["id"]], views[b["id"]]), 3)})
    return {"week": week, "matchups": out}


# Serving (2026-10-19): building every team's week and simulating takes ~4 s, so the last result is kept. Fresh for a
# minute; older → the saved one is served at once and rebuilt in the background. A lineup / roster change (any move,
# add, drop, trade) rebuilds right away, so a manager never sees the chance from before his own move. One rebuild per
# change: viewers arriving meanwhile wait for it (2026-10-29, week_cache.single_flight).
FRESH = 60
_WP: dict = {}            # (scenario, week) -> (built at, roster fingerprint, result)
_BUSY: set = set()
_LOCK = threading.Lock()
_MISS: dict = {}          # (scenario, week) -> (roster fingerprint, threading.Event): the rebuild under way


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
    from .week_cache import single_flight
    key = (scenario, week_no)
    hit = _WP.get(key)
    fp = _rosters(cur, scenario)
    if not hit or hit[1] != fp:
        return single_flight(_MISS, _LOCK, key, fp, lambda: _build(key), lambda: _WP.get(key))
    if time.time() - hit[0] >= FRESH:
        with _LOCK:
            if key not in _BUSY:
                _BUSY.add(key)
                threading.Thread(target=_build, args=(key,), daemon=True).start()
    return hit[2]
