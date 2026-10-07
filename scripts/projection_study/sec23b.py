"""Per-step numbers for sections 2 (minutes / possessions) and 3 (usage), plus the 2026-27 random sample."""
import contextlib, io, json, os, runpy
import numpy as np, pandas as pd
os.environ["APPLY_LATE"] = "1"
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
with contextlib.redirect_stdout(io.StringIO()):
    P = runpy.run_path(S + "pipeline.py", run_name="lib")
    U = runpy.run_path(S + "usage_resplit.py", run_name="lib")
actual, pid_of = P["actual"], P["pid_of"]


def adv(s):
    rs = json.load(open(f"{R}player_advanced/{s}.json"))["resultSets"][0]
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"]).set_index("PLAYER_ID")


def tadv(s):
    rs = json.load(open(f"{R}team_advanced/{s}.json"))["resultSets"][0]
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"])


A25, A26 = adv("2024-25"), adv("2025-26")
abbr = pd.read_csv(R + "rosters/2025-26.csv").drop_duplicates("TeamID").set_index("TeamID").TEAM.to_dict()
tp25 = {abbr[r.TEAM_ID]: r.PACE for r in tadv("2024-25").itertuples()}
first26 = P["FIRST"]["2025-26"]

# ---- minutes ladder on the same 389 players
L0, L1 = pd.read_csv(S + "ladder_0.csv"), pd.read_csv(S + "ladder_1.csv")
d = L0.merge(L1[["pid", "7 + late-jump rule mpg"]], on="pid")
MB, UB = [0, 16, 22, 28, 32, 35, 99], [0, .16, .20, .24, .28, 1]
GRID = [[2.3, 3.1, 2.6, 2.4, 2.4], [-0.2, -1.5, -0.8, -0.1, -0.1], [-2.2, -1.2, -1.3, -1.3, -1.3],
        [-2.4, -1.8, -1.3, -0.9, -0.6], [-0.9, -1.1, -1.3, -0.8, 0.1], [-1.1, -1.1, -1.0, -1.0, -0.7]]
m25 = d.pid.map(lambda p: A25.MIN.get(p, np.nan))
u25 = d.pid.map(lambda p: A25.USG_PCT.get(p, np.nan))
d["s_last"] = m25
d["s_flat"] = 26.9 + 0.7 * (m25 - 26.9)
mi = np.clip(np.searchsorted(MB, m25.fillna(0), side="right") - 1, 0, 5)
ui = np.clip(np.searchsorted(UB, u25.fillna(0), side="right") - 1, 0, 4)
d["s_group"] = m25 + [GRID[a][b] for a, b in zip(mi, ui)]
STEPS = [("s_last", "Same as last season"), ("s_flat", "Flat pull toward 26.9"), ("s_group", "Change learned by minutes × usage group"),
         ("3 component model mpg", "Career model (age, years, role size, trend)"), ("4 + healthy-season base mpg", "+ trained and based on healthy seasons"),
         ("5 + short-history pull mpg", "+ pull toward bench minutes for short histories"), ("6 + team quality / moved mpg", "+ team quality and team change"),
         ("7 + late-jump rule mpg", "+ late-season minutes down-weighted (final)")]
steps = []
for col, lab in STEPS:
    ok = d[col].notna() & d.act_mpg.notna()
    e = (d[col] - d.act_mpg)[ok]
    steps.append(dict(col=col, label=lab, err=round(float(e.abs().mean()), 2), bias=round(float(e.mean()), 2), n=int(ok.sum())))
MP = ["Anthony Edwards", "Nikola Jokić", "Tyrese Maxey", "DeMar DeRozan", "Brandon Miller", "Jonathan Mogbo", "Ryan Rollins", "Drew Timme"]
mins_players = []
for n in MP:
    p = pid_of(n)
    r = d[d.pid == p]
    a25 = actual(p, "2024-25")
    row = dict(name=n, m25=float(A25.MIN.get(p, np.nan)), gp25=int(A25.GP.get(p, 0)), act=float(r.act_mpg.iloc[0]) if len(r) else None,
               gp26=int(A26.GP.get(p, 0)), usg25=float(A25.USG_PCT.get(p, np.nan)), age25=float(A25.AGE.get(p, np.nan)))
    for col, _ in STEPS:
        row[col] = None if r.empty or pd.isna(r[col].iloc[0]) else float(r[col].iloc[0])
    mins_players.append(row)

