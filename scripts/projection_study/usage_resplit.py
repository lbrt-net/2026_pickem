"""Usage resplit: project next-season usage from prior-year usage, re-normalized on the new roster.

Per target team: roster = players on it for the target season (backtests: his first game's team that season;
forward: 2026-27 CommonTeamRoster). Each player gets prior-year USG_PCT and prior-year MPG (raw — the minutes
pull distorts the split); team MPG scaled to 240. No prior-year data (rookies etc.): 18% usage, 15 MPG.
Team constraint: sum(usage * MPG) = 0.20 * 240 = 48. Scale all usage by one factor to hit it, cap at 40%,
hand the excess back to the uncapped players in proportion to their usage, repeat until it holds.
Scored on players with 60+ games for their team in both seasons (box scores), movers vs stayers,
pooled over '22→'23, '23→'24, '24→'25, '25→'26.
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
CAP, DEF_USG, DEF_MPG = 0.40, 0.18, 15.0


def adv(s):
    rs = json.load(open(f"{R}player_advanced/{s}.json"))["resultSets"][0]
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"]).set_index("PLAYER_ID")


def box(s):
    d = pd.read_parquet(BOX[s])
    d = d[d.game_id.astype(str).str[2] == "2"].copy()
    d["player_id"] = d.player_id.astype(int)
    d["m"] = d["minutes"].map(minutes)
    return d[d.m > 0]


def resplit(roster: pd.DataFrame) -> pd.Series:
    m = roster.mpg * 240 / roster.mpg.sum()
    u = roster.usg.copy()
    capped = pd.Series(False, index=u.index)
    for _ in range(50):
        free = ~capped
        need = 48 - (u[capped] * m[capped]).sum()
        u[free] = u[free] * need / (u[free] * m[free]).sum()
        over = free & (u > CAP)
        if not over.any():
            break
        u[over] = CAP
        capped |= over
    return u


def project(prior: pd.DataFrame, rosters: dict) -> pd.Series:
    out = {}
    for team, pl in rosters.items():
        r = pd.DataFrame(index=pd.Index(sorted(pl), name="player_id"))
        r["usg"] = [prior.USG_PCT.get(p, DEF_USG) for p in r.index]
        r["mpg"] = [prior.MIN.get(p, DEF_MPG) for p in r.index]
        out.update(resplit(r).to_dict())
    return pd.Series(out)


def transition(s0, s1):
    a0, a1, b0, b1 = adv(s0), adv(s1), box(s0), box(s1)
    opening = b1.sort_values("game_id").groupby("player_id").team_tricode.first()
    proj = project(a0, opening.groupby(opening).apply(lambda s: set(s.index)).to_dict())
    gp0 = b0.groupby(["player_id", "team_tricode"]).game_id.nunique()
    gp1 = b1.groupby(["player_id", "team_tricode"]).game_id.nunique()
    main0 = gp0.reset_index().sort_values("game_id").groupby("player_id").last()
    rows = []
    for p, t1 in opening.items():
        if p not in main0.index or p not in a0.index or p not in a1.index:
            continue
        t0, g0 = main0.loc[p, "team_tricode"], main0.loc[p, "game_id"]
        if g0 >= 60 and gp1.get((p, t1), 0) >= 60:
            rows.append(dict(pid=p, tr=f"'{s0[-2:]}→'{s1[-2:]}", name=a1.PLAYER_NAME[p], t0=t0, t1=t1, moved=t0 != t1,
                             u0=a0.USG_PCT[p], proj=proj[p], act=a1.USG_PCT[p]))
    return pd.DataFrame(rows)


SEAS = list(BOX)
v = pd.concat(transition(a, b) for a, b in zip(SEAS, SEAS[1:]))
v["d_act"], v["d_proj"] = v.act - v.u0, v.proj - v.u0


def line(lab, s):
    c = np.corrcoef(s.d_proj, s.d_act)[0, 1]
    slope = np.cov(s.d_proj, s.d_act)[0, 1] / s.d_proj.var()
    print(f"  {lab:<16}{len(s):>4}   same as prior {100 * s.d_act.abs().mean():5.2f}   resplit {100 * (s.proj - s.act).abs().mean():5.2f}"
          f"   bias {100 * (s.proj - s.act).mean():+5.2f}   corr(proj Δ, actual Δ) {c:+.2f}   best scale on Δ {slope:.2f}")


print("Usage error, % points (players with 60+ games for their team both seasons)\n")
for tr, s in v.groupby("tr", sort=False):
    line(f"{tr} all", s)
print()
line("POOLED all", v)
line("POOLED changed", v[v.moved])
line("POOLED stayed", v[~v.moved])

print("\nChanged teams, pooled (usage %: prior → projected → actual):")
for x in v[v.moved].sort_values("u0", ascending=False).itertuples():
    print(f"  {x.tr} {x.name:<24} {x.t0}→{x.t1}  {100 * x.u0:5.1f} → {100 * x.proj:5.1f} → {100 * x.act:5.1f}")

# ---- forward: '26 → 2026-27 ----
a26, b26 = adv("2025-26"), box("2025-26")
r27 = pd.read_csv(f"{R}rosters/2026-27.csv")
proj27 = project(a26, r27.groupby("TEAM").PLAYER_ID.apply(set).to_dict())
main26 = b26.groupby(["player_id", "team_tricode"]).game_id.nunique().reset_index().sort_values("game_id").groupby("player_id").last().team_tricode
f = r27.assign(t26=r27.PLAYER_ID.map(main26), u26=r27.PLAYER_ID.map(a26.USG_PCT), mpg26=r27.PLAYER_ID.map(a26.MIN),
               proj=r27.PLAYER_ID.map(proj27))
f = f[f.t26.notna() & (f.t26 != f.TEAM) & (f.mpg26 >= 20)].sort_values("u26", ascending=False)
print("\n2026-27 — players on a new team (20+ MPG in '26), usage % '26 → projected '27:")
for x in f.head(20).itertuples():
    print(f"  {x.PLAYER:<24} {x.t26}→{x.TEAM}  {100 * x.u26:5.1f} → {100 * x.proj:5.1f}  ({100 * (x.proj - x.u26):+.1f})")
