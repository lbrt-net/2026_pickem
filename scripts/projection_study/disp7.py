"""Player-specific PROJ MAX (hack). Layers, in order:
  1. volume: SD = 3.45 × mean^0.33
  2. archetype prior (median spread ratio by archetype × FP band, '22–'25): Big / Self-creator outside / Self-creator
     mid-paint / Assisted; Big = 6'9"+ with rim+paint ≥ 50% of FGA, < 35% threes and < 20% mid; self-creator = 25%+ usage or
     45%+ of makes unassisted; outside = 40%+ of FGA from 3
  3. his own spread ratio over the 3 input seasons, weight w = 0.5 × min(games / 200, 1) (log scale)
  4. shape of his weekly best: simulated best of n from his own standardized games (blend up to 50% at 300+ games)
     with the pooled shape of players at his level (under 12 / 12–20 / 20+ FP/G)
Outputs per player: expected best of 2/3/4 games, and floor (25th pct) / typical (median) / ceiling (90th pct) week."""
import json
import numpy as np
import pandas as pd

R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
F = json.load(open(S + "disp_fit.json"))
A0, B0 = float(np.exp(F["a"])), float(F["b"])
SEAS = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
rng = np.random.default_rng(27)
import os
WS_CAP = float(os.environ.get("WS_CAP", "1.0"))
KST = float(os.environ.get("KST", "0.2"))  # steady players: lower half of the weekly-best range shifted down KST SDs per 0.1 of (1 − factor)
G = pd.read_parquet(S + "disp_games.parquet")
G["week"] = (G.date - pd.to_timedelta(G.date.dt.weekday, unit="D")).dt.date
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
dev = d[d.season < "2025-26"]
PRIOR = dev.groupby(["arch", "band"], observed=True).ratio.median().to_dict()
print("archetype prior (median spread ÷ volume-expected):", {f"{k[0]} {k[1]}": round(v, 2) for k, v in PRIOR.items()})


def pool(z, n, k=20000):
    return np.sort(rng.choice(z, size=(k, n)).max(axis=1))


def player_model(pid, ins, mu):
    """spread factor and weekly-best quantiles (in FP above mean) for n=2,3,4, from input seasons `ins`"""
    q = d[(d.PLAYER_ID == pid) & d.season.isin(ins)]
    gp = int(q.n.sum()) if len(q) else 0
    last = q.sort_values("season").iloc[-1] if len(q) else None
    band = "<15" if mu < 15 else ("15–25" if mu < 25 else "25+")
    prior = PRIOR.get((last.arch, band), 1.0) if last is not None else 1.0
    own = float(np.exp(np.average(np.log(q.ratio), weights=q.n))) if len(q) else 1.0
    w = 0.5 * min(gp / 200, 1)
    f = float(np.exp((1 - w) * np.log(prior) + w * np.log(own)))
    sd = A0 * mu ** B0 * f
    zo = G[(G.PLAYER_ID == pid) & G.season.isin(ins) & (G["size"] >= 20)].z.dropna().to_numpy()
    ws = min(len(zo) / 300, 1.0) * WS_CAP if len(zo) >= 100 else 0.0
    out = dict(f=f, prior=prior, own=own, w=w, arch=last.arch if last is not None else "—", sd=sd, gp=gp, ws=ws)
    for n in (2, 3, 4):
        lq = LEAGUE[(ins[-1], lvl(mu), n)]
        if ws > 0:
            oq = pool(zo, n)
            qs = (1 - ws) * lq + ws * oq
        else:
            qs = lq
        # asymmetric: steady players' bad weeks are worse than their spread says, their good weeks aren't — shift only
        # the lower half of the weekly-best range down
        med = np.median(qs)
        qs = np.where(qs < med, qs - KST * max(0.0, 1 - f) / 0.1, qs)
        out[f"e{n}"] = mu + sd * qs.mean()
        out[f"p25_{n}"], out[f"p50_{n}"], out[f"p90_{n}"] = (mu + sd * np.quantile(qs, x) for x in (0.25, 0.5, 0.9))
    return out


LEAGUE = {}


def lvl(mu):
    return "lo" if mu < 12 else ("mid" if mu < 20 else "hi")


for last in SEAS[1:]:
    base = G[(G.season <= last) & (G.season >= SEAS[max(0, SEAS.index(last) - 2)]) & (G["size"] >= 40)]
    for lv, (lo, hi) in {"lo": (0, 12), "mid": (12, 20), "hi": (20, 99)}.items():
        zl = base[(base["mean"] >= lo) & (base["mean"] < hi)].z.dropna().to_numpy()
        for n in (2, 3, 4):
            LEAGUE[(last, lv, n)] = pool(zl, n)

