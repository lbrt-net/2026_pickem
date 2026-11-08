"""What makes a bench-tier player (ranked 70–125) a good one-week pickup? (2026-11-08, commissioner)

Raw box scores '22–'26 only (nba-pipeline raw traditional boxes + fantasy points per game). Everything is known at the
end of week W; target = his best game in week W+1 (0 if he didn't play). Baseline = his season points per game, with
the week's game count and his availability (games ~ Binomial(team games, availability), best of k ≈ level + 35%·level·E[max of k]).
Each factor: band player-weeks split into groups, actual next-week score minus the baseline, in fantasy points.

Factors:
  games       his team's games next week
  swing       his own spread of game scores ÷ his average (season so far)
  opp_soft    next week's opponents: fantasy points they've given up per game so far, vs the league (avg over his games)
  freed       minutes a game of teammates (15+ mpg over their last 10) who missed his team's last game for a reason
              other than a coach's decision (injury / not with team / absent) — out going into the week
  freed_pos   same, teammates at his position (starting position he's listed at most)
  star_use    the heaviest-usage teammate's (FGA + 0.44·FTA + TOV) per 36 (20+ mpg teammates)
  own_use     his own (FGA + 0.44·FTA + TOV) per 36
  fouls       his personal fouls per 36
  min_swing   his minutes spread ÷ his average minutes (season so far)
  min_trend   his minutes a game, last 2 weeks minus season
Run: .venv/bin/python scripts/projection_study/pickup_factors.py
"""
import sys
from math import comb

import numpy as np
import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__file__))
import fa_study as f  # noqa: E402

RAW = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/box_scores_traditional/trad_box_scores_{}.parquet"
ALT = {"2021-22": "/Users/allan/PycharmProjects/nba-pipeline/data/box_scores/trad_box_scores_2021_22.parquet",
       "2025-26": "/Users/allan/PycharmProjects/nba-pipeline/data/box_scores/trad_box_scores_2025_26.parquet"}
C = [0, 0, 0.564, 0.846, 1.029, 1.163]


def week_proj(m, sd, n, p):
    n, p = int(n), max(p, 0.05)
    return sum(comb(n, k) * p ** k * (1 - p) ** (n - k) * (m + sd * C[min(k, 5)]) for k in range(1, n + 1))


def mins(x):
    if isinstance(x, str) and ":" in x:
        a, b = x.split(":")[:2]
        try:
            return int(float(a)) + float(b.split("-")[0] or 0) / 60
        except ValueError:
            return 0.0
    try:
        return float(x or 0)
    except ValueError:
        return 0.0


fpg = pd.read_parquet(f.W + "disp_games.parquet")
fpg["GAME_ID"] = fpg.GAME_ID.astype(str)
rows = []
for s in f.SEASONS:
    import os
    path = RAW.format(s.replace("-", "_"))
    if not os.path.exists(path):
        path = ALT[s]
    b = pd.read_parquet(path)
    b["game_id"] = b.game_id.astype(str)
    b["min"] = b.minutes.map(mins)
    g = fpg[fpg.season == s][["GAME_ID", "PLAYER_ID", "date", "fp"]].rename(columns={"GAME_ID": "game_id", "PLAYER_ID": "player_id"})
    dates = g.groupby("game_id").date.first()
    b["date"] = pd.to_datetime(b.game_id.map(dates))
    b = b[b.date.notna()].merge(g[["game_id", "player_id", "fp"]], on=["game_id", "player_id"], how="left")
    b["season"] = s
    rows.append(b[["season", "game_id", "date", "team_tricode", "player_id", "player_name", "position", "comment", "min", "fp",
                   "fga", "fta", "tov", "pf"]])
