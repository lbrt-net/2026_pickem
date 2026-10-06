import contextlib, io, runpy, numpy as np, pandas as pd
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
out = {}
for lab, f in [("without late-jump rule", "pipeline_nolate.py"), ("with late-jump rule", "pipeline.py")]:
    with contextlib.redirect_stdout(io.StringIO()):
        P = runpy.run_path(S + f, run_name="lib")
    A, actual, project = P["A"], P["actual"], P["project"]
    ids = [p for p in A["2025-26"].index if (a := actual(p, "2025-26")) and a["gp"] >= 20]
    rows = []
    for p in ids:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                g = project(p, "2025-26")
        except Exception:
            g = None
        if g:
            a = actual(p, "2025-26")
            rows.append((p, A["2025-26"].PLAYER_NAME[p], g["fp"], a["fp"], g["mpg"], a["mpg"]))
    d = pd.DataFrame(rows, columns=["pid", "name", "proj", "act", "pmpg", "ampg"]).set_index("pid")
    out[lab] = (d, P["LATE_JUMPS"])
    e = d.proj - d.act
    print(f"{lab:<24} n={len(d)}  FP/G error {e.abs().mean():.2f}  MPG error {(d.pmpg - d.ampg).abs().mean():.2f}  ±3 {(e.abs() <= 3).mean():.0%}")
d0, d1 = out["without late-jump rule"][0], out["with late-jump rule"][0]
J = out["with late-jump rule"][1]
names = {}
for s in A: names.update(A[s].PLAYER_NAME.to_dict())
flag25 = set(J.get("2024-25", {})) | set(J.get("2023-24", {})) | set(J.get("2022-23", {}))
hit = [p for p in d1.index if p in flag25]
print(f"\n'26 players with a flagged season in '23–'25: {len(hit)}")
e0, e1 = (d0.loc[hit].proj - d0.loc[hit].act).abs().mean(), (d1.loc[hit].proj - d1.loc[hit].act).abs().mean()
print(f"  their FP/G error: without {e0:.2f} → with {e1:.2f}")
for p in hit:
    print(f"  {names[p]:<24} proj {d0.proj[p]:5.1f} → {d1.proj[p]:5.1f}   actual {d1.act[p]:5.1f}")
print("\nFlagged in '25 (feeds '26) and '26 (feeds '27):")
for s in ["2024-25", "2025-26"]:
    print(f"  {s}: " + "; ".join(f"{names.get(p, p)} {v[0]}→{v[1]} ({v[2]}/{v[3]} GP)" for p, v in sorted(J[s].items(), key=lambda x: -x[1][1])))
for n in ["Drew Timme", "Jonathan Mogbo", "Jeremy Sochan", "Tyus Jones", "Anthony Edwards", "Nikola Jokić"]:
    p = next((q for q in d1.index if names.get(q) == n), None)
    if p:
        print(f"  {n:<20} {d0.proj[p]:5.1f} → {d1.proj[p]:5.1f}   actual {d1.act[p]:5.1f}")
