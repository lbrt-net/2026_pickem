# Bidding guide

Auction draft, lineup **G / F / C / TM / FLX + 2 bench** (FLX = any player or an NBA team), **$200** budget,
**$1** minimum bid. The draft room's **Rec bid** column uses this formula (`backend/fantasy_2026_27/bid.py`), for your
team only, recomputed after every buy. Updated 2026-10-08.

## The formula

**Price = $1 + scale × (points over replacement)^1.25**

- **Points over replacement:** his weekly value minus the best player at his position who'd still be free once every
  team fills its roster. Weekly value is his PROJ MAX, or the TEAM projection for an NBA team.
- **The ^1.25 bend:** each point above replacement costs a little more than the one before. Stars cost more than a
  straight line would say, but less than the whole budget.
- **Scale:** set so that everyone who'll be drafted adds up to all the league's money ($200 × teams, minus $1 per
  roster spot). It's recomputed after every buy, so if stars go cheap, everyone left gets more expensive.
- **No bid** if he doesn't fit any of your open spots, and never more than you can spend while still filling your
  other spots at $1.

## Prices at the start of the draft

| Teams | Jokić | Wemby | SGA | Luka | Tatum | Embiid | Sengun | DET | BOS |
|---|---|---|---|---|---|---|---|---|---|
| 4 | $136 | $91 | $81 | $80 | $42 | $12 | $11 | $21 | $16 |
| 6 | $153 | $109 | $94 | $93 | $54 | $26 | $25 | $26 | $20 |
| 8 | $170 | $126 | $103 | $101 | $61 | $42 | $41 | $31 | $25 |
| 10 | $182 | $139 | $105 | $104 | $69 | $56 | $55 | $33 | $27 |
| 12 | $161 | $124 | $107 | $105 | $73 | $50 | $49 | $39 | $34 |
| 14 | $153 | $119 | $106 | $105 | $75 | $53 | $52 | $38 | $33 |

## Rules of thumb

1. **Stars are the best buys.** In the mock auctions, the teams built on the top five or six players finished on top.
2. **Jokić isn't worth the whole budget.** Around $160–180 depending on league size.
3. **Don't overpay the next tier of centers or NBA teams.** Teams that paid $55–80 for Sengun, Embiid, Duren or Towns,
   or $45–55 for DET or BOS, finished last.
4. **Spend all your money.** Every team that left $20–40 unspent finished at or near last.

## Where it comes from

A mock 2026-27 auction (`scratchpad auction_seq.py`, same lineup and budget): players come up best-first, and each
team bids the most it can pay for a player while still ending up with a better whole roster than without him,
counting its FLX and bench. It ran at 4, 8, 10 and 12 teams.

- **Fit:** the formula matches those 210 sales to within $9 on a typical player, and the stars to within a few dollars
  at 8–12 teams. Where the formula is lower than what was paid (second-tier centers, NBA teams), the teams that paid
  more finished at the bottom. The formula is the price to pay, not what the mock bidders did.
- **Less sure at 4, 6 and 14 teams:** 6 and 14 weren't simulated. At 4 teams the auction paid ~$176 for Jokić against
  the formula's $136.
- **The earlier straight-line formula** (no bend, priced against one starting spot) overpriced Jokić and Wemby by
  $15–25, because it ignored what money buys at FLX and on the bench.
