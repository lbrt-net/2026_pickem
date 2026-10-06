"""BLKD (own shot blocked) framework.
1. League block rate per zone: BLKA_i ≈ Σ_z rate_z × FGA_{z,i}, least squares (non-negative) over '22–'25 player-seasons (200+ FGA).
2. Player factor = (his BLKA + K) / (his zone-expected BLKA + K) over the input seasons, K = 15 expected blocks.
3. Projection: zone attempts × zone rate × factor.
Validation on '26 (inputs '23–'25), two ways: with actual '26 zone attempts (tests the rate model alone), and per FGA.
"""
import json

import numpy as np
import pandas as pd

R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
ZMAP = {"Restricted Area": "RA", "In The Paint (Non-RA)": "Paint", "Mid-Range": "Mid", "Left Corner 3": "Corner3",
        "Right Corner 3": "Corner3", "Above the Break 3": "Other3", "Backcourt": "Other3"}
ZONES = ["RA", "Paint", "Mid", "Corner3", "Other3"]
K = 15.0


def zones(s):
    rs = json.load(open(f"{R}shot_locations/{s}.json"))["resultSets"]
    cat, _ = rs["headers"]
    skip, names = cat["columnsToSkip"], cat["columnNames"]
    out = {}
    for r in rs["rowSet"]:
        z = dict.fromkeys(ZONES, 0.0)
        for i, n in enumerate(names):
            if n in ZMAP:
                z[ZMAP[n]] += r[skip + 3 * i + 1] or 0
        out[r[0]] = z
    return pd.DataFrame(out).T[ZONES]


def blka(s):
    rs = json.load(open(f"{R}game_logs/{s}.json"))["resultSets"][0]
    d = pd.DataFrame(rs["rowSet"], columns=rs["headers"])
    return d.groupby("PLAYER_ID").agg(blka=("BLKA", "sum"), fga=("FGA", "sum"), gp=("GAME_ID", "nunique"),
                                      name=("PLAYER_NAME", "last"))


SE = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
Z = {s: zones(s) for s in SE}
B = {s: blka(s) for s in SE}

# 1. league zone rates on '22–'25 (fit seasons only)
X, y = [], []
for s in SE[:4]:
    j = Z[s].join(B[s], how="inner")
    j = j[j.fga >= 200]
    X.append(j[ZONES].to_numpy(float))
    y.append(j.blka.to_numpy(float))
X, y = np.vstack(X), np.concatenate(y)
active = list(range(5))
for _ in range(5):  # simple non-negative least squares: drop negative coefficients and refit
    coef, *_ = np.linalg.lstsq(X[:, active], y, rcond=None)
    if (coef >= 0).all():
        break
    active = [a for a, c in zip(active, coef) if c >= 0]
rate = np.zeros(5)
rate[active] = coef
print("League block rate by zone (share of attempts blocked), fit on '22–'25:")
print("  " + "   ".join(f"{z} {100 * r:.1f}%" for z, r in zip(ZONES, rate)))
print(f"  overall: {100 * y.sum() / X.sum():.1f}% of FGA blocked\n")


def proj(pid, ins, zone_att):
    exp_ = sum((Z[s].loc[pid].to_numpy(float) @ rate) if pid in Z[s].index else 0 for s in ins)
    act_ = sum(B[s].blka.get(pid, 0) for s in ins)
    factor = (act_ + K) / (exp_ + K)
    return float(zone_att @ rate * factor), factor


# 2–3. validation on '26
ins = SE[1:4]
rows = []
for pid in B["2025-26"].index:
    if pid not in Z["2025-26"].index or B["2025-26"].fga.get(pid, 0) < 200:
        continue
    if not any(pid in Z[s].index for s in ins):
        continue
    za = Z["2025-26"].loc[pid].to_numpy(float)
    p, f = proj(pid, ins, za)
    zone_only = float(za @ rate)
    a_, f_ = sum(B[s].blka.get(pid, 0) for s in ins), sum(B[s].fga.get(pid, 0) for s in ins)
    per_fga = B["2025-26"].fga[pid] * (a_ / f_ if f_ else y.sum() / X.sum())
    rows.append(dict(name=B["2025-26"].name[pid], gp=B["2025-26"].gp[pid], act=B["2025-26"].blka[pid], proj=p,
                     zone_only=zone_only, per_fga=per_fga, factor=f))
v = pd.DataFrame(rows)
for c in ["proj", "zone_only", "per_fga"]:
    v[c + "_g"] = v[c] / v.gp
v["act_g"] = v.act / v.gp
print(f"'26 validation, {len(v)} players with 200+ FGA (season BLKD per game; given actual '26 zone attempts):")
for c, lab in [("per_fga", "his own blocked-per-FGA × FGA"), ("zone_only", "league zone rates only"), ("proj", "zone rates × player factor")]:
    print(f"  {lab:<32} error {np.abs(v[c + '_g'] - v.act_g).mean():.3f}/G   corr {np.corrcoef(v[c + '_g'], v.act_g)[0, 1]:.2f}")
print(f"  (typical BLKD/G {v.act_g.median():.2f}; max {v.act_g.max():.2f}; FP cost = 0.5 × BLKD/G)\n")
print("Most blocked per game in '26 (proj → actual), and player factor (1.0 = what his zone mix predicts):")
for x in v.sort_values("act_g", ascending=False).head(10).itertuples():
    print(f"  {x.name:<24} {x.proj_g:.2f} → {x.act_g:.2f}   factor {x.factor:.2f}")
print("Factor extremes (input seasons, shrunk):")
lo, hi = v.sort_values("factor").head(5), v.sort_values("factor").tail(5)
print("  least blocked for his shots: " + ", ".join(f"{n} {f:.2f}" for n, f in zip(lo.name, lo.factor)))
print("  most blocked for his shots:  " + ", ".join(f"{n} {f:.2f}" for n, f in zip(hi.name, hi.factor)))
