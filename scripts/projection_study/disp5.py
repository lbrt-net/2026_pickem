"""Dispersion part 3: (A) actual per-player spread season by season ('23–'25) — is it a trait for established players?
(B) spread by scoring component: each component's best-of-3 vs its average, and which components make the weekly best game."""
import json
import numpy as np
import pandas as pd

R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
F = json.load(open(S + "disp_fit.json"))
a, b = np.exp(F["a"]), F["b"]
SEAS = ["2022-23", "2023-24", "2024-25"]
COMP = {"PTS": ("PTS", 1.0), "FG−": (None, -0.5), "BLKD": ("BLKA", -0.5), "3PM": ("FG3M", 0.5), "FT−": (None, -1.0), "OREB": ("OREB", 1.5),
        "DREB": ("DREB", 0.5), "AST": ("AST", 1.0), "STL": ("STL", 2.0), "BLK": ("BLK", 1.5), "TOV": ("TOV", -2.0)}


def J(kind, s):
    rs = json.load(open(f"{R}{kind}/{s}.json"))["resultSets"]
    rs = rs[0] if isinstance(rs, list) else rs
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"])


frames = []
for s in SEAS:
    g = J("game_logs", s)
    g = g[g.MIN > 0].copy()
    for k, (col, w) in COMP.items():
        if k == "FG−":
            g[k] = w * (g.FGA - g.FGM)
        elif k == "FT−":
            g[k] = w * (g.FTA - g.FTM)
        else:
            g[k] = w * g[col]
    g["FP"] = g[list(COMP)].sum(axis=1)
    g["season"] = s
    g["date"] = pd.to_datetime(g.GAME_DATE)
    g["week"] = (g.date - pd.to_timedelta(g.date.dt.weekday, unit="D")).dt.date
    frames.append(g[["season", "PLAYER_ID", "PLAYER_NAME", "week", "MIN", "FP"] + list(COMP)])
G = pd.concat(frames)
n = G.groupby(["season", "PLAYER_ID"]).FP.transform("size")
G = G[n >= 40]

# ---------- (A) actual spread by player, by season
ps = G.groupby(["season", "PLAYER_ID"]).agg(name=("PLAYER_NAME", "last"), n=("FP", "size"), mean=("FP", "mean"), sd=("FP", "std")).reset_index()
ps["ratio"] = ps.sd / (a * ps["mean"] ** b)
wide = ps.pivot_table(index="PLAYER_ID", columns="season", values="ratio")
mean_w = ps.pivot_table(index="PLAYER_ID", columns="season", values="mean")
n_w = ps.pivot_table(index="PLAYER_ID", columns="season", values="n")
names = ps.groupby("PLAYER_ID").name.last()
print("(A) Does a player's spread (vs what his average predicts) repeat? correlation season to season")
for lab, sel in [("all 40+ game player-seasons", lambda p: True),
                 ("20+ FP/G and 60+ games both seasons", lambda p: True)]:
    pass
for s0, s1 in [("2022-23", "2023-24"), ("2023-24", "2024-25")]:
    ok = wide[[s0, s1]].dropna()
    est = ok[(mean_w.loc[ok.index, s0] >= 20) & (mean_w.loc[ok.index, s1] >= 20) & (n_w.loc[ok.index, s0] >= 60) & (n_w.loc[ok.index, s1] >= 60)]
    print(f"  {s0[-2:]}→{s1[-2:]}: all r={ok[s0].corr(ok[s1]):.2f} (n={len(ok)});  20+ FP/G, 60+ GP both: r={est[s0].corr(est[s1]):.2f} (n={len(est)})")
three = wide.dropna()
three = three[(mean_w.loc[three.index].min(axis=1) >= 20) & (n_w.loc[three.index].min(axis=1) >= 50)]
three = three.assign(name=names.reindex(three.index), avg=three.mean(axis=1), lo=three.min(axis=1), hi=three.max(axis=1),
                     fp=mean_w.loc[three.index].mean(axis=1))
three = three.sort_values("avg")
consistent_hi = three[three.lo > 1.0]
consistent_lo = three[three.hi < 1.0]
print(f"  established (20+ FP/G, 50+ GP all 3 seasons): {len(three)}; above expected all 3 seasons: {len(consistent_hi)}; below all 3: {len(consistent_lo)}"
      f"  (if spread were pure luck you'd expect about {len(three) / 8:.0f} each)")
print("  always above:", [(r["name"], [round(r[s], 2) for s in SEAS]) for _, r in consistent_hi.sort_values("avg", ascending=False).iterrows()])
print("  always below:", [(r["name"], [round(r[s], 2) for s in SEAS]) for _, r in consistent_lo.iterrows()])

