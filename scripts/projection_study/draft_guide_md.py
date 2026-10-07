"""Writes DRAFT_GUIDE.md from draft_guide.json."""
import json

S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
D = json.load(open(S + "draft_guide.json"))
NAMES = {"any3": "3 starters, any player (no positions)", "gfc": "1 G / 1 F / 1 C", "gfcx": "1 G / 1 F / 1 C / 1 FLX"}
L = []
w = L.append
w("# Draft guide — the gap to replacement, and how big a TEAM slot should be\n")
w("Running analysis (started 2026-10-07). Theorycrafting, not final: **PROJ MAX is taken as unbiased** (no availability, "
  "no bench, players only). Purpose: know how much each player slot is worth over replacement, so the TEAM slot's "
  "scoring (being reworked) can be sized to an appropriate importance next to them. Numbers come from "
  "`scripts/projection_study/draft_guide.py` on the 2026-27 pool (PROJ MAX under the real schedule).\n")
w("## The formula\n")
w("- **Value over replacement**: VOR = PROJ MAX − replacement, where replacement = the best player still undrafted "
  "who can fill **the slot he fills** once every team's starters are taken (a C slot only takes centers; FLX or ANY takes anyone).")
w("- Starters are filled best PROJ MAX first, most specific slot first (his position, then FLX / ANY). This is the "
  "\"everyone drafts by PROJ MAX\" baseline.")
w("- **The answer to \"what's the gap between the player I can draft now and a replacement-level player\"** is his VOR: "
  "how many points a week he adds over what you'd start in that spot for free.")
w("- **What a point is worth**: one matchup's score difference swings with an SD of about 20 FP a week with 3 starters "
  "and 23 with 4 (each player's 3-game weekly score swings ±9–10). So **+1 point a week ≈ +2% weekly win probability** "
  "(+1.7% with 4 starters). Jokić at 8 teams, G/F/C (+17.6) ≈ +33% a week over a replacement center.")
w("- Auction, if wanted: $ = min bid + VOR ÷ total starter VOR × (teams × budget − starters × min bid). Below "
  "replacement = the minimum bid.\n")

w("## Slot value, by setup and league size\n")
w("Per slot: replacement level, the best player at it and his VOR, and the **average starter's VOR** (the slot's "
  "importance: how much a typical team gains from filling it well).\n")
for setup in ("any3", "gfc", "gfcx"):
    w(f"### {NAMES[setup]}\n")
    slots = list(D[f"{setup}|4"]["by_slot"])
    w("| Teams | " + " | ".join(f"{s}: replacement / best (VOR) / avg starter VOR" for s in slots) + " | +1 pt/week |")
    w("|---|" + "---|" * len(slots) + "---|")
    for N in (4, 8, 10, 12):
        v = D[f"{setup}|{N}"]
        cells = [f"{b['repl']:.1f} / {b['best_name'].split()[-1]} +{b['best_vor']:.1f} / **+{b['avg_vor']:.1f}**" for b in v["by_slot"].values()]
        w(f"| {N} | " + " | ".join(cells) + f" | +{100 * v['win1']:.1f}% win |")
    w("")
w("**What it says**")
w("- **C is the scarce slot.** Good centers run out fast, so the average starting C is worth +6 to +8 over replacement, "
  "against G +3 to +6 and F under +4 (forwards are plentiful, so the one left over is nearly as good).")
w("- **A FLX slot adds almost nothing** (+0.7 to +1.0 per starter): its replacement is the best leftover player of any "
  "position, so the gap is small. What FLX does is raise the G replacement level (guards spill into it).")
w("- **With no positions**, all value sits in the top five (Jokić, Wembanyama, Luka, SGA, Tatum); every other starter "
  "is within a few points of replacement (average starter +4).")
w("- Bigger leagues lower replacement and widen every gap, most at C (Jokić +13 at 4 teams → +21 at 12).\n")

