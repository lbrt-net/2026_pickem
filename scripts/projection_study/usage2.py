"""Usage, last pass: does age or last season's efficiency predict next season's usage beyond the re-split?

Rows: '22→'23 … '25→'26 transitions (60+ GP for the team both seasons), from usage_resplit.transition.
Base = re-split (stayers) or own usage (movers). Target = actual next usage − base.
Candidate inputs (all known before the season):
  age (band), TS% minus league TS% that season, eFG% minus the eFG% his shot zones predict (zone league rates),
  usage level (u0 − 20%), moved, moved × usage level.
Fit on three transitions, check on the fourth (each in turn); report '26 player by player.
"""
import contextlib, io, json, runpy
import numpy as np, pandas as pd
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
with contextlib.redirect_stdout(io.StringIO()):
    U = runpy.run_path(S + "usage_resplit.py", run_name="lib")
    Z = runpy.run_path(S + "zone_projection.py", run_name="lib")


def adv(s):
    rs = json.load(open(f"{R}player_advanced/{s}.json"))["resultSets"][0]
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"]).set_index("PLAYER_ID")


SE = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
A = {s: adv(s) for s in SE}
ZONES = Z["ZONES"]
VAL = np.array([2, 2, 2, 3, 3], float)
xefg = {}
for s in SE:
    z = Z["load"](s).pivot_table(index="pid", columns="zone", values=["fga", "fgm"], fill_value=0)
    a, m = z["fga"][ZONES], z["fgm"][ZONES]
    lg = m.sum() / a.sum()  # league make rate by zone
    exp_pts = (a * lg * VAL).sum(1)
    act_pts = (m * VAL).sum(1)
    xefg[s] = ((act_pts - exp_pts) / (2 * a.sum(1).replace(0, np.nan)))  # eFG over zone-expected
v = pd.concat(U["transition"](a, b) for a, b in zip(SE, SE[1:])).reset_index(drop=True)
s0 = {"'22→'23": "2021-22", "'23→'24": "2022-23", "'24→'25": "2023-24", "'25→'26": "2024-25"}
v["s0"] = v.tr.map(s0)
v["age"] = [A[s].AGE.get(p, np.nan) for s, p in zip(v.s0, v.pid)]
lgts = {s: (A[s].TS_PCT * A[s].POSS).sum() / A[s].POSS.sum() for s in SE}
v["ts_rel"] = [A[s].TS_PCT.get(p, np.nan) - lgts[s] for s, p in zip(v.s0, v.pid)]
v["xefg"] = [xefg[s].get(p, np.nan) for s, p in zip(v.s0, v.pid)]
v["base"] = np.where(v.moved, v.u0, v.proj)
v["y"] = v.act - v.base
v["lvl"] = v.u0 - 0.20
v = v.dropna(subset=["age", "ts_rel", "xefg"]).reset_index(drop=True)
AGE_CUTS = [0, 24, 28, 31, 34, 99]
AGE_LAB = ["≤23", "24–27", "28–30", "31–33", "34+"]
ab = pd.cut(v.age, AGE_CUTS, labels=False, right=False)
print(f"{len(v)} player-seasons ({v.moved.sum()} movers)\n")
print("Raw patterns: usage change vs the base, by group")
for lab, g in v.groupby(pd.cut(v.age, AGE_CUTS, labels=AGE_LAB, right=False), observed=True):
    print(f"  age {lab:<6} n={len(g):>3}  {100 * g.y.mean():+.2f} pts  (stayed {100 * g[~g.moved].y.mean():+.2f}, moved {100 * g[g.moved].y.mean():+.2f})")
for lab, g in v.groupby(pd.qcut(v.ts_rel, 4, labels=["TS bottom quarter", "2nd", "3rd", "TS top quarter"]), observed=True):
    print(f"  {lab:<17} n={len(g):>3}  {100 * g.y.mean():+.2f} pts")
for lab, g in v.groupby(pd.qcut(v.xefg, 4, labels=["vs zones bottom", "2nd", "3rd", "vs zones top"]), observed=True):
    print(f"  {lab:<17} n={len(g):>3}  {100 * g.y.mean():+.2f} pts")


def X(df, feats):
    cols = [np.ones(len(df))]
    if "age" in feats:
        b = pd.cut(df.age, AGE_CUTS, labels=False, right=False)
        cols += [(b == i).astype(float) for i in range(1, len(AGE_LAB))]
    for f in feats:
        if f == "age":
            continue
        if f == "moved_lvl":
            cols.append(df.moved.astype(float) * df.lvl)
        elif f == "moved":
            cols.append(df.moved.astype(float))
        else:
            cols.append(df[f].astype(float))
    return np.column_stack(cols)


SPECS = {"re-split / own (current)": [], "+ age": ["age"], "+ efficiency (TS)": ["ts_rel"], "+ efficiency vs zones": ["xefg"],
         "+ usage level & moved": ["lvl", "moved", "moved_lvl"], "+ all": ["age", "ts_rel", "xefg", "lvl", "moved", "moved_lvl"]}
res = {}
print("\nCheck on each held-out season change (fit on the other three): players within 1.5 points / right direction when it moves 1+")
for lab, feats in SPECS.items():
    preds = np.zeros(len(v))
    for tr in v.tr.unique():
        trn, tst = v.tr != tr, v.tr == tr
        if feats:
            b, *_ = np.linalg.lstsq(X(v[trn], feats), v.y[trn], rcond=None)
            preds[tst] = v.base[tst] + X(v[tst], feats) @ b
        else:
            preds[tst] = v.base[tst]
    v["p_" + lab] = preds
    w = (np.abs(preds - v.act) <= 0.015)
    mv = np.abs(preds - v.base) >= 0.01
    right = ((preds - v.base) * (v.act - v.base) > 0)[mv]
    t26 = v.tr == "'25→'26"
    res[lab] = dict(w=int(w.sum()), n=len(v), w26=int(w[t26].sum()), n26=int(t26.sum()), right=int(right.sum()), moved=int(mv.sum()),
                    wm=int(w[v.moved].sum()), nm=int(v.moved.sum()))
    print(f"  {lab:<28} within 1.5: {w.sum()}/{len(v)}  ('26: {w[t26].sum()}/{t26.sum()})   movers {w[v.moved].sum()}/{v.moved.sum()}"
          + (f"   right direction {right.sum()}/{mv.sum()}" if feats else ""))
b_all, *_ = np.linalg.lstsq(X(v, SPECS["+ all"]), v.y, rcond=None)
names = ["intercept"] + [f"age {a}" for a in AGE_LAB[1:]] + ["TS rel", "eFG vs zones", "usage level", "moved", "moved × level"]
print("\nFit on all four (usage points):", ", ".join(f"{n} {100 * c:+.2f}" for n, c in zip(names, b_all)))
json.dump({"coef": dict(zip(names, map(float, b_all))), "res": res}, open(S + "usage2.json", "w"))
v.to_pickle(S + "usage2_rows.pkl")
