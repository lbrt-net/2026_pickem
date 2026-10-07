"""Player-level data for sections 9–12: age / career stage, injuries and the base season, bad players, rookies."""
import contextlib, io, json, os, runpy
import numpy as np, pandas as pd
os.environ["APPLY_LATE"] = "1"
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
with contextlib.redirect_stdout(io.StringIO()):
    P = runpy.run_path(S + "pipeline.py", run_name="lib")
    RK = runpy.run_path(S + "rookies.py", run_name="lib")
A, actual = P["A"], P["actual"]
D48 = json.load(open(S + "sec48.json"))
EIGHT = [e["name"] for e in D48["eight"]]
B27 = pd.read_csv(R + "projections_2026_27.csv")
B27["rank"] = np.arange(1, len(B27) + 1)


def pid_of(n):
    try:
        return P["pid_of"](n)
    except KeyError:
        return None


def proj(pid, target):
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            return P["project"](pid, target)
        except Exception:
            return None


# ---- '26 rows: vets projected from '23–'25, 20+ GP in '26
rows = []
for r in D48["rows"]:
    if not r["last"] or r["act"]["gp"] < 20:
        continue
    pid = r["pid"]
    g = proj(pid, "2025-26")
    if not g:
        continue
    rows.append(dict(name=r["name"], pid=pid, age=r["age"], moved=r["moved"], base=g["base"], gap=g["gap"],
                     gp25=int(A["2024-25"].GP.get(pid, 0)), gp26=r["act"]["gp"], mpg26=r["act"]["mpg"],
                     last=r["last"]["fp"], proj=g["fp"], act=r["act"]["fp"], epm_flag=g["epm_flag"],
                     proj_mpg=g["mpg"], act_mpg=r["act"]["mpg"], last_mpg=r["last"]["mpg"]))
# ---- base season not '25 (missed most of '25)
injured25 = [x for x in rows if x["base"] != "2024-25"]
# ---- hurt during '26 (under 40 GP): per-game when playing
hurt26 = [x for x in rows if x["gp26"] < 40 and x["last"] >= 15]
# ---- '27: flags
b = B27.head(150)
inj27 = [dict(name=x.name, team=x.team, rank=int(x.rank), fp=float(x.fp), flags=x.flags if isinstance(x.flags, str) else "")
         for x in b.itertuples() if isinstance(x.flags, str) and "injured" in x.flags]
for d in inj27:
    pid = pid_of(d["name"])
    g = proj(pid, "2026-27")
    d["base"], d["gp26"] = g["base"], int(A["2025-26"].GP.get(pid, 0))
    a25 = actual(pid, "2024-25")
    d["fp25"] = a25["fp"] if a25 else None
    a26 = actual(pid, "2025-26")
    d["fp26"] = a26["fp"] if a26 else None
epm = pd.read_csv(R + "epm_manual_2025_26.csv", comment="#")
epm_rows = []
for x in epm.itertuples():
    pid = pid_of(x.name)
    if pid is None:
        continue
    a = actual(pid, "2025-26")
    if not a or a["gp"] < 20:
        continue
    epm_rows.append(dict(name=x.name, epm=float(x.epm), fp=a["fp"], mpg=a["mpg"]))
flag27 = []
for x in B27.itertuples():
    if isinstance(x.flags, str) and "EPM" in x.flags:
        pid = int(x.pid)
        a = actual(pid, "2025-26")
        flag27.append(dict(name=x.name, team=x.team, rank=int(x.rank), fp=float(x.fp), mpg=float(x.mpg),
                           fp26=a["fp"] if a else None, mpg26=a["mpg"] if a else None,
                           epm=float(epm.set_index("name").epm.get(x.name, np.nan))))
# ---- eight for '27
eight = []
for n in EIGHT:
    pid = pid_of(n)
    g = proj(pid, "2026-27")
    a26 = actual(pid, "2025-26")
    a25 = actual(pid, "2024-25")
    eight.append(dict(name=n, age=g["age"], base=g["base"], gp26=int(A["2025-26"].GP.get(pid, 0)), gp25=int(A["2024-25"].GP.get(pid, 0)),
                      fp26=a26["fp"] if a26 else None, fp25=a25["fp"] if a25 else None, fp=g["fp"], mpg=g["mpg"],
                      mpg26=a26["mpg"] if a26 else None, epm=float(epm.set_index("name").epm.get(n, np.nan)),
                      stayed=bool(g["stayed"]), team=g["team"]))
# ---- rookies
va = RK["va"]
rook26 = [dict(name=x["name"], pick=int(x.pick), team=x.team, height=float(x.height), weight=float(x.weight), tdiff=float(x.tdiff),
               proj=float(x.proj_fp), act=float(x.fp), proj_mpg=float(x.proj_mpg), act_mpg=float(x.mpg), gp=int(x.gp)) for _, x in va.iterrows()]
fits = {k: [float(v) for v in RK["fits"][k]] for k in RK["fits"]}
fw = {k: [float(v) for v in RK["fw"][k]] for k in RK["fw"]}
ok = RK["ok"].sort_values("pick")
rook27 = [dict(name=x["name"], pick=int(x.pick), team=x.team, height=float(x.height), weight=float(x.weight), tdiff=float(x.tdiff),
               fp=float(x.fp), mpg=float(x.mpg)) for _, x in ok.head(20).iterrows()]
tr = RK["tr"]
cls_avg = {s: float(tr[tr.season == s].fp.mean()) for s in sorted(tr.season.unique())}
json.dump(dict(rows=rows, injured25=injured25, hurt26=hurt26, inj27=inj27, epm_rows=epm_rows, flag27=flag27, eight=eight,
               rook26=rook26, fits=fits, fw=fw, rook27=rook27, ntrain=int(len(tr))),
          open(S + "sec912.json", "w"), default=lambda o: None if o is None else float(o))
print(len(rows), "vets;", len(injured25), "base≠'25;", len(hurt26), "hurt '26;", len(inj27), "injured '27;", len(epm_rows), "EPM;",
      len(flag27), "flagged '27;", len(rook26), "rookies '26")
