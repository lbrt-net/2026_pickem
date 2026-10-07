# Draft guide — the gap to replacement, and how big a TEAM slot should be

Running analysis (started 2026-10-07). Theorycrafting, not final: **PROJ MAX is taken as unbiased** (no availability, no bench, players only). Purpose: know how much each player slot is worth over replacement, so the TEAM slot's scoring (being reworked) can be sized to an appropriate importance next to them. Numbers come from `scripts/projection_study/draft_guide.py` on the 2026-27 pool (PROJ MAX under the real schedule).

## The formula

- **Value over replacement**: VOR = PROJ MAX − replacement, where replacement = the best player still undrafted who can fill **the slot he fills** once every team's starters are taken (a C slot only takes centers; FLX or ANY takes anyone).
- Starters are filled best PROJ MAX first, most specific slot first (his position, then FLX / ANY). This is the "everyone drafts by PROJ MAX" baseline.
- **The answer to "what's the gap between the player I can draft now and a replacement-level player"** is his VOR: how many points a week he adds over what you'd start in that spot for free.
- **What a point is worth**: one matchup's score difference swings with an SD of about 20 FP a week with 3 starters and 23 with 4 (each player's 3-game weekly score swings ±9–10). So **+1 point a week ≈ +2% weekly win probability** (+1.7% with 4 starters). Jokić at 8 teams, G/F/C (+17.6) ≈ +33% a week over a replacement center.
- Auction, if wanted: $ = min bid + VOR ÷ total starter VOR × (teams × budget − starters × min bid). Below replacement = the minimum bid.

## Slot value, by setup and league size

Per slot: replacement level, the best player at it and his VOR, and the **average starter's VOR** (the slot's importance: how much a typical team gains from filling it well).

### 3 starters, any player (no positions)

| Teams | ANY: replacement / best (VOR) / avg starter VOR | +1 pt/week |
|---|---|---|
| 4 | 36.5 / Jokić +12.7 / **+4.0** | +2.0% win |
| 8 | 34.2 / Jokić +14.9 / **+3.7** | +2.0% win |
| 10 | 33.5 / Jokić +15.7 / **+3.7** | +2.0% win |
| 12 | 32.5 / Jokić +16.7 / **+4.0** | +2.0% win |

### 1 G / 1 F / 1 C

| Teams | G: replacement / best (VOR) / avg starter VOR | F: replacement / best (VOR) / avg starter VOR | C: replacement / best (VOR) / avg starter VOR | +1 pt/week |
|---|---|---|---|---|
| 4 | 37.6 / Dončić +7.2 / **+3.6** | 34.8 / Tatum +5.4 / **+2.3** | 35.8 / Jokić +13.4 / **+6.3** | +1.9% win |
| 8 | 36.5 / Dončić +8.4 / **+2.8** | 34.1 / Tatum +6.1 / **+1.7** | 31.6 / Jokić +17.6 / **+6.3** | +2.0% win |
| 10 | 34.2 / Dončić +10.6 / **+4.4** | 33.8 / Tatum +6.4 / **+1.7** | 28.8 / Jokić +20.4 / **+7.6** | +2.0% win |
| 12 | 33.3 / Dončić +11.5 / **+4.6** | 33.5 / Tatum +6.7 / **+1.7** | 28.0 / Jokić +21.2 / **+7.2** | +2.0% win |

### 1 G / 1 F / 1 C / 1 FLX

| Teams | G: replacement / best (VOR) / avg starter VOR | F: replacement / best (VOR) / avg starter VOR | C: replacement / best (VOR) / avg starter VOR | FLX: replacement / best (VOR) / avg starter VOR | +1 pt/week |
|---|---|---|---|---|---|
| 4 | 36.5 / Dončić +8.4 / **+4.8** | 34.8 / Tatum +5.4 / **+2.3** | 35.8 / Jokić +13.4 / **+6.3** | 36.5 / Mitchell +1.2 / **+0.7** | +1.7% win |
| 8 | 33.3 / Dončić +11.5 / **+6.0** | 33.5 / Tatum +6.7 / **+2.3** | 31.6 / Jokić +17.6 / **+6.3** | 33.5 / Edwards +3.0 / **+1.0** | +1.7% win |
| 10 | 32.5 / Dončić +12.4 / **+6.2** | 32.4 / Tatum +7.8 / **+3.0** | 28.8 / Jokić +20.4 / **+7.6** | 32.5 / Young +1.8 / **+0.9** | +1.7% win |
| 12 | 31.9 / Dončić +13.0 / **+6.0** | 31.4 / Tatum +8.8 / **+3.8** | 28.0 / Jokić +21.2 / **+7.2** | 31.9 / Barnes +1.6 / **+0.8** | +1.8% win |

