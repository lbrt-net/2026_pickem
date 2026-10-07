"""Player-level data for sections 4–8: '26 projection vs last season vs actual, per component; plus the random eight for '27."""
import contextlib, io, json, os, runpy
import numpy as np, pandas as pd
os.environ["APPLY_LATE"] = "1"
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
with contextlib.redirect_stdout(io.StringIO()):
    P = runpy.run_path(S + "pipeline.py", run_name="lib")
A, ZS, ZONES, actual, BLKA = P["A"], P["ZS"], P["ZONES"], P["actual"], P["BLKA"]


def raw(s):
    rs = json.load(open(f"{R}player_advanced/{s}.json"))["resultSets"][0]
    return pd.DataFrame(rs["rowSet"], columns=rs["headers"]).set_index("PLAYER_ID")


RA = {s: raw(s) for s in ["2024-25", "2025-26"]}
first26 = P["FIRST"]["2025-26"]


def zone(pid, s):
    a = np.array([ZS[s]["fga"][z].get(pid, 0) if z in ZS[s]["fga"] else 0 for z in ZONES], float)
    m = np.array([ZS[s]["fgm"][z].get(pid, 0) if z in ZS[s]["fgm"] else 0 for z in ZONES], float)
    return a, m


def season(pid, s):
    a = actual(pid, s)
    if not a or pid not in RA[s].index:
        return None
    ad = RA[s].loc[pid]
    pg = float(ad.POSS / ad.GP)
    za, zm = zone(pid, s)
    out = dict(gp=int(a["gp"]), mpg=a["mpg"], poss=pg, fp=a["fp"], ft_pct=a["ftm"] / a["fta"] if a["fta"] else None,
               fta=a["fta"], blkd=a["blkd"], fga=a["fga"], fg3a=None, fgm=a["fgm"],
               share=list(za / za.sum()) if za.sum() else None, zpct=[float(m / x) if x else None for m, x in zip(zm, za)],
               zatt=list(za), fg_pct=a["fgm"] / a["fga"] if a["fga"] else None, dreb_pct=float(ad.DREB_PCT), oreb_pct=float(ad.OREB_PCT))
    for st in ["fga", "fta", "oreb", "dreb", "ast", "stl", "blk", "tov", "pts"]:
        out[st + "75"] = 75 * a[st] / pg
        out[st] = a[st]
    out["fgpts"] = a["pts"] - a["ftm"]
    return out


rows = []
for pid in RA["2025-26"].index:
    act = season(pid, "2025-26")
    if not act or act["gp"] < 20:
        continue
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            g = P["project"](pid, "2025-26")
        except Exception:
            g = None
    if not g:
        continue
    last = season(pid, "2024-25")
    pr = dict(mpg=g["mpg"], poss=g["poss"], fp=g["fp"], share=g["share"], zpct=g["zone_pct"], fga=g["fga"], fgm=g["fgm"],
              fg_pct=g["fgm"] / g["fga"] if g["fga"] else None, fta=g["fta"], ft_pct=g["ftm"] / g["fta"] if g["fta"] else None,
              blkd=g["blkd"], blkd_factor=g["blkd_factor"], dreb_shift=g["dreb_shift"], fgpts=g["pts"] - g["ftm"])
    for st in ["fga", "fta", "oreb", "dreb", "ast", "stl", "blk", "tov", "pts"]:
        pr[st + "75"] = 75 * g[st] / g["poss"]
        pr[st] = g[st]
    t25 = RA["2024-25"].TEAM_ABBREVIATION.get(pid)
    rows.append(dict(pid=int(pid), name=RA["2025-26"].PLAYER_NAME[pid], age=float(RA["2025-26"].AGE[pid]),
                     moved=bool(t25 and first26.get(pid) and t25 != first26.get(pid)), team=first26.get(pid), proj=pr, last=last, act=act))
s27 = json.load(open(S + "sec23b.json"))["sample27"]
eight = []
for r in s27:
    pid = P["pid_of"](r["name"])
    with contextlib.redirect_stdout(io.StringIO()):
        g = P["project"](pid, "2026-27")
    a26 = season(pid, "2025-26")
    eight.append(dict(name=r["name"], team=r["team"], rank=r["rank"], last=a26,
                      proj=dict(share=g["share"], zpct=g["zone_pct"], fga=g["fga"], fgm=g["fgm"], fg3m=g["fg3m"], fg3a=g["fg3a"], fta=g["fta"],
                                ft_pct=g["ftm"] / g["fta"] if g["fta"] else None, oreb=g["oreb"], dreb=g["dreb"], ast=g["ast"], stl=g["stl"],
                                blk=g["blk"], tov=g["tov"], blkd=g["blkd"], pts=g["pts"], fp=g["fp"], dreb_shift=g["dreb_shift"])))
json.dump(dict(rows=rows, eight=eight, zones=ZONES), open(S + "sec48.json", "w"), default=lambda o: None if o is None else float(o))
print(len(rows), "players;", [e["name"] for e in eight])