B = pd.concat(rows, ignore_index=True)
B["fp"] = B.fp.fillna(0)
B["played"] = B["min"] > 0
B["use"] = B.fga + 0.44 * B.fta + B.tov
# each game's two teams → opponent; fantasy points a team gave up in a game = its opponents' players' points
tg = B.groupby(["season", "game_id", "team_tricode"]).agg(date=("date", "first"), fp_for=("fp", "sum")).reset_index()
opp = tg.merge(tg[["season", "game_id", "team_tricode", "fp_for"]], on=["season", "game_id"], suffixes=("", "_o"))
opp = opp[opp.team_tricode != opp.team_tricode_o].rename(columns={"team_tricode_o": "opp", "fp_for_o": "fp_allowed_by_opp"})
# fp_allowed for team T in game = fp_for of the other team
allowed = opp[["season", "game_id", "date", "team_tricode", "opp", "fp_for"]].rename(columns={"team_tricode": "t", "fp_for": "x"})
allowed = allowed.rename(columns={"opp": "team", "x": "fp_allowed"})[["season", "game_id", "date", "team", "fp_allowed"]]

out = []
for s in f.SEASONS:
    x = B[B.season == s].copy()
    monday = x.date.min() - pd.to_timedelta(x.date.min().weekday(), unit="D")
    x["wk"] = (x.date - monday).dt.days // 7
    o = opp[opp.season == s].copy(); o["wk"] = (o.date - monday).dt.days // 7
    a = allowed[allowed.season == s].copy(); a["wk"] = (a.date - monday).dt.days // 7
    tgames = o.groupby(["team_tricode", "wk"]).game_id.nunique()
    last = int(x.wk.max())
    pos_mode = x[x.position.isin(["G", "F", "C"])].groupby("player_id").position.agg(lambda v: v.mode().iat[0])
    for W_ in range(2, last):
        pr = x[x.wk <= W_]
        pl = pr[pr.played]
        g = pl.groupby("player_id").agg(name=("player_name", "last"), team=("team_tricode", "last"), n=("fp", "size"),
                                        pg=("fp", "mean"), sd=("fp", "std"), mpg=("min", "mean"), msd=("min", "std"),
                                        use=("use", "sum"), pf=("pf", "sum"), mt=("min", "sum"))
        g = g[g.n >= 3]
        l4 = pl[pl.wk > W_ - 4].groupby("player_id").size()
        team4 = o[(o.wk > W_ - 4) & (o.wk <= W_)].groupby("team_tricode").game_id.nunique()
        g["avail"] = (l4.reindex(g.index).fillna(0) / g.team.map(team4)).clip(0, 1).fillna(0)
        g["level"] = g.pg * g.avail
        g["rank"] = g.level.rank(ascending=False, method="first")
        g = g[(g["rank"] >= 70) & (g["rank"] <= 125)].copy()
        g["games"] = [tgames.get((t, W_ + 1), 0) for t in g.team]
        g = g[g.games > 0]
        if g.empty:
            continue
        nxt = x[(x.wk == W_ + 1) & x.played].groupby("player_id").fp.max()
        g["target"] = nxt.reindex(g.index).fillna(0)
        g["base"] = [week_proj(m, .35 * m, n, p) for m, n, p in zip(g.pg, g.games, g.avail)]
        g["swing"] = g.sd / g.pg
        # opponents next week, their FP allowed per game so far vs league
        ap = a[a.wk <= W_].groupby("team").fp_allowed.mean()
        lg = a[a.wk <= W_].fp_allowed.mean()
        nx = o[o.wk == W_ + 1].groupby("team_tricode").opp.apply(list)
        g["opp_soft"] = [np.mean([ap.get(t2, lg) - lg for t2 in nx.get(t, [])]) if nx.get(t) is not None else 0 for t in g.team]
        # a week = his best game: the softest opponent he gets, and how many soft games (opponent in the softest third)
        cut = ap.quantile(2 / 3) - lg
        g["opp_best"] = [max([ap.get(t2, lg) - lg for t2 in nx.get(t, [])]) if nx.get(t) is not None else 0 for t in g.team]
        g["opp_worst"] = [min([ap.get(t2, lg) - lg for t2 in nx.get(t, [])]) if nx.get(t) is not None else 0 for t in g.team]
        g["n_soft"] = [sum(ap.get(t2, lg) - lg >= cut for t2 in nx.get(t, [])) if nx.get(t) is not None else 0 for t in g.team]
        # teammates out going into the week: missed the team's last game (not a coach's decision), 15+ mpg over last 10
        lastg = pr.groupby("team_tricode").date.max()
        recent = pl.sort_values("date").groupby("player_id").tail(10).groupby("player_id").agg(m10=("min", "mean"), team=("team_tricode", "last"))
        lastday = pr[pr.date == pr.team_tricode.map(lastg)]
        played_last = set(lastday[lastday.played].player_id)
        coach = set(lastday[lastday.comment.str.contains("Coach", na=False)].player_id)
        # fresh: he played in one of his team's 3 games before the last one (long absences and trades are already in the
        # numbers; a player who left the team isn't freeing anything new)
        tdates = pr.drop_duplicates(["team_tricode", "date"]).sort_values("date").groupby("team_tricode").date.apply(lambda d: d.iloc[-4:-1].min() if len(d) > 1 else d.iloc[0])
        lastplay = pl.groupby("player_id").date.max()
        recent = recent[lastplay.reindex(recent.index) >= recent.team.map(tdates)]
        out_ = recent[(recent.m10 >= 15) & ~recent.index.isin(played_last) & ~recent.index.isin(coach)].copy()
        out_["pos"] = out_.index.map(pos_mode)
        fr = out_.groupby("team").m10.sum()
        own_out = out_.m10.reindex(g.index).fillna(0)          # never count his own minutes as freed
        g["self_out"] = own_out > 0
        g["freed"] = g.team.map(fr).fillna(0) - own_out
        g["pos"] = g.index.map(pos_mode)
        frp = out_.groupby(["team", "pos"]).m10.sum()
        g["freed_pos"] = [frp.get((t, p_), 0) if isinstance(p_, str) else 0 for t, p_ in zip(g.team, g.pos)] - own_out.where(g.pos.notna(), 0)
        # usage: own, and the heaviest 20+ mpg teammate (current team)
        u = pl.groupby("player_id").agg(use=("use", "sum"), mt=("min", "sum"), team=("team_tricode", "last"))
        u["u36"] = u.use / u.mt * 36
        heavy = u[(u.mt / pl.groupby("player_id").size().reindex(u.index)) >= 20]
        g["own_use"] = g.use / g.mt * 36
        g["star_use"] = [heavy[(heavy.team == t) & (heavy.index != pid)].u36.max() for pid, t in zip(g.index, g.team)]
        g["fouls"] = g.pf / g.mt * 36
        g["min_swing"] = g.msd / g.mpg
        l2 = pl[pl.wk > W_ - 2].groupby("player_id")["min"].mean()
        g["min_trend"] = l2.reindex(g.index) - g.mpg
        g["season"], g["W"] = s, W_
        out.append(g)
