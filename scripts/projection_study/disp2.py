"""Dispersion study, part 1: game-to-game FP spread against the commissioner's axes (usage, minutes, good/bad player),
holding the player's own mean fixed, and whether a player's extra spread repeats next season.

Games: PlayerGameLogs (regular season, every game played), league scoring incl. BLKD.
Player-seasons with 40+ games. Development seasons '22–'25; '26 only as a check.
"""
import json
import numpy as np
import pandas as pd

R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
SEAS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]


def J(kind, s):
    rs = json.load(open(f"{R}{kind}/{s}.json"))["resultSets"]
    rs = rs[0] if isinstance(rs, list) else rs
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"])


def games(s):
    g = J("game_logs", s)
    g = g[g.MIN > 0].copy()
    g["fp"] = (g.PTS - 0.5 * (g.FGA - g.FGM) - 0.5 * g.BLKA + 0.5 * g.FG3M - (g.FTA - g.FTM) + 1.5 * g.OREB + 0.5 * g.DREB
               + g.AST + 2 * g.STL + 1.5 * g.BLK - 2 * g.TOV)
    g["season"] = s
    g["date"] = pd.to_datetime(g.GAME_DATE)
    return g[["season", "PLAYER_ID", "PLAYER_NAME", "TEAM_ABBREVIATION", "GAME_ID", "date", "MIN", "fp", "MATCHUP"]]


G = pd.concat(games(s) for s in SEAS)
G.to_parquet(S + "disp_games.parquet")
adv = pd.concat(J("player_advanced", s).assign(season=s) for s in SEAS)
bio = pd.concat(J("bios", s).assign(season=s) for s in SEAS)
pos = pd.read_csv(R + "role_positions_single_2025_26.csv", index_col=0).final

ps = G.groupby(["season", "PLAYER_ID"]).agg(name=("PLAYER_NAME", "last"), n=("fp", "size"), mean=("fp", "mean"), sd=("fp", "std"),
                                             mpg=("MIN", "mean"), sdmin=("MIN", "std")).reset_index()
ps = ps[ps.n >= 40].merge(adv[["season", "PLAYER_ID", "USG_PCT", "PIE", "AGE"]], on=["season", "PLAYER_ID"], how="left")
ps["pos"] = ps.PLAYER_ID.map(pos)
dev = ps[ps.season < "2025-26"]
b, a = np.polyfit(np.log(dev["mean"]), np.log(dev.sd), 1)
ps["sd_exp"] = np.exp(a) * ps["mean"] ** b
ps["ratio"] = ps.sd / ps.sd_exp  # >1 = more spread than players at his level
ps["fp36"] = ps["mean"] / ps.mpg * 36
print(f"{len(dev)} dev player-seasons; SD = {np.exp(a):.2f} × mean^{b:.2f}  (10 FP/G → ±{np.exp(a) * 10 ** b:.1f}, 25 → ±{np.exp(a) * 25 ** b:.1f}, 40 → ±{np.exp(a) * 40 ** b:.1f})")
dev = ps[ps.season < "2025-26"]


def bands(col, edges, labels):
    c = pd.cut(dev[col], edges, labels=labels)
    t = dev.groupby(c, observed=True).agg(n=("ratio", "size"), ratio=("ratio", "median"), mean=("mean", "median"))
    return t


out = {}
for col, edges, labels in [("USG_PCT", [0, .15, .19, .23, .27, 1], ["<15%", "15–19", "19–23", "23–27", "27%+"]),
                           ("mpg", [0, 18, 24, 30, 34, 60], ["<18", "18–24", "24–30", "30–34", "34+"]),
                           ("PIE", [-1, .07, .09, .11, .13, 1], ["<7", "7–9", "9–11", "11–13", "13+"]),
                           ("fp36", [0, 22, 27, 32, 37, 99], ["<22", "22–27", "27–32", "32–37", "37+"]),
                           ("AGE", [0, 23, 27, 31, 50], ["≤23", "24–27", "28–31", "32+"])]:
    t = bands(col, edges, labels)
    out[col] = t
    print(f"\nby {col}: " + "  ".join(f"{i}: n={r.n} SD×{r.ratio:.2f} (mean FP {r['mean']:.0f})" for i, r in t.iterrows()))
t = dev.groupby("pos").agg(n=("ratio", "size"), ratio=("ratio", "median"))
print("\nby position ('26 role):", t.to_dict("index"))
# minutes volatility as the driver: within-player SD of minutes, relative
dev2 = dev.assign(cvmin=dev.sdmin / dev.mpg)
print("\ncorr(ratio, minutes CV) = %.2f;  corr(ratio, usage) = %.2f;  corr(ratio, PIE) = %.2f;  corr(ratio, mpg) = %.2f" % (
    dev2.ratio.corr(dev2.cvmin), dev2.ratio.corr(dev2.USG_PCT), dev2.ratio.corr(dev2.PIE), dev2.ratio.corr(dev2.mpg)))
# persistence: does a player's ratio repeat next season?
pr = ps.pivot_table(index="PLAYER_ID", columns="season", values="ratio")
pairs = [(SEAS[i], SEAS[i + 1]) for i in range(len(SEAS) - 1)]
for s0, s1 in pairs:
    ok = pr[[s0, s1]].dropna()
    print(f"persistence {s0[-2:]}→{s1[-2:]}: r={ok[s0].corr(ok[s1]):.2f} (n={len(ok)})")
# who is steady / volatile (dev seasons, 3+ seasons, 20+ FP/G)
agg = dev.groupby("PLAYER_ID").agg(name=("name", "last"), k=("ratio", "size"), ratio=("ratio", "mean"), mean=("mean", "mean"))
agg = agg[(agg.k >= 3) & (agg["mean"] >= 20)].sort_values("ratio")
print("\nsteadiest (3+ seasons, 20+ FP/G):", [(r.name, round(r.ratio, 2), round(r["mean"], 1)) for _, r in agg.head(10).iterrows()])
print("most volatile:", [(r.name, round(r.ratio, 2), round(r["mean"], 1)) for _, r in agg.tail(10).iterrows()])
ps.to_csv(S + "disp_ps.csv", index=False)
json.dump(dict(a=float(a), b=float(b)), open(S + "disp_fit.json", "w"))
