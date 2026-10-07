"""Dispersion part 4: explain each player's spread residual (actual SD ÷ volume-scaled SD) by archetype.
Archetypes from how he scores: bigs; self-creating jump shooters split into outside shooters and mid-range/paint
maestros; assisted (spot-up / cutter) players; plus turnover-heavy without the assists. Fit on '22–'25, check on '26."""
import contextlib, io, json, runpy
import numpy as np, pandas as pd

R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
SEAS = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
with contextlib.redirect_stdout(io.StringIO()):
    Z = runpy.run_path(S + "zone_projection.py", run_name="lib")


def J(kind, s):
    rs = json.load(open(f"{R}{kind}/{s}.json"))["resultSets"]
    rs = rs[0] if isinstance(rs, list) else rs
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"])


ps = pd.read_csv(S + "disp_ps.csv")  # season, PLAYER_ID, n, mean, sd, ratio ...
feats = []
for s in SEAS:
    g = J("game_logs", s)
    g = g[g.MIN > 0]
    t = g.groupby("PLAYER_ID")[["FGA", "FG3A", "FTA", "AST", "TOV", "PTS", "STL", "BLK", "OREB", "DREB", "FG3M"]].mean()
    sc = J("player_scoring", s).set_index("PLAYER_ID")
    t["uast"] = sc.PCT_UAST_FGM.reindex(t.index)  # share of his made FGs that were unassisted (self-created)
    z = Z["load"](s).pivot_table(index="pid", columns="zone", values="fga", aggfunc="sum", fill_value=0)
    tot = z.sum(axis=1).replace(0, np.nan)
    t["rim"] = (z.get("RA", 0) / tot).reindex(t.index)
    t["paint"] = (z.get("Paint", 0) / tot).reindex(t.index)
    t["mid"] = (z.get("Mid", 0) / tot).reindex(t.index)
    t["three"] = ((z.get("Corner3", 0) + z.get("Other3", 0)) / tot).reindex(t.index)
    t["season"] = s
    feats.append(t.reset_index())
F = pd.concat(feats)
HT = {}
for s in ["2019-20"] + SEAS:
    b = J("bios", s).set_index("PLAYER_ID")
    HT.update(b.PLAYER_HEIGHT_INCHES.dropna().to_dict())
d = ps.merge(F, on=["season", "PLAYER_ID"], how="left")
d["ht"] = d.PLAYER_ID.map(HT)
d = d.dropna(subset=["uast", "three", "ht"])
d["tov_ast"] = d.TOV / d.AST.clip(lower=0.5)


def arche(r):
    if r.ht >= 82 or (r.rim + r.paint >= 0.55 and r.three < 0.25):
        return "Big"
    if r.uast >= 0.45:
        return "Self-creator, outside" if r.three >= 0.40 else "Self-creator, mid/paint"
    return "Assisted wing / guard"


d["arch"] = d.apply(arche, axis=1)
d["tov_heavy"] = (d.TOV >= 2.5) & (d.tov_ast >= 0.45)
d["lr"] = np.log(d.ratio)
dev = d[d.season < "2025-26"]
print("Spread vs what his volume predicts (median ratio), dev '22–'25, by archetype × FP level:")
for lab, lo, hi in [("all", 0, 99), ("under 15 FP/G", 0, 15), ("15–25", 15, 25), ("25+", 25, 99)]:
    q = dev[(dev["mean"] >= lo) & (dev["mean"] < hi)]
    t = q.groupby("arch").ratio.agg(["median", "size"])
    print(f"  {lab:<14} " + "  ".join(f"{i}: {r['median']:.2f} (n={int(r['size'])})" for i, r in t.iterrows()))
for lab, q in [("turnover-heavy (2.5+ TOV, TOV/AST ≥ 0.45)", dev[dev.tov_heavy]), ("not", dev[~dev.tov_heavy & (dev.TOV >= 1.5)])]:
    print(f"  {lab}: median ratio {q.ratio.median():.2f} (n={len(q)})")
# regression of log ratio on archetype + continuous features, weighted by games
X = pd.get_dummies(dev.arch, drop_first=False).astype(float)
X = X.drop(columns=["Assisted wing / guard"])
for c in ["tov_ast", "three", "uast"]:
    X[c] = dev[c]
X.insert(0, "const", 1.0)
w = np.sqrt(dev.n)
beta = np.linalg.lstsq(X.to_numpy() * w.to_numpy()[:, None], dev.lr.to_numpy() * w.to_numpy(), rcond=None)[0]
coef = dict(zip(X.columns, beta))
print("\nlog(spread ratio) model:", {k: round(v, 3) for k, v in coef.items()})


def pred(df):
    x = pd.get_dummies(df.arch).reindex(columns=[c for c in X.columns if c not in ("const", "tov_ast", "three", "uast")], fill_value=0).astype(float)
    out = coef["const"] + sum(coef[c] * x[c] for c in x.columns) + sum(coef[c] * df[c] for c in ["tov_ast", "three", "uast"])
    return out


d["lr_arch"] = pred(d)
# next-season prediction test: predict season t ratio from season t-1 features / own ratio
prev = d.set_index(["PLAYER_ID", "season"])
rows = []
for s0, s1 in zip(SEAS[:-1], SEAS[1:]):
    a0 = d[d.season == s0].set_index("PLAYER_ID")
    a1 = d[d.season == s1].set_index("PLAYER_ID")
    ok = a0.index.intersection(a1.index)
    for p in ok:
        rows.append(dict(s1=s1, pid=p, act=a1.lr[p], arch=a0.lr_arch[p], own=a0.lr[p], n0=a0.n[p], fp0=a0["mean"][p], n1=a1.n[p]))
T = pd.DataFrame(rows)
for s1 in ["2023-24", "2024-25", "2025-26"]:
    q = T[(T.s1 == s1) & (T.fp0 >= 15)]
    for lab, p in [("volume only (ratio 1)", 0 * q.act), ("archetype", q.arch), ("own last season ×0.4", 0.4 * q.own),
                   ("archetype + 0.4×(own − archetype)", q.arch + 0.4 * (q.own - q.arch))]:
        e = np.abs(np.exp(p) - np.exp(q.act))
        print(f"  {s1[-2:]}{' (check)' if s1 == '2025-26' else ''} 15+ FP/G n={len(q)}  {lab:<36} |ratio error| {e.mean():.3f}   corr {np.corrcoef(p, q.act)[0, 1] if p.std() > 0 else 0:.2f}")
d.to_csv(S + "disp_arch.csv", index=False)
json.dump({k: float(v) for k, v in coef.items()}, open(S + "disp_arch_coef.json", "w"))
for nm in ["Stephen Curry", "Kevin Durant", "Nikola Jokić", "Shai Gilgeous-Alexander", "Luka Dončić", "Domantas Sabonis", "Tyrese Haliburton", "DeMar DeRozan",
           "Rudy Gobert", "Trae Young", "Cade Cunningham", "Giannis Antetokounmpo", "Victor Wembanyama", "Jalen Brunson"]:
    q = d[(d.name == nm) & (d.season == "2025-26")]
    if len(q):
        r = q.iloc[0]
        print(f"  {nm:<24} {r.arch:<24} tov-heavy {bool(r.tov_heavy)!s:<5} unassisted {r.uast:.2f} 3PA share {r.three:.2f}  archetype ratio {np.exp(r.lr_arch):.2f}  actual '26 {r.ratio:.2f}")
