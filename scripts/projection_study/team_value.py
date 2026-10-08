"""TEAM vs players on one draft board (lineup G / F / C / TEAM). Players' value over replacement is discounted to the share
of fantasy weeks they actually play (AVAIL, '24–'26 top 100 = 86%; when a player sits you start a replacement); TEAMs never
miss. → team_value.json"""
import json, math
import pandas as pd

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
AVAIL = 0.86
DG = json.load(open(S + "draft_guide.json"))
R = json.load(open(S + "team_draft4.json"))["res"]["draft 4"]
P = pd.DataFrame(R["proj"]).sort_values("proj_max", ascending=False).reset_index(drop=True)
team_sd = R["sd"]
sd = math.sqrt(2 * (3 * 9.5 ** 2 + team_sd ** 2))  # one matchup's swing: 3 players (±9.5 a week each) + TEAM, both sides
per_pt = math.erf(1 / sd / math.sqrt(2))  # +1 point a week → this much more weekly win probability
out = {"avail": AVAIL}
for N in (4, 8, 12):
    st = pd.DataFrame(DG[f"gfc|{N}"]["st"])[["name", "slot", "proj_max", "vor"]].assign(vor=lambda d: d.vor * AVAIL)
    repl = float(P.proj_max.iloc[N])
    tm = P.head(N).assign(name=lambda d: d.team, slot="TEAM", vor=lambda d: d.proj_max - repl)[["name", "slot", "proj_max", "vor"]]
    board = pd.concat([st, tm]).sort_values("vor", ascending=False).reset_index(drop=True)
    board["pick"] = board.index + 1
    sl = {s: float(st[st.slot == s].vor.mean()) for s in ("G", "F", "C")}
    out[str(N)] = dict(per_pt=per_pt, repl=repl, team_avg=float(tm.vor.mean()), team_best=float(tm.vor.max()), g=sl["G"], f=sl["F"], c=sl["C"],
                       jokic=float(st.vor.max()), teams=board[board.slot == "TEAM"].to_dict("records"))
    t = out[str(N)]
    print(f"{N} teams: TEAM avg +{t['team_avg']:.1f} best +{t['team_best']:.1f} | G {t['g']:+.1f} F {t['f']:+.1f} C {t['c']:+.1f} Jokić +{t['jokic']:.1f} | "
          + ", ".join(f"{y['name']} #{y['pick']}" for y in t["teams"][:5]))
print(f"+1 point a week ≈ +{100 * per_pt:.1f}% weekly win")
json.dump(out, open(S + "team_value.json", "w"), default=float)
