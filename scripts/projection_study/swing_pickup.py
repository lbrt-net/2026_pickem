"""Does a bench-tier player's own swing make him a better one-week pickup? (2026-11-08, commissioner's question)

Prior seasons '22–'26. Every week W (end of week W known), the band = players ranked 70–125 by season-to-date points
per game × availability (3+ games played). Target = his score next week (best game; 0 if he didn't play).
Compare four ways to pick among the band:
  level     season points per game × availability (no schedule)
  flat      expected best game next week, everyone's swing = 35% of level (games ~ Binomial(team games, avail))
  own       same, his own season-to-date spread of game scores
  shrunk    same, own spread pulled toward 35% of level with a 12-game prior (what fa_week6 uses)
Reported in real units: top-5 picks' actual average next-week score, and how often the higher-ranked of two band
players actually scored more. Then the direct check: band players split by own swing (same level ± 2), actual
next-week score vs the flat projection.
Run: .venv/bin/python scripts/projection_study/swing_pickup.py
"""
import sys
from math import comb

import numpy as np
import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__file__))
import fa_study as f  # noqa: E402

C = [0, 0, 0.564, 0.846, 1.029, 1.163]   # expected max of k standard normals


def week_proj(m, sd, n, p):
    n = int(n)
    p = max(p, 0.05)
    return sum(comb(n, k) * p ** k * (1 - p) ** (n - k) * (m + sd * C[min(k, 5)]) for k in range(1, n + 1))


pw, _ = f.player_weeks()
g = pd.read_parquet(f.W + "disp_games.parquet")
g["date"] = pd.to_datetime(g["date"])
g = g[g.MIN > 0]
rows = []
for s in f.SEASONS:
    gs = g[g.season == s].copy()
    monday = gs.date.min() - pd.to_timedelta(gs.date.min().weekday(), unit="D")
    gs["wk"] = (gs.date - monday).dt.days // 7
    last = int(pw[pw.season == s].wk.max())
    for W_ in range(2, last):
        F = f.features(pw, s, W_)
        F = F[F.g >= 3].copy()
        F["level"] = F.season_pg * F.avail
        F["rank"] = F.level.rank(ascending=False, method="first")
        F = F[(F["rank"] >= 70) & (F["rank"] <= 125) & (F.next_games > 0)].copy()
        if F.empty:
            continue
        sd = gs[gs.wk <= W_].groupby("PLAYER_ID").fp.std().reindex(F.index).fillna(0)
        F["own_sd"] = sd
        F["flat"] = [week_proj(m, .35 * m, n, p) for m, n, p in zip(F.season_pg, F.next_games, F.avail)]
        F["own"] = [week_proj(m, s_, n, p) for m, s_, n, p in zip(F.season_pg, F.own_sd, F.next_games, F.avail)]
        F["shrunk"] = [week_proj(m, (s_ * k + .35 * m * 12) / (k + 12), n, p)
                       for m, s_, k, n, p in zip(F.season_pg, F.own_sd, F.g, F.next_games, F.avail)]
        F["season"], F["W"] = s, W_
        rows.append(F[["name", "season", "W", "g", "season_pg", "avail", "own_sd", "next_games", "level", "flat", "own",
                       "shrunk", "target"]])
R = pd.concat(rows)
R.to_csv(f.W + "swing_pickup.csv")


def report(R, label):
    print(f"\n== {label}: {R.groupby(['season', 'W']).ngroups} weeks, {len(R)} player-weeks ==")
    print(f"{'pick by':8s} {'top-5 next wk':>14s} {'pairs right':>12s}")
    for m in ["level", "flat", "own", "shrunk"]:
        top5, pair = [], []
        for _, w in R.groupby(["season", "W"]):
            top5.append(w.nlargest(5, m).target.mean())
            a = w[m].values; t = w.target.values
            i, j = np.triu_indices(len(w), 1)
            d = np.sign(a[i] - a[j]) * np.sign(t[i] - t[j])
            pair.append((d > 0).sum() / max((d != 0).sum(), 1))
        print(f"{m:8s} {np.mean(top5):14.1f} {100 * np.mean(pair):11.1f}%")
    best = np.mean([w.nlargest(5, "target").target.mean() for _, w in R.groupby(["season", "W"])])
    print(f"{'best':8s} {best:14.1f}")


report(R, "All weeks")
report(R[R.W <= 5], "Early season (3–6 weeks of games known, like now)")

# Direct check: same level, different swing — does the swingy one beat the flat projection?
R["lvl_bin"] = (R.season_pg // 4) * 4
R["swing"] = R.own_sd / R.season_pg
R["swing_band"] = R.groupby("lvl_bin").swing.transform(lambda x: pd.qcut(x, 3, labels=["steady", "middle", "swingy"]))
print("\n== Same level, split by own swing (season so far): actual next week vs flat projection ==")
t = R.groupby("swing_band", observed=True).agg(n=("target", "size"), swing=("swing", "mean"), level=("season_pg", "mean"),
                                               flat=("flat", "mean"), actual=("target", "mean"))
t["actual - flat"] = t.actual - t.flat
print(t.round(2).to_string())
e = R[R.W <= 5]
t = e.groupby("swing_band", observed=True).agg(n=("target", "size"), swing=("swing", "mean"), level=("season_pg", "mean"),
                                               flat=("flat", "mean"), actual=("target", "mean"))
t["actual - flat"] = t.actual - t.flat
print("\nEarly season only:\n" + t.round(2).to_string())

print("\n== Games next week (band players, all weeks): actual next-week score ==")
print(R.groupby("next_games").agg(n=("target", "size"), level=("season_pg", "mean"), actual=("target", "mean")).round(1).to_string())
