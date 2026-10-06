"""Career-phase corrections: next-season change in MPG, FGA/75, FTA/75 explained by
  age band + years-in-league band + production tier (usage x MPG, fifths) + decline (prior-year MPG change band).
Additive bands, light ridge. Train: '22→'23, '23→'24, '24→'25 (decline needs the season before).
Test: '25→'26 (players with 20+ GP both seasons), then points/G for the 210 zone-study players.
"""
import contextlib
import io
import json
import runpy
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem/scripts")
from load_historical_boxscores import minutes  # noqa: E402

R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
SEAS = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
BOX = {"2021-22": "/Users/allan/PycharmProjects/nba-pipeline/data/box_scores/trad_box_scores_2021_22.parquet",
       "2022-23": R + "box_scores_traditional/trad_box_scores_2022_23.parquet",
       "2023-24": R + "box_scores_traditional/trad_box_scores_2023_24.parquet",
       "2024-25": R + "box_scores_traditional/trad_box_scores_2024_25.parquet",
       "2025-26": "/Users/allan/PycharmProjects/nba-pipeline/data/box_scores/trad_box_scores_2025_26.parquet"}


def tab(kind, s):
    rs = json.load(open(f"{R}{kind}/{s}.json"))["resultSets"][0]
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"]).set_index("PLAYER_ID")


A = {s: tab("player_advanced", s) for s in SEAS}
FTA = {}
for s, f in BOX.items():
    d = pd.read_parquet(f)
    d = d[d.game_id.astype(str).str[2] == "2"].copy()
    d["player_id"] = d.player_id.astype(int)
    FTA[s] = d.groupby("player_id").fta.sum()

# years in league: season start year - draft year; undrafted → roster EXP (2025-26) back-dated; else unknown
draft = {}
for s in SEAS:
    b = tab("bios", s)
    for p, y in b.DRAFT_YEAR.items():
        if str(y).isdigit():
            draft[p] = int(y)
exp26 = pd.read_csv(f"{R}rosters/2025-26.csv").set_index("PLAYER_ID").EXP
exp26 = pd.to_numeric(exp26.replace("R", 0), errors="coerce")


def years(p, s):
    start = int(s[:4])
    if p in draft:
        return start - draft[p]
    if p in exp26.index and not np.isnan(exp26[p]):
        return int(exp26[p]) - (2025 - start)
    return np.nan


def rows(s_prev, s0, s1):
    a0, a1, ap = A[s0], A[s1], A[s_prev]
    j = a0[["AGE", "GP", "MIN", "POSS", "FGA", "USG_PCT"]].join(a1[["GP", "MIN", "POSS", "FGA"]], rsuffix="_1", how="inner")
    j = j[(j.GP >= 20) & (j.GP_1 >= 20)].copy()
    j["MIN_prev"] = ap.MIN.reindex(j.index)
    j["fga75_0"], j["fga75_1"] = 75 * j.FGA / j.POSS, 75 * j.FGA_1 / j.POSS_1
    j["fta75_0"] = 75 * FTA[s0].reindex(j.index).fillna(0) / j.POSS
    j["fta75_1"] = 75 * FTA[s1].reindex(j.index).fillna(0) / j.POSS_1
    j["yrs"] = [years(p, s0) for p in j.index]
    j["prod"] = j.USG_PCT * j.MIN
    j["trend"] = j.MIN - j.MIN_prev
    j["tr"] = f"'{s0[-2:]}→'{s1[-2:]}"
    return j


train = pd.concat(rows(a, b, c) for a, b, c in zip(SEAS[:3], SEAS[1:4], SEAS[2:5]))
test = rows("2023-24", "2024-25", "2025-26")
PROD_CUTS = list(np.quantile(train["prod"], [0.2, 0.4, 0.6, 0.8]))
BANDS = {
    "age": ([0, 23, 26, 29, 32, 35, 99], ["≤22", "23–25", "26–28", "29–31", "32–34", "35+"]),
    "yrs": ([-99, 2, 4, 7, 11, 99], ["0–1", "2–3", "4–6", "7–10", "11+"]),
    "prod": ([-1] + PROD_CUTS + [99], ["P1 low", "P2", "P3", "P4", "P5 top"]),
    "trend": ([-99, -4, -1, 1, 4, 99], ["fell 4+", "fell 1–4", "flat", "rose 1–4", "rose 4+"]),
}
SRC = {"age": "AGE", "yrs": "yrs", "prod": "prod", "trend": "trend"}


def design(df):
    cols = []
    for f, (cuts, labs) in BANDS.items():
        b = pd.cut(df[SRC[f]], cuts, labels=False, right=False)
        for i, lab in enumerate(labs):
            cols.append(((b == i) & b.notna()).astype(float).rename(f"{f}:{lab}"))
        cols.append(b.isna().astype(float).rename(f"{f}:unknown"))
    return pd.concat(cols, axis=1)


