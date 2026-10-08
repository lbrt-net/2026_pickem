"""Availability for the 2026-27 projections (AVAILABILITY.md): how many games a player plays, and how missed games
fall across fantasy weeks. Used for PROJ MAX only (PROJ AVG is per game played and doesn't change).

Season-ending injuries are left out on purpose (commissioner, 2026-10-08): any run of SEASON_ENDING+ straight team
games missed, and any season missed entirely, is removed from his history and from the outcomes the model is fit on.
So the projection is "games he plays if no season-ending injury hits": higher than a pure expected value, by design.

1. Expected games. Per season: games played ÷ the team games that count (his team's games, minus long-injury runs).
   His last three seasons' rate goes through a durability curve fit separately for 1, 2 and 3 seasons of history
   (monotone fit of next season's rate on the history rate; rotation players, 20+ minutes when they play; targets
   '23–'25, '26 kept for the check). A long clean record is trusted; one great season isn't. No history: rotation
   players of a similar build (height, weight).
2. How misses fall: clustered. Zero-game week share = (share of games missed)^ZERO_POWER (fit on '23–'26 rotation
   player-weeks, long-injury weeks removed); in the other weeks he plays each game with q = (1 − missed) ÷ (1 − zero).

Writes nba-pipeline data/raw/availability_2026_27.json: player id → {games, missed, zero, q}.
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import R  # noqa: E402

SEAS = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
SEASON_ENDING = 25           # straight team games missed that count as a season-ending (left-out) injury
MIN_COUNTED = 20             # a season needs this many counted team games to be history
NB = 40                      # neighbours for the build prior


def J(kind, s):
    rs = json.load(open(f"{R}{kind}/{s}.json"))["resultSets"]
    rs = rs[0] if isinstance(rs, list) else rs
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"])


L = pd.concat(J("game_logs", s).assign(season=s) for s in SEAS)
L["GAME_DATE"] = pd.to_datetime(L.GAME_DATE)
TEAMG = L.drop_duplicates(["season", "TEAM_ID", "GAME_ID"])[["season", "TEAM_ID", "GAME_ID", "GAME_DATE"]].sort_values("GAME_DATE")
P = L[L.MIN > 0]
names = P.groupby("PLAYER_ID").PLAYER_NAME.last()
bio = pd.concat(J("bios", s).assign(season=s) for s in SEAS).sort_values("season").groupby("PLAYER_ID").last()
bio["PLAYER_WEIGHT"] = pd.to_numeric(bio.PLAYER_WEIGHT, errors="coerce")
r27 = set(pd.read_csv(R + "rosters/2026-27.csv").PLAYER_ID.astype(int))
mpg = P.groupby("PLAYER_ID").MIN.mean()


def season_line(pid, s, g, prev_played):
    """(games played, counted team games, played-flags in team-game order) for one player-season. His team's games
    from the season start (if he played the season before) or his first game, to the season end; a trade switches
    to the new team's games from his first game there."""
    stints = g.sort_values("GAME_DATE").groupby("TEAM_ID", sort=False).GAME_DATE.agg(["min", "max"]).sort_values("min")
    flags = []
    played = set(g.GAME_ID)
    teams = list(stints.index)
    for j, (tid, st) in enumerate(stints.iterrows()):
        tg = TEAMG[(TEAMG.season == s) & (TEAMG.TEAM_ID == tid)]
        start = tg.GAME_DATE.min() if (j == 0 and prev_played) else st["min"]
        end = stints["min"].iloc[j + 1] if j + 1 < len(teams) else tg.GAME_DATE.max()
        span = tg[(tg.GAME_DATE >= start) & ((tg.GAME_DATE < end) if j + 1 < len(teams) else (tg.GAME_DATE <= end))]
        flags += [gid in played for gid in span.GAME_ID]
    return flags


def counted(flags):
    """games played, team games that count (runs of SEASON_ENDING+ straight misses removed)"""
    n_out, run = 0, 0
    for f in flags + [True]:
        if not f:
            run += 1
        else:
            if run >= SEASON_ENDING:
                n_out += run
            run = 0
    return sum(flags), len(flags) - n_out


rows = []
for pid, g in P.groupby("PLAYER_ID"):
    seasons = set(g.season)
    for s in SEAS:
        if s not in seasons:
            continue  # a season missed entirely is a season-ending injury: left out
        i = SEAS.index(s)
        gp, tgc = counted(season_line(pid, s, g[g.season == s], i > 0 and SEAS[i - 1] in seasons))
        rows.append(dict(pid=pid, season=s, gp=gp, tg=tgc))
D = pd.DataFrame(rows)
D = D[D.tg >= MIN_COUNTED]
D["rate"] = (D.gp / D.tg).clip(upper=1)
D["rot"] = D.pid.map(mpg) >= 20


def history(pid, upto):
    """(rate, seasons) over his last three counted seasons before index `upto`"""
    h = D[(D.pid == pid) & D.season.isin(SEAS[max(0, upto - 3):upto])]
    return (float(h.gp.sum() / h.tg.sum()), len(h)) if len(h) else (None, 0)


def pav(x, y):
    o = np.argsort(x)
    blocks = [[float(v), 1, [float(xx)]] for xx, v in zip(np.asarray(x)[o], np.asarray(y)[o])]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] > blocks[i + 1][0]:
            a, b = blocks[i], blocks[i + 1]
            blocks[i] = [(a[0] * a[1] + b[0] * b[1]) / (a[1] + b[1]), a[1] + b[1], a[2] + b[2]]
            del blocks[i + 1]
            i = max(i - 1, 0)
        else:
            i += 1
    return np.array([np.mean(b[2]) for b in blocks]), np.array([b[0] for b in blocks])