# ---- pace / possessions for the stars
PP = ["Nikola Jokić", "Shai Gilgeous-Alexander", "Anthony Edwards", "Jalen Brunson", "Tyrese Maxey", "Brandon Miller"]
pace_rows, own_e, team_e = [], [], []
ids = [p for p in d.pid]
for p in ids:
    with contextlib.redirect_stdout(io.StringIO()):
        g = P["project"](p, "2025-26")
    if not g or p not in A26.index:
        continue
    tp = tp25.get(first26.get(p))
    own_e.append(abs(g["pace"] - A26.PACE[p]))
    if tp:
        team_e.append(abs(tp - A26.PACE[p]))
    if A26.PLAYER_NAME[p] in PP:
        pace_rows.append(dict(name=A26.PLAYER_NAME[p], team=first26.get(p), pace25=float(A25.PACE.get(p, np.nan)), team_pace=tp,
                              own=g["pace"], act=float(A26.PACE[p]), mpg=g["mpg"], poss=g["poss"],
                              act_poss=float(A26.POSS[p] / A26.GP[p]), act_mpg=float(A26.MIN[p])))
pace_err = dict(own=round(float(np.mean(own_e)), 2), team=round(float(np.mean(team_e)), 2), n=len(own_e))

# ---- usage, '25→'26, players with 60+ GP for their team both seasons
v = U["transition"]("2024-25", "2025-26")
v = v.reset_index(drop=True)
ust = []
for lab, kind in [("Same as last season", "same"), ("Re-split for everyone", "all"), ("Re-split for players who stayed (final)", "stay")]:
    p_ = v.u0 if kind == "same" else (v.proj if kind == "all" else np.where(v.moved, v.u0, v.proj))
    e = np.abs(np.asarray(p_) - v.act) * 100
    ust.append(dict(label=lab, kind=kind, all=round(float(e.mean()), 2), stay=round(float(e[~v.moved].mean()), 2),
                    move=round(float(e[v.moved].mean()), 2)))
UP = ["Jalen Brunson", "Anthony Edwards", "Nikola Jokić", "Shai Gilgeous-Alexander", "Desmond Bane", "Myles Turner", "Kevin Durant"]
use_players = []
for n in UP:
    r = v[v.name == n]
    if r.empty:
        continue
    r = r.iloc[0]
    use_players.append(dict(name=n, t0=r.t0, t1=r.t1, moved=bool(r.moved), u0=float(r.u0), resplit=float(r.proj), act=float(r.act)))

# ---- 2026-27 random sample from the top 125 (veterans), same players for every section
b = pd.read_csv(R + "projections_2026_27.csv").head(125)
vets = b[b.kind == "vet"]
sample = vets.sample(8, random_state=27).sort_values("fp", ascending=False)
s27 = []
for x in sample.itertuples():
    p = int(x.pid)
    with contextlib.redirect_stdout(io.StringIO()):
        g = P["project"](p, "2026-27")
    a = actual(p, "2025-26")
    s27.append(dict(name=x.name, team=x.team, rank=int(b.index[b.pid == x.pid][0]) + 1, fp=float(x.fp), age=g["age"], stayed=bool(g["stayed"]),
                    base=g["base"], gp26=int(A26.GP.get(p, 0)), mpg26=a["mpg"] if a else None,
                    poss26=float(A26.POSS[p] / A26.GP[p]) if p in A26.index else None, pace26=float(A26.PACE.get(p, np.nan)),
                    usg26=float(A26.USG_PCT.get(p, np.nan)), base_usg=float(P["A"][g["base"]].USG_PCT[p]),
                    mpg=g["mpg"], pace=g["pace"], poss=g["poss"], usg=g["usg"]))
json.dump(dict(steps=steps, mins_players=mins_players, pace_rows=pace_rows, pace_err=pace_err, ust=ust, use_players=use_players,
               sample27=s27), open(S + "sec23b.json", "w"), default=float)
print(json.dumps(steps, indent=0)); print(pace_err); print(json.dumps(ust)); print([u["name"] for u in use_players]); print([s["name"] for s in s27])
