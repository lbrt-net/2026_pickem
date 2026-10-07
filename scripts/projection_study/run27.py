"""Full 2026-27 per-game projection for every 2026-27 roster player (veterans: pipeline; rookies: rookie model).
Adds position (role-based single position + overrides; rookies/unknown: roster POSITION's first letter), a middle-50%
range from the '26 validation residuals, and flags. Saves nba-pipeline/data/raw/projections_2026_27.csv."""
import contextlib, io, runpy
import numpy as np, pandas as pd
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
with contextlib.redirect_stdout(io.StringIO()):
    P = runpy.run_path(S + "pipeline.py", run_name="lib")
r27 = pd.read_csv(R + "rosters/2026-27.csv")
rook = pd.read_csv(R + "rookie_projections_2026_27.csv", index_col=0)
pos = pd.read_csv(R + "role_positions_single_2025_26.csv", index_col=0)
POS = pos.final.to_dict()
VET_RANGE = [(12, (-2.0, 3.7)), (18, (-3.6, 1.8)), (24, (-3.0, 1.4)), (99, (-2.0, 2.3))]   # '26 residuals by projected FP/G
ROOK_RANGE = [(5, (1.5, 7.1)), (14, (-2.6, 2.4)), (30, (-2.7, 0.0)), (99, (-3.1, 4.2))]    # '26 rookie residuals by pick
injured26 = set(pd.read_csv(R + "top50_superset_23_26.csv").pipe(lambda t: t[t["rk'26"].isna()]).name)
late26 = set(P["LATE_JUMPS"].get("2025-26", {}))
rows = []
for x in r27.itertuples():
    p = int(x.PLAYER_ID)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            g = P["project"](p, "2026-27")
    except Exception:
        g = None
    rp = str(x.POSITION or "F").split("-")[0][:1] or "F"
    if g:
        lo, hi = next(r for t, r in VET_RANGE if g["fp"] < t)
        flags = [f for f, on in [("EPM≤−2.5", g["epm_flag"] is not None), ("injured '26", x.PLAYER in injured26),
                                 ("late jump '26", p in late26), ("new team", g["stayed"] is False)] if on]
        rows.append(dict(pid=p, name=x.PLAYER, team=x.TEAM, pos=POS.get(p, rp), kind="vet", age=round(g["age"]), fp=g["fp"],
                         lo=g["fp"] + lo, hi=g["fp"] + hi, mpg=g["mpg"], pts=g["pts"], reb=g["oreb"] + g["dreb"], ast=g["ast"],
                         flags=", ".join(flags)))
    elif p in rook.index:
        r = rook.loc[p]
        lo, hi = next(rr for t, rr in ROOK_RANGE if r.pick <= t)
        rows.append(dict(pid=p, name=x.PLAYER, team=x.TEAM, pos=rp, kind="rookie", age=np.nan, fp=r.fp, lo=r.fp + lo, hi=r.fp + hi,
                         mpg=r.mpg, pts=np.nan, reb=np.nan, ast=np.nan, flags=f"rookie #{int(r.pick)}"))
    else:
        rows.append(dict(pid=p, name=x.PLAYER, team=x.TEAM, pos=rp, kind="none", fp=np.nan, flags="no projection"))
d = pd.DataFrame(rows).sort_values("fp", ascending=False)
d.to_csv(R + "projections_2026_27.csv", index=False)
print(f"2026-27: {len(d)} roster players → vet {(d.kind == 'vet').sum()}, rookie {(d.kind == 'rookie').sum()}, none {(d.kind == 'none').sum()}")
print(f"positions among top 60: {d.head(60).pos.value_counts().to_dict()}\n")
print(f"{'rk':>3} {'player':<26}{'tm':<4}{'pos':<4}{'age':>4}{'FP/G':>6}  {'middle 50%':<12}{'MPG':>5}{'PTS':>6}{'REB':>5}{'AST':>5}  flags")
for i, x in enumerate(d.head(70).itertuples(), 1):
    age = "" if pd.isna(x.age) else f"{x.age:.0f}"
    pts = "" if pd.isna(x.pts) else f"{x.pts:5.1f}"
    reb = "" if pd.isna(x.reb) else f"{x.reb:4.1f}"
    ast = "" if pd.isna(x.ast) else f"{x.ast:4.1f}"
    print(f"{i:>3} {x.name:<26}{x.team:<4}{x.pos:<4}{age:>4}{x.fp:6.1f}  {x.lo:4.1f}–{x.hi:<6.1f}{x.mpg:5.1f}{pts:>6}{reb:>5}{ast:>5}  {x.flags}")
top50 = pd.read_csv(R + "top50_superset_23_26.csv")
miss = top50[~top50.name.isin(d.head(80).name)]
print(f"\nTop-50 list players NOT in the projected top 80 ({len(miss)}):")
for n in miss.name:
    r = d[d.name == n]
    print(f"  {n:<26} " + (f"projected {r.fp.iloc[0]:5.1f} (rank {d.index.get_loc(r.index[0]) + 1 if False else list(d.name).index(n) + 1})  {r["flags"].iloc[0]}" if len(r) and not pd.isna(r.fp.iloc[0]) else "not on a 2026-27 roster / no projection"))
