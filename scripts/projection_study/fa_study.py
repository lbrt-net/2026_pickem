"""Free-agent advisor study (2026-10-11, commissioner's spec).

League: 12 teams; the top 72 players and top 12 NBA teams (by last season's average weekly score) are drafted; rosters
never change. Every week, everyone else is a free agent. Week = Mon–Sun, score = best game (0 if no game).

1. Which formula best predicts a free agent's NEXT-week score? Candidate parts (all known at the end of week W):
   windows of recent weekly scores (1, 2, 3, 4, 6, 8 weeks, season), last season's average, minutes (recent vs
   season — a role change), points per minute × recent minutes, availability (share of his team's games played in
   the last 4 weeks), and next week's game count. Simple formulas are compared head to head, then a linear model
   fit on '22–'25 and checked on '26 says which parts carry weight.
2. How much data helps: next-week accuracy by window length.
3. Who is predictable: accuracy by player type (minutes, games so far, steadiness).
4. How many teams benefit: rosters drafted snake from the 72 by last season; each team starts its 4 best players by
   the same formula (players are position-free here) + its NBA team. A team benefits from the advice if the top
   recommended free agent would actually have outscored its weakest starter next week.
Run: .venv/bin/python scripts/projection_study/fa_study.py   (prints the tables; writes fa_study_*.csv)
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import INPUTS, TEAM, W, scoring  # noqa: E402

TEAMS, PER = 12, 6


def rcorr(a, b):
    """Spearman rank correlation without scipy."""
    return pd.Series(a).rank().corr(pd.Series(b).rank())
SEASONS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
ALL = ["2020-21"] + SEASONS


def player_weeks():
    g = pd.read_parquet(W + "disp_games.parquet")
    g["date"] = pd.to_datetime(g["date"])
    out = []
    for s in ALL:
        x = g[g.season == s].copy()
        monday = x.date.min() - pd.to_timedelta(x.date.min().weekday(), unit="D")
        x["wk"] = (x.date - monday).dt.days // 7
        team_g = x.groupby(["TEAM_ABBREVIATION", "wk"]).GAME_ID.nunique().rename("team_games")
        p = x[x.MIN > 0].groupby(["PLAYER_ID", "wk"]).agg(score=("fp", "max"), games=("fp", "size"), fp_sum=("fp", "sum"),
                                                         mins=("MIN", "sum"), team=("TEAM_ABBREVIATION", "last"),
                                                         name=("PLAYER_NAME", "last")).reset_index()
        p = p.join(team_g, on=["team", "wk"])
        p["season"] = s
        tg = team_g.reset_index()
        tg["season"] = s
        out.append((p, tg))
    return pd.concat([o[0] for o in out]), pd.concat([o[1] for o in out])


def team_weeks():
    d = pd.read_parquet(INPUTS + "team_full.parquet")
    d["GAME_DATE"] = pd.to_datetime(d["GAME_DATE"])
    rows = []
    for r in d.itertuples():
        x = {"fb_pts_allowed": r.OPP_PTS_FB, "paint_pts_allowed": r.OPP_PTS_PAINT, "tov_forced": r.OPP_TOV,
             "dreb_margin": r.DREB - r.OPP_DREB, "shot_clock_forced": getattr(r, "SC_FORCED", None)}
        line = scoring.team_line(r.PTS, r.OPP_PTS, {k: v for k, v in x.items() if pd.notna(v)})
        rows.append((r.season, r.TEAM_ABBREVIATION, r.GAME_DATE, scoring.points(TEAM, line)))
    t = pd.DataFrame(rows, columns=["season", "team", "date", "fp"])
    out = []
    for s, x in t.groupby("season"):
        monday = x.date.min() - pd.to_timedelta(x.date.min().weekday(), unit="D")
        x = x.assign(wk=(x.date - monday).dt.days // 7)
        out.append(x.groupby(["team", "wk"]).agg(score=("fp", "max"), games=("fp", "size")).reset_index().assign(season=s))
    return pd.concat(out)


def features(pw, season, W_):
    """Every player's features at the end of week W (this season's weeks ≤ W) + target (week W+1)."""
    cur = pw[(pw.season == season) & (pw.wk <= W_)]
    prev = pw[pw.season == ALL[ALL.index(season) - 1]]
    f = cur.groupby("PLAYER_ID").agg(name=("name", "last"), team=("team", "last"), weeks=("wk", "nunique"),
                                     g=("games", "sum"), fp=("fp_sum", "sum"), mins=("mins", "sum"))
    f["season_pg"] = f.fp / f.g
    f["season_wk"] = cur.groupby("PLAYER_ID").score.mean()
    for k in (1, 2, 3, 4, 6, 8):
        win = cur[cur.wk > W_ - k]
        f[f"wk{k}"] = win.groupby("PLAYER_ID").score.sum().reindex(f.index).fillna(0) / k   # missed weeks count 0
        f[f"pg{k}"] = (win.groupby("PLAYER_ID").fp_sum.sum() / win.groupby("PLAYER_ID").games.sum()).reindex(f.index)
    w2 = cur[cur.wk > W_ - 2]
    f["min_season"] = f.mins / f.g
    f["min2"] = (w2.groupby("PLAYER_ID").mins.sum() / w2.groupby("PLAYER_ID").games.sum()).reindex(f.index)
    f["fpm_x_min2"] = (f.fp / f.mins) * f.min2
    f["role_change"] = f.min2 - f.min_season
    last4 = cur[cur.wk > W_ - 4]
    tg4 = last4.groupby("team").team_games.first()  # approximate: team games in the last week seen
    team4 = pw[(pw.season == season) & (pw.wk > W_ - 4) & (pw.wk <= W_)].groupby(["team", "wk"]).team_games.first().groupby("team").sum()
    f["avail"] = (last4.groupby("PLAYER_ID").games.sum().reindex(f.index).fillna(0) / f.team.map(team4)).clip(0, 1).fillna(0)
    f["prior_wk"] = prev.groupby("PLAYER_ID").score.mean().reindex(f.index)
    nxt_team = pw[(pw.season == season) & (pw.wk == W_ + 1)].groupby("team").team_games.first()
    f["next_games"] = f.team.map(nxt_team).fillna(0)
    nxt = pw[(pw.season == season) & (pw.wk == W_ + 1)].set_index("PLAYER_ID").score
    f["target"] = nxt.reindex(f.index).fillna(0)
    return f


def drafted(pw, season):
    prev = pw[pw.season == ALL[ALL.index(season) - 1]]
    v = prev.groupby("PLAYER_ID").agg(m=("score", "mean"), n=("wk", "nunique"))
    return list(v[v.n >= 10].m.nlargest(TEAMS * PER).index)


FORMULAS = {
    "last week": lambda f: f.wk1,
    "last 2 weeks": lambda f: f.wk2,
    "last 4 weeks": lambda f: f.wk4,
    "last 8 weeks": lambda f: f.wk8,
    "season (weeks played)": lambda f: f.season_wk,
    "season per game × availability": lambda f: f.season_pg * f.avail,
    "pts/min × last-2-wk minutes × availability": lambda f: f.fpm_x_min2.fillna(0) * f.avail,
    "blend: 4 wks + season + last season": lambda f: (0.45 * f.wk4 + 0.35 * f.season_wk.fillna(0)
                                                     + 0.20 * f.prior_wk.fillna(f.season_wk).fillna(0)),
}


def main():
    pw, _ = player_weeks()
    rows, feats = [], []
    for season in SEASONS:
        taken = set(drafted(pw, season))
        last = pw[pw.season == season].wk.max()
        for W_ in range(3, last - 1):
            f = features(pw, season, W_)
            fa = f[~f.index.isin(taken) & (f.g >= 3)].copy()
            fa["season"], fa["week"] = season, W_ + 1
            feats.append(fa)
            best = fa.target.nlargest(10).mean()
            for name, fn in FORMULAS.items():
                top = fn(fa).fillna(0).nlargest(10).index
                rows.append({"season": season, "week": W_ + 1, "formula": name, "top10": fa.loc[top, "target"].mean(),
                             "best": best, "rc": rcorr(fn(fa).fillna(0), fa.target)})
    r = pd.DataFrame(rows)
    F = pd.concat(feats)
    F.to_csv(W + "fa_study_features.csv")
    r.to_csv(W + "fa_study_formulas.csv", index=False)

    print("\n1) FORMULAS — avg next-week score of the top-10 free-agent picks (best possible in brackets)")
    t = r.groupby(["formula", "season"]).top10.mean().unstack().round(1)
    t["all"] = r.groupby("formula").top10.mean().round(1)
    t["weeks won"] = r.loc[r.groupby(["season", "week"]).top10.idxmax()].formula.value_counts().reindex(t.index).fillna(0).astype(int)
    t["rank corr"] = r.groupby("formula")["rc"].mean().round(3)
    print(t.sort_values("all", ascending=False).to_string())
    print("   best possible:", r.groupby("season").best.mean().round(1).to_dict())

    # linear model: fit '22–'25, test '26 — which parts carry weight
    cols = ["wk1", "wk2", "wk4", "wk8", "season_wk", "prior_wk", "fpm_x_min2", "role_change", "avail", "next_games", "min2"]
    X = F[cols].fillna(0)
    X = (X - X.mean()) / X.std()
    tr, te = F.season != "2025-26", F.season == "2025-26"
    A = np.c_[np.ones(tr.sum()), X[tr].values]
    coef = np.linalg.lstsq(A.T @ A + 5 * np.eye(A.shape[1]), A.T @ F.target[tr].values, rcond=None)[0]
    print("\n2) WHAT CARRIES WEIGHT — standardized linear-model weights (fit '22–'25):")
    for c, w in sorted(zip(cols, coef[1:]), key=lambda kv: -abs(kv[1])):
        print(f"   {c:12s} {w:+.2f}")
    pred = np.c_[np.ones(te.sum()), X[te].values] @ coef
    Ft = F[te].assign(pred=pred)
    lm = Ft.groupby("week").apply(lambda d: d.loc[d.pred.nlargest(10).index, "target"].mean()).mean()
    print(f"   model on '26 holdout: top-10 picks avg {lm:.1f} vs best formula {r[r.season == '2025-26'].groupby('formula').top10.mean().max():.1f}")

    print("\n3) HOW MUCH DATA — rank correlation with next week, by window (higher = better):")
    for k in ("wk1", "wk2", "wk4", "wk8", "season_wk"):
        print(f"   {k:10s} {F.groupby(['season','week']).apply(lambda d: rcorr(d[k], d.target)).mean():.3f}")

    print("\n4) WHO IS PREDICTABLE — avg miss (|actual − 4-week avg|) by player type:")
    F["miss"] = (F.target - F.wk4).abs()
    F["min_band"] = pd.cut(F.min_season, [0, 15, 22, 28, 48], labels=["<15 min", "15–22", "22–28", "28+"])
    F["sample"] = pd.cut(F.g, [0, 8, 20, 99], labels=["≤8 games", "9–20", "21+"])
    for c in ("min_band", "sample"):
        print("  ", F.groupby(c, observed=True).agg(miss=("miss", "mean"), level=("wk4", "mean"), n=("miss", "size")).round(1).to_string().replace("\n", "\n   "))
    return pw, F, r


if __name__ == "__main__":
    main()


def benefit():
    """How many of the 12 teams gain from the advice each week (no transactions ever: the draft rosters all season).
    Players: snake draft of the 72 by last season; each team starts its 4 best by the winning formula. A team gains if
    the advisor's #1 free agent actually outscored its weakest starter next week. NBA teams: a team gains if the #1
    free-agent NBA team outscored its own NBA team."""
    pw, _ = player_weeks()
    fn = FORMULAS["season per game × availability"]
    rows = []
    for season in SEASONS:
        order = drafted(pw, season)
        rosters = [[] for _ in range(TEAMS)]
        for i, pid in enumerate(order):
            rnd, k = divmod(i, TEAMS)
            rosters[k if rnd % 2 == 0 else TEAMS - 1 - k].append(pid)
        taken = set(order)
        last = pw[pw.season == season].wk.max()
        for W_ in range(3, last - 1):
            f = features(pw, season, W_)
            f["v"] = fn(f).fillna(0)
            fa = f[~f.index.isin(taken) & (f.g >= 3)]
            if fa.empty:
                continue
            best_fa = fa.v.idxmax()
            gain = 0
            for r in rosters:
                mine = f.reindex(r).dropna(subset=["v"])
                starters = mine.nlargest(4, "v")
                if len(starters) and f.target.get(best_fa, 0) > starters.target.min():
                    gain += 1
            top3 = fa.v.nlargest(3).index
            gain3 = sum(1 for r in rosters if len(f.reindex(r).dropna(subset=["v"]).nlargest(4, "v"))
                        and f.loc[top3, "target"].mean() > f.reindex(r).dropna(subset=["v"]).nlargest(4, "v").target.min())
            rows.append({"season": season, "week": W_ + 1, "gain_top1": gain, "gain_top3avg": gain3})
    b = pd.DataFrame(rows)
    print("\n5) PLAYERS — teams (of 12) whose weakest starter the advice beat next week:")
    print("  ", b.groupby("season")[["gain_top1", "gain_top3avg"]].mean().round(1).to_string().replace("\n", "\n   "))
    print(f"   all seasons: #1 pick beats the weakest starter on {b.gain_top1.mean():.1f} of 12 teams a week; the top-3 picks' average on {b.gain_top3avg.mean():.1f}")

    tw = team_weeks()
    trows = []
    for season in ["2023-24", "2024-25", "2025-26"]:
        prev = tw[tw.season == ["2022-23", "2023-24", "2024-25"][["2023-24", "2024-25", "2025-26"].index(season)]]
        own = list(prev.groupby("team").score.mean().nlargest(TEAMS).index)
        cur = tw[tw.season == season]
        for W_ in range(3, cur.wk.max() - 1):
            past = cur[cur.wk <= W_]
            v = past.groupby("team").score.mean()
            nxt = cur[cur.wk == W_ + 1].set_index("team").score
            fa = v.drop(own, errors="ignore")
            best = fa.idxmax()
            trows.append({"season": season, "week": W_ + 1,
                          "gain": sum(1 for t in own if nxt.get(best, 0) > nxt.get(t, 0))})
    t = pd.DataFrame(trows)
    print("\n6) NBA TEAMS — teams (of 12) whose NBA team the #1 free-agent NBA team outscored next week:")
    print("  ", t.groupby("season").gain.mean().round(1).to_string().replace("\n", "\n   "))
    print(f"   all: {t.gain.mean():.1f} of 12 a week")
