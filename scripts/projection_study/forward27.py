"""2026-27 per-game projection (points and its inputs) for named players, using '22–'26 as inputs.
MPG: career model (age/yrs/prod/trend bands), trained on healthy seasons ('22→'26 transitions incl. '25→'26).
Pace: own on-court PACE, '24–'26, minutes-weighted, recency r=3.  poss/G = MPG x pace / 48.
FGA/75, FTA/75: '24–'26 possession-weighted, recency r=2 (NBA POSS).
Zone share: '22–'26 shares, FGA-weighted, recency r=5, no trend.  Zone FG%: '24–'26 attempt-weighted, k=25, no pull at 200+.
FT%: '24–'26 attempt-weighted, k=25, no pull at 200+.  Usage resplit on 2026-27 rosters shown for reference (not applied).
"""
import contextlib
import io
import json
import runpy
import sys

import numpy as np
import pandas as pd

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
WHO = sys.argv[1:] or ["Anthony Edwards", "Jalen Brunson"]

# --- career MPG model, healthy training, including '25→'26 ---
src = open(S + "career.py").read().split("# points/G for the 210")[0]
src = src.replace('j = j[(j.GP >= 20) & (j.GP_1 >= 20)].copy()',
                  'j = j[(j.GP >= 20) & (j.GP_1 >= 20)].copy()\n    j["GP_prev"] = ap.GP.reindex(j.index)\n'
                  '    j["healthy"] = (j.GP >= 50) & (j.GP_1 >= 50) & (j.GP_prev.fillna(0) >= 50)')
src = src.replace("train = pd.concat(rows(a, b, c) for a, b, c in zip(SEAS[:3], SEAS[1:4], SEAS[2:5]))",
                  "train = pd.concat(rows(a, b, c) for a, b, c in zip(SEAS[:4], SEAS[1:5], SEAS[2:6]))\ntrain = train[train.healthy]")
C = {}
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(src, "career", "exec"), C)
A, design, Xtr, beta = C["A"], C["design"], C["Xtr"], C["fits"]["MPG"]
a26, a25, a24 = A["2025-26"], A["2024-25"], A["2023-24"]


def tab(kind, s):
    rs = json.load(open(f"{R}{kind}/{s}.json"))["resultSets"][0]
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"]).set_index("PLAYER_ID")


# --- zones ---
with contextlib.redirect_stdout(io.StringIO()):
    Z = runpy.run_path(S + "zone_projection.py", run_name="lib")
ZONES, VAL, load = Z["ZONES"], Z["VAL"], Z["load"]
zs = {s: load(s).pivot_table(index="pid", columns="zone", values=["fga", "fgm"], fill_value=0)
      for s in ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]}

# --- usage resplit 2026-27 ---
with contextlib.redirect_stdout(io.StringIO()):
    U = runpy.run_path(S + "usage_resplit.py", run_name="lib")
r27 = pd.read_csv(f"{R}rosters/2026-27.csv")
usg27 = U["project"](a26, r27.groupby("TEAM").PLAYER_ID.apply(set).to_dict())

