"""2026-27 weekly-best curve per player, for the draft pool: for n = 1..10 games in a fantasy period, the expected best
game (PROJ MAX for that week), floor (25th pct) and ceiling (90th pct). Same model as disp7.py (DISPERSION.md):
volume × archetype prior × own spread, own game shape, asymmetric downside for steady players. Rookies / players with
no history: volume and level only. Writes nba-pipeline/data/raw/proj_week_2026_27.json (player_id → {e, p25, p90})."""
import json
import numpy as np
import pandas as pd

R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
F = json.load(open(S + "disp_fit.json"))
A0, B0 = float(np.exp(F["a"])), float(F["b"])
NMAX, KST = 10, 0.2
INS = ["2023-24", "2024-25", "2025-26"]
rng = np.random.default_rng(27)
G = pd.read_parquet(S + "disp_games.parquet")
st = G.groupby(["season", "PLAYER_ID"]).fp.agg(["mean", "std", "size"])
G = G.join(st, on=["season", "PLAYER_ID"])
G["z"] = (G.fp - G["mean"]) / G["std"]
d = pd.read_csv(S + "disp_arch.csv")


def arche(r):
    if r.ht >= 81 and (r.rim + r.paint >= 0.50) and r.three < 0.35 and r.mid < 0.20:
        return "Big"
    if (r.USG_PCT == r.USG_PCT and r.USG_PCT >= 0.25) or r.uast >= 0.45:
        return "Self-creator, outside" if r.three >= 0.40 else "Self-creator, mid/paint"
    return "Assisted"


d["arch"] = d.apply(arche, axis=1)
d["band"] = pd.cut(d["mean"], [0, 15, 25, 99], labels=["<15", "15–25", "25+"])
PRIOR = d[d.season < "2025-26"].groupby(["arch", "band"], observed=True).ratio.median().to_dict()


def lvl(mu):
    return "lo" if mu < 12 else ("mid" if mu < 20 else "hi")


def pool(z, n, k=20000):
    return np.sort(rng.choice(z, size=(k, n)).max(axis=1))


base = G[G.season.isin(INS) & (G["size"] >= 40)]
LEAGUE = {}
for lv, (lo, hi) in {"lo": (0, 12), "mid": (12, 20), "hi": (20, 99)}.items():
    zl = base[(base["mean"] >= lo) & (base["mean"] < hi)].z.dropna().to_numpy()
    for n in range(1, NMAX + 1):
        LEAGUE[(lv, n)] = pool(zl, n)


def curve(pid, mu):
    q = d[(d.PLAYER_ID == pid) & d.season.isin(INS)]
    gp = int(q.n.sum()) if len(q) else 0
    band = "<15" if mu < 15 else ("15–25" if mu < 25 else "25+")
    if len(q):
        last = q.sort_values("season").iloc[-1]
        prior = PRIOR.get((last.arch, band), 1.0)
        own = float(np.exp(np.average(np.log(q.ratio), weights=q.n)))
    else:
        prior, own = 1.0, 1.0
    w = 0.5 * min(gp / 200, 1)
    f = float(np.exp((1 - w) * np.log(prior) + w * np.log(own)))
    sd = A0 * max(mu, 0.5) ** B0 * f
    zo = G[(G.PLAYER_ID == pid) & G.season.isin(INS) & (G["size"] >= 20)].z.dropna().to_numpy()
    ws = min(len(zo) / 300, 1.0) if len(zo) >= 100 else 0.0
    out = {"e": [], "p25": [], "p90": []}
    for n in range(1, NMAX + 1):
        lq = LEAGUE[(lvl(mu), n)]
        qs = (1 - ws) * lq + ws * pool(zo, n) if ws > 0 else lq
        med = np.median(qs)
        qs = np.where(qs < med, qs - KST * max(0.0, 1 - f) / 0.1, qs)
        out["e"].append(round(float(mu if n == 1 else mu + sd * qs.mean()), 2))  # a 1-game week's expected score is PROJ AVG
        out["p25"].append(round(float(mu + sd * np.quantile(qs, 0.25)), 2))
        out["p90"].append(round(float(mu + sd * np.quantile(qs, 0.9)), 2))
    return out


# ---- clutch points (SCORING_SCALE.md: +2 per point scored in clutch time). Projected clutch points per game = his plain
# 3-season average ('24–'26): total clutch points ÷ total games played. No history (rookies) = 0.
def _clutch(s):
    d = json.load(open(f"{R}player_clutch/{s}.json"))
    rows = [dict(zip(x["headers"], r)) for x in d.values() for r in x["rows"]]
    return pd.DataFrame(rows).groupby("PLAYER_ID").PTS.sum() if rows else pd.Series(dtype=float)


def _games(s):
    rs = json.load(open(f"{R}game_logs/{s}.json"))["resultSets"][0]
    g = pd.DataFrame(rs["rowSet"], columns=rs["headers"])
    return g[g.MIN > 0].groupby("PLAYER_ID").size()


CL = {s: _clutch(s) for s in INS}
GP = {s: _games(s) for s in INS}
CLUTCH_PTS = 2.0


def clutch_pg(pid):
    gp = sum(int(GP[s].get(pid, 0)) for s in INS)
    return sum(float(CL[s].get(pid, 0)) for s in INS) / gp if gp else 0.0


B = pd.read_csv(R + "projections_2026_27.csv")
res = {}
for x in B.itertuples():
    if x.fp != x.fp:
        continue
    pid = int(x.pid)
    cpg = clutch_pg(pid)                                               # 3-season clutch points per game
    avg = float(x.fp) + CLUTCH_PTS * cpg                              # PROJ AVG with the clutch category
    c = curve(pid, avg)
    c["avg"], c["clutch_pg"] = round(avg, 2), round(cpg, 3)
    res[str(pid)] = c
print("clutch per game, top:", sorted(((v["clutch_pg"], k) for k, v in res.items()), reverse=True)[:5])
json.dump(res, open(R + "proj_week_2026_27.json", "w"))
print(len(res), "players;", {k: res[k]["e"][:4] for k in list(res)[:3]})
