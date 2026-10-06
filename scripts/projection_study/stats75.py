"""(1) Usage applied to the points pipeline: FGA/75 and FTA/75 x (resplit usage / prior usage)^alpha.
(2) AST, STL, BLK, TOV per 75: '23–'25 possession-weighted, recency r tuned; usage scaling tested on AST/TOV.
Validation '25→'26 on the 210 zone-study players; usage resplit uses '26 opening rosters (first-game team).
"""
import contextlib
import io
import runpy

import numpy as np
import pandas as pd

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
with contextlib.redirect_stdout(io.StringIO()):
    P = runpy.run_path(S + "points.py", run_name="lib")
    U = runpy.run_path(S + "usage_resplit.py", run_name="lib")
pids, act_ppg, IN = P["pids"], P["act_ppg"], P["IN"]
A, B, col = P["A"], P["B"], P["col"]

# usage resplit '25 → '26 rosters
R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
op = pd.read_csv(f"{R}rosters/opening_2025_26_from_box.csv").set_index("player_id")
proj_u = U["project"](A["2024-25"], op.team26.groupby(op.team26).apply(lambda s: set(s.index)).to_dict())
u25 = np.array([A["2024-25"].USG_PCT.get(p, np.nan) for p in pids])
ratio = np.array([proj_u.get(p, np.nan) for p in pids]) / u25
ratio = np.where(np.isfinite(ratio), ratio, 1.0)
moved = np.array([op.team26.get(p) != op.team25.get(p) for p in pids])

poss_g, pps, ftp, fga75, ft75 = P["poss_g"], P["pps"], P["ftp"], P["fga75"], P["ft75"]
print("(1) POINTS/G with usage applied (210 players, '26):")
print(f"   {'alpha':<28}{'all':>7}{'stayed':>9}{'moved':>8}{'bias':>8}")
for lab, al_stay, al_move in [("none (current)", 0, 0), ("0.5 everyone", .5, .5), ("1.0 everyone", 1, 1),
                              ("1.0 stayers, none movers", 1, 0), ("0.5 stayers, none movers", .5, 0)]:
    al = np.where(moved, al_move, al_stay)
    sc = ratio ** al
    pts = poss_g / 75 * (fga75 * sc * pps + ft75 * sc * ftp)
    e = pts - act_ppg
    print(f"   {lab:<28}{np.abs(e).mean():7.2f}{np.abs(e[~moved]).mean():9.2f}{np.abs(e[moved]).mean():8.2f}{e.mean():+8.2f}")
print(f"   ({(~moved).sum()} stayed, {moved.sum()} moved)")

# (2) other counting stats per 75
import sys  # noqa: E402
sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem/scripts")
from load_historical_boxscores import minutes  # noqa: E402
box = {}
for s, f in P["BOX"].items():
    d = pd.read_parquet(f)
    d = d[d.game_id.astype(str).str[2] == "2"].copy()
    d["player_id"] = d.player_id.astype(int)
    d["m"] = d["minutes"].map(minutes)
    box[s] = d[d.m > 0].groupby("player_id")[["ast", "stl", "blk", "tov"]].sum()
poss = np.stack([col(s, "POSS", A) for s in IN], 1)
a_poss, a_gp = col("2025-26", "POSS", A), col("2025-26", "gp", B)
mae = lambda p, a, rows: np.abs(p[rows] - a[rows]).mean()  # noqa: E731
rng = np.random.default_rng(26)
splits = [rng.permutation(len(pids)) for _ in range(20)]
print("\n(2) per 75 possessions ('26 error, held-out 40%, 20 splits) and per game:")
print(f"   {'stat':<5}{'typical/75':>11}{'r':>5}{'same as 25':>12}{'model':>8}{'+usage':>8}{'per-game err':>14}")
out = {}
for st in ["ast", "stl", "blk", "tov"]:
    x = np.stack([np.array([box[s][st].get(p, 0) for p in pids], float) for s in IN], 1)
    act75 = 75 * np.array([box["2025-26"][st].get(p, 0) for p in pids]) / a_poss

    def rate(r):
        w = r ** np.arange(3.0)
        return 75 * (x * w).sum(1) / (poss * w).sum(1)

    errs, base, use, picks = [], [], [], []
    for perm in splits:
        T, V = perm[:126], perm[126:]
        r = min([1, 2, 3, 5, 8, 1000], key=lambda q: mae(rate(q), act75, T))
        picks.append(r)
        errs.append(mae(rate(r), act75, V))
        base.append(mae(rate(1000), act75, V))
        use.append(mae(rate(r) * np.where(moved, 1, ratio), act75, V))
    r = max(set(picks), key=picks.count)
    proj75 = rate(r) * (np.where(moved, 1, ratio) if st in ("ast", "tov") and np.mean(use) < np.mean(errs) else 1)
    out[st] = proj75
    pg_err = np.abs(poss_g / 75 * proj75 - act75 * a_poss / 75 / a_gp).mean()
    print(f"   {st.upper():<5}{np.median(act75):11.2f}{r:>5}{np.mean(base):12.3f}{np.mean(errs):8.3f}{np.mean(use):8.3f}{pg_err:14.2f}")
