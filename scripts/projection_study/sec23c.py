"""Player-level data for sections 2–3: projected vs actual '26 minutes and usage, per attempt, with reasons."""
import contextlib, io, json, os, runpy
import numpy as np, pandas as pd
os.environ["APPLY_LATE"] = "1"
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
with contextlib.redirect_stdout(io.StringIO()):
    P = runpy.run_path(S + "pipeline.py", run_name="lib")
    U = runpy.run_path(S + "usage_resplit.py", run_name="lib")


def adv(s):
    rs = json.load(open(f"{R}player_advanced/{s}.json"))["resultSets"][0]
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"]).set_index("PLAYER_ID")


A24, A25, A26 = adv("2023-24"), adv("2024-25"), adv("2025-26")
first26 = P["FIRST"]["2025-26"]
late25 = set(P["LATE_JUMPS"].get("2024-25", {}))
L0, L1 = pd.read_csv(S + "ladder_0.csv"), pd.read_csv(S + "ladder_1.csv")
d = L0.merge(L1[["pid", "7 + late-jump rule mpg"]], on="pid")
rows = []
for x in d.itertuples():
    p = x.pid
    m25 = A25.MIN.get(p, np.nan)
    t25 = A25.TEAM_ABBREVIATION.get(p)
    t26 = first26.get(p)
    reasons = []
    if t25 and t26 and t25 != t26:
        reasons.append("new team")
    if A25.GP.get(p, 0) < 40:
        reasons.append(f"{int(A25.GP.get(p, 0))} GP in '25")
    if A26.GP.get(p, 0) < 40:
        reasons.append(f"{int(A26.GP.get(p, 0))} GP in '26")
    if A25.AGE.get(p, 0) >= 33:
        reasons.append(f"age {int(A25.AGE.get(p) + 1)}")
    if p in late25:
        reasons.append("late-season jump in '25")
    rows.append(dict(name=x.name, act=x.act_mpg, last=None if np.isnan(m25) else float(m25),
                     flat=None if np.isnan(m25) else float(26.9 + 0.7 * (m25 - 26.9)),
                     final=None if pd.isna(x._asdict().get("_9")) else None, gp26=int(A26.GP.get(p, 0)), why=", ".join(reasons)))
fin = dict(zip(d.pid, d["7 + late-jump rule mpg"]))
for r, p in zip(rows, d.pid):
    v = fin.get(p)
    r["final"] = None if v is None or pd.isna(v) else float(v)
# usage '25 → '26, 60+ GP for team both seasons
v = U["transition"]("2024-25", "2025-26").reset_index(drop=True)
urows = [dict(name=r.name, t0=r.t0, t1=r.t1, moved=bool(r.moved), u0=float(r.u0), resplit=float(r.proj), act=float(r.act),
              final=float(r.u0 if r.moved else r.proj)) for r in v.itertuples()]
json.dump(dict(mins=rows, usage=urows), open(S + "sec23c.json", "w"), default=float)
m = pd.DataFrame(rows)
print(len(m), m.final.notna().sum(), len(urows))
