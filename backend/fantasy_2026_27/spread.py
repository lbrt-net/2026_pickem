"""Projected FLOOR / CEILING (shown as MAX low / MAX high) from how a player's weekly bests actually spread
(DISPERSION.md, 2026-10-15). Replaces the per-week curve's averaged 25th / 90th percentiles, which came out too tight:
projected floors 12–24% below MAX and ceilings 22–47% above, against ~10–32% / ~20–62% in real seasons.

- A season's spread: D = (mean − 25th pct) ÷ mean and U = (90th pct − mean) ÷ mean of his weekly bests (every week he
  played, any game count — the same way the actual seasons are measured).
- Prior by level (his last season's mean weekly best: <20, 20–30, 30–40, 40+), then his own history (last 3 seasons,
  weighted by weeks, trusted fully at 60+ weeks) moves it: D' = prior + coef · own deviation. Fit on '23–'25 only
  ('26 held out): next season's floor AND ceiling follow his past floor drop; his past ceiling rise adds nothing, so the
  two stay tied (the lopsided part doesn't repeat). Held-out '26: corr 0.52 (floor) / 0.47 (ceiling); one simulated
  20-week season from these lands at 10–34% / 21–60%, like the real seasons.
- FLOOR = MAX × (1 − D), CEILING = MAX × (1 + U); MAX = the shown PROJ MAX.
"""
LEVELS = (20, 30, 40)
PRIOR_D = (0.3809, 0.2453, 0.1875, 0.1718)
PRIOR_U = (0.6706, 0.4508, 0.3566, 0.3192)
COEF_D = (-0.0039, 0.4614, 0.0428)   # intercept, own floor-drop deviation, own ceiling-rise deviation
COEF_U = (-0.0061, 0.9844, -0.0585)
FULL_TRUST_WEEKS = 60
SEASONS = ("2023-24", "2024-25", "2025-26")
MIN_WEEKS = 15


def _level(mu: float) -> int:
    return sum(mu >= x for x in LEVELS)


def _quantile(xs: list, q: float) -> float:
    s = sorted(xs)
    i = (len(s) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


def season_spread(maxes: list) -> tuple | None:
    if len(maxes) < MIN_WEEKS:
        return None
    mu = sum(maxes) / len(maxes)
    if mu <= 0:
        return None
    return (mu - _quantile(maxes, 0.25)) / mu, (_quantile(maxes, 0.9) - mu) / mu, mu, len(maxes)


def spread(seasons: list, projected_max: float | None) -> tuple:
    """(D, U) for a player from his past seasons' spreads [(D, U, mean, weeks), ...], oldest first."""
    seasons = [s for s in seasons if s]
    level = _level(seasons[-1][2] if seasons else (projected_max or 0))
    pd_, pu_ = PRIOR_D[level], PRIOR_U[level]
    if not seasons:
        return pd_ + COEF_D[0], pu_ + COEF_U[0]
    weeks = sum(s[3] for s in seasons)
    own_d = sum(s[0] * s[3] for s in seasons) / weeks
    own_u = sum(s[1] * s[3] for s in seasons) / weeks
    k = min(weeks / FULL_TRUST_WEEKS, 1.0)
    x = (1.0, k * (own_d - pd_), k * (own_u - pu_))
    d = pd_ + sum(c * v for c, v in zip(COEF_D, x))
    u = pu_ + sum(c * v for c, v in zip(COEF_U, x))
    return max(0.0, d), max(0.0, u)


def history_spreads(cur, player_ids: list) -> dict:
    """player id → [season spreads, oldest first] from fantasy_history (the last 3 seasons)."""
    if not player_ids:
        return {}
    cur.execute("SELECT player_id, season, data FROM fantasy_history WHERE season = ANY(%s) AND player_id = ANY(%s) ORDER BY season",
                (list(SEASONS), list(player_ids)))
    out = {}
    for r in cur.fetchall():
        s = season_spread([w["max"] for w in (r["data"] or {}).get("weeks", []) if w.get("max") is not None])
        if s:
            out.setdefault(r["player_id"], []).append(s)
    return out