**What it says**
- **C is the scarce slot.** Good centers run out fast, so the average starting C is worth +6 to +8 over replacement, against G +3 to +6 and F under +4 (forwards are plentiful, so the one left over is nearly as good).
- **A FLX slot adds almost nothing** (+0.7 to +1.0 per starter): its replacement is the best leftover player of any position, so the gap is small. What FLX does is raise the G replacement level (guards spill into it).
- **With no positions**, all value sits in the top five (Jokić, Wembanyama, Luka, SGA, Tatum); every other starter is within a few points of replacement (average starter +4).
- Bigger leagues lower replacement and widen every gap, most at C (Jokić +13 at 4 teams → +21 at 12).

## The gap pick by pick

VOR of the player taken at each overall pick when everyone drafts by PROJ MAX (no positions shown = ANY).

**3 starters, any player (no positions), 4 teams**: 1. Jokić (ANY) +12.7, 2. Wembanyama (ANY) +9.8, 3. Dončić (ANY) +8.3, 4. Gilgeous-Alexander (ANY) +7.1, 5. Tatum (ANY) +3.7, 6. Maxey (ANY) +2.2, 7. Haliburton (ANY) +1.5, 8. Mitchell (ANY) +1.1

**3 starters, any player (no positions), 8 teams**: 1. Jokić (ANY) +14.9, 2. Wembanyama (ANY) +12.1, 3. Dončić (ANY) +10.6, 4. Gilgeous-Alexander (ANY) +9.4, 5. Tatum (ANY) +6.0, 6. Maxey (ANY) +4.5, 7. Haliburton (ANY) +3.8, 8. Mitchell (ANY) +3.4

**3 starters, any player (no positions), 12 teams**: 1. Jokić (ANY) +16.7, 2. Wembanyama (ANY) +13.9, 3. Dončić (ANY) +12.4, 4. Gilgeous-Alexander (ANY) +11.2, 5. Tatum (ANY) +7.8, 6. Maxey (ANY) +6.2, 7. Haliburton (ANY) +5.6, 8. Mitchell (ANY) +5.2, 9. Cunningham (ANY) +5.1, 10. Murray (ANY) +4.7, 11. Davis (ANY) +4.3, 12. Embiid (ANY) +4.2

**1 G / 1 F / 1 C, 4 teams**: 1. Jokić (C) +13.4, 2. Wembanyama (C) +10.6, 3. Dončić (G) +7.2, 4. Gilgeous-Alexander (G) +6.0, 5. Tatum (F) +5.4, 6. Maxey (G) +1.1, 7. Haliburton (G) +0.4, 8. Davis (F) +1.9

**1 G / 1 F / 1 C, 8 teams**: 1. Jokić (C) +17.6, 2. Wembanyama (C) +14.7, 3. Dončić (G) +8.4, 4. Gilgeous-Alexander (G) +7.2, 5. Tatum (F) +6.1, 6. Maxey (G) +2.2, 7. Haliburton (G) +1.5, 8. Mitchell (G) +1.2

**1 G / 1 F / 1 C, 12 teams**: 1. Jokić (C) +21.2, 2. Wembanyama (C) +18.3, 3. Dončić (G) +11.5, 4. Gilgeous-Alexander (G) +10.4, 5. Tatum (F) +6.7, 6. Maxey (G) +5.4, 7. Haliburton (G) +4.7, 8. Mitchell (G) +4.4, 9. Cunningham (G) +4.2, 10. Murray (G) +3.8, 11. Davis (F) +3.2, 12. Embiid (C) +8.6

**1 G / 1 F / 1 C / 1 FLX, 4 teams**: 1. Jokić (C) +13.4, 2. Wembanyama (C) +10.6, 3. Dončić (G) +8.4, 4. Gilgeous-Alexander (G) +7.2, 5. Tatum (F) +5.4, 6. Maxey (G) +2.2, 7. Haliburton (G) +1.5, 8. Mitchell (FLX) +1.2

