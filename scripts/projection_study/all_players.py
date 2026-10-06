"""(1) Validation for everyone: project '26 from '23–'25 for every player with 20+ GP in '26; biggest misses.
(2) Uncertainty: '26 residuals (actual − projected FP/G) → middle-50% and 80% ranges, by group.
(3) Coverage for '27: every 2026-27 roster player — vet projection, rookie projection, or nothing.
FP excludes BLKD on both sides (consistent).
"""
import contextlib
import io
import runpy

import numpy as np
import pandas as pd

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
with contextlib.redirect_stdout(io.StringIO()):
    P = runpy.run_path(S + "pipeline.py", run_name="lib")
project, actual, A = P["project"], P["actual"], P["A"]

rows = []
for pid in A["2025-26"].index:
    a = actual(pid, "2025-26")
    if not a or a["gp"] < 20:
        continue
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            g = project(pid, "2025-26")
    except Exception as e:  # noqa: BLE001
        g = None
    rows.append(dict(pid=pid, name=A["2025-26"].PLAYER_NAME[pid], gp=a["gp"], act=a["fp"], act_mpg=a["mpg"],
                     proj=g["fp"] if g else np.nan, proj_mpg=g["mpg"] if g else np.nan,
                     age=g["age"] if g else A["2025-26"].AGE[pid], base=g["base"] if g else None,
                     stayed=g["stayed"] if g else None,
                     hist_gp=sum(A[s].GP.get(pid, 0) for s in ["2022-23", "2023-24", "2024-25"])))
v = pd.DataFrame(rows)
v["res"] = v.act - v.proj
have = v.dropna(subset=["proj"])
print(f"(1) '26 players with 20+ GP: {len(v)}   projected: {len(have)}   no projection (no '23–'25 games): {v.proj.isna().sum()}")
print(f"    FP/G error {have.res.abs().mean():.2f} (median {have.res.abs().median():.2f}), bias {(-have.res).mean():+.2f}; "
      f"within ±3: {(have.res.abs() <= 3).mean():.0%}, ±6: {(have.res.abs() <= 6).mean():.0%}")
print("\n    Biggest UNDER-projections (did better):")
for x in have.sort_values("res", ascending=False).head(12).itertuples():
    print(f"      {x.name:<24} proj {x.proj:5.1f} → {x.act:5.1f}   MPG {x.proj_mpg:4.1f} → {x.act_mpg:4.1f}   age {x.age:.0f}  {'moved' if x.stayed is False else 'stayed'}  hist GP {x.hist_gp}")
print("\n    Biggest OVER-projections (did worse):")
for x in have.sort_values("res").head(12).itertuples():
    print(f"      {x.name:<24} proj {x.proj:5.1f} → {x.act:5.1f}   MPG {x.proj_mpg:4.1f} → {x.act_mpg:4.1f}   age {x.age:.0f}  {'moved' if x.stayed is False else 'stayed'}  hist GP {x.hist_gp}")


def rng(r):
    q = np.percentile(r, [10, 25, 50, 75, 90])
    return f"n={len(r):>3}  median {q[2]:+5.1f}   middle 50% [{q[1]:+5.1f}, {q[3]:+5.1f}]   80% [{q[0]:+5.1f}, {q[4]:+5.1f}]"


print("\n(2) Uncertainty: actual − projected FP/G, '26")
print(f"    all            {rng(have.res)}")
groups = {
    "projected FP/G": pd.cut(have.proj, [0, 12, 18, 24, 60], labels=["<12", "12–18", "18–24", "24+"]),
    "age": pd.cut(have.age, [0, 24, 28, 32, 50], labels=["≤23", "24–27", "28–31", "32+"], right=False),
    "games '23–'25": pd.cut(have.hist_gp, [0, 80, 160, 300], labels=["<80", "80–159", "160+"], right=False),
    "team": have.stayed.map({True: "stayed", False: "moved"}),
}
for gname, gcol in groups.items():
    print(f"    by {gname}:")
    for lab, s in have.groupby(gcol, observed=True):
        print(f"      {str(lab):<12} {rng(s.res)}")

# rookie uncertainty ('26 class residuals of the rookie model, by pick)
with contextlib.redirect_stdout(io.StringIO()):
    RK = runpy.run_path(S + "rookies.py", run_name="lib")
va = RK["va"]
rr = va.fp - va.proj_fp
print("    rookies ('26 class, rookie model):")
for lab, s in rr.groupby(pd.cut(va.pick, [0, 5, 14, 30, 61], labels=["picks 1–5", "6–14", "15–30", "2nd rd/UDFA"])):
    print(f"      {str(lab):<12} {rng(s)}")
have.to_csv(R + "validation_26_all.csv", index=False)

# ---- (3) '27 coverage ----
r27 = pd.read_csv(R + "rosters/2026-27.csv")
rook = pd.read_csv(R + "rookie_projections_2026_27.csv", index_col=0)
cov = []
for x in r27.itertuples():
    p = int(x.PLAYER_ID)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            g = project(p, "2026-27")
    except Exception:  # noqa: BLE001
        g = None
    kind = "veteran" if g else ("rookie" if p in rook.index else "none")
    cov.append(dict(pid=p, name=x.PLAYER, team=x.TEAM, exp=x.EXP, kind=kind, fp=g["fp"] if g else rook.fp.get(p, np.nan)))
c = pd.DataFrame(cov)
print(f"\n(3) 2026-27 rosters: {len(c)} players → veteran projection {(c.kind == 'veteran').sum()}, rookie projection "
      f"{(c.kind == 'rookie').sum()}, NONE {(c.kind == 'none').sum()}")
none = c[c.kind == "none"]
print(f"    no projection, by listed experience: {none.exp.value_counts().to_dict()}")
print("    " + ", ".join(f"{n} ({t}, exp {e})" for n, t, e in zip(none.name, none.team, none.exp)))
c.to_csv(R + "coverage_2026_27.csv", index=False)
