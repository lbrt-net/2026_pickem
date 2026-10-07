"""Data for sections 13 (positions), 14 (player cards, the random eight), 15 (2026-27 board, top 50)."""
import contextlib, io, json, os, runpy
import numpy as np, pandas as pd
os.environ["APPLY_LATE"] = "1"
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
R = "/Users/allan/PycharmProjects/nba-pipeline/data/raw/"
with contextlib.redirect_stdout(io.StringIO()):
    P = runpy.run_path(S + "pipeline.py", run_name="lib")
    SB = runpy.run_path(S + "slot_balance.py", run_name="lib")
A, actual = P["A"], P["actual"]
tm = SB["tm"]


def pid_of(n):
    try:
        return P["pid_of"](n)
    except KeyError:
        return None


rp = pd.read_csv(R + "role_positions_single_2025_26.csv", index_col=0)
rp["pos"] = rp["pos"].fillna("—")


def slots(col, N):
    order = rp.sort_values("val", ascending=False)
    used, out = set(), {}
    for s in ("G", "F", "C"):
        q = order[(order[col] == s) & ~order.index.isin(used)]
        used |= set(q.head(N).index)
        out[s] = (q.val.head(N).mean(), q.val.iloc[N] if len(q) > N else np.nan)
    rest = order[~order.index.isin(used)]
    out["FLX"] = (rest.val.head(N).mean(), rest.val.iloc[N])
    out["TEAM"] = (tm.head(N).mean(), tm.iloc[N])
    return {k: round(float(a - b), 1) for k, (a, b) in out.items()}


bal = {N: dict(old=slots("pos", N), new=slots("final", N)) for N in (8, 10, 12)}
counts = {c: rp[c].value_counts().to_dict() for c in ("pos", "final")}
pts = [dict(name=r.name, grp=r.final, big=float(r.big), create=float(r.create), val=float(r.val)) for r in rp.itertuples() if r.big == r.big and r.create == r.create]
chk_names = ["Shai Gilgeous-Alexander", "Luka Dončić", "Nikola Jokić", "Giannis Antetokounmpo", "LeBron James", "Anthony Edwards", "Jayson Tatum",
             "Kevin Durant", "Cade Cunningham", "Victor Wembanyama", "Stephen Curry", "Jalen Brunson", "Scottie Barnes", "Lauri Markkanen",
             "Bam Adebayo", "Karl-Anthony Towns", "Josh Giddey", "Evan Mobley"]
chk = [dict(name=n, old=rp.pos[rp.name == n].iloc[0], new=rp.final[rp.name == n].iloc[0], big=float(rp.big[rp.name == n].iloc[0]),
            create=float(rp.create[rp.name == n].iloc[0])) for n in chk_names if (rp.name == n).any()]
B = pd.read_csv(R + "projections_2026_27.csv")
B["rank"] = np.arange(1, len(B) + 1)
top_pos = {s: [dict(rank=int(x.rank), name=x.name, team=x.team, fp=float(x.fp)) for x in B[B.pos == s].head(12).itertuples()] for s in ("G", "F", "C")}


def line(a):
    if not a:
        return None
    return dict(gp=int(a["gp"]), mpg=a["mpg"], pts=a["pts"], reb=a["oreb"] + a["dreb"], ast=a["ast"], stl=a["stl"], blk=a["blk"], tov=a["tov"],
                fg3m=a["fg3m"], fp=a["fp"])


EIGHT = [e["name"] for e in json.load(open(S + "sec48.json"))["eight"]]
cards = []
for n in EIGHT:
    pid = pid_of(n)
    with contextlib.redirect_stdout(io.StringIO()):
        g = P["project"](pid, "2026-27")
    seas = {s: line(actual(pid, s)) for s in ("2023-24", "2024-25", "2025-26")}
    usg = {s: float(A[s].USG_PCT.get(pid, np.nan)) for s in ("2023-24", "2024-25", "2025-26")}
    b = B[B.pid == pid].iloc[0]
    cards.append(dict(name=n, team=b.team, pos=b.pos, rank=int(b["rank"]), age=float(g["age"]), base=g["base"], stayed=bool(g["stayed"]),
                      seasons=seas, usg=usg, flags=b.flags if isinstance(b.flags, str) else "",
                      proj=dict(gp=None, mpg=g["mpg"], pts=g["pts"], reb=g["oreb"] + g["dreb"], ast=g["ast"], stl=g["stl"], blk=g["blk"], tov=g["tov"],
                                fg3m=g["fg3m"], fp=g["fp"], usg=g["usg"])))
board = []
for x in B.head(50).itertuples():
    pid = int(x.pid)
    a = line(actual(pid, "2025-26"))
    board.append(dict(rank=int(x.rank), name=x.name, team=x.team, pos=x.pos, age=float(x.age) if x.age == x.age else None, kind=x.kind,
                      fp=float(x.fp), mpg=float(x.mpg), pts=float(x.pts), reb=float(x.reb), ast=float(x.ast), flags=x.flags if isinstance(x.flags, str) else "",
                      a26=a))
json.dump(dict(bal=bal, counts=counts, pts=pts, chk=chk, top_pos=top_pos, cards=cards, board=board),
          open(S + "sec1316.json", "w"), default=lambda o: None if o is None else float(o))
print({N: v for N, v in bal.items()}, counts, len(cards), len(board))