IN3 = ["2023-24", "2024-25", "2025-26"]
FTA = C["FTA"]
for name in WHO:
    pid = a26.index[a26.PLAYER_NAME == name][0]
    team27 = r27.set_index("PLAYER_ID").TEAM.get(pid, "?")
    # MPG
    row = pd.DataFrame([dict(AGE=a26.AGE[pid], yrs=C["years"](pid, "2025-26"), prod=a26.USG_PCT[pid] * a26.MIN[pid],
                             trend=a26.MIN[pid] - a25.MIN.get(pid, np.nan))])
    x = design(row).reindex(columns=Xtr.columns, fill_value=0).to_numpy()[0]
    mpg = a26.MIN[pid] + beta[0] + x @ beta[1:]
    # pace, rates
    gp = np.array([A[s].GP.get(pid, 0) for s in IN3], float)
    mn = np.array([A[s].MIN.get(pid, 0) for s in IN3], float)
    pace = np.array([A[s].PACE.get(pid, 0) for s in IN3], float)
    poss = np.array([A[s].POSS.get(pid, 0) for s in IN3], float)
    fga = np.array([A[s].FGA.get(pid, 0) for s in IN3], float)
    fta = np.array([FTA[s].get(pid, 0) for s in IN3], float)
    w3 = 3.0 ** np.arange(3) * gp * mn
    pace_p = (pace * w3).sum() / w3.sum()
    w2 = 2.0 ** np.arange(3)
    fga75 = 75 * (fga * w2).sum() / (poss * w2).sum()
    fta75 = 75 * (fta * w2).sum() / (poss * w2).sum()
    poss_g = mpg * pace_p / 48
    # zones
    seas5 = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
    A5 = np.array([[zs[s]["fga"].get(z, pd.Series()).get(pid, 0) for z in ZONES] for s in seas5], float)
    M5 = np.array([[zs[s]["fgm"].get(z, pd.Series()).get(pid, 0) for z in ZONES] for s in seas5], float)
    tot = A5.sum(1)
    w = np.where(tot >= 100, tot, 0) * 5.0 ** np.arange(5)
    share = (A5 / np.where(tot > 0, tot, 1)[:, None] * w[:, None]).sum(0) / w.sum()
    allA = np.stack([zs[s]["fga"][ZONES].sum() for s in seas5[-3:]]).sum(0)
    allM = np.stack([zs[s]["fgm"][ZONES].sum() for s in seas5[-3:]]).sum(0)
    mu = allM / allA
    a3, m3 = A5[-3:].sum(0), M5[-3:].sum(0)
    k = np.where(a3 >= 200, 0.0, 25.0)
    pct = (m3 + k * mu) / (a3 + k)
    ftm3 = np.array([C["FTA"][s].get(pid, 0) for s in IN3])  # placeholder (replaced below)
    # FT% from box
    ftm = []
    for s in IN3:
        d = pd.read_parquet(C["BOX"][s])
        d = d[(d.game_id.astype(str).str[2] == "2") & (d.player_id.astype(int) == pid)]
        ftm.append(d.ftm.sum())
    ftm = np.array(ftm, float)
    ftp = (ftm.sum() + (0 if fta.sum() >= 200 else 25 * 0.79)) / (fta.sum() + (0 if fta.sum() >= 200 else 25))
    stayed = r27.set_index("PLAYER_ID").TEAM.get(pid) == C["A"]["2025-26"].TEAM_ABBREVIATION.get(pid)
    uratio = (usg27.get(pid, a26.USG_PCT[pid]) / a26.USG_PCT[pid]) if stayed else 1.0
    fga75 *= uratio ** 0.5
    fta75 *= uratio ** 0.5
    other = {}
    for st, r in [("ast", 5), ("stl", 1), ("blk", 5), ("tov", 2)]:
        xs = []
        for s in IN3:
            d = pd.read_parquet(C["BOX"][s])
            d = d[(d.game_id.astype(str).str[2] == "2") & (d.player_id.astype(int) == pid)]
            xs.append(d[st].sum())
        wr = float(r) ** np.arange(3)
        other[st] = 75 * (np.array(xs, float) * wr).sum() / (poss * wr).sum() * (uratio if st == "tov" else 1.0)
    fga_g = poss_g / 75 * fga75
    zone_att = fga_g * share
    zone_mk = zone_att * pct
    fg_pts = (zone_mk * np.array([VAL[z] for z in ZONES])).sum()
    fta_g = poss_g / 75 * fta75
    pts = fg_pts + fta_g * ftp

    print(f"\n{name} — {team27} 2026-27 (age {a26.AGE[pid]:.0f} in '26)")
    print(f"  MINUTES/G   {mpg:5.1f}   ('26 {a26.MIN[pid]:.1f}, '25 {a25.MIN.get(pid, np.nan):.1f}, '24 {a24.MIN.get(pid, np.nan):.1f})")
    print(f"  PACE        {pace_p:5.1f}   POSS/G {poss_g:4.1f}")
    print(f"  USAGE       '26 {100 * a26.USG_PCT[pid]:.1f}%  → resplit on '27 roster {100 * usg27.get(pid, np.nan):.1f}%  (reference, not applied)")
    print(f"  FGA/75 {fga75:4.1f} → FGA/G {fga_g:4.1f}      FTA/75 {fta75:4.1f} → FTA/G {fta_g:4.1f} at {100 * ftp:.1f}%")
    print(f"  {'zone':<8}{'share':>7}{'att/G':>7}{'FG%':>7}")
    for j, z in enumerate(ZONES):
        print(f"  {z:<8}{100 * share[j]:6.1f}%{zone_att[j]:7.1f}{100 * pct[j]:6.1f}%")
    print(f"  FG {zone_mk.sum():.1f}/{fga_g:.1f} ({100 * zone_mk.sum() / fga_g:.1f}%), 3PM {zone_mk[3] + zone_mk[4]:.1f}/{zone_att[3] + zone_att[4]:.1f}, "
          f"FTM {fta_g * ftp:.1f}/{fta_g:.1f}")
    print(f"  usage applied: x{uratio:.3f} (half strength → FGA/FTA x{uratio ** 0.5:.3f}; TOV x{uratio:.3f})" if stayed else "  usage not applied (changed team)")
    print(f"  POINTS/G {pts:5.1f}   AST {poss_g / 75 * other['ast']:4.1f}   STL {poss_g / 75 * other['stl']:4.2f}   BLK {poss_g / 75 * other['blk']:4.2f}   TOV {poss_g / 75 * other['tov']:4.2f}")
