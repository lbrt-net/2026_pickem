"""Team defense from its roster: does player continuity, age and rookie minutes explain how a TEAM's score carries over?

Per team-season (TEAM scoring = the app's current team rules, per game):
  continuity — share of the season's minutes played by players who were on that team the season before
  age        — minutes-weighted age (bios); also its change from last season
  rookies    — share of minutes played by first-year players
Model: next season's per-game score = a + b × last season's score + effects of the above. Fit on '23→'24 and
'24→'25, checked once on '25→'26 against the current carryover model (last season pulled toward the league).
2026-27: the same three numbers from the 2026-27 rosters and projected minutes. Writes WORK/team_roster.json.
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import INPUTS, R, TEAM, W, scoring  # noqa: E402

SEAS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]


def J(kind, s):
    rs = json.load(open(f"{R}{kind}/{s}.json"))["resultSets"]
    rs = rs[0] if isinstance(rs, list) else rs
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"])


# team TEAM score per game, per season
D = pd.read_parquet(INPUTS + "team_full.parquet").merge(
    pd.read_parquet(INPUTS + "team_viol_forced.parquet")[["GAME_ID", "TEAM_ABBREVIATION", "SHOT_CLOCK"]], on=["GAME_ID", "TEAM_ABBREVIATION"], how="left")


def line(r):
    x = {"shot_clock_forced": r.SHOT_CLOCK, "fb_pts_allowed": r.OPP_PTS_FB, "paint_pts_allowed": r.OPP_PTS_PAINT,
         "tov_forced": r.OPP_TOV, "dreb_margin": r.DREB - r.OPP_DREB}
    return scoring.team_line(r.PTS, r.OPP_PTS, {k: v for k, v in x.items() if pd.notna(v)})


D["s"] = [scoring.points(TEAM, line(r)) for r in D.itertuples()]
SCORE = D.groupby(["season", "TEAM_ABBREVIATION"]).agg(score=("s", "mean"), drtg=("DEF_RATING", "mean")).reset_index()

# player minutes by team-season, ages, first season
L = pd.concat(J("game_logs", s).assign(season=s) for s in SEAS)
MIN = L.groupby(["season", "TEAM_ABBREVIATION", "PLAYER_ID"]).MIN.sum().reset_index()
BIO = pd.concat(J("bios", s).assign(season=s) for s in SEAS)[["season", "PLAYER_ID", "AGE", "DRAFT_YEAR"]]
MIN = MIN.merge(BIO, on=["season", "PLAYER_ID"], how="left")
first = L.groupby("PLAYER_ID").season.min()
MIN["rookie"] = MIN.PLAYER_ID.map(first).eq(MIN.season) & (MIN.season != SEAS[0]) & (MIN.DRAFT_YEAR.astype(str) == MIN.season.str[:4])


def roster_feats(m, prev_ids):
    w = m.MIN / m.MIN.sum()
    return dict(continuity=float(w[m.PLAYER_ID.isin(prev_ids)].sum()), age=float(np.nansum(w * m.AGE) / w[m.AGE.notna()].sum()),
                rookies=float(w[m.rookie].sum()))


rows = []
for i, s in enumerate(SEAS[1:], 1):
    for t, m in MIN[MIN.season == s].groupby("TEAM_ABBREVIATION"):
        prev = set(MIN[(MIN.season == SEAS[i - 1]) & (MIN.TEAM_ABBREVIATION == t)].PLAYER_ID)
        rows.append(dict(season=s, team=t, **roster_feats(m, prev)))
F = pd.DataFrame(rows).merge(SCORE, left_on=["season", "team"], right_on=["season", "TEAM_ABBREVIATION"]).drop(columns="TEAM_ABBREVIATION")
F = F.sort_values(["team", "season"])
F["prev_score"] = F.groupby("team").score.shift()
F["prev_age"] = F.groupby("team").age.shift()
F["d_age"] = F.age - F.prev_age
F = F.dropna(subset=["prev_score"])
LG = F.groupby("season").score.transform("mean")
F["prev_dev"] = F.prev_score - F.groupby("season").prev_score.transform("mean")
F["y"] = F.score - LG                               # next season vs league

FIT, HOLD = F[F.season.isin(["2023-24", "2024-25"])], F[F.season == "2025-26"]


def design(X, cols):
    return np.column_stack([np.ones(len(X))] + [X[c].to_numpy() for c in cols])


def ols(cols):
    b, *_ = np.linalg.lstsq(design(FIT, cols), FIT.y.to_numpy(), rcond=None)
    pred = design(HOLD, cols) @ b
    return b, float(np.sqrt(np.mean((pred - HOLD.y) ** 2)))


if __name__ == "__main__":
    pd.set_option("display.width", 160)
    print(f"team-seasons: fit {len(FIT)}, check {len(HOLD)}; per-game TEAM score sd across teams {F.score.std():.1f}\n")
    print("how a team's score carries over, by roster continuity (fit seasons):")
    for lo, hi in ((0, 0.5), (0.5, 0.7), (0.7, 1.01)):
        q = FIT[(FIT.continuity >= lo) & (FIT.continuity < hi)]
        if len(q) > 5:
            print(f"  {int(lo * 100)}–{int(min(hi, 1) * 100)}% minutes returning: {len(q)} teams, carryover {np.polyfit(q.prev_dev, q.y, 1)[0]:.2f}")
    base = float(np.sqrt(np.mean((0.6 * HOLD.prev_dev - HOLD.y) ** 2)))
    print(f"\nchecked on '25→'26 (miss in points per game, RMSE):\n  current model (last season × 0.6): {base:.2f}")
    FIT = FIT.assign(cont_x=FIT.prev_dev * FIT.continuity); HOLD = HOLD.assign(cont_x=HOLD.prev_dev * HOLD.continuity)
    for name, cols in [("last season only", ["prev_dev"]),
                       ("+ continuity (carryover scales with minutes returning)", ["prev_dev", "cont_x"]),
                       ("+ age change", ["prev_dev", "cont_x", "d_age"]),
                       ("+ age level", ["prev_dev", "cont_x", "d_age", "age"]),
                       ("+ rookie minutes", ["prev_dev", "cont_x", "d_age", "age", "rookies"])]:
        b, e = ols(cols)
        print(f"  {name:<56} {e:.2f}   coefficients " + ", ".join(f"{c} {v:+.2f}" for c, v in zip(["const"] + cols, b)))
    print("\ncorrelations with next season vs league (fit seasons):",
          {c: round(float(FIT[c].corr(FIT.y)), 2) for c in ("prev_dev", "continuity", "age", "d_age", "rookies")})
