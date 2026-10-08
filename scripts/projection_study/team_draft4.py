"""TEAM draft 4 (commissioner's numbers), per game:
  +1 per point the opponent finishes under 125; +10 under 100; +15 more under 90
  +5 per time violation forced (shot clock, 8-second, 5-second)
  +5 single-digit fast-break points allowed; +10 under 30 paint points allowed; +5 20+ turnovers forced;
  +5 defensive glass: our defensive rebounds minus theirs by 10+ (commissioner's definition and cutoffs, 2026-10-07)
Weekly score = best game of the fantasy week. Checked on '23–'26; 2026-27 projection like team_proj.py; value next to players."""
import json, sys
import numpy as np
import pandas as pd
import psycopg2, psycopg2.extras
sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem")
from backend.fantasy_2026_27.weeks import build_weeks, season_weeks, week_for  # noqa: E402
from backend.fantasy_2026_27.projections import team_games  # noqa: E402

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
D = pd.read_parquet(S + "team_full.parquet")
VF = pd.read_parquet(S + "team_viol_forced.parquet")[["GAME_ID", "TEAM_ABBREVIATION", "SHOT_CLOCK", "EIGHT_SEC", "FIVE_SEC", "OFF_FOUL"]]
D = D.merge(VF, on=["GAME_ID", "TEAM_ABBREVIATION"], how="left")
D["time_viol"] = D.SHOT_CLOCK + D.EIGHT_SEC + D.FIVE_SEC
PARTS = {
    "Points under 125 (+1 each)": lambda d: (125 - d.OPP_PTS).clip(lower=0),
    "Under 100 (+10)": lambda d: 10 * (d.OPP_PTS < 100),
    "Under 90 (+15 more)": lambda d: 15 * (d.OPP_PTS < 90),
    "Time violations forced (+5 each)": lambda d: 5 * d.time_viol,
    "Single-digit fast-break pts (+5)": lambda d: 5 * (d.OPP_PTS_FB <= 9),
    "Under 30 paint pts (+10)": lambda d: 10 * (d.OPP_PTS_PAINT < 30),
    "20+ turnovers forced (+5)": lambda d: 5 * (d.OPP_TOV >= 20),
}
GLASS = {"draft 4": lambda d: 5 * ((d.DREB - d.OPP_DREB) >= 10)}
out = []
for s, g in D.groupby("season"):
    weeks = build_weeks(set(g.GAME_DATE.dt.date), [])
    out.append(g.assign(week=[(w["week"] if (w := week_for(weeks, x)) else None) for x in g.GAME_DATE.dt.date]).dropna(subset=["week"]))
G = pd.concat(out)
for k, f in PARTS.items():
    G[k] = f(G).astype(float)
dr = G.groupby(["season", "TEAM_ABBREVIATION"]).apply(lambda q: (q.DEF_RATING * q.POSS).sum() / q.POSS.sum(), include_groups=False).rename("dr")
conn = psycopg2.connect("dbname=pickem_local")
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
weeks27 = season_weeks(cur, "2026-27")
TG = team_games(cur, "2026-27", weeks27)
DG = json.load(open(S + "draft_guide.json"))
rng = np.random.default_rng(27)
res = {}
hit = {k: float((G[k] > 0).mean()) for k in PARTS}
for gl, gf in GLASS.items():
    G["glass"] = gf(G).astype(float)
    hit_gl = float((G.glass > 0).mean())
    G["score"] = G[list(PARTS)].sum(axis=1) + G.glass
    idx = G.groupby(["season", "TEAM_ABBREVIATION", "week"]).score.idxmax()
    wk = G.loc[idx]
    t = wk.groupby(["season", "TEAM_ABBREVIATION"]).score.agg(["mean", "std"]).join(dr)
    corr = float(np.mean([np.corrcoef(q["mean"], -q.dr)[0, 1] for _, q in t.groupby(level=0)]))
    w = t["mean"].unstack(0)
    yoy = float(np.nanmean([w[[a, b]].dropna().corr().iloc[0, 1] for a, b in zip(w.columns[:-1], w.columns[1:])]))
    share = {k: float(wk[k].sum() / wk.score.sum()) for k in PARTS} | {"Glass": float(wk.glass.sum() / wk.score.sum())}
    s26 = t.loc["2025-26"].sort_values("mean", ascending=False)
    # projection 2026-27
    m = G.groupby(["season", "TEAM_ABBREVIATION"]).score.mean().unstack(0)
    c = float(np.mean([np.polyfit(m[a] - m[a].mean(), m[b] - m[b].mean(), 1)[0] for a, b in (("2022-23", "2023-24"), ("2023-24", "2024-25"))]))
    lg = m["2025-26"].mean()
    proj = []
    for team in m.index:
        games = G[(G.season == "2025-26") & (G.TEAM_ABBREVIATION == team)].score.to_numpy()
        pm = lg + c * (m.loc[team, "2025-26"] - lg)
        sh = games - games.mean() + pm
        curve = {n: float(rng.choice(sh, size=(20000, n)).max(axis=1).mean()) for n in range(1, 11)}
        wkp = [curve[min(TG[team].get(x["week"], 0), 10)] if TG[team].get(x["week"], 0) else 0.0 for x in weeks27]
        proj.append(dict(team=team, proj_avg=float(pm), proj_max=float(np.mean(wkp)), week26=float(s26.loc[team, "mean"])))
    P = pd.DataFrame(proj).sort_values("proj_max", ascending=False).reset_index(drop=True)
    vor = {N: dict(avg=float(P.proj_max.head(N).mean() - P.proj_max.iloc[N]), best=float(P.proj_max.iloc[0] - P.proj_max.iloc[N])) for N in (4, 8, 10, 12)}
    res[gl] = dict(week=float(wk.score.mean()), sd=float(wk.score.std()), corr=corr, yoy=yoy, share=share, hit_glass=hit_gl, carry=c,
                   top26=[(k, float(r["mean"])) for k, r in s26.head(5).iterrows()], bottom26=[(k, float(r["mean"])) for k, r in s26.tail(3).iterrows()],
                   proj=P.to_dict("records"), vor=vor)
    print(f"\n{gl}: weekly {res[gl]['week']:.1f} ± {res[gl]['sd']:.1f}; follows defense {corr:.2f}; repeats {yoy:.2f}; glass bonus in {100 * hit_gl:.0f}% of games")
    print("   where the weekly score comes from:", {k.split(" (")[0]: f"{100 * v:.0f}%" for k, v in share.items()})
    print("   '26 top:", [(k, round(x, 1)) for k, x in res[gl]["top26"]], "bottom:", [(k, round(x, 1)) for k, x in res[gl]["bottom26"]])
    print("   2026-27 projected:", [(r.team, round(r.proj_max, 1)) for r in P.head(6).itertuples()], "…", [(r.team, round(r.proj_max, 1)) for r in P.tail(3).itertuples()])
    for N in (4, 8, 12):
        pl = DG[f"gfc|{N}"]["by_slot"]
        print(f"   {N} teams: TEAM avg starter +{vor[N]['avg']:.1f} best +{vor[N]['best']:.1f} | G +{pl['G']['avg_vor']:.1f} F +{pl['F']['avg_vor']:.1f} C +{pl['C']['avg_vor']:.1f}")
print("\nhow often each part pays (per game):", {k.split(" (")[0]: f"{100 * v:.0f}%" for k, v in hit.items()})
json.dump(dict(res=res, hit=hit), open(S + "team_draft4.json", "w"))
