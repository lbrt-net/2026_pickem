"""Two-axis role positions with dual eligibility ('26 data).

big score      = mean z of height, weight, REB%, BLK/75           → C = top QC of draftable players
creation score = mean z of AST%, 3PA share of FGA, −height          → among non-C, G = top QG
F = the rest. Dual: within BAND (z units) of a cutoff on its axis → eligible for both sides (G/F or F/C).
Balance: greedy fill by weekly value — each player (best first) takes an open G/F/C start he's eligible for
(dual players take whichever of their open slots has the weaker next-best eligible player), else FLX.
Replacement = best unused eligible player per slot.  Tuned only lightly (grid on QC, QG; BAND fixed).
"""
import contextlib
import io
import runpy

import numpy as np
import pandas as pd

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
BAND, TUNE_N = 0.0, 8
with contextlib.redirect_stdout(io.StringIO()):
    RP = runpy.run_path(S + "role_positions.py", run_name="lib")
pv, tm = RP["pv"].copy(), RP["tm"]
zs = lambda f: (pv[f] - pv[f].mean()) / pv[f].std()  # noqa: E731
pv["big"] = pd.concat([zs("height"), zs("reb"), zs("reb"), zs("blk75"), zs("blk75")], axis=1).mean(axis=1, skipna=True)
pv["create"] = pd.concat([zs("ast"), zs("three"), -zs("height")], axis=1).mean(axis=1, skipna=True)


def assign(qc, qg):
    cc = pv.big.quantile(1 - qc)
    is_c = pv.big >= cc
    gc = pv.create[~is_c].quantile(1 - qg)
    elig = {}
    for p, r in pv.iterrows():
        e = set()
        if r.big >= cc - BAND:
            e.add("C")
        if r.big < cc + BAND:  # not clearly a center → guard/forward side
            if r.create >= gc - BAND:
                e.add("G")
            if r.create < gc + BAND:
                e.add("F")
        elig[p] = e or {"F"}
    return elig


def fill(elig, N):
    open_ = {"G": N, "F": N, "C": N}
    start = {"G": [], "F": [], "C": [], "FLX": []}
    used = set()
    order = pv.sort_values("val", ascending=False).index
    for p in order:
        opts = [s for s in ("G", "F", "C") if s in elig[p] and open_[s] > 0]
        if opts:
            # dual: take the slot whose best remaining eligible alternative is weakest
            def nxt(s):
                rest = [q for q in order if q not in used and q != p and s in elig[q]]
                return pv.val[rest[0]] if rest else -1
            s = min(opts, key=nxt) if len(opts) > 1 else opts[0]
            start[s].append(pv.val[p])
            open_[s] -= 1
            used.add(p)
        elif len(start["FLX"]) < N and sum(open_.values()) == 0:
            start["FLX"].append(pv.val[p])
            used.add(p)
        if sum(open_.values()) == 0 and len(start["FLX"]) == N:
            break
    out = {}
    for s in ("G", "F", "C"):
        rest = [pv.val[q] for q in order if q not in used and s in elig[q]]
        out[s] = np.mean(start[s]) - (rest[0] if rest else np.nan)
    rest = [pv.val[q] for q in order if q not in used]
    out["FLX"] = np.mean(start["FLX"]) - rest[0]
    out["TEAM"] = tm.head(N).mean() - tm.iloc[N]
    return out


best = (0, 0.20, 0.40, None)
for qc in []:
    for qg in np.arange(0.30, 0.71, 0.05):
        e = assign(qc, qg)
        v = fill(e, TUNE_N)
        sp = max(v["G"], v["F"], v["C"]) - min(v["G"], v["F"], v["C"])
        if best is None or sp < best[0]:
            best = (sp, qc, qg, e)
_, qc, qg, _ = best
elig = assign(qc, qg)
lab = pd.Series({p: "/".join(s for s in ("G", "F", "C") if s in e) for p, e in elig.items()})
pv["new"] = lab
print(f"C = top {qc:.1%} by size/rebounding; G = top {qg:.0%} of the rest by creation; dual band ±{BAND} z")
print(f"  designations: {lab.value_counts().to_dict()}\n")
old = {p: {pv.pos[p]} if pv.pos[p] != "—" else set() for p in pv.index}
for N in [4, 8, 10, 12]:
    o, n = fill(old, N), fill(elig, N)
    print(f"  N={N:<3} avg starter − replacement  " + "   ".join(f"{k} {o[k]:4.1f}→{n[k]:4.1f}" for k in ["G", "F", "C", "FLX", "TEAM"]))

print("\nChecks:")
for n in ["Shai Gilgeous-Alexander", "Luka Dončić", "Nikola Jokić", "Giannis Antetokounmpo", "LeBron James", "Anthony Edwards",
          "Jayson Tatum", "Kevin Durant", "Cade Cunningham", "Victor Wembanyama", "Stephen Curry", "Jalen Brunson",
          "Scottie Barnes", "Lauri Markkanen", "Bam Adebayo", "Karl-Anthony Towns", "Josh Giddey", "Evan Mobley"]:
    r = pv[pv.name == n]
    if len(r):
        print(f"  {n:<24} {r.pos.iloc[0]:<2} → {r.new.iloc[0]:<6} (big {r.big.iloc[0]:+.2f}, creation {r.create.iloc[0]:+.2f})")
print("\nTop 15 eligible at each slot ('26 weekly value):")
for s in ("G", "F", "C"):
    t = pv[pv.new.str.contains(s)].sort_values("val", ascending=False).head(15)
    print(f"  {s}: " + ", ".join(f"{n.split()[-1] if n.split()[-1] not in ('Jr.', 'III', 'II') else n.split()[-2]}[{d}] {v:.1f}"
                               for n, d, v in zip(t.name, t.new, t.val)))
pv[["name", "pos", "new", "big", "create", "val", "height", "weight", "reb", "ast", "blk75", "three"]].sort_values(
    "val", ascending=False).to_csv(R + "role_positions_single_2025_26.csv")
