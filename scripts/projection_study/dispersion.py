"""Is game-to-game spread homoscedastic across players?

Player-seasons '23–'25 with 40+ games (games with 10+ minutes). For each stat:
  per game (count) and per 75 possessions (rate; game possessions from team totals, split by minutes).
Across player-seasons fit log(SD) = a + b·log(mean):  b≈0 homoscedastic, ≈0.5 Poisson-like, ≈1 constant CV.
Also variance/mean (dispersion index; 1 = Poisson) for counts.
Within players: does a rate's spread depend on possessions played that game? (short games → noisier rates)
"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem/scripts")
sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem")
from load_historical_boxscores import minutes  # noqa: E402
from backend.fantasy_2026_27.logic import SCORING  # noqa: E402

R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/box_scores_traditional/trad_box_scores_{}.parquet"
STATS = ["pts", "reb", "ast", "stl", "blk", "tov", "fg3m", "fga", "fta", "oreb", "dreb", "fp"]
frames = []
for tag in ["2022_23", "2023_24", "2024_25"]:
    d = pd.read_parquet(R.format(tag))
    d = d[d.game_id.astype(str).str[2] == "2"].copy()
    d["m"] = d["minutes"].map(minutes)
    tm = d.groupby(["game_id", "team_tricode"]).agg(fga=("fga", "sum"), fta=("fta", "sum"), oreb=("oreb", "sum"),
                                                    tov=("tov", "sum"), tmin=("m", "sum")).reset_index()
    tm["poss"] = tm.fga + 0.44 * tm.fta - tm.oreb + tm.tov
    gm = tm.groupby("game_id").agg(gposs=("poss", "mean"), glen=("tmin", "mean")).reset_index()
    d = d.merge(gm, on="game_id")
    d = d[d.m >= 10].copy()
    d["poss"] = d.m * d.gposs / (d.glen / 5)
    d["reb"] = d.oreb + d.dreb
    d["fp"] = (d.pts + (d.fga - d.fgm) * SCORING["fgx"] + d.fg3m * SCORING["fg3m"] + (d.fta - d.ftm) * SCORING["ftx"]
               + d.oreb * SCORING["oreb"] + d.dreb * SCORING["dreb"] + d.ast * SCORING["ast"] + d.stl * SCORING["stl"]
               + d.blk * SCORING["blk"] + d.tov * SCORING["tov"])
    d["season"] = tag
    frames.append(d)
g = pd.concat(frames)
g["pid"] = g.player_id.astype(int)
n = g.groupby(["pid", "season"]).game_id.transform("nunique")
g = g[n >= 40]
print(f"{g.groupby(['pid', 'season']).ngroups} player-seasons, {len(g)} games (10+ min)\n")


def fit(mean, sd):
    ok = (mean > 0) & (sd > 0)
    x, y = np.log(mean[ok]), np.log(sd[ok])
    b, a = np.polyfit(x, y, 1)
    r2 = np.corrcoef(x, y)[0, 1] ** 2
    return b, r2


rows = []
for st in STATS:
    agg = g.groupby(["pid", "season"]).agg(m=(st, "mean"), s=(st, "std"))
    b_c, r2_c = fit(agg.m.to_numpy(), agg.s.to_numpy())
    g["_r"] = 75 * g[st] / g.poss
    ar = g.groupby(["pid", "season"]).agg(m=("_r", "mean"), s=("_r", "std"))
    b_r, r2_r = fit(ar.m.to_numpy(), ar.s.to_numpy())
    disp = (agg.s ** 2 / agg.m).replace([np.inf], np.nan).median() if st != "fp" else np.nan
    cv = (agg.s / agg.m).median()
    # low vs high quartile of players by mean: ratio of SDs vs ratio of means
    q1, q4 = agg.m.quantile([0.25, 0.75])
    lo, hi = agg[agg.m <= q1], agg[agg.m >= q4]
    rows.append(dict(stat=st.upper(), b_count=b_c, r2_count=r2_c, b_rate=b_r, r2_rate=r2_r, disp=disp, cv=cv,
                     mean_lo=lo.m.mean(), sd_lo=lo.s.mean(), mean_hi=hi.m.mean(), sd_hi=hi.s.mean()))
t = pd.DataFrame(rows)
print("Across players: SD ∝ mean^b   (b≈0 homoscedastic · 0.5 Poisson-like · 1 constant CV)")
print(f"  {'stat':<5}{'b (per game)':>13}{'R²':>6}{'b (per 75)':>12}{'R²':>6}{'var/mean':>10}{'CV':>6}   low-quartile mean/SD → high-quartile mean/SD")
for r in t.itertuples():
    dsp = "" if np.isnan(r.disp) else f"{r.disp:.2f}"
    print(f"  {r.stat:<5}{r.b_count:13.2f}{r.r2_count:6.2f}{r.b_rate:12.2f}{r.r2_rate:6.2f}{dsp:>10}{r.cv:6.2f}   "
          f"{r.mean_lo:5.1f}/{r.sd_lo:4.1f} → {r.mean_hi:5.1f}/{r.sd_hi:4.1f}")

# within player: rate spread vs possessions that game
print("\nWithin players: SD of the per-75 rate (deviation from his own season mean) by possessions played that game")
g["poss_band"] = pd.cut(g.poss, [0, 40, 55, 70, 200], labels=["<40", "40–55", "55–70", "70+"])
for st in ["pts", "reb", "ast", "fp"]:
    g["_r"] = 75 * g[st] / g.poss
    g["_dev"] = g._r - g.groupby(["pid", "season"])._r.transform("mean")
    sd = g.groupby("poss_band", observed=True)._dev.std()
    print(f"  {st.upper():<4}" + "  ".join(f"{k}: {v:5.2f}" for k, v in sd.items()) +
          f"   (√ ratio <40 vs 70+ if pure counting noise: {np.sqrt(77 / 33):.2f}×; observed {sd.iloc[0] / sd.iloc[-1]:.2f}×)")
