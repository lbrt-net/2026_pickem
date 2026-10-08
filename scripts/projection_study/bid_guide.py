"""Auction bidding guide for the lineup G / F / C / TM / FLX (FLX = any player or an NBA team). Budget $200, min bid $1.
Players: PROJ MAX (2026-27 pool), counted at the 86% of weeks they play; TEAMs: draft 6 projections, every week.
For N teams: fill every team's starters best-first (most specific slot first), replacement level per slot = the best one
left who can fill it; market rate = money above minimums ÷ all starters' points over replacement; check that fair prices
of all starters add up to the league's money. → bid_guide.json"""
import json
import pandas as pd
import psycopg2, psycopg2.extras

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
AVAIL, BUDGET, MINBID = 0.86, 200, 1
SLOTS = ["G", "F", "C", "TM", "FLX"]
cur = psycopg2.connect("dbname=pickem_local").cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("SELECT name, position, nba_team, proj_max FROM fantasy_pool WHERE season = '2026-27' AND proj_max IS NOT NULL")
pl = pd.DataFrame(cur.fetchall()).assign(kind="player", avail=AVAIL)
tm = pd.DataFrame(json.load(open(S + "team_draft4.json"))["res"]["draft 4"]["proj"]).rename(columns={"team": "name"})
tm = tm.assign(position="TM", nba_team=tm.name, kind="team", avail=1.0)[["name", "position", "nba_team", "proj_max", "kind", "avail"]]
POOL = pd.concat([pl, tm]).sort_values("proj_max", ascending=False).reset_index(drop=True)
# rank on value as it counts in a season (players miss weeks)
POOL["eff"] = POOL.proj_max * POOL.avail


def fits(pos, slot):
    return slot == "FLX" or pos == slot


def fill(N):
    open_ = {s: N for s in SLOTS}
    taken, starters = set(), []
    for i, p in POOL.sort_values("eff", ascending=False).iterrows():
        for s in ([p.position] if p.position in open_ else []) + ["FLX"]:
            if open_[s] > 0:
                open_[s] -= 1
                taken.add(i)
                starters.append((i, s))
                break
        if sum(open_.values()) == 0:
            break
    rest = POOL.drop(index=list(taken))
    repl = {s: float(rest[rest.position.map(lambda q: fits(q, s))].eff.max()) for s in SLOTS}
    st = POOL.loc[[i for i, _ in starters]].assign(slot=[s for _, s in starters])
    st["por"] = st.eff - st.slot.map(repl)
    return st, repl


out = {}
for N in (4, 8, 12):
    st, repl = fill(N)
    money = N * BUDGET - N * len(SLOTS) * MINBID
    k = money / st.por.clip(lower=0).sum()
    st["fair"] = MINBID + k * st.por.clip(lower=0)
    check = st.fair.sum()
    # what a player is worth to YOU by your open slots
    rows = []
    for _, p in POOL.sort_values("eff", ascending=False).head(60).iterrows():
        own = p.position if p.position in SLOTS[:4] else None
        por_own = p.eff - repl[own] if own else None
        por_flx = p.eff - repl["FLX"]
        rows.append(dict(name=p["name"], pos=p.position, proj=float(p.proj_max), eff=float(p.eff),
                         own=None if por_own is None else round(float(MINBID + k * max(por_own, 0)), 0),
                         flx=round(float(MINBID + k * max(por_flx, 0)), 0)))
    out[N] = dict(repl=repl, k=k, check=check, total=N * BUDGET, slot_avg={s: float(st[st.slot == s].fair.mean()) for s in SLOTS},
                  slot_top={s: st[st.slot == s].sort_values("fair", ascending=False).head(3)[["name", "fair"]].values.tolist() for s in SLOTS}, rows=rows)
    print(f"\n{N} teams: replacement {({s: round(v, 1) for s, v in repl.items()})}; ${k:.2f} per point a week; "
          f"fair prices of all {len(st)} starters add to ${check:.0f} (league money ${N * BUDGET})")
    print("  average starter price by slot:", {s: round(v) for s, v in out[N]["slot_avg"].items()})
    for r in rows[:14]:
        print(f"   {r['name']:<24} {r['pos']}  PROJ {r['proj']:5.1f}  in his slot ${r['own'] if r['own'] is not None else '—'}  in FLX ${r['flx']}")
json.dump(out, open(S + "bid_guide.json", "w"), default=float)
