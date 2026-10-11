"""Mock: 2025-26, advice going into Week 6. 12 balanced teams (6 players + 1 NBA team each, frozen at the draft).
Two levels: BETTER PLAYER (rest of season: level × availability vs a rostered player's level — an injured star keeps
his level, so he's never a drop) and BETTER THIS WEEK (week projection = expected best game with next week's games)."""
import sys
from math import comb

import numpy as np
import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__file__))
import fa_study as f  # noqa: E402

S, WK = "2025-26", 6
W_ = WK - 2                      # end of the week before (week 1 = wk 0)
C = [0, 0, 0.564, 0.846, 1.029, 1.163]


def week_proj(m, sd, n, p):
    n = int(n)
    return sum(comb(n, k) * p ** k * (1 - p) ** (n - k) * (m + sd * C[min(k, 5)]) for k in range(1, n + 1))


pw, _ = f.player_weeks()
x = pw[pw.season == S]
games = pd.read_parquet(f.W + "disp_games.parquet")
games = games[(games.season == S) & (games.MIN > 0)]
F = f.features(pw, S, W_)
b = x[x.wk <= W_ - 4].groupby("PLAYER_ID")[["fp_sum", "games", "mins"]].sum()
pre = (b.fp_sum / b.games).reindex(F.index)
premin = (b.mins / b.games).reindex(F.index)
min4 = (F.mins - b.mins.reindex(F.index).fillna(0)) / (F.g - b.games.reindex(F.index).fillna(0)).replace(0, np.nan)
w = np.where(min4 - premin >= 4, 0.6, 0.5)
F["level"] = pd.Series(np.where(F.pg4.notna() & pre.notna(), w * F.pg4 + (1 - w) * pre, F.season_pg), index=F.index).fillna(F.season_pg).fillna(0)
prev = pw[pw.season == "2024-25"].groupby("PLAYER_ID").score.mean()
own_sd = games[games.date <= games.date.max()].groupby("PLAYER_ID").fp.std()
n_g = games.groupby("PLAYER_ID").size()
F["sd"] = ((own_sd.reindex(F.index).fillna(0) * n_g.reindex(F.index).fillna(0) + 0.35 * F.level * 12) / (n_g.reindex(F.index).fillna(0) + 12))
F["week"] = [week_proj(m, s, n, max(p, 0.05)) for m, s, n, p in zip(F.level, F.sd, F.next_games, F.avail)]
F["value"] = F.level * F.avail.clip(lower=0.6)       # rest-of-season: a short absence doesn't sink a player

# draft: the top 72 by last season, balanced — each pick goes to the team with the lowest total so far (6 each)
order = f.drafted(pw, S)
val = prev.reindex(order)
teams = [{"players": [], "total": 0.0} for _ in range(12)]
for pid in order:
    t = min((t for t in teams if len(t["players"]) < 6), key=lambda t: t["total"])
    t["players"].append(pid); t["total"] += val[pid]
names = pw.groupby("PLAYER_ID").name.last()
owner = {p: i for i, t in enumerate(teams) for p in t["players"]}
print(f"Mock 2025-26, going into Week {WK}. 12 teams, drafted by last season, balanced:")
print("  team totals (last season's avg weekly score, 6 players):", ", ".join(f"{t['total']:.0f}" for t in teams))

fa = F[~F.index.isin(owner) & (F.g >= 3)]
ros = F.reindex(list(owner)).assign(team=lambda d: d.index.map(owner))

# Level 1 — better player: free agent's value beats a rostered player's level (an injured star keeps his level)
L1, used = [], set()
for pid, r in fa.sort_values("value", ascending=False).iterrows():
    cand = ros[~ros.index.isin(used)].sort_values("level")
    if cand.empty or r.value <= cand.level.iloc[0]:
        break
    d = cand.index[0]; used.add(d)
    L1.append((pid, d))
# Level 2 — better this week: free agent's week projection beats a rostered player's (not already moved in level 1)
taken_fa = {a for a, _ in L1}
L2 = []
for pid, r in fa[~fa.index.isin(taken_fa)].sort_values("week", ascending=False).iterrows():
    cand = ros[~ros.index.isin(used)].sort_values("week")
    if cand.empty or r.week <= cand.week.iloc[0] + 2:      # worth a move only if it's 2+ points better this week
        break
    d = cand.index[0]; used.add(d)
    L2.append((pid, d))


def show(title, pairs, key):
    print(f"\n{title}: {len(pairs)}")
    print(f"  {'add':24s}{'proj':>6s}{'games':>6s}{'wk6':>6s}    {'for (team)':28s}{'proj':>6s}{'games':>6s}{'wk6':>6s}")
    good = 0
    for a, d in pairs:
        A, D = F.loc[a], F.loc[d]
        ok = A.target > D.target; good += ok
        print(f"  {names[a][:23]:24s}{A[key]:6.1f}{int(A.next_games):6d}{A.target:6.1f}    {names[d][:21] + f' (T{owner[d] + 1})':28s}"
              f"{D[key if key == 'week' else 'level']:6.1f}{int(D.next_games):6d}{D.target:6.1f}  {'✓' if ok else '✗'}")
    if pairs:
        gain = sum(F.loc[a].target - F.loc[d].target for a, d in pairs)
        print(f"  → {good} of {len(pairs)} paid off in week {WK}; net {gain:+.1f} points")


show("BETTER PLAYER (add / drop for the rest of the season)", L1, "value")
show("BETTER THIS WEEK (stream for week 6, +2 projected or more)", L2, "week")
per = pd.Series([owner[d] + 1 for _, d in L1 + L2]).value_counts().sort_index()
print("\nSuggestions per team:", ", ".join(f"T{k} {v}" for k, v in per.items()), f"· teams with none: {12 - len(per)}")

rest = x[x.wk >= W_ + 1].groupby(["PLAYER_ID", "wk"]).score.max().groupby("PLAYER_ID").sum() / (x.wk.max() - W_)
ok = sum(rest.get(a, 0) > rest.get(d, 0) for a, d in L1)
gain = sum(rest.get(a, 0) - rest.get(d, 0) for a, d in L1)
print(f"\nBETTER PLAYER over the rest of the season (avg weekly score from week {WK} on): {ok} of {len(L1)} adds outscored the drop; "
      f"net {gain:+.1f} a week across the league")