w("## The gap pick by pick\n")
w("VOR of the player taken at each overall pick when everyone drafts by PROJ MAX (no positions shown = ANY).\n")
for setup in ("any3", "gfc", "gfcx"):
    for N in (4, 8, 12):
        st = D[f"{setup}|{N}"]["st"]
        w(f"**{NAMES[setup]}, {N} teams**: " + ", ".join(f"{i + 1}. {p['name'].split()[-1]} ({p['slot']}) +{p['vor']:.1f}" for i, p in enumerate(st[:max(8, N)])) + "\n")

w("## Sizing the TEAM slot\n")
w("To make TEAM as important as a player slot, its scoring should give the **same gap between the average starting "
  "NBA team and the best team left over** as a player slot does — and a similar week-to-week swing (±9–10), so it "
  "neither decides matchups by itself nor disappears into the noise.\n")
w("| Setup | Teams | Weakest player slot (avg starter VOR) | Average player slot | Strongest (C) | Best single player at a slot |")
w("|---|---|---|---|---|---|")
for setup in ("gfc", "gfcx"):
    for N in (4, 8, 10, 12):
        bs = D[f"{setup}|{N}"]["by_slot"]
        vals = {s: b["avg_vor"] for s, b in bs.items()}
        pos = {s: v for s, v in vals.items() if s != "FLX"}
        w(f"| {NAMES[setup]} | {N} | {min(pos, key=pos.get)} +{min(pos.values()):.1f} | +{sum(pos.values()) / len(pos):.1f} | "
          f"+{bs['C']['avg_vor']:.1f} | {max(bs.values(), key=lambda b: b['best_vor'])['best_name']} +{max(b['best_vor'] for b in bs.values()):.1f} |")
w("")
w("- **Target for an average starting TEAM: about +3 to +5 over the replacement team** (between F and C), with the "
  "best NBA team about +6 to +10 over replacement (like the best G or F, not Jokić-level).")
w("- For reference, the current structure (point margin totaled over the week) gave the average starting TEAM "
  "+9.8 to +11.8 over replacement at 8–12 teams on '26 actual weeks (PROJECTIONS.md, Positions) — about twice a "
  "C and three to six times a G or F. It needs to come down by roughly half to two-thirds.\n")
w("## Draft decisions (commissioner's notes, 2026-10-07)\n")
w("Example: 4 teams, snake. Jokić, SGA and Luka go 1–3; you pick 4 and 5, and still need a G, an F and a C.\n")
w("**The rule, ignoring the other teams:**")
w("1. Take the biggest gap over replacement among your **open G / F / C slots**. At pick 5 that's the best center left "
  "(Wembanyama, +10 over the replacement C at 4 teams): the scarce role beats the best player overall.")
w("2. **FLX last.** Its gap is always the smallest (+1 to +3 per starter), because anyone can fill it: its replacement "
  "is the best leftover player of any position. So FLX doesn't complicate the order — it's simply the last slot you "
  "fill, with the best player left.\n")
w("**The one real complication is the other teams (denial).** Taking a second center you don't need for your C slot "
  "takes value away from an opponent: he drops toward the replacement C, the steepest drop at any position. In "
  "head-to-head every point taken from a rival's lineup counts in the weeks you face him (every third week in a "
  "4-team league). This exists with or without FLX; FLX just makes it cheaper, because the second center has a slot "
  "to play in. The replacement math above ignores it. Measuring it needs a draft simulation (opponents draft by need "
  "and value; you try each choice; compare lineups over simulated weeks) — not built.\n")
w("## Not in here yet")
w("- Availability (missed weeks), bench depth (raises replacement), and in-season waivers.")
w("- The TEAM scoring itself — this only sets the target it should hit.")
open("/Users/allan/PycharmProjects/2026_pickem/DRAFT_GUIDE.md", "w").write("\n".join(L) + "\n")
print("written", len(L), "lines")
