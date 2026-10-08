"""The draft list's numbers for one view (GET /players/board): every player's MAX, AVG, GP, MAX low /
MAX high and rank, either projected (the league season's pool) or actual (a past season's history).

- Projected: MAX = PROJ MAX, AVG = PROJ AVG; MAX low / high = his projected bad week (p25) / big week (p90)
  averaged over the weeks he has games. Rank by PROJ MAX (else PROJ AVG), like the draft.
- A past season ("2025-26" …): TOTAL = his weekly maxes added up over the season, MAX = average weekly max,
  AVG = FP per game, GP = games; MAX low / high = the 25th / 90th percentile of his actual weekly maxes.
  Rank by TOTAL (it rewards the weeks he actually showed up for).
"""
from . import projections
from .history import HISTORY_SEASONS


def _pct(vals: list[float], q: float) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    i = (len(s) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


def _r(v):
    return None if v is None else round(float(v), 1)


def board(cur, scenario: str, view: str) -> dict:
    if view == "proj":
        season = projections.league_season(cur, scenario)
        cur.execute("""SELECT player_id, proj_avg, proj_max, proj_weeks FROM fantasy_pool
                       WHERE season = %s AND (proj_avg IS NOT NULL OR proj_max IS NOT NULL)""", (season,))
        rows = {}
        for r in cur.fetchall():
            wk = [w for w in (r["proj_weeks"] or []) if w.get("games")]
            rows[r["player_id"]] = {
                "max": _r(r["proj_max"]), "avg": _r(r["proj_avg"]), "gp": None,
                "max_low": _r(sum(w["p25"] for w in wk) / len(wk)) if wk else None,
                "max_high": _r(sum(w["p90"] for w in wk) / len(wk)) if wk else None,
            }
        key = lambda pid: rows[pid]["max"] if rows[pid]["max"] is not None else (rows[pid]["avg"] or 0)
    elif view in HISTORY_SEASONS:
        season = view
        cur.execute("SELECT player_id, data FROM fantasy_history WHERE season = %s", (season,))
        rows = {}
        for r in cur.fetchall():
            d = r["data"]
            maxes = [w["max"] for w in d.get("weeks", [])]
            rows[r["player_id"]] = {"total": _r(sum(maxes)), "max": _r(d.get("avg_max")), "avg": _r(d.get("fp_per_game")), "gp": d.get("games"),
                                    "max_low": _r(_pct(maxes, 0.25)), "max_high": _r(_pct(maxes, 0.9))}
        key = lambda pid: rows[pid]["total"] or 0
    else:
        raise ValueError("view must be 'proj' or one of " + ", ".join(HISTORY_SEASONS))
    for n, pid in enumerate(sorted(rows, key=key, reverse=True), 1):
        rows[pid]["rank"] = n
    return {"view": view, "season": season, "players": rows}
