"""Rookie per-game projection from draft pick, height, weight, and the point differential (per game, prior season)
of the team he plays for.

Classes: 2021 draft → '22 … 2024 draft → '25 (train); 2025 draft → '26 (validation); 2026 draft → '27 (forward).
Rookie season stats from box scores (regular season, GP >= 10 for training/scoring). Team = first-game team
(forward: 2026-27 roster team, else drafting team). Height/weight from that season's bios (forward: 2026-27 roster).
Undrafted = pick 61. Model: linear in log(pick), height, weight, prior team pt diff/G, fit separately for FP/G and MPG.
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem/scripts")
sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem")
from load_historical_boxscores import minutes  # noqa: E402
sys.path.insert(0, "/Users/allan/PycharmProjects/2026_pickem/scripts/projection_study")
from common import fp as player_points  # noqa: E402  (fantasy points under the build's scoring rules)

D = "/Users/allan/PycharmProjects/nba-pipeline/data/"
R = D + "raw/"
BOXF = {"2021-22": D + "box_scores/trad_box_scores_2021_22.parquet",
        "2022-23": R + "box_scores_traditional/trad_box_scores_2022_23.parquet",
        "2023-24": R + "box_scores_traditional/trad_box_scores_2023_24.parquet",
        "2024-25": R + "box_scores_traditional/trad_box_scores_2024_25.parquet",
        "2025-26": D + "box_scores/trad_box_scores_2025_26.parquet"}
dh = json.load(open(R + "draft_history.json"))["resultSets"][0]
DH = pd.DataFrame(dh["rowSet"], columns=dh["headers"])
DH = DH[DH.SEASON.astype(int) >= 2021]
DH["PERSON_ID"] = DH.PERSON_ID.astype(int)


def tab(kind, s):
    rs = json.load(open(f"{R}{kind}/{s}.json"))["resultSets"][0]
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"]).set_index("PLAYER_ID")


def ptdiff(season):
    s = pd.read_parquet(R + f"schedules/schedule_{season.replace('-', '_')}.parquet")
    s = s[(s.game_id.astype(str).str[2] == "2") & (s.game_status == 3)]
    rows = [(r.home_team_tricode, r.home_score - r.away_score) for r in s.itertuples()] + \
           [(r.away_team_tricode, r.away_score - r.home_score) for r in s.itertuples()]
    return pd.DataFrame(rows, columns=["t", "d"]).groupby("t").d.mean()


def prev(s):
    y = int(s[:4]) - 1
    return f"{y}-{str(y + 1)[-2:]}"


def season_rows(season):
    """rookies (drafted the summer before, or undrafted with no prior NBA games) and their rookie-year per-game line"""
    d = pd.read_parquet(BOXF[season])
    d = d[d.game_id.astype(str).str[2] == "2"].copy()
    d["player_id"] = d.player_id.astype(int)
    d["m"] = d["minutes"].map(minutes)
    d = d[d.m > 0]
    d["fp"] = [player_points(r) for r in d[["pts", "fga", "fgm", "fg3m", "fta", "ftm", "oreb", "dreb", "ast", "stl", "blk", "tov"]].to_dict("records")]
    g = d.groupby("player_id").agg(gp=("game_id", "nunique"), mpg=("m", "mean"), fp=("fp", "mean"), name=("player_name", "last"))
    team = d.sort_values("game_id").groupby("player_id").team_tricode.first()
    bio = tab("bios", season)
    year = int(season[:4])
    drafted = DH[DH.SEASON.astype(int) == year].set_index("PERSON_ID")
    rook = [p for p in g.index if p in drafted.index or (str(bio.DRAFT_YEAR.get(p, "")) == "Undrafted" and bio.AGE.get(p, 99) <= 24
                                                        and all(p not in pd.read_parquet(BOXF[s], columns=["player_id"]).player_id.astype(int).values
                                                                for s in BOXF if s < season))]
    pdiff = ptdiff(prev(season))
    out = pd.DataFrame(index=rook)
    out["name"], out["gp"], out["mpg"], out["fp"] = g.name, g.gp, g.mpg, g.fp
    out["pick"] = [drafted.OVERALL_PICK.get(p, 61) if p in drafted.index else 61 for p in rook]
    out["team"] = team.reindex(rook)
    out["height"] = bio.PLAYER_HEIGHT_INCHES.reindex(rook).astype(float)
    out["weight"] = pd.to_numeric(bio.PLAYER_WEIGHT.reindex(rook), errors="coerce")
    out["tdiff"] = out.team.map(pdiff)
    out["season"] = season
    return out


FEATS = ["lpick", "height", "weight", "tdiff"]


def X(df, cols=FEATS):
    return np.column_stack([np.ones(len(df))] + [df[c].to_numpy(float) for c in cols])


allr = pd.concat(season_rows(s) for s in ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"])
allr["lpick"] = np.log(allr.pick)
allr = allr.dropna(subset=["height", "weight", "tdiff"])
tr, va = allr[(allr.season < "2025-26") & (allr.gp >= 10)], allr[(allr.season == "2025-26") & (allr.gp >= 10)]
print(f"Rookies with 10+ GP: train ('22–'25) {len(tr)}, validation ('26) {len(va)}.  "
      f"Drafted 1st-rounders who didn't reach 10 GP in year 1 (train): "
      f"{((allr.season < '2025-26') & (allr.pick <= 30) & (allr.gp < 10)).sum()}\n")
fits = {}
for tgt in ["fp", "mpg"]:
    w = tr.gp.to_numpy(float)
    b, *_ = np.linalg.lstsq(X(tr) * np.sqrt(w)[:, None], tr[tgt].to_numpy() * np.sqrt(w), rcond=None)
    b0, *_ = np.linalg.lstsq(X(tr, ["lpick"]) * np.sqrt(w)[:, None], tr[tgt].to_numpy() * np.sqrt(w), rcond=None)
    fits[tgt] = b
    p, p0 = X(va) @ b, X(va, ["lpick"]) @ b0
    print(f"{tgt.upper():<4} = {b[0]:+.1f} {b[1]:+.2f}·ln(pick) {b[2]:+.3f}·height(in) {b[3]:+.3f}·weight(lb) {b[4]:+.3f}·team pt diff/G")
    print(f"     '26 validation error: full model {np.abs(p - va[tgt]).mean():.2f}   pick only {np.abs(p0 - va[tgt]).mean():.2f}   "
          f"class average {np.abs(tr[tgt].mean() - va[tgt]).mean():.2f}")
    if tgt == "fp":
        va = va.assign(proj_fp=p)
    else:
        va = va.assign(proj_mpg=p)
print("\nTeam effect: a rookie joining a team that was −10/G the year before vs +10/G:  "
      f"{20 * fits['fp'][4]:+.1f} FP/G, {20 * fits['mpg'][4]:+.1f} MPG")
print("\n'26 class (2025 draft), top 15 picks: proj FP/G → actual  (MPG proj → actual)")
for _, x in va.sort_values("pick").head(15).iterrows():
    print(f"  #{int(x.pick):<3}{x['name']:<24}{x.team}  prior diff {x.tdiff:+5.1f}   FP {x.proj_fp:5.1f} → {x.fp:5.1f}   MPG {x.proj_mpg:4.1f} → {x.mpg:4.1f}  ({int(x.gp)} GP)")

# ---- forward: 2026 draft → '27, refit on all classes incl. '26 ----
full = allr[allr.gp >= 10]
w = full.gp.to_numpy(float)
fw = {t: np.linalg.lstsq(X(full) * np.sqrt(w)[:, None], full[t].to_numpy() * np.sqrt(w), rcond=None)[0] for t in ["fp", "mpg"]}
r27 = pd.read_csv(R + "rosters/2026-27.csv").set_index("PLAYER_ID")
d26 = DH[DH.SEASON == "2026"].set_index("PERSON_ID")
pd26 = ptdiff("2025-26")
cls = pd.DataFrame(index=d26.index)
cls["name"], cls["pick"] = d26.PLAYER_NAME, d26.OVERALL_PICK
cls["team"] = [r27.TEAM.get(p, d26.TEAM_ABBREVIATION[p]) for p in cls.index]
cls["on_roster"] = cls.index.isin(r27.index)
ht = r27.HEIGHT.reindex(cls.index).dropna().map(lambda h: int(h.split("-")[0]) * 12 + int(h.split("-")[1]))
cls["height"] = ht.reindex(cls.index)
cls["weight"] = pd.to_numeric(r27.WEIGHT.reindex(cls.index), errors="coerce")
cls["tdiff"] = cls.team.map(pd26)
cls["lpick"] = np.log(cls.pick)
ok = cls.dropna(subset=["height", "weight", "tdiff"])
ok = ok.assign(fp=X(ok) @ fw["fp"], mpg=X(ok) @ fw["mpg"])
print(f"\n2026 draft → '27 projections ({len(ok)} of {len(cls)} picks with roster height/weight; refit on '22–'26 classes):")
for _, x in ok.sort_values("pick").head(30).iterrows():
    print(f"  #{int(x.pick):<3}{x['name']:<24}{x.team}  {int(x.height) // 12}-{int(x.height) % 12} {x.weight:.0f}  team diff '26 {x.tdiff:+5.1f}   "
          f"FP/G {x.fp:5.1f}   MPG {x.mpg:4.1f}")
ok.to_csv(R + "rookie_projections_2026_27.csv")
