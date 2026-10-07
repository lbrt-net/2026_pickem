"""Dispersion study, part 2: the weekly best game (the league's score) — how well does each spread model predict it?

Every player-week (Mon–Sun) in the target season, n = games he played that week. Each model gets the player's actual
season mean FP/G (so only the spread is tested) and predicts E[best of n games].
  mean only   : best = mean (no dispersion)
  normal      : SD = a·mean^b (fit on '22–'25 player-seasons), normal max
  normal+own  : SD × his prior-season spread ratio, kept at 20% (it repeats at r≈0.2)
  league shape: the league's pooled shape of standardized games (skewed), scaled by SD = a·mean^b
  own games   : his own prior-season games, rescaled to this season's mean (what lineup.expected_best does)
Dev targets '24, '25; '26 shown as the check.
"""
import json
import numpy as np
import pandas as pd

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
G = pd.read_parquet(S + "disp_games.parquet")
ps = pd.read_csv(S + "disp_ps.csv")
F = json.load(open(S + "disp_fit.json"))
a, b = np.exp(F["a"]), F["b"]
SEAS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
G["week"] = (G.date - pd.to_timedelta(G.date.dt.weekday, unit="D")).dt.date
st = G.groupby(["season", "PLAYER_ID"]).fp.agg(["mean", "std", "size"])
G = G.join(st, on=["season", "PLAYER_ID"])
G["z"] = (G.fp - G["mean"]) / G["std"]
NORM = {1: 0.0, 2: 0.5642, 3: 0.8463, 4: 1.0294, 5: 1.1630}


def emax(sorted_v, n):
    m = len(sorted_v)
    i = np.arange(m)
    w = ((i + 1) / m) ** n - (i / m) ** n
    return float((sorted_v * w).sum())


ZL = {}  # league shape per season: pooled z of dev games before the target season
ratio_prev = ps.set_index(["season", "PLAYER_ID"]).ratio
res = []
for t in ["2023-24", "2024-25", "2025-26"]:
    ti = SEAS.index(t)
    prev = SEAS[ti - 1]
    pool = np.sort(G[(G.season < t) & (G.season >= SEAS[max(0, ti - 3)]) & (G["size"] >= 40)].z.dropna().to_numpy())
    zmax = {n: emax(pool, n) for n in range(1, 6)}
    own_prev = {pid: np.sort(((x.fp - x.fp.mean()) / x.fp.std()).to_numpy()) for pid, x in G[(G.season == prev)].groupby("PLAYER_ID") if len(x) >= 30}
    gt = G[(G.season == t) & (G["size"] >= 20)]
    wk = gt.groupby(["PLAYER_ID", "week"]).agg(best=("fp", "max"), n=("fp", "size"), mu=("mean", "first"), name=("PLAYER_NAME", "last")).reset_index()
    wk = wk[wk.n <= 5]
    for r in wk.itertuples():
        sd = a * max(r.mu, 0.5) ** b
        own_r = ratio_prev.get((prev, r.PLAYER_ID), np.nan)
        f = 1 + 0.2 * (own_r - 1) if own_r == own_r else 1.0
        own = own_prev.get(r.PLAYER_ID)
        res.append(dict(season=t, pid=r.PLAYER_ID, name=r.name, week=r.week, n=r.n, mu=r.mu, best=r.best,
                        m_mean=r.mu, m_norm=r.mu + sd * NORM[r.n], m_own_ratio=r.mu + sd * f * NORM[r.n],
                        m_league=r.mu + sd * zmax[r.n], m_own=(r.mu + sd * emax(own, r.n)) if own is not None else np.nan))
d = pd.DataFrame(res)
d = d.dropna(subset=["m_own"])
d.to_parquet(S + "disp_weeks.parquet")
M = ["m_mean", "m_norm", "m_own_ratio", "m_league", "m_own"]
for t in ["2023-24", "2024-25", "2025-26"]:
    q = d[d.season == t]
    print(f"\n'{t[-2:]}{' (check)' if t == '2025-26' else ''}: {len(q)} player-weeks")
    print("  model         " + "  ".join(f"n={n} bias" for n in range(1, 6)) + "    |error| all")
    for m in M:
        print(f"  {m:<13} " + "  ".join(f"{(q[q.n == n][m] - q[q.n == n].best).mean():+8.2f}" for n in range(1, 6))
              + f"    {np.abs(q[m] - q.best).mean():.2f}")
print("\nleague shape: E[max] in SDs for n=1..5:", [round(emax(np.sort(G[(G.season < '2025-26') & (G['size'] >= 40)].z.dropna().to_numpy()), n), 3) for n in range(1, 6)],
      "  normal:", list(NORM.values()))