# ---------- (B) components
def emax(v, k=3):
    v = np.sort(v)
    m = len(v)
    i = np.arange(m)
    return float((v * (((i + 1) / m) ** k - (i / m) ** k)).sum())


def emin(v, k=3):
    return -emax(-np.asarray(v), k)


rows = []
for (s, pid), x in G.groupby(["season", "PLAYER_ID"]):
    if x.FP.mean() < 10:
        continue
    r = dict(season=s, pid=pid, name=x.PLAYER_NAME.iloc[-1], fp=x.FP.mean())
    for k in list(COMP) + ["FP"]:
        v = x[k].to_numpy()
        r[k + "_mean"], r[k + "_sd"] = v.mean(), v.std(ddof=1)
        r[k + "_max3"], r[k + "_min3"] = emax(v), emin(v)
    rows.append(r)
C = pd.DataFrame(rows)
print(f"\n(B) components, {len(C)} player-seasons '23–'25 with 10+ FP/G. Per player-season, then the median across players:")
print(f"  {'part':<6}{'avg FP/G':>9}{'SD':>7}{'SD/avg':>8}{'best of 3':>11}{'best3÷avg':>11}{'best3−avg':>11}{'worst of 3':>12}")
comp_tbl = []
for k in list(COMP) + ["FP"]:
    m, sd, mx, mn = C[k + "_mean"], C[k + "_sd"], C[k + "_max3"], C[k + "_min3"]
    pos = m.median() > 0
    ratio = (mx / m).replace([np.inf, -np.inf], np.nan) if pos else (mn / m).replace([np.inf, -np.inf], np.nan)
    row = dict(part=k, mean=float(m.median()), sd=float(sd.median()), cv=float((sd / m.abs()).replace([np.inf], np.nan).median()),
               max3=float(mx.median()), ratio=float(ratio.median()), up=float((mx - m).median()), min3=float(mn.median()), pos=bool(pos))
    comp_tbl.append(row)
    print(f"  {k:<6}{row['mean']:9.2f}{row['sd']:7.2f}{row['cv']:8.2f}{row['max3']:11.2f}{row['ratio']:11.2f}{row['up']:11.2f}{row['min3']:12.2f}")

# which components make the weekly best game: in each 3-game week, best game (by FP) minus his season average, by part
G2 = G.merge(C[["season", "pid"] + [k + "_mean" for k in COMP] + ["FP_mean"]], left_on=["season", "PLAYER_ID"], right_on=["season", "pid"])
G2["wn"] = G2.groupby(["season", "PLAYER_ID", "week"]).FP.transform("size")
wk = G2[G2.wn == 3]
best = wk.loc[wk.groupby(["season", "PLAYER_ID", "week"]).FP.idxmax()]
dec = {k: float((best[k] - best[k + "_mean"]).mean()) for k in COMP}
tot = float((best.FP - best.FP_mean).mean())
print(f"\nIn the best game of a 3-game week ({len(best)} player-weeks), FP above his season average: {tot:.2f}, by part:")
for k, v in sorted(dec.items(), key=lambda kv: -kv[1]):
    print(f"  {k:<6}{v:+6.2f}  ({v / tot * 100:+.0f}%)")
# by player: 3PM share of the best-game uplift for named players
def dec_player(nm):
    q = best[best.PLAYER_NAME == nm]
    if len(q) < 10:
        return None
    t = (q.FP - q.FP_mean).mean()
    return dict(name=nm, weeks=int(len(q)), up=float(t), parts={k: float((q[k] - q[k + "_mean"]).mean()) for k in COMP})
NAMED = ["Stephen Curry", "Kevin Durant", "Nikola Jokić", "Rudy Gobert", "Luka Dončić", "Shai Gilgeous-Alexander", "Domantas Sabonis", "Devin Booker",
         "Anthony Edwards", "Giannis Antetokounmpo", "Tyrese Haliburton", "Victor Wembanyama"]
pdec = [x for x in (dec_player(n) for n in NAMED) if x]
for x in pdec:
    top = sorted(x["parts"].items(), key=lambda kv: -kv[1])[:4]
    print(f"  {x['name']:<24} best game +{x['up']:.1f} over avg ({x['weeks']} wks): " + ", ".join(f"{k} {v:+.1f}" for k, v in top))
json.dump(dict(three=[dict(name=r["name"], r=[float(r[s]) for s in SEAS], avg=float(r["avg"]), fp=float(r["fp"])) for _, r in three.iterrows()],
               n_hi=int(len(consistent_hi)), n_lo=int(len(consistent_lo)), n3=int(len(three)), comp=comp_tbl, dec=dec, dectot=tot, nbest=int(len(best)), pdec=pdec),
          open(S + "disp5.json", "w"))