R = pd.concat(out)
R["resid"] = R.target - R.base
R.to_csv(f.W + "pickup_factors.csv")
print(f"{len(R)} player-weeks, {R.groupby(['season', 'W']).ngroups} weeks; baseline average {R.base.mean():.1f}, actual {R.target.mean():.1f}")


def split(col, bins=None, labels=None, q=5):
    t = R.dropna(subset=[col]).copy()
    t["grp"] = pd.cut(t[col], bins, labels=labels) if bins is not None else pd.qcut(t[col].rank(method="first"), q, labels=[f"{i + 1}" for i in range(q)])
    rng = t.groupby("grp", observed=True)[col].agg(["min", "max"])
    r = t.groupby("grp", observed=True).agg(n=("resid", "size"), actual=("target", "mean"), base=("base", "mean"), resid=("resid", "mean"))
    e = t[t.W <= 5].groupby("grp", observed=True).resid.mean().rename("early")
    r = r.join(rng).join(e)
    print(f"\n== {col} ==")
    print(r.round(2).to_string())


split("games", [0, 1, 2, 3, 4, 9], ["1", "2", "3", "4", "5"])
R["self_out_n"] = R.self_out.astype(int)
split("self_out_n", [-1, 0, 1], ["played last game", "missed it (not coach)"])
R = R[~R.self_out]   # the rest: players who played their team's last game
split("swing")
split("opp_soft", q=10)
split("opp_best", q=10)
split("opp_worst", q=5)
split("n_soft", [-1, 0, 1, 2, 9], ["0", "1", "2", "3+"])
split("freed", [-1, 0, 25, 45, 300], ["none", "≤25", "25–45", "45+"])
split("freed_pos", [-1, 0, 25, 300], ["none", "≤25", "25+"])
split("star_use")
split("own_use")
split("fouls")
split("min_swing")
split("min_trend")
