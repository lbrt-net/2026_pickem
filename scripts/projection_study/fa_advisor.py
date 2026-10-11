"""Free-agent advisor backtest (2026-10-11): which blend of recency / season / last season / schedule best predicts
NEXT week's score, for the players a team could actually pick up?

Data: disp_games.parquet (every player game '21–'26 with fantasy points). Weeks are Mon–Sun. The week score = the
best game of the week (league rule), 0 if he didn't play.

Each week W of '22–'26 (each with the prior season available), at the end of W, for every player:
  per-game level m = mix of
     recent   = exponentially weighted avg of his games so far this season (half-life h weeks)
     season   = plain avg of his games so far this season
     prior    = his avg last season (stands in for the preseason projection)
     weights: recency share r, prior weight shrinks as games pile up (k games of evidence = prior worth k_prior games)
  spread sd = his game-to-game SD (shrunk to 0.35·m when thin)
  games next week: his team's games in W+1 (the schedule is known) × his availability (share of his team's games he
     played in the last 4 weeks) — expected best of the games he plays.
Pool: the players a team could pick up — outside the top 60 by season-to-date average that week (7 teams × ~8 spots,
  plus slack). Metrics on that pool, per week: the actual next-week score of the advisor's top 10 (avg), and how many
  of its top 10 were in the actual top 10. '26 is the holdout: params are picked on '22–'25 only.
Run: .venv/bin/python scripts/projection_study/fa_advisor.py
"""
import itertools
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import W  # noqa: E402

G = pd.read_parquet(W + "disp_games.parquet")
G["date"] = pd.to_datetime(G["date"])
G = G[G.MIN > 0].copy()
SEASONS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
POOL_SKIP = 60
C_MAX = np.array([0, 0, 0.564, 0.846, 1.029, 1.163, 1.267, 1.352])   # E[max of n normals] in SDs


def weekno(d, start):
    return ((d - start).dt.days // 7).astype(int)


def prep(season):
    g = G[G.season == season].copy()
    monday = g.date.min() - pd.to_timedelta(g.date.min().weekday(), unit="D")
    g["wk"] = weekno(g.date, monday)
    prior = G[G.season == SEASONS[SEASONS.index(season) - 1]] if season != SEASONS[0] else G[G.season == "2020-21"]
    pr = prior.groupby("PLAYER_ID").fp.agg(["mean", "count"])
    team_games = g.groupby(["TEAM_ABBREVIATION", "wk"]).GAME_ID.nunique()
    weekly = g.groupby(["PLAYER_ID", "wk"]).fp.max()                 # best game of the week
    return g, pr, team_games, weekly


def exp_best(m, sd, n_team, avail):
    """E[best game] with n_team games, each played with chance avail (binomial over games played)."""
    out = np.zeros_like(m)
    for k in range(1, 8):
        pk = np.where(k <= n_team, _binom(n_team, k, avail), 0.0)
        out += pk * (m + sd * C_MAX[k])
    return out


def _binom(n, k, p):
    from math import comb
    n = n.astype(int)
    c = np.array([comb(int(a), k) if k <= a else 0 for a in n], dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        v = c * p ** k * (1 - p) ** np.maximum(n - k, 0)
    return np.nan_to_num(v)


def run(params, seasons):
    h, r, k_prior, sched = params
    res = []
    for season in seasons:
        g, pr, team_games, weekly = prep(season)
        last_wk = g.wk.max()
        for W_ in range(3, last_wk):
            past = g[g.wk <= W_]
            age = W_ - past.wk
            wts = 0.5 ** (age / h) if h else (age == 0).astype(float)
            agg = past.assign(w=wts, wfp=wts * past.fp).groupby("PLAYER_ID").agg(
                wsum=("w", "sum"), wfp=("wfp", "sum"), n=("fp", "size"), mean=("fp", "mean"), sd=("fp", "std"),
                team=("TEAM_ABBREVIATION", "last"))
            agg["recent"] = agg.wfp / agg.wsum
            agg["now"] = r * agg.recent + (1 - r) * agg["mean"]
            agg = agg.join(pr.rename(columns={"mean": "prior", "count": "pn"}), how="left")
            has = agg.prior.notna()
            agg["m"] = np.where(has, (agg.now * agg.n + agg.prior * k_prior) / (agg.n + k_prior), agg.now)
            agg["sdx"] = np.where((agg.n >= 6) & agg.sd.notna(), agg.sd, 0.35 * agg.m)
            # availability: share of his team's games he played, last 4 weeks
            recent_g = g[(g.wk > W_ - 4) & (g.wk <= W_)]
            played = recent_g.groupby("PLAYER_ID").GAME_ID.nunique()
            tg4 = recent_g.groupby(["TEAM_ABBREVIATION"]).GAME_ID.nunique()
            agg["avail"] = (played.reindex(agg.index).fillna(0) / agg.team.map(tg4).fillna(1)).clip(0, 1)
            nxt = agg.team.map(lambda t: team_games.get((t, W_ + 1), 0)).astype(int)
            if sched:
                agg["pred"] = exp_best(agg.m.values, agg.sdx.values, nxt.values, agg.avail.values)
            else:
                agg["pred"] = agg.m * agg.avail
            # the pool a team could pick from: outside the top 60 by season-to-date average (min 3 games)
            ranked = agg[agg.n >= 3].sort_values("mean", ascending=False)
            pool = ranked.iloc[POOL_SKIP:].copy()
            pool["actual"] = [weekly.get((p, W_ + 1), 0.0) for p in pool.index]
            top = pool.nlargest(10, "pred")
            best = pool.nlargest(10, "actual")
            res.append({"season": season, "wk": W_, "top10_avg": top.actual.mean(), "oracle_avg": best.actual.mean(),
                        "hits": len(set(top.index) & set(best.index))})
    return pd.DataFrame(res)


if __name__ == "__main__":
    fit, hold = SEASONS[:-1], SEASONS[-1:]
    grid = list(itertools.product([0, 1, 2, 4, 8], [0.0, 0.5, 1.0], [0, 10, 25], [False, True]))
    rows = []
    for p in grid:
        d = run(p, fit)
        rows.append({"half_life": p[0], "recency": p[1], "prior_games": p[2], "schedule": p[3],
                     "top10_avg": round(d.top10_avg.mean(), 2), "hits": round(d.hits.mean(), 2)})
        print(rows[-1], flush=True)
    t = pd.DataFrame(rows).sort_values("top10_avg", ascending=False)
    t.to_csv(W + "fa_advisor_grid.csv", index=False)
    print(t.head(12).to_string(index=False))
    b = t.iloc[0]
    best = (int(b.half_life), float(b.recency), int(b.prior_games), bool(b.schedule))
    base = {"last week only": (0, 1.0, 0, False), "season avg only": (1, 0.0, 0, False), "best": best}
    for name, p in base.items():
        for label, seasons in (("fit '22–'25", fit), ("holdout '26", hold)):
            d = run(p, seasons)
            print(f"{name:16s} {label}: top-10 picks avg {d.top10_avg.mean():.1f} (best possible {d.oracle_avg.mean():.1f}), hits {d.hits.mean():.2f}/10")