def fit_curves(targets):
    pairs = {1: [], 2: [], 3: []}
    for r in D[D.rot & D.season.isin(targets)].itertuples():
        h, n = history(r.pid, SEAS.index(r.season))
        if n:
            pairs[n].append((h, r.rate))
    return {n: pav([a for a, _ in p], [b for _, b in p]) for n, p in pairs.items() if p}


CURVES = fit_curves(SEAS[2:5])


def curve(rate, n):
    kx, ky = CURVES[min(n, 3)]
    return float(np.interp(rate, kx, ky))


base = D[D.rot].join(bio[["PLAYER_HEIGHT_INCHES", "PLAYER_WEIGHT"]], on="pid").dropna(subset=["PLAYER_HEIGHT_INCHES", "PLAYER_WEIGHT"])
SD = base[["PLAYER_HEIGHT_INCHES", "PLAYER_WEIGHT"]].std().values


def build_rate(pid):
    ht, wt = bio.PLAYER_HEIGHT_INCHES.get(pid, np.nan), bio.PLAYER_WEIGHT.get(pid, np.nan)
    b = base[base.pid != pid]
    if ht != ht or wt != wt:
        return float(b.gp.sum() / b.tg.sum()), b
    near = b.assign(d=(((b[["PLAYER_HEIGHT_INCHES", "PLAYER_WEIGHT"]] - [ht, wt]) / SD) ** 2).sum(axis=1)).nsmallest(NB, "d")
    return float(near.gp.sum() / near.tg.sum()), near


def zero_power():
    """zero-game week share = missed^p, fit on '23–'26 rotation player-weeks with long-injury runs removed"""
    X = pd.read_csv(R.replace("raw/", "derived/projections_2026_27/") + "avail_weeks.csv")
    X = X.sort_values(["pid", "season", "week"])
    # drop runs of 7+ straight zero weeks (≈ SEASON_ENDING games)
    keep = []
    for _, g in X.groupby(["pid", "season"]):
        z = (g.played == 0).to_numpy()
        k = np.ones(len(z), bool)
        i = 0
        while i < len(z):
            if z[i]:
                j = i
                while j < len(z) and z[j]:
                    j += 1
                if j - i >= 7:
                    k[i:j] = False
                i = j
            else:
                i += 1
        keep.append(g[k])
    X = pd.concat(keep)
    sr = X.groupby(["season", "pid"]).agg(p=("played", "sum"), n=("tg", "sum"))
    X = X.join((1 - sr.p / sr.n).rename("m"), on=["season", "pid"])
    g = X.groupby(pd.cut(X.m, np.arange(0, 1.01, 0.05)), observed=True).agg(m=("m", "mean"), z=("played", lambda v: (v == 0).mean()), n=("m", "size"))
    g = g[g.n >= 50]
    best = min(np.arange(1.0, 3.01, 0.05), key=lambda p: float(np.sum(g.n * (g.m ** p - g.z) ** 2)))
    return float(best), g


ZERO_POWER = 1.55


def availability(pid) -> dict:
    h, n = history(pid, len(SEAS))
    rate = curve(h, n) if n else build_rate(pid)[0]
    missed = 1 - rate
    zero = missed ** ZERO_POWER
    q = min(1.0, rate / (1 - zero)) if zero < 1 else 0.0
    return dict(games=round(82 * rate, 1), missed=round(missed, 4), zero=round(zero, 4), q=round(q, 4))


if __name__ == "__main__":
    ZERO_POWER, zt = zero_power()
    print(f"zero-week share = missed^{ZERO_POWER:.2f} (long-injury weeks removed)")
    for n, (kx, ky) in CURVES.items():
        print(f"{n} season(s) of history: " + ", ".join(f"{82 * x:.0f}→{82 * float(np.interp(x, kx, ky)):.0f}" for x in (0.6, 0.7, 0.8, 0.9, 0.95, 1.0)))
    ho = D[D.rot & (D.season == "2025-26")]
    pr = [(curve(*history(p, 5)), r) for p, r in zip(ho.pid, ho.rate) if history(p, 5)[1]]
    p, a = np.array(pr).T
    print(f"holdout '26: RMSE {np.sqrt(np.mean((82 * (p - a)) ** 2)):.1f} games (league average for all: {np.sqrt(np.mean((82 * (a.mean() - a)) ** 2)):.1f}); "
          f"avg predicted {82 * p.mean():.1f} vs actual {82 * a.mean():.1f}")
    out = {str(int(pid)): availability(int(pid)) for pid in r27}
    json.dump(dict(zero_power=ZERO_POWER, season_ending=SEASON_ENDING, players=out), open(R + "availability_2026_27.json", "w"))
    for nm in ["Victor Wembanyama", "Mikal Bridges", "Nikola Jokić", "Shai Gilgeous-Alexander", "Luka Dončić", "Anthony Edwards",
               "Jayson Tatum", "Tyrese Haliburton", "Chet Holmgren", "Joel Embiid", "Kawhi Leonard", "Anthony Davis", "Stephen Curry"]:
        pid = int(names[names == nm].index[0])
        h = D[D.pid == pid].sort_values("season")
        print(f"{nm:<24} counted seasons {[f'{int(a)}/{int(b)}' for a, b in zip(h.gp, h.tg)]} → {out[str(pid)]['games']} games, zero weeks {out[str(pid)]['zero']:.1%}")
    br, near = build_rate(1641705)
    print(f"Wemby's build: similar rotation players {82 * br:.0f} games")
    print(len(out), "players written")