Xtr, Xte = design(train), design(test)
Xtr = Xtr.loc[:, Xtr.sum() > 0]
Xte = Xte.reindex(columns=Xtr.columns, fill_value=0)
LAM = 5.0
TARGETS = {"MPG": ("MIN", "MIN_1"), "FGA/75": ("fga75_0", "fga75_1"), "FTA/75": ("fta75_0", "fta75_1")}
fits = {}
for name, (c0, c1) in TARGETS.items():
    y = (train[c1] - train[c0]).to_numpy()
    X = np.column_stack([np.ones(len(Xtr)), Xtr.to_numpy()])
    pen = LAM * np.eye(X.shape[1])
    pen[0, 0] = 0
    beta = np.linalg.solve(X.T @ X + pen, X.T @ y)
    fits[name] = beta
    pred = beta[0] + Xte.to_numpy() @ beta[1:]
    test[f"proj_{name}"] = test[c0] + pred

print(f"Training: {len(train)} player-seasons ('22→'25). Test '25→'26: {len(test)} players (20+ GP both).\n")
print("Effects on next-season change (intercept + band effect), MPG | FGA/75 | FTA/75:")
names = list(Xtr.columns)
for f in BANDS:
    print(f"  {f}")
    for i, n in enumerate(names):
        if n.startswith(f + ":"):
            cnt = int(Xtr[n].sum())
            eff = [fits[t][0] + fits[t][i + 1] for t in TARGETS]
            print(f"    {n.split(':', 1)[1]:<10} n={cnt:>4}   {eff[0]:+5.2f} | {eff[1]:+5.2f} | {eff[2]:+5.2f}")

print("\nTest error ('25→'26):")
pull = 26.9 + 0.7 * (test.MIN - 26.9)
print(f"  MPG      same as '25 {(test.MIN - test.MIN_1).abs().mean():.2f}   flat 70% pull {(pull - test.MIN_1).abs().mean():.2f}   "
      f"career model {(test['proj_MPG'] - test.MIN_1).abs().mean():.2f}")
for t, (c0, c1) in list(TARGETS.items())[1:]:
    print(f"  {t:<8} same as '25 {(test[c0] - test[c1]).abs().mean():.2f}   career model {(test[f'proj_{t}'] - test[c1]).abs().mean():.2f}")
print("  MPG bias by age band (career model):  " + "  ".join(
    f"{lab} {(s['proj_MPG'] - s.MIN_1).mean():+.1f}" for lab, s in test.groupby(pd.cut(test.AGE, BANDS['age'][0], labels=BANDS['age'][1], right=False), observed=True)))

# points/G for the 210 zone-study players with career-model MPG + rates
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
with contextlib.redirect_stdout(io.StringIO()):
    P = runpy.run_path(S + "points.py", run_name="lib")
pids, act, nm = P["pids"], P["act_ppg"], P["names"]
t = test.reindex(pids)
ok = t.proj_MPG.notna().to_numpy()
poss_g = t.proj_MPG.to_numpy() * P["own_pace"] / 48
pts_career = poss_g / 75 * (t["proj_FGA/75"].to_numpy() * P["pps"] + t["proj_FTA/75"].to_numpy() * P["ftp"])
cur = P["proj_pts"]
print(f"\nPOINTS/G, {ok.sum()} players:   current model {np.abs(cur[ok] - act[ok]).mean():.2f} (bias {(cur[ok] - act[ok]).mean():+.2f})   "
      f"career model {np.abs(pts_career[ok] - act[ok]).mean():.2f} (bias {(pts_career[ok] - act[ok]).mean():+.2f})")
age = t.AGE.to_numpy()
for lo, hi, lab in [(0, 26, "≤25"), (26, 31, "26–30"), (31, 99, "31+")]:
    s = ok & (age >= lo) & (age < hi)
    print(f"   age {lab:<6} n={s.sum():>3}   current bias {(cur[s] - act[s]).mean():+.2f}   career bias {(pts_career[s] - act[s]).mean():+.2f}   "
          f"error {np.abs(cur[s] - act[s]).mean():.2f} → {np.abs(pts_career[s] - act[s]).mean():.2f}")
print("\nPoints/G (current → career → actual):")
for n in ["Anthony Edwards", "Luka Dončić", "Tyrese Maxey", "Stephen Curry", "Shai Gilgeous-Alexander", "Nikola Jokić",
          "DeMar DeRozan", "LeBron James", "Kevin Durant", "Cade Cunningham"]:
    if n in nm and ok[nm.index(n)]:
        i = nm.index(n)
        print(f"  {n:<24} {cur[i]:5.1f} → {pts_career[i]:5.1f} → {act[i]:5.1f}   (age {age[i]:.0f}, MPG {t.proj_MPG.iloc[i]:.1f} → {t.MIN_1.iloc[i]:.1f})")
