"""Rebound share resplit test: is OREB% / DREB% individual or shared?

Per target team (roster = first game's team that season): each player gets prior-year OREB_PCT / DREB_PCT and
prior MPG (team scaled to 240). On-floor shares of one pool add up to the team rate:
  sum(pct_i * mpg_i) = 48 * team_rate.  Target team_rate = prior-season league-average team rate.
Projected pct_i = prior pct_i * (target / roster sum)^alpha.  alpha=0: same as last year; 1: full resplit.
No prior data: league median of players under 15 MPG. Scored on 60+ GP for the team both seasons,
pooled '22→'23 … '25→'26, stayers vs movers.
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem/scripts")
from load_historical_boxscores import minutes  # noqa: E402

R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
BOX = {"2021-22": "/Users/allan/PycharmProjects/nba-pipeline/data/box_scores/trad_box_scores_2021_22.parquet",
       "2022-23": R + "box_scores_traditional/trad_box_scores_2022_23.parquet",
       "2023-24": R + "box_scores_traditional/trad_box_scores_2023_24.parquet",
       "2024-25": R + "box_scores_traditional/trad_box_scores_2024_25.parquet",
       "2025-26": "/Users/allan/PycharmProjects/nba-pipeline/data/box_scores/trad_box_scores_2025_26.parquet"}


def tab(kind, s):
    rs = json.load(open(f"{R}{kind}/{s}.json"))["resultSets"][0]
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"])


def box(s):
    d = pd.read_parquet(BOX[s])
    d = d[d.game_id.astype(str).str[2] == "2"].copy()
    d["player_id"] = d.player_id.astype(int)
    d["m"] = d["minutes"].map(minutes)
    return d[d.m > 0]


def transition(s0, s1, alphas):
    a0, a1 = tab("player_advanced", s0).set_index("PLAYER_ID"), tab("player_advanced", s1).set_index("PLAYER_ID")
    t0 = tab("team_advanced", s0)
    b0, b1 = box(s0), box(s1)
    opening = b1.sort_values("game_id").groupby("player_id").team_tricode.first()
    gp0 = b0.groupby(["player_id", "team_tricode"]).game_id.nunique()
    gp1 = b1.groupby(["player_id", "team_tricode"]).game_id.nunique()
    main0 = gp0.reset_index().sort_values("game_id").groupby("player_id").last()
    low = a0[a0.MIN < 15]
    proj = {(st, al): {} for st in ("OREB_PCT", "DREB_PCT") for al in alphas}
    sums = {}
    for team, pl in opening.groupby(opening):
        ids = list(pl.index)
        m = np.array([a0.MIN.get(p, 15.0) for p in ids], float)
        m = m * 240 / m.sum()
        for st in ("OREB_PCT", "DREB_PCT"):
            pct = np.array([a0[st].get(p, low[st].median()) for p in ids], float)
            target = 48 * t0[st].mean()
            ratio = target / (pct * m).sum()
            sums[(team, st)] = ratio
            for al in alphas:
                for p, v in zip(ids, pct * ratio ** al):
                    proj[(st, al)][p] = v
    rows = []
    for p, t1 in opening.items():
        if p not in main0.index or p not in a0.index or p not in a1.index:
            continue
        tm0, g0 = main0.loc[p, "team_tricode"], main0.loc[p, "game_id"]
        if g0 >= 60 and gp1.get((p, t1), 0) >= 60:
            r = dict(tr=f"'{s0[-2:]}→'{s1[-2:]}", name=a1.PLAYER_NAME[p], moved=tm0 != t1, t1=t1)
            for st in ("OREB_PCT", "DREB_PCT"):
                r[f"{st}_0"], r[f"{st}_1"] = a0[st][p], a1[st][p]
                r[f"{st}_ratio"] = sums[(t1, st)]
                for al in alphas:
                    r[f"{st}_a{al}"] = proj[(st, al)][p]
            rows.append(r)
    return pd.DataFrame(rows)


ALPHAS = [0, 0.25, 0.5, 0.75, 1.0]
S = list(BOX)
v = pd.concat(transition(a, b, ALPHAS) for a, b in zip(S, S[1:])).reset_index(drop=True)
print(f"{len(v)} player-seasons ({v.moved.sum()} changed teams). Error in % points of rebound share (mean abs).\n")
for st, lab in [("OREB_PCT", "OFFENSIVE rebound %"), ("DREB_PCT", "DEFENSIVE rebound %")]:
    print(f"{lab}   (typical {100 * v[f'{st}_1'].median():.1f}%)")
    print(f"   {'alpha':<8}{'all':>7}{'stayed':>9}{'moved':>8}")
    for al in ALPHAS:
        e = (v[f"{st}_a{al}"] - v[f"{st}_1"]).abs() * 100
        tag = "  ← same as last year" if al == 0 else ("  ← full resplit" if al == 1 else "")
        print(f"   {al:<8}{e.mean():7.2f}{e[~v.moved].mean():9.2f}{e[v.moved].mean():8.2f}{tag}")
    d_act = v[f"{st}_1"] - v[f"{st}_0"]
    d_prj = v[f"{st}_a1.0"] - v[f"{st}_0"]
    for lab2, s in [("stayed", ~v.moved), ("moved", v.moved)]:
        c = np.corrcoef(d_prj[s], d_act[s])[0, 1]
        k = np.cov(d_prj[s], d_act[s])[0, 1] / d_prj[s].var()
        print(f"   {lab2:<7} corr(resplit change, actual change) {c:+.2f}   best scale {k:.2f}")
    print()

# who moved and how DREB% shifted
m = v[v.moved].assign(dd=lambda x: 100 * (x.DREB_PCT_1 - x.DREB_PCT_0), dp=lambda x: 100 * (x["DREB_PCT_a1.0"] - x.DREB_PCT_0))
print("Movers with the biggest DREB% change (prior → resplit → actual, %):")
for _, x in m.loc[m.dd.abs().sort_values(ascending=False).index].head(12).iterrows():
    print(f"   {x.tr} {x['name']:<24} →{x.t1}  {100 * x.DREB_PCT_0:5.1f} → {100 * x['DREB_PCT_a1.0']:5.1f} → {100 * x.DREB_PCT_1:5.1f}")