# ---------- checks: '25 (inputs '22–'24) and '26 (inputs '23–'25); mu = his actual season mean (tests the spread only)
CHK = {}
for TGT, INS in [("2022-23", ["2020-21", "2021-22"]), ("2023-24", ["2020-21", "2021-22", "2022-23"]), ("2024-25", ["2021-22", "2022-23", "2023-24"]), ("2025-26", ["2022-23", "2023-24", "2024-25"])]:
    wk = G[G.season == TGT].groupby(["PLAYER_ID", "week"]).agg(best=("fp", "max"), n=("fp", "size"), name=("PLAYER_NAME", "last"), mu=("mean", "first"))
    tg = G[G.season == TGT].groupby(["TEAM_ABBREVIATION", "week"]).GAME_ID.nunique()
    team = G[G.season == TGT].groupby(["PLAYER_ID", "week"]).TEAM_ABBREVIATION.last()
    wk["tg"] = [tg.get((team[i], i[1]), 0) for i in wk.index]
    wk = wk[(wk.n == 3) & (wk.n >= wk.tg)].reset_index()
    cnt = wk.groupby("PLAYER_ID").size()
    chk = []
    for pid in cnt[cnt >= 8].index:
        x = wk[wk.PLAYER_ID == pid]
        mu = float(x.mu.iloc[0])
        if mu < 15:
            continue
        m = player_model(pid, INS, mu)
        sd0 = A0 * mu ** B0
        lq = LEAGUE[(INS[-1], lvl(mu), 3)]
        v90, v25 = mu + sd0 * np.quantile(lq, .9), mu + sd0 * np.quantile(lq, .25)
        chk.append(dict(season=TGT, name=x.name.iloc[0], mu=mu, k=len(x), f=m["f"], arch=m["arch"], p25=m["p25_3"], p90=m["p90_3"], v25=v25, v90=v90,
                        o90v=int((x.best > v90).sum()), o90p=int((x.best > m["p90_3"]).sum()), u25v=int((x.best < v25).sum()), u25p=int((x.best < m["p25_3"]).sum()),
                        act_mean=float(x.best.mean()), pmean=m["e3"], vmean=mu + sd0 * lq.mean()))
    C = pd.DataFrame(chk)
    CHK[TGT] = C
    print(f"\n'{TGT[-2:]} check: {len(C)} players (15+ FP/G, 8+ full 3-game weeks). Share of weeks above the ceiling (target 10%) / below the floor (target 25%):")
    for lab, q in [("all", C), ("high-spread (factor ≥ 1.03)", C[C.f >= 1.03]), ("low-spread (factor ≤ 0.97)", C[C.f <= 0.97])]:
        k = q.k.sum()
        print(f"    {lab:<30} players {len(q):3d} weeks {k:4d}  above ceiling: volume-only {100 * q.o90v.sum() / k:4.1f}% → player {100 * q.o90p.sum() / k:4.1f}%   "
              f"below floor: {100 * q.u25v.sum() / k:4.1f}% → {100 * q.u25p.sum() / k:4.1f}%")
    print(f"    expected best |error| volume-only {np.abs(C.vmean - C.act_mean).mean():.2f} → player {np.abs(C.pmean - C.act_mean).mean():.2f}")
C = pd.concat(CHK.values())
C.to_csv(S + "disp7_check.csv", index=False)

# ---------- 2026-27 board
B = pd.read_csv(R + "projections_2026_27.csv")
B["rank"] = np.arange(1, len(B) + 1)
eight = [e["name"] for e in json.load(open(S + "sec48.json"))["eight"]]
board = []
for x in B.itertuples():
    if not (x.rank <= 30 or x.name in eight) or x.kind != "vet":
        continue
    m = player_model(int(x.pid), ["2023-24", "2024-25", "2025-26"], float(x.fp))
    board.append(dict(rank=int(x.rank), name=x.name, team=x.team, pos=x.pos, fp=float(x.fp), sd0=A0 * float(x.fp) ** B0, **m))
json.dump(dict(prior={f"{k[0]}|{k[1]}": float(v) for k, v in PRIOR.items()}, check=C.to_dict("records"), board=board), open(S + "disp7.json", "w"), default=float)
print("\n2026-27 (3-game week): PROJ AVG, spread volume-only → player, factor (archetype prior / own / weight), floor / typical / ceiling, expected best 2/3/4")
for r in sorted(board, key=lambda r: -r["e3"])[:30]:
    print(f"  #{r['rank']:<3} {r['name']:<24} {r['fp']:5.1f}  ±{r['sd0']:.1f} → ±{r['sd']:.1f}  ×{r['f']:.2f} ({r['arch']}, prior {r['prior']:.2f}, own {r['own']:.2f}, w {r['w']:.2f})"
          f"  {r['p25_3']:5.1f} / {r['p50_3']:5.1f} / {r['p90_3']:5.1f}   {r['e2']:5.1f} {r['e3']:5.1f} {r['e4']:5.1f}")
