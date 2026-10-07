"""TEAM_SCORING.md — candidate structures × weekly form, on the league's fantasy weeks ('23–'26).
Per structure: weekly score mean / SD, team separation, and draft value: each team projected from its prior season
(carry-over 0.6 toward the league mean, like players are projected) → average starting TEAM minus the best team left,
for 4 / 8 / 10 / 12 teams. Compare with DRAFT_GUIDE.md: target +3 to +5 (best +6 to +10), weekly swing like a player (±9–10)."""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem")
from backend.fantasy_2026_27.weeks import build_weeks, week_for  # noqa: E402

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
D = pd.read_parquet(S + "team_games.parquet")
D["date"] = D.GAME_DATE.dt.date


def tiers(p):  # points allowed, football-style
    return np.select([p < 95, p < 105, p < 115, p < 125], [12, 8, 4, 0], -4).astype(float)


STRUCT = {
    "A: tiers only": lambda d: tiers(d.OPP_PTS),
    "B: tiers + 0.5 / turnover forced": lambda d: tiers(d.OPP_PTS) + 0.5 * d.OPP_TOV,
    "C: B + 3 if opp paint < 40": lambda d: tiers(d.OPP_PTS) + 0.5 * d.OPP_TOV + 3.0 * (d.OPP_PTS_PAINT < 40),
    "D: commissioner's (<100 +10, <110 +5)": lambda d: 10.0 * (d.OPP_PTS < 100) + 5.0 * (d.OPP_PTS < 110),
    "E: (125 − opp points) / 2": lambda d: (125 - d.OPP_PTS) / 2,
    "F: (125 − def rating) / 2": lambda d: (125 - d.DEF_RATING) / 2,
    "G: E + 0.25 / turnover forced": lambda d: (125 - d.OPP_PTS) / 2 + 0.25 * d.OPP_TOV,
}
out = []
for s in ["2022-23", "2023-24", "2024-25", "2025-26"]:
    g = D[D.season == s].copy()
    weeks = build_weeks(set(g.date), [])
    g["week"] = [(w["week"] if (w := week_for(weeks, x)) else None) for x in g.date]
    g = g.dropna(subset=["week"])
    for lab, fn in STRUCT.items():
        g["v"] = fn(g)
        for form in ("best game", "week total", "week avg ×3"):
            how = {"best game": "max", "week total": "sum", "week avg ×3": "mean"}[form]
            agg = g.groupby(["TEAM_ABBREVIATION", "week"]).v.agg(how).rename("w").reset_index()
            if form == "week avg ×3":
                agg["w"] *= 3
            agg["season"], agg["struct"], agg["form"] = s, lab, form
            out.append(agg)
W = pd.concat(out)
T = W.groupby(["struct", "form", "season", "TEAM_ABBREVIATION"]).w.mean().rename("tm").reset_index()
rows = []
for (st, form), q in W.groupby(["struct", "form"]):
    tm = T[(T.struct == st) & (T.form == form)].pivot(index="TEAM_ABBREVIATION", columns="season", values="tm")
    vor = {}
    for N in (4, 8, 10, 12):
        vals = []
        for s0, s1 in [("2022-23", "2023-24"), ("2023-24", "2024-25"), ("2024-25", "2025-26")]:
            proj = tm[s1].mean() + 0.6 * (tm[s0] - tm[s0].mean())  # projected from the prior season
            order = proj.sort_values(ascending=False)
            vals.append((order.head(N).mean() - order.iloc[N], order.iloc[0] - order.iloc[N]))
        vor[N] = (np.mean([v[0] for v in vals]), np.mean([v[1] for v in vals]))
    rows.append(dict(struct=st, form=form, mean=q.w.mean(), wk_sd=q.groupby(["season", "TEAM_ABBREVIATION"]).w.std().mean(),
                     team_sd=T[(T.struct == st) & (T.form == form)].groupby("season").tm.std().mean(),
                     **{f"avg{N}": vor[N][0] for N in vor}, **{f"best{N}": vor[N][1] for N in vor}))
R = pd.DataFrame(rows)
R["ratio8"] = R.avg8 / R.wk_sd  # draft gap per unit of weekly swing (players: C 0.66, G 0.30, F 0.18 at 8 teams, G/F/C)
pd.set_option("display.width", 220)
print(R.round(1).to_string(index=False))
R.to_csv(S + "team_calib.csv", index=False)
