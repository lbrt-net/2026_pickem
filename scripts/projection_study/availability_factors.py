"""Does age, build or playing style explain games played beyond a player's own record? (AVAILABILITY.md)

Base: the availability model's prediction (availability.py: own record up to five seasons → durability curve).
For rotation player-seasons 2022-23 → 2024-25: residual = games played − base prediction (season-ending injuries left
out, as in the model). Each factor is taken from the season before (what's known before the season starts).
Factors: age; height, weight, heavy-for-height (weight ÷ height²); style archetype from the season before:
  creator (usage 27%+) → paint/rebounder (55%+ shots rim+paint, 9+ reb/36) → defensive specialist (2.5+ stl+blk/36,
  usage < 18%) → jump shooter (45%+ threes) → slasher (35%+ at the rim) → balanced.
Group adjustments are fit on '23–'25 and checked once on '26 (held out).
"""
import runpy
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import W  # noqa: E402

A = runpy.run_path(__file__.replace("availability_factors.py", "availability.py"), run_name="lib")
D, SEAS, history, curve, bio = A["D"], A["SEAS"], A["history"], A["curve"], A["bio"]
ARCH = pd.read_csv(W + "disp_arch.csv")
ARCH["reb36"] = (ARCH.OREB + ARCH.DREB) * 36 / ARCH.mpg
ARCH["def36"] = (ARCH.STL + ARCH.BLK) * 36 / ARCH.mpg


def style(r):
    if r.USG_PCT >= 0.27:
        return "creator"
    if r.rim + r.paint >= 0.55 and r.reb36 >= 9:
        return "paint / rebounder"
    if r.def36 >= 2.5 and r.USG_PCT < 0.18:
        return "defensive specialist"
    if r.three >= 0.45:
        return "jump shooter"
    if r.rim >= 0.35:
        return "slasher"
    return "balanced"


ARCH["style"] = ARCH.apply(style, axis=1)
PREV = ARCH.set_index(["season", "PLAYER_ID"])


def frame(targets):
    rows = []
    for r in D[D.rot & D.season.isin(targets)].itertuples():
        i = SEAS.index(r.season)
        h, n = history(r.pid, i)
        if not n or (SEAS[i - 1], r.pid) not in PREV.index:
            continue
        pv = PREV.loc[(SEAS[i - 1], r.pid)]
        ht, wt = bio.PLAYER_HEIGHT_INCHES.get(r.pid, np.nan), bio.PLAYER_WEIGHT.get(r.pid, np.nan)
        rows.append(dict(pid=r.pid, season=r.season, pred=82 * curve(h, n), actual=82 * r.rate, age=pv.AGE + 1,
                         ht=ht, wt=wt, bmi=703 * wt / ht ** 2 if ht == ht and wt == wt else np.nan, style=pv["style"],
                         mpg=pv.mpg))
    X = pd.DataFrame(rows)
    X["resid"] = X.actual - X.pred
    return X


def groups(X, col, bins=None):
    g = pd.cut(X[col], bins) if bins is not None else X[col]
    t = X.groupby(g, observed=True).resid.agg(["size", "mean", "std"])
    t["se"] = t["std"] / np.sqrt(t["size"])
    return t[["size", "mean", "se"]].round(1)


if __name__ == "__main__":
    F = frame(SEAS[2:5])
    H = frame(["2025-26"])
    pd.set_option("display.width", 160)
    print(f"fit seasons: {len(F)} player-seasons, average miss (actual − predicted) {F.resid.mean():+.1f} games\n")
    TESTS = {"age": [18, 23, 26, 29, 32, 35, 45], "ht": [60, 76, 79, 82, 90], "wt": [150, 200, 220, 240, 320],
             "bmi": [15, 23.5, 25, 26.5, 35], "style": None, "mpg": [0, 25, 30, 34, 45]}
    for col, bins in TESTS.items():
        print(f"— {col}: games played vs prediction (mean, ± standard error)")
        print(groups(F, col, bins).to_string(), "\n")
    # holdout: does a shrunk group adjustment (fit on '23–'25) shrink the '26 miss?
    base = np.sqrt(np.mean(H.resid ** 2))
    print(f"held-out '26: base miss {base:.2f} games (RMSE), {len(H)} player-seasons")
    for col, bins in TESTS.items():
        gF = pd.cut(F[col], bins) if bins else F[col]
        gH = pd.cut(H[col], bins) if bins else H[col]
        t = F.groupby(gF, observed=True).resid.agg(["size", "mean"])
        adj = (t["mean"] * t["size"] / (t["size"] + 50)).to_dict()      # shrink small groups toward 0
        new = H.resid - gH.map(adj).astype(float).fillna(0)
        print(f"  + {col:<6} adjustment: miss {np.sqrt(np.mean(new ** 2)):.2f} ({np.sqrt(np.mean(new ** 2)) - base:+.2f})")
    F.to_csv(W + "availability_factors.csv", index=False)