**1 G / 1 F / 1 C / 1 FLX, 8 teams**: 1. Jokić (C) +17.6, 2. Wembanyama (C) +14.7, 3. Dončić (G) +11.5, 4. Gilgeous-Alexander (G) +10.4, 5. Tatum (F) +6.7, 6. Maxey (G) +5.4, 7. Haliburton (G) +4.7, 8. Mitchell (G) +4.4

**1 G / 1 F / 1 C / 1 FLX, 12 teams**: 1. Jokić (C) +21.2, 2. Wembanyama (C) +18.3, 3. Dončić (G) +13.0, 4. Gilgeous-Alexander (G) +11.8, 5. Tatum (F) +8.8, 6. Maxey (G) +6.8, 7. Haliburton (G) +6.1, 8. Mitchell (G) +5.8, 9. Cunningham (G) +5.6, 10. Murray (G) +5.3, 11. Davis (F) +5.3, 12. Embiid (C) +8.6

## Sizing the TEAM slot

To make TEAM as important as a player slot, its scoring should give the **same gap between the average starting NBA team and the best team left over** as a player slot does — and a similar week-to-week swing (±9–10), so it neither decides matchups by itself nor disappears into the noise.

| Setup | Teams | Weakest player slot (avg starter VOR) | Average player slot | Strongest (C) | Best single player at a slot |
|---|---|---|---|---|---|
| 1 G / 1 F / 1 C | 4 | F +2.3 | +4.1 | +6.3 | Nikola Jokić +13.4 |
| 1 G / 1 F / 1 C | 8 | F +1.7 | +3.6 | +6.3 | Nikola Jokić +17.6 |
| 1 G / 1 F / 1 C | 10 | F +1.7 | +4.5 | +7.6 | Nikola Jokić +20.4 |
| 1 G / 1 F / 1 C | 12 | F +1.7 | +4.5 | +7.2 | Nikola Jokić +21.2 |
| 1 G / 1 F / 1 C / 1 FLX | 4 | F +2.3 | +4.5 | +6.3 | Nikola Jokić +13.4 |
| 1 G / 1 F / 1 C / 1 FLX | 8 | F +2.3 | +4.8 | +6.3 | Nikola Jokić +17.6 |
| 1 G / 1 F / 1 C / 1 FLX | 10 | F +3.0 | +5.6 | +7.6 | Nikola Jokić +20.4 |
| 1 G / 1 F / 1 C / 1 FLX | 12 | F +3.8 | +5.6 | +7.2 | Nikola Jokić +21.2 |

- **Target for an average starting TEAM: about +3 to +5 over the replacement team** (between F and C), with the best NBA team about +6 to +10 over replacement (like the best G or F, not Jokić-level).
- For reference, the current structure (point margin totaled over the week) gave the average starting TEAM +9.8 to +11.8 over replacement at 8–12 teams on '26 actual weeks (PROJECTIONS.md, Positions) — about twice a C and three to six times a G or F. It needs to come down by roughly half to two-thirds.

## Draft decisions (commissioner's notes, 2026-10-07)

Example: 4 teams, snake. Jokić, SGA and Luka go 1–3; you pick 4 and 5, and still need a G, an F and a C.

**The rule, ignoring the other teams:**
1. Take the biggest gap over replacement among your **open G / F / C slots**. At pick 5 that's the best center left (Wembanyama, +10 over the replacement C at 4 teams): the scarce role beats the best player overall.
2. **FLX last.** Its gap is always the smallest (+1 to +3 per starter), because anyone can fill it: its replacement is the best leftover player of any position. So FLX doesn't complicate the order — it's simply the last slot you fill, with the best player left.

**The one real complication is the other teams (denial).** Taking a second center you don't need for your C slot takes value away from an opponent: he drops toward the replacement C, the steepest drop at any position. In head-to-head every point taken from a rival's lineup counts in the weeks you face him (every third week in a 4-team league). This exists with or without FLX; FLX just makes it cheaper, because the second center has a slot to play in. The replacement math above ignores it. Measuring it needs a draft simulation (opponents draft by need and value; you try each choice; compare lineups over simulated weeks) — not built.

## Not in here yet
- Availability (missed weeks), bench depth (raises replacement), and in-season waivers.
- The TEAM scoring itself — this only sets the target it should hit.
