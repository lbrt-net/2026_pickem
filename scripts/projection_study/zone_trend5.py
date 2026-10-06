"""5-season shot-share trend ('21–'25 → '26), 60/40 player split (T tunes, V scores), 20 random splits.
FG%: '23–'25 attempt-weighted, k=25 toward league zone %, no pull at/above a zone-attempt floor.

Share model per player: weighted linear fit of each zone's share on season (t = -4..0), weights = FGA * r^(t+4)
(seasons under 100 FGA get weight 0). Projection = level at weighted-mean t + lam * slope * (1 - tbar).
Eligible: 100+ FGA in '25 and in at least 3 of the 5 input seasons; scored where '26 has 200+ FGA.
"""
import itertools
import runpy

import numpy as np

ns = runpy.run_path("/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/zone_projection.py",
                    run_name="lib")
W, ZONES, VAL, SIX = ns["W"], ns["ZONES"], ns["VAL"], ns["SIX"]
IN5 = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]
OUT = "2025-26"

# load '21 too (zone_projection only loaded '22–'26)
import pandas as pd  # noqa: E402
W = pd.concat([ns["load"]("2020-21").pivot_table(index=["pid", "season"], columns="zone", values=["fgm", "fga"], fill_value=0), W])


def arr(seasons, pids):
    fga, fgm = [], []
    for s in seasons:
        x = W.xs(s, level="season").reindex(pids).fillna(0)
        fga.append(x["fga"][ZONES].to_numpy(float))
        fgm.append(x["fgm"][ZONES].to_numpy(float))
    return np.stack(fga, 1), np.stack(fgm, 1)  # [p, s, z]


cand = sorted(set(W.index.get_level_values(0)))
fga5, fgm5 = arr(IN5, cand)
tot5 = fga5.sum(2)
elig = (tot5[:, -1] >= 100) & ((tot5 >= 100).sum(1) >= 3)
fga26, fgm26 = arr([OUT], cand)
fga26, fgm26 = fga26[:, 0], fgm26[:, 0]
scored = elig & (fga26.sum(1) >= 200)
idx = np.where(scored)[0]
pids = [cand[i] for i in idx]
fga5, fgm5, tot5, fga26, fgm26 = fga5[idx], fgm5[idx], tot5[idx], fga26[idx], fgm26[idx]
t = np.arange(-4, 1, dtype=float)
share5 = np.where(tot5[:, :, None] > 0, fga5 / np.where(tot5 > 0, tot5, 1)[:, :, None], 0)
act_share = fga26 / fga26.sum(1, keepdims=True)


def proj_share(r, lam, n_seasons=5):
    tt, sh, tot = t[-n_seasons:], share5[:, -n_seasons:], tot5[:, -n_seasons:]
    w = np.where(tot >= 100, tot, 0) * r ** (tt + 4)
    wn = w / w.sum(1, keepdims=True)
    tbar = (wn * tt).sum(1)
    lvl = (wn[:, :, None] * sh).sum(1)
    dt = tt[None] - tbar[:, None]
    var = (wn * dt ** 2).sum(1)
    slope = (wn[:, :, None] * dt[:, :, None] * (sh - lvl[:, None])).sum(1) / np.where(var > 0, var, 1)[:, None]
    p = np.clip(lvl + lam * slope * (1 - tbar)[:, None], 0, None)
    return p / p.sum(1, keepdims=True)


def share_err(p, rows):
    tot = fga26.sum(1)[rows]
    return (np.abs(p[rows] - act_share[rows]).sum(1) / 2 * tot).sum() / tot.sum()


GRID = list(itertools.product([1, 2, 3, 5, 8, 16, 1000], [0, 0.25, 0.5, 0.75, 1, 1.5, 2]))
P = {g: proj_share(*g) for g in GRID}
P3 = {g: proj_share(*g, n_seasons=3) for g in GRID}
rng = np.random.default_rng(26)
res = []
for _ in range(20):
    perm = rng.permutation(len(pids))
    T, V = perm[: int(0.6 * len(pids))], perm[int(0.6 * len(pids)):]
    g5 = min(GRID, key=lambda g: share_err(P[g], T))
    g3 = min(GRID, key=lambda g: share_err(P3[g], T))
    res.append(dict(g5=g5, g3=g3, v5=share_err(P[g5], V), v3=share_err(P3[g3], V),
                    v_last=share_err(share5[:, -1], V), v_flat5=share_err(P[(1, 0)], V)))
print(f"{len(pids)} players scored (100+ FGA in '25 and 3+ of '21–'25; 200+ FGA in '26). 20 random 60/40 splits.\n")
print("Shot share — % of '26 shots in the wrong zone, on the held-out 40% (mean over splits, [min–max]):")
for key, label in [("v_last", "same as '25"), ("v_flat5", "5-yr weighted avg, no trend"),
                   ("v3", "3-yr + tuned trend"), ("v5", "5-yr + tuned trend")]:
    v = np.array([r[key] for r in res]) * 100
    print(f"  {label:<30} {v.mean():5.2f}%   [{v.min():.2f}–{v.max():.2f}]")
from collections import Counter  # noqa: E402
print("\n  tuned (recency r, trend lam) picked across splits, 5-yr:", Counter(r["g5"] for r in res).most_common(4))
print("  tuned (recency r, trend lam) picked across splits, 3-yr:", Counter(r["g3"] for r in res).most_common(4))
best5 = Counter(r["g5"] for r in res).most_common(1)[0][0]

# FG%: '23–'25 pooled, k=25, no pull at/above floor
fga3, fgm3 = fga5[:, -3:].sum(1), fgm5[:, -3:].sum(1)
mu = fgm3.sum(0) / fga3.sum(0)
print("\nFG% ('23–'25 attempt-weighted, k=25) — attempt-weighted mean abs error on '26, pp, all scored players:")
print(f"  {'no-pull floor':<16}" + "  ".join(f"{z:>7}" for z in ZONES))
for floor in [None, 50, 100, 200]:
    k = np.where(fga3 >= floor, 0.0, 25.0) if floor else np.full_like(fga3, 25.0)
    pp = (fgm3 + k * mu) / (fga3 + k)
    errs = []
    for j in range(5):
        n = fga26[:, j]
        h = n > 0
        errs.append((np.abs(pp[h, j] - fgm26[h, j] / n[h]) * n[h]).sum() / n[h].sum() * 100)
    print(f"  {('k=25 everywhere' if floor is None else f'floor {floor} att'):<16}" + "  ".join(f"{e:7.2f}" for e in errs))

ps = P[best5]
print(f"\nThe six — '26 shot share, projected (5-yr, r={best5[0]}, lam={best5[1]}) → actual:")
for pid, n in SIX.items():
    if pid not in pids:
        print(f"  {n}: not scored")
        continue
    i = pids.index(pid)
    print(f"  {n:<9}" + "  ".join(f"{z} {100 * ps[i, j]:4.1f}→{100 * act_share[i, j]:4.1f}" for j, z in enumerate(ZONES)))
