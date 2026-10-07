"""Draft guide numbers: value over replacement (VOR) on PROJ MAX (taken as unbiased), three roster setups × league
sizes, auction prices, and what a point of weekly score is worth in weekly win probability. Reads the local app DB
(fantasy_pool for 2026-27, loaded by scripts/load_projections.py)."""
import json
import math
import psycopg2
import psycopg2.extras

conn = psycopg2.connect("dbname=pickem_local")
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("""SELECT player_id, name, nba_team, position, proj_avg, proj_max, proj_week
               FROM fantasy_pool WHERE season = '2026-27' AND proj_max IS NOT NULL ORDER BY proj_max DESC""")
P = [dict(r) for r in cur.fetchall()]
for p in P:
    c = p["proj_week"]
    p["sd_week"] = (c["p90"][2] - c["p25"][2]) / 1.956  # spread of his 3-game weekly score (normal approx, 25th–90th)
SETUPS = {"any3": {"ANY": 3}, "gfc": {"G": 1, "F": 1, "C": 1}, "gfcx": {"G": 1, "F": 1, "C": 1, "FLX": 1}}


def starters(setup, N):
    """Every team fills its starting slots, best PROJ MAX first, most specific slot first (his position, then FLX /
    ANY). Replacement at a slot = best player left who can fill it."""
    slots = SETUPS[setup]
    open_ = {k: v * N for k, v in slots.items()}
    taken, out = set(), []
    for p in P:
        for s in ([p["position"]] if p["position"] in open_ else []) + [x for x in ("FLX", "ANY") if x in open_]:
            if open_[s] > 0:
                open_[s] -= 1
                taken.add(p["player_id"])
                out.append({**p, "slot": s})
                break
        if sum(open_.values()) == 0:
            break
    rest = [p for p in P if p["player_id"] not in taken]
    repl = {s: next((p["proj_max"] for p in rest if s in ("ANY", "FLX") or p["position"] == s), 0.0) for s in slots}
    # His replacement: the best leftover who can fill the slot he fills (a C slot takes only centers; FLX / ANY anyone).
    for p in out:
        p["repl"] = repl[p["slot"]]
        p["vor"] = p["proj_max"] - p["repl"]
    return out, repl, sum(slots.values())


def auction(st, N, K, budget=200, minbid=1):
    """Money above the minimum bids, split in proportion to VOR: $ = min bid + VOR / total VOR × (N·budget − N·K·min bid)."""
    pot = N * budget - N * K * minbid
    tot = sum(max(p["vor"], 0) for p in st)
    for p in st:
        p["price"] = minbid + pot * max(p["vor"], 0) / tot
    return pot / tot  # dollars per point of VOR


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


res = {}
for setup in SETUPS:
    for N in (4, 8, 10, 12):
        st, repl, K = starters(setup, N)
        per_pt = auction(st, N, K)
        sd_team = math.sqrt(sum(p["sd_week"] ** 2 for p in st) / len(st) * K)  # a typical lineup's weekly score SD
        sd_diff = math.sqrt(2) * sd_team                                         # one matchup: your score − his
        by_slot = {}
        for s in SETUPS[setup]:
            q = [p for p in st if p["slot"] == s]
            by_slot[s] = dict(n=len(q), best=q[0]["proj_max"], best_vor=q[0]["vor"], avg_vor=sum(p["vor"] for p in q) / len(q), repl=repl[s],
                              best_name=q[0]["name"], sd_week=sum(p["sd_week"] for p in q) / len(q))
        res[f"{setup}|{N}"] = dict(repl=repl, K=K, per_pt=per_pt, sd_team=sd_team, sd_diff=sd_diff, by_slot=by_slot,
                                   win1=phi(1 / sd_diff) - 0.5,
                                   st=[{k: p[k] for k in ("name", "nba_team", "position", "slot", "proj_avg", "proj_max", "repl", "vor", "price")} for p in st])
json.dump(res, open("/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/draft_guide.json", "w"), default=float)
for key, v in res.items():
    st = v["st"]
    print(f"\n{key}: " + "  ".join(f"{s}: best {b['best_name'].split()[-1]} +{b['best_vor']:.1f}, avg starter +{b['avg_vor']:.1f}, repl {b['repl']:.1f}" for s, b in v["by_slot"].items()))
    print(f"   replacement {({k: round(x, 1) for k, x in v['repl'].items()})}  ${v['per_pt']:.2f}/VOR pt  matchup SD {v['sd_diff']:.1f} → +1 pt/wk = +{100 * v['win1']:.1f}% win")
    for p in st[:5] + st[-2:]:
        print(f"   {p['name']:<24} {p['position']} {p['slot']:<4} PROJ MAX {p['proj_max']:5.1f}  repl {p['repl']:5.1f}  VOR {p['vor']:5.1f}  ${p['price']:5.1f}")
