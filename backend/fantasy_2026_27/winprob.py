"""Weekly win probability: play the rest of the week out a few thousand times.

Each starter's state:
  current  — what he's already locked in this week (best game so far; None = no game yet)
  left     — games still to play this week
  p_play   — chance he plays each of them (availability; injuries mark games out before this is built)
  games    — optional, instead of left / p_play: [(chance he plays it, opponent factor)] per remaining game
  scores   — his own game scores (this season, topped up with last season's while thin) — his range / volatility

One run: every starter gets a form for the week (FORM_SD), plays each remaining game with chance p_play, each game
drawn from his own scores × that form; his week =
his best game (or the sum, for a "sum" side). Team = sum of starters. Win probability = share of runs won (ties ½).
With nothing left to play, it's the actual result. Back-tested on 2025-26: scripts/backtest_winprob.py (WINPROB.md).
"""
import random

RUNS = 4000
FORM_SD = 0.0    # week-to-week form (minutes, role, health): off until the back-test shows it helps


def _week_value(st: dict, mode: str, rnd: random.Random, form_sd: float) -> float:
    cur = st.get("current")
    scores = st.get("scores") or []
    form = max(0.0, rnd.gauss(1.0, form_sd)) if form_sd else 1.0  # this week's form scales his games still to come
    # each remaining game: (chance he plays it, opponent factor); without a per-game list, `left` games at p_play
    games = st.get("games") or [(st.get("p_play", 1.0), 1.0)] * st.get("left", 0)
    draws = [rnd.choice(scores) * form * f for p, f in games if scores and rnd.random() < p]
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
        views[t["id"]] = [e["_sim"] for e in v["entries"] if e.get("slot") not in ("BENCH", "IR") and "_sim" in e]
    if not week or week["kind"] != "regular":
        return {"week": week, "matchups": []}
    out = []
    for a, b in week_pairings(teams, week["week"], matchup_overrides(cur, scenario)):
        out.append({"a": a["id"], "b": b["id"], "p": round(win_prob(views[a["id"]], views[b["id"]], seed=week["week"]), 3)})
    return {"week": week, "matchups": out}
