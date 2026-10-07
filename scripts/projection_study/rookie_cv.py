"""Rookie model variants, chosen by leave-one-class-out on the '22–'25 classes only ('26 shown as check)."""
import contextlib, io, runpy, numpy as np, pandas as pd
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
with contextlib.redirect_stdout(io.StringIO()):
    RK = runpy.run_path(S + "rookies.py", run_name="lib")
allr = RK["allr"]
allr = allr[allr.gp >= 10].copy()
allr["top3"] = (allr.pick <= 3).astype(float)
allr["top5"] = (allr.pick <= 5).astype(float)
allr["big"] = (allr.height >= 82).astype(float)
allr["bigxlate"] = allr.big * (allr.pick > 5)
VARS = {"current: ln(pick), height, weight, team diff": ["lpick", "height", "weight", "tdiff"],
        "+ top-3 pick": ["lpick", "height", "weight", "tdiff", "top3"],
        "+ top-5 pick": ["lpick", "height", "weight", "tdiff", "top5"],
        "+ top-3, no height/weight": ["lpick", "tdiff", "top3"],
        "+ top-3, 7-footer (6'10\"+) outside the top 5": ["lpick", "height", "weight", "tdiff", "top3", "bigxlate"],
        "ln(pick), team diff, top-3, 6'10\"+ outside top 5": ["lpick", "tdiff", "top3", "bigxlate"]}
def X(d, c): return np.column_stack([np.ones(len(d))] + [d[k].to_numpy(float) for k in c])
tr = allr[allr.season < "2025-26"]; va = allr[allr.season == "2025-26"]
for lab, c in VARS.items():
    h = n = 0
    for s in sorted(tr.season.unique()):
        a, b = tr[tr.season != s], tr[tr.season == s]
        w = np.sqrt(a.gp.to_numpy(float))
        beta = np.linalg.lstsq(X(a, c) * w[:, None], a.fp.to_numpy() * w, rcond=None)[0]
        p = X(b, c) @ beta; h += int((abs(p - b.fp) <= 3).sum()); n += len(b)
    w = np.sqrt(tr.gp.to_numpy(float))
    beta = np.linalg.lstsq(X(tr, c) * w[:, None], tr.fp.to_numpy() * w, rcond=None)[0]
    pv = X(va, c) @ beta
    names = {nm: round(float(p), 1) for nm, p in zip(va["name"], pv) if nm in ("Cooper Flagg", "VJ Edgecombe", "Kon Knueppel", "Khaman Maluach", "Hansen Yang", "Dylan Harper")}
    print(f"{lab:<50} '22–'25 held-out classes within 3 FP: {h}/{n}   '26 check {int((abs(pv - va.fp) <= 3).sum())}/{len(va)}   {names}")
