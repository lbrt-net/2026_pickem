"""TEAM draft 6 game scores on 2025-26 as one long text sparkline per team, weeks divided by '|', for TEAM_SCORING.md.
'·' = a zero game; ▁▂▃▄▅▆▇█ = score in eighths of 40+ (each bar step = 5 points)."""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem")
from backend.fantasy_2026_27.weeks import build_weeks, week_for  # noqa: E402

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
D = pd.read_parquet(S + "team_full.parquet")
VF = pd.read_parquet(S + "team_viol_forced.parquet")[["GAME_ID", "TEAM_ABBREVIATION", "SHOT_CLOCK", "EIGHT_SEC", "FIVE_SEC"]]
g = D[D.season == "2025-26"].merge(VF, on=["GAME_ID", "TEAM_ABBREVIATION"], how="left")
g["score"] = (2 * ((125 - g.OPP_PTS).clip(lower=0) // 5) + 10 * (g.OPP_PTS < 100) + 2 * g.SHOT_CLOCK
              + 5 * (g.OPP_PTS_FB <= 9) + 10 * (g.OPP_PTS_PAINT < 30) + 10 * (g.OPP_TOV >= 20) + 5 * ((g.DREB - g.OPP_DREB) >= 10))
weeks = build_weeks(set(g.GAME_DATE.dt.date), [])
g["week"] = [(w["week"] if (w := week_for(weeks, x)) else None) for x in g.GAME_DATE.dt.date]
g = g.dropna(subset=["week"]).sort_values("GAME_DATE")
BARS = "▁▂▃▄▅▆▇█"


def ch(v):
    if v <= 0:
        return "·"
    return BARS[min(int(v / 40 * 8), 7)]


wk_best = g.groupby(["TEAM_ABBREVIATION", "week"]).score.max()
order = wk_best.groupby(level=0).mean().sort_values(ascending=False).index
lines = []
for t in order:
    q = g[g.TEAM_ABBREVIATION == t]
    parts = ["".join(ch(v) for v in q[q.week == w["week"]].score) for w in weeks]
    zero = (q.score <= 0).mean()
    lines.append(f"{t} {wk_best.loc[t].mean():4.1f} {100 * zero:3.0f}% |" + "|".join(parts) + "|")
head = f"Team, average weekly score, share of games at 0, then every game Oct → Mar ('|' = new fantasy week; {len(weeks)} weeks)"
print(head)
print("\n".join(lines[:3]))
open(S + "team_timeline.txt", "w").write("\n".join(lines))
g[["TEAM_ABBREVIATION", "GAME_DATE", "week", "score", "OPP_PTS", "MATCHUP"]].to_parquet(S + "team_timeline_games.parquet")
import json
json.dump(dict(order=list(order), weeks=[dict(week=w["week"], start=w["start"].isoformat(), end=w["end"].isoformat(), label=w["label"]) for w in weeks],
               avg={t: float(wk_best.loc[t].mean()) for t in order}, zero={t: float((g[g.TEAM_ABBREVIATION == t].score <= 0).mean()) for t in order}),
          open(S + "team_timeline_meta.json", "w"))
zero_all = (g.score <= 0).mean()
wk0 = (wk_best <= 0).mean()
print(f"league: {100 * zero_all:.0f}% of games score 0; {100 * wk0:.1f}% of weeks (best game) score 0")
