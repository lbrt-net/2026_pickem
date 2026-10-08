"""TEAM draft 3 candidates ('23–'26): one steady bread-and-butter category + the swingy part.
  swingy (both): under 100 +15 / under 95 +10 / under 90 +10; +5 per violation forced; +10 each: 20+ turnovers forced,
                 opp fast-break ≤ 6, opp paint ≤ 32, DREB − opp OREB ≥ 30
  A bread and butter: +1 per turnover forced
  B bread and butter: +1 per point under 125 allowed (0 at 125+)
Per season and team: weekly score (best game of the fantasy week), how much of it is the bread and butter, swing, zero
weeks, follows defense, repeats next season. → team_draft3.json"""
import json, sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem")
from backend.fantasy_2026_27.weeks import build_weeks, week_for  # noqa: E402

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
D = pd.read_parquet(S + "team_full.parquet")
D["swing"] = (15 * (D.OPP_PTS < 100) + 10 * (D.OPP_PTS < 95) + 10 * (D.OPP_PTS < 90) + 5 * D.VIOL_FORCED
              + 10 * ((D.OPP_TOV >= 20).astype(int) + (D.OPP_PTS_FB <= 6).astype(int) + (D.OPP_PTS_PAINT <= 32).astype(int) + (D.DREB_MARGIN >= 30).astype(int)))
D["bbA"] = D.OPP_TOV.astype(float)
D["bbB"] = (125 - D.OPP_PTS).clip(lower=0)
D["A"], D["B"] = D.bbA + D.swing, D.bbB + D.swing
out = []
for s, g in D.groupby("season"):
    weeks = build_weeks(set(g.GAME_DATE.dt.date), [])
    g = g.assign(week=[(w["week"] if (w := week_for(weeks, x)) else None) for x in g.GAME_DATE.dt.date]).dropna(subset=["week"])
    out.append(g)
G = pd.concat(out)
dr = G.groupby(["season", "TEAM_ABBREVIATION"]).apply(lambda q: (q.DEF_RATING * q.POSS).sum() / q.POSS.sum(), include_groups=False).rename("dr")
res = {}
for v in ("A", "B"):
    idx = G.groupby(["season", "TEAM_ABBREVIATION", "week"])[v].idxmax()
    best = G.loc[idx]
    wk = best[["season", "TEAM_ABBREVIATION", "week", v, "bb" + v]].rename(columns={v: "score", "bb" + v: "bb"})
    t = wk.groupby(["season", "TEAM_ABBREVIATION"]).agg(week=("score", "mean"), sd=("score", "std"), bb_share=("bb", "sum"),
                                                         tot=("score", "sum"), zero=("score", lambda x: float((x <= 5).mean()))).join(dr)
    t["bb_share"] = t.bb_share / t.tot
    corr = float(np.mean([np.corrcoef(q.week, -q.dr)[0, 1] for _, q in t.groupby(level=0)]))
    w = t.week.unstack(0)
    yoy = float(np.nanmean([w[[a, b]].dropna().corr().iloc[0, 1] for a, b in zip(w.columns[:-1], w.columns[1:])]))
    s26 = t.loc["2025-26"].sort_values("week", ascending=False)
    res[v] = dict(week=float(wk.score.mean()), sd=float(wk.score.std()), bb_share=float(wk.bb.sum() / wk.score.sum()), low_weeks=float((wk.score <= 5).mean()),
                  corr=corr, yoy=yoy, top=[(k, float(r.week)) for k, r in s26.head(5).iterrows()], bottom=[(k, float(r.week)) for k, r in s26.tail(3).iterrows()],
                  team_spread=float(s26.week.max() - s26.week.min()), teams26={k: dict(week=float(r.week), sd=float(r.sd), dr=float(r.dr)) for k, r in s26.iterrows()})
    print(f"{v}: weekly {res[v]['week']:.1f} ± {res[v]['sd']:.1f}; bread and butter = {res[v]['bb_share']:.0%} of the weekly score; weeks of 5 or less {res[v]['low_weeks']:.1%}; "
          f"follows defense {corr:.2f}; repeats {yoy:.2f}; '26 best–worst {res[v]['team_spread']:.1f}")
    print("   top '26:", [(k, round(x, 1)) for k, x in res[v]["top"]], " bottom:", [(k, round(x, 1)) for k, x in res[v]["bottom"]])
json.dump(res, open(S + "team_draft3.json", "w"))
G.to_parquet(S + "team_weeks.parquet")
