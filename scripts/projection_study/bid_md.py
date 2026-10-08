"""Writes BIDDING_GUIDE.md from bid_guide.json (every number from the data)."""
import json

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
B = json.load(open(S + "bid_guide.json"))
L = []
w = L.append
w("# Bidding guide — what a player is worth to you right now\n")
w("Auction drafts, lineup **G / F / C / TM / FLX** (FLX = any player or an NBA team), budget **$200**, minimum bid **$1**. "
  "Players: PROJ MAX including the clutch-points category (+2 per point scored in clutch time, his 3-season clutch "
  "average), counted at the 86% of weeks players actually play. NBA teams: TEAM scoring draft 6, every week. Running doc, "
  "started 2026-10-07.\n")
w("## The formula\n")
w("For the player on the block:\n")
w("1. **Which slot he'd fill on your roster**: his own position (G, F or C; an NBA team → TM) if that slot is open, "
  "otherwise FLX if FLX is open. Neither open → he's worth **$0** to you (no bench).")
w("2. **Points over replacement** for that slot = his weekly value − the replacement level for that slot (tables below). "
  "Weekly value = PROJ MAX × 0.86 for a player, the TEAM projection for a team.")
w("3. **Fair price** = $1 + points over replacement × the **going rate** (dollars per point a week, below).")
w("4. **Your money adjustment**: multiply by *(your dollars − $1 × your open slots) ÷ (your open slots × $39)* — $39 is "
  "the average money above the minimum per slot at the start ($195 ÷ 5). Flush with money → bid up; short → bid down.")
w("5. **Never bid more than** your dollars − $1 × (your open slots − 1), so you can still fill every slot.\n")
w("The going rate = all the league's money above the $1 minimums ÷ all the starters' points over replacement, so the "
  "fair prices of every starter add up to exactly the league's money (checked below).\n")
for N in ("4", "8", "12"):
    b = B[N]
    w(f"## {N} teams\n")
    w(f"Going rate **${b['k']:.2f} per point a week**. Fair prices of all {5 * int(N)} starters add to **${b['check']:.0f}** = "
      f"the league's money (${b['total']}).\n")
    w("| Slot | Replacement level (weekly value) | Average starter's fair price | Top three |")
    w("|---|---|---|---|")
    for s in ("G", "F", "C", "TM", "FLX"):
        w(f"| {s} | {b['repl'][s]:.1f} | ${b['slot_avg'][s]:.0f} | " + ", ".join(f"{n} ${p:.0f}" for n, p in b["slot_top"][s]) + " |")
    w("")
    w("Fair price at the start of the draft, by which of your slots he'd fill:\n")
    w("| Player | Pos | PROJ MAX | Fills his own slot | Fills FLX |")
    w("|---|---|---|---|---|")
    for r in b["rows"][:30]:
        w(f"| {r['name']} | {r['pos']} | {r['proj']:.1f} | {'$%d' % r['own'] if r['own'] is not None else '—'} | ${r['flx']:.0f} |")
    w("")
b4 = {r["name"]: r for r in B["4"]["rows"]}
gap = sorted([r for r in B["4"]["rows"] if r["own"] is not None and r["own"] - r["flx"] >= 10], key=lambda r: -(r["own"] - r["flx"]))[:3]
w("## Reading it\n")
w(f"- **Centers are where the money goes.** Good centers are scarce: at 4 teams the average starting C is worth "
  f"${B['4']['slot_avg']['C']:.0f}, a G ${B['4']['slot_avg']['G']:.0f}, an F ${B['4']['slot_avg']['F']:.0f}.")
w("- **FLX is cheap.** Its replacement is the best player left of any position, so a player bought only for FLX is worth "
  "less: " + "; ".join(f"{r['name']} ${r['own']:.0f} in his own slot vs ${r['flx']:.0f} in FLX" for r in gap) + " (4 teams).")
w("- **Your second guard or center is a FLX buy**: once your own slot is filled, price him off the FLX column.")
w(f"- **TEAMs fill TM**: the average starting TEAM is worth ${B['4']['slot_avg']['TM']:.0f} at 4 teams, "
  f"${B['8']['slot_avg']['TM']:.0f} at 8, ${B['12']['slot_avg']['TM']:.0f} at 12 — about a forward. A TEAM is never worth anything in FLX (players beat teams there).")
w("- **Small leagues flatten everything**: at 4 teams only the top ~15 are worth real money; at 8, about the top 40; at 12, about the top 60.\n")
w("## For the draft room (backend)\n")
w("- Inputs per entity: weekly value (PROJ MAX × 0.86 for players, TEAM projection for teams) and slot eligibility. Per "
  "league: replacement level per slot and the going rate, from filling every team's starters best-first at the start of "
  "the draft (`scripts/projection_study/bid_guide.py`). Per viewer: open slots and dollars left → steps 1–5 above = the "
  "Rec bid.")
w("- Numbers here are from the local 2026-27 pool with clutch included; prod isn't loaded with the clutch version yet.")
open("/Users/allan/PycharmProjects/2026_pickem/BIDDING_GUIDE.md", "w").write("\n".join(L) + "\n")
print("ok")
