"""Model ladder on '26 validation: FP/G error for each step, by group (all / top-50 list / bad-EPM list).
Steps 3–7 are the per-game pipeline with features switched on one at a time."""
import contextlib, io, os, runpy, sys, json
import numpy as np, pandas as pd
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
late = sys.argv[1] if len(sys.argv) > 1 else "0"
os.environ["APPLY_LATE"] = late
with contextlib.redirect_stdout(io.StringIO()):
    P = runpy.run_path(S + "pipeline.py", run_name="lib")
g = P["project"].__globals__
A, actual, key = P["A"], P["actual"], P["name_key"]
ids = [p for p in A["2025-26"].index if (a := actual(p, "2025-26")) and a["gp"] >= 20]
acts = {p: actual(p, "2025-26") for p in ids}
def run(**kw):
    for k, v in kw.items():
        g[k] = v
    g["_models"].clear(); g["_usg"].clear()
    out = {}
    for p in ids:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                pr = g["project"](p, "2025-26")
        except Exception:
            pr = None
        out[p] = (pr["fp"], pr["mpg"]) if pr else (np.nan, np.nan)
    return out
steps = ([("3 component model", dict(BASE_NEEDS=(20, 1), CRED_K=0, USE_TEAM=False)),
          ("4 + healthy-season base", dict(BASE_NEEDS=(50, 20, 1), CRED_K=0, USE_TEAM=False)),
          ("5 + short-history pull", dict(BASE_NEEDS=(50, 20, 1), CRED_K=15, USE_TEAM=False)),
          ("6 + team quality / moved", dict(BASE_NEEDS=(50, 20, 1), CRED_K=15, USE_TEAM=True))]
         if late == "0" else [("7 + late-jump rule", dict(BASE_NEEDS=(50, 20, 1), CRED_K=15, USE_TEAM=True))])
res = {lab: run(**kw) for lab, kw in steps}
rows = []
for p in ids:
    r = dict(pid=p, name=A["2025-26"].PLAYER_NAME[p], act=acts[p]["fp"], act_mpg=acts[p]["mpg"])
    for lab, o in res.items():
        r[lab], r[lab + " mpg"] = o[p]
    rows.append(r)
pd.DataFrame(rows).to_csv(S + f"ladder_{late}.csv", index=False)
print("done", late)
