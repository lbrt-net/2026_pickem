"""Write-up data for the weekly-best-game (PROJ MAX) study."""
import json
import numpy as np
import pandas as pd

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
G = pd.read_parquet(S + "disp_games.parquet")
ps = pd.read_csv(S + "disp_ps2.csv")
F = json.load(open(S + "disp_fit.json"))
a, b = float(np.exp(F["a"])), float(F["b"])
d = pd.read_parquet(S + "disp_weeks.parquet")
names = G.groupby("PLAYER_ID").PLAYER_NAME.last()
KL = [0.0, 0.557, 0.859, 1.063, 1.215]  # league shape: E[best of n] in SDs above the mean, n = 1..5
dev = ps[ps.season < "2025-26"]
# mean vs SD points ('25 dev season, for the chart)
pts = [dict(name=r["name"], grp="g", mean=float(r["mean"]), sd=float(r.sd)) for _, r in ps[ps.season == "2024-25"].iterrows()]
# steady / volatile (dev, 3+ seasons, 20+ FP/G)
ag = dev.groupby("PLAYER_ID").agg(k=("ratio", "size"), ratio=("ratio", "mean"), mean=("mean", "mean"))
ag = ag[(ag.k >= 3) & (ag["mean"] >= 20)].sort_values("ratio")
ag["name"] = names.reindex(ag.index).values
steady = [dict(name=r["name"], ratio=float(r.ratio), mean=float(r["mean"])) for _, r in ag.head(10).iterrows()]
volat = [dict(name=r["name"], ratio=float(r.ratio), mean=float(r["mean"])) for _, r in ag.tail(10).iloc[::-1].iterrows()]
# per-player check, '26: full-availability 3-game weeks; avg projected best vs avg actual best
q = d[(d.season == "2025-26") & d.full & (d.n == 3)]
pp = q.groupby("pid").agg(name=("name", "last"), k=("best", "size"), pred=("m_league", "mean"), act=("best", "mean"), mu=("mu", "first"))
pp = pp[pp.k >= 6]
pcheck = [dict(name=r["name"], grp="g", pred=float(r.pred), act=float(r.act), mu=float(r.mu), k=int(r.k)) for _, r in pp.iterrows()]
within = int((abs(pp.pred - pp.act) <= 3).sum())
# bias tables (already printed by disp3 / split)
bias = {}
for t in ["2023-24", "2024-25", "2025-26"]:
    qq = d[d.season == t]
    bias[t] = {m: [float((qq[qq.n == n][m] - qq[qq.n == n].best).mean()) for n in range(1, 5)] for m in ["m_mean", "m_norm", "m_league", "m_own"]}
    bias[t]["full"] = [float((qq[(qq.n == n) & qq.full].m_league - qq[(qq.n == n) & qq.full].best).mean()) for n in range(1, 5)]
    bias[t]["miss"] = [float((qq[(qq.n == n) & ~qq.full].m_league - qq[(qq.n == n) & ~qq.full].best).mean()) for n in range(1, 4)]
    bias[t]["count"] = [int((qq.n == n).sum()) for n in range(1, 5)]
# axes table (dev)
axes = {}
for col, edges, labels in [("USG_PCT", [0, .15, .19, .23, .27, 1], ["under 15%", "15–19%", "19–23%", "23–27%", "27%+"]),
                           ("mpg", [0, 18, 24, 30, 34, 60], ["under 18", "18–24", "24–30", "30–34", "34+"]),
                           ("PIE", [-1, .07, .09, .11, .13, 1], ["under 7", "7–9", "9–11", "11–13", "13+"]),
                           ("AGE", [0, 23, 27, 31, 50], ["23 and under", "24–27", "28–31", "32+"]),
                           ("pts_share", list(dev.pts_share.quantile([0, .2, .4, .6, .8, 1]) + [0, 0, 0, 0, 0, 1e-9]), ["lowest fifth", "2nd", "3rd", "4th", "highest fifth"]),
                           ("reb_share", list(dev.reb_share.quantile([0, .2, .4, .6, .8, 1]) + [0, 0, 0, 0, 0, 1e-9]), ["lowest fifth", "2nd", "3rd", "4th", "highest fifth"])]:
    c = pd.cut(dev[col], edges, labels=labels, include_lowest=True)
    t = dev.groupby(c, observed=True).agg(n=("ratio", "size"), ratio=("ratio", "median"), mean=("mean", "median"))
    axes[col] = [(str(i), int(r.n), float(r.ratio), float(r["mean"])) for i, r in t.iterrows()]
pers = {}
pr = ps.pivot_table(index="PLAYER_ID", columns="season", values="ratio")
SEAS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
for s0, s1 in zip(SEAS[:-1], SEAS[1:]):
    ok = pr[[s0, s1]].dropna()
    pers[f"'{s0[-2:]}→'{s1[-2:]}"] = float(ok[s0].corr(ok[s1]))
# 2026-27 PROJ MAX for the top 25 + the eight
B = pd.read_csv(R + "projections_2026_27.csv")
B["rank"] = np.arange(1, len(B) + 1)
eight = [e["name"] for e in json.load(open(S + "sec48.json"))["eight"]]
def pm(mu, n):
    return mu + a * mu ** b * KL[n - 1]
board = [dict(rank=int(x.rank), name=x.name, team=x.team, pos=x.pos, fp=float(x.fp), sd=a * float(x.fp) ** b,
              m2=pm(float(x.fp), 2), m3=pm(float(x.fp), 3), m4=pm(float(x.fp), 4)) for x in B.itertuples() if x.rank <= 25 or x.name in eight]
json.dump(dict(a=a, b=b, KL=KL, pts=pts, steady=steady, volat=volat, pcheck=pcheck, within=within, npc=len(pp), bias=bias, axes=axes,
               pers=pers, board=board, ndev=int(len(dev)), r2=0.081), open(S + "disp_report.json", "w"))
print(a, b, within, len(pp), [s["name"] for s in steady][:5], [v["name"] for v in volat][:5])
