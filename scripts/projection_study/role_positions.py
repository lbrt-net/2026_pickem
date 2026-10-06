"""Role-based positions tuned for slot balance ('26 data).

Role score (guard-like → big-like) = mean of z-scores: +height, +weight, +REB%, +BLK/75, −AST%, −3PA share of FGA.
G = lowest scores, C = highest, F = between. Cutoffs (percentiles of the score among draftable players) are chosen
so avg-starter-minus-replacement is as equal as possible across G, F, C for N teams (TUNE_N), FLX/TEAM reported too.
Values = '26 average weekly best game (from slot_balance.py).
"""
import contextlib
import io
import json
import runpy

import numpy as np
import pandas as pd

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
TUNE_N = 8
with contextlib.redirect_stdout(io.StringIO()):
    SB = runpy.run_path(S + "slot_balance.py", run_name="lib")
pv, tm, b = SB["pv"].copy(), SB["tm"], SB["b"]


def tab(kind, s):
    rs = json.load(open(f"{R}{kind}/{s}.json"))["resultSets"][0]
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"]).set_index("PLAYER_ID")


bio, adv = tab("bios", "2025-26"), tab("player_advanced", "2025-26")
tot = b.groupby("player_id")[["blk", "fg3a", "fga"]].sum()
pv["height"] = bio.PLAYER_HEIGHT_INCHES.reindex(pv.index).astype(float)
pv["weight"] = pd.to_numeric(bio.PLAYER_WEIGHT.reindex(pv.index), errors="coerce")
pv["reb"] = adv.REB_PCT.reindex(pv.index)
pv["ast"] = adv.AST_PCT.reindex(pv.index)
pv["blk75"] = 75 * tot.blk.reindex(pv.index) / adv.POSS.reindex(pv.index)
pv["three"] = tot.fg3a.reindex(pv.index) / tot.fga.reindex(pv.index).replace(0, np.nan)
feat = {"height": +1, "weight": +1, "reb": +1, "blk75": +1, "ast": -1, "three": -1}
z = pd.DataFrame({f: sgn * (pv[f] - pv[f].mean()) / pv[f].std() for f, sgn in feat.items()})
pv["role"] = z.mean(axis=1, skipna=True)


def table(pos, N):
    taken, out = set(), {}
    for p in ["G", "F", "C"]:
        s = pv[pos == p].sort_values("val", ascending=False)
        out[p] = (s.val.head(N), s.val.iloc[N] if len(s) > N else np.nan)
        taken |= set(s.head(N).index)
    rest = pv.drop(index=list(taken)).sort_values("val", ascending=False)
    out["FLX"] = (rest.val.head(N), rest.val.iloc[N])
    out["TEAM"] = (tm.head(N), tm.iloc[N])
    return out


def vorp(pos, N):
    t = table(pos, N)
    return {k: v[0].mean() - v[1] for k, v in t.items()}


def assign(q1, q2):
    lo, hi = pv.role.quantile(q1), pv.role.quantile(q2)
    return pd.Series(np.where(pv.role <= lo, "G", np.where(pv.role > hi, "C", "F")), index=pv.index)


best = None
for q1 in np.arange(0.20, 0.61, 0.01):
    for q2 in np.arange(q1 + 0.10, 0.96, 0.01):
        v = vorp(assign(q1, q2), TUNE_N)
        spread = max(v["G"], v["F"], v["C"]) - min(v["G"], v["F"], v["C"])
        if best is None or spread < best[0]:
            best = (spread, q1, q2)
_, q1, q2 = best
pos = assign(q1, q2)
pv["new"] = pos
print(f"Tuned for {TUNE_N} teams: G = lowest {q1:.0%} of role score, C = top {1 - q2:.0%}, F = middle {q2 - q1:.0%}")
print(f"  counts (draftable '26 players): {pos.value_counts().to_dict()}   (box-score labels: {pv.pos.value_counts().to_dict()})\n")
for N in [4, 8, 10, 12]:
    old, new = vorp(pv.pos.replace('—', 'X'), N), vorp(pos, N)
    print(f"  N={N:<3} avg starter − replacement   " + "   ".join(f"{k} {old[k]:4.1f}→{new[k]:4.1f}" for k in ["G", "F", "C", "FLX", "TEAM"]))

print("\nTop 12 at each new position ('26 weekly value; old box label in brackets):")
for p in ["G", "F", "C"]:
    s = pv[pos == p].sort_values("val", ascending=False).head(12)
    print(f"  {p}: " + ", ".join(f"{n.split()[-1] if not n.split()[-1] in ('Jr.', 'III', 'II') else n.split()[-2]} {v:.1f}[{o}]"
                               for n, v, o in zip(s.name, s.val, s.pos)))
moved = pv[(pv.pos != pos) & (pv.pos != "—")].sort_values("val", ascending=False)
print(f"\nPlayers whose position changed (top 25 by value, of {len(moved)}):")
for x in moved.head(25).itertuples():
    print(f"  {x.name:<26} {x.pos} → {x.new}   {x.val:4.1f}   ht {x.height:.0f}  wt {x.weight:.0f}  REB% {100 * x.reb:4.1f}  AST% {100 * x.ast:4.1f}  3PA share {100 * x.three:3.0f}%")
for n in ["Nikola Jokić", "Giannis Antetokounmpo", "LeBron James", "Luka Dončić", "Kevin Durant", "Victor Wembanyama"]:
    r = pv[pv.name == n]
    if len(r):
        print(f"  check: {n} → {r.new.iloc[0]} (role score {r.role.iloc[0]:+.2f})")
pv[["name", "pos", "new", "role", "val", "height", "weight", "reb", "ast", "blk75", "three"]].sort_values("val", ascending=False).to_csv(
    R + "role_positions_2025_26.csv")
