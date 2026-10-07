"""Player scoring rescale on 2024-25 (the season with play-by-play on disk).
S0 current · S1 points ×0.5 · S2 S1 + clutch (points 1.0 each, FT made 1.0, TOV −4, STL 4, BLK 3, OREB 3) ·
S3 same with clutch points 1.5 each. Clutch = 4th quarter or OT, 5:00 or less left, score within 5 (before the play)."""
import json, re, sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem")
from backend.fantasy_2026_27.weeks import build_weeks, week_for  # noqa: E402

R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
p = pd.read_parquet(R + "play_by_play/pbp_2024_25.parquet",
                    columns=["game_id", "action_number", "clock", "period", "person_id", "location", "action_type", "shot_value", "shot_result", "description", "score_home", "score_away"])
p = p[p.game_id.str[2] == "2"].sort_values(["game_id", "action_number"]).reset_index(drop=True)
for c in ("score_home", "score_away"):
    p[c] = pd.to_numeric(p[c].replace("", np.nan), errors="coerce")
    p[c] = p.groupby("game_id")[c].ffill().fillna(0)
    p[c + "_before"] = p.groupby("game_id")[c].shift(1).fillna(0)
m = p.clock.str.extract(r"PT(\d+)M([\d.]+)S").astype(float)
p["secs"] = m[0] * 60 + m[1]
p["clutch"] = (p.period >= 4) & (p.secs <= 300) & ((p.score_home_before - p.score_away_before).abs() <= 5)
p["is_player"] = p.person_id < 1610612737
desc = p.description.fillna("")
p["fg_pts"] = np.where(p.action_type == "Made Shot", p.shot_value, 0)
p["ftm"] = ((p.action_type == "Free Throw") & ~desc.str.startswith("MISS")).astype(int)
p["tov"] = ((p.action_type == "Turnover") & p.is_player).astype(int)
p["stl"] = desc.str.contains(r" STEAL \(").astype(int)
p["blk"] = desc.str.contains(r" BLOCK \(").astype(int)
# offensive rebound = rebounder's side took the last missed shot / free throw
miss = (p.action_type == "Missed Shot") | ((p.action_type == "Free Throw") & desc.str.startswith("MISS"))
p["miss_loc"] = np.where(miss, p.location, None)
p["miss_loc"] = p.groupby("game_id").miss_loc.ffill()
p["oreb"] = ((p.action_type == "Rebound") & p.is_player & (p.location == p.miss_loc)).astype(int)
cl = p[p.clutch & p.is_player].groupby(["game_id", "person_id"])[["fg_pts", "ftm", "tov", "stl", "blk", "oreb"]].sum().reset_index()
cl.columns = ["GAME_ID", "PLAYER_ID", "c_fgpts", "c_ftm", "c_tov", "c_stl", "c_blk", "c_oreb"]
print(f"clutch player-games: {len(cl)}; clutch events: pts {cl.c_fgpts.sum() + cl.c_ftm.sum():.0f}, tov {cl.c_tov.sum()}, stl {cl.c_stl.sum()}, blk {cl.c_blk.sum()}, oreb {cl.c_oreb.sum()}")

rs = json.load(open(R + "game_logs/2024-25.json"))["resultSets"][0]
g = pd.DataFrame(rs["rowSet"], columns=rs["headers"])
g = g[g.MIN > 0].copy()
g = g.merge(cl, on=["GAME_ID", "PLAYER_ID"], how="left").fillna({c: 0 for c in cl.columns[2:]})
base_other = (-0.5 * (g.FGA - g.FGM) - 0.5 * g.BLKA + 0.5 * g.FG3M - (g.FTA - g.FTM) + 1.5 * g.OREB + 0.5 * g.DREB + g.AST + 2 * g.STL + 1.5 * g.BLK - 2 * g.TOV)
g["S0"] = g.PTS + base_other
g["S1"] = 0.5 * g.PTS + base_other
clutch_extra = 0.5 * g.c_ftm - 2 * g.c_tov + 2 * g.c_stl + 1.5 * g.c_blk + 1.5 * g.c_oreb
g["S2"] = g.S1 + 0.5 * g.c_fgpts + clutch_extra
g["S3"] = g.S1 + 1.0 * g.c_fgpts + clutch_extra
g["clutch2"] = g.S2 - g.S1
g["date"] = pd.to_datetime(g.GAME_DATE).dt.date
weeks = build_weeks(set(g.date), [])
g["week"] = [(w["week"] if (w := week_for(weeks, d)) else None) for d in g.date]
g = g.dropna(subset=["week"])
V = ["S0", "S1", "S2", "S3"]
pg = g.groupby("PLAYER_ID").agg(name=("PLAYER_NAME", "last"), gp=("S0", "size"), **{v: (v, "mean") for v in V}, clutch2=("clutch2", "mean"),
                                 pts=("PTS", "mean"), cpts=("c_fgpts", "mean"))
wk = g.groupby(["PLAYER_ID", "week"])[V].max().groupby("PLAYER_ID").mean().add_prefix("wk_")
pg = pg.join(wk)
pg = pg[pg.gp >= 40]
pg.to_csv(S + "scoring_scale.csv")
pd.set_option("display.width", 240)
for v in V:
    t = pg.sort_values("wk_" + v, ascending=False).head(12)
    print(f"\n{v} — top 12 by weekly best:  " + ", ".join(f"{r['name'].split()[-1]} {r['wk_' + v]:.1f}" for _, r in t.iterrows()))
print("\nScale (players with 40+ games): median per game / weekly best, top-12 average weekly best")
for v in V:
    print(f"  {v}: per game {pg[v].median():.1f}, weekly best {pg['wk_' + v].median():.1f}, top-12 weekly {pg['wk_' + v].nlargest(12).mean():.1f}")
pg["pts_share0"] = pg.pts / pg.S0
pg["pts_share1"] = 0.5 * pg.pts / pg.S1
print(f"\nPoints share of FP (top 50 by S0): S0 {pg.nlargest(50, 'S0').pts_share0.median():.0%}, S1 {pg.nlargest(50, 'S0').pts_share1.median():.0%}")
pg["rank0"] = pg.wk_S0.rank(ascending=False)
pg["rank2"] = pg.wk_S2.rank(ascending=False)
mv = pg[pg.rank0 <= 60].assign(move=lambda x: x.rank0 - x.rank2).sort_values("move")
print("Biggest risers S0 → S2 (top 60):", [(r["name"], int(r.rank0), int(r.rank2)) for _, r in mv.tail(8).iloc[::-1].iterrows()])
print("Biggest fallers:", [(r["name"], int(r.rank0), int(r.rank2)) for _, r in mv.head(8).iterrows()])
print("Clutch adds per game (S2), top:", [(r["name"], round(r.clutch2, 2)) for _, r in pg.sort_values("clutch2", ascending=False).head(10).iterrows()])
print(f"Clutch adds per game, median of top-50 players: {pg.nlargest(50, 'S0').clutch2.median():.2f}; share of S2 weekly best from clutch: {(pg.nlargest(50,'S0').clutch2 / pg.nlargest(50,'S0').S2).median():.1%}")
