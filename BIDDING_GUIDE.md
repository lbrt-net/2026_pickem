# Bidding guide

Auction draft, lineup **G / F / C / TM / FLX + 2 bench** (FLX = any player or an NBA team), **$200** budget, **$1**
minimum bid, raises of at least **4% of the high bid** (rounded up, $1 minimum). The guide is a formula, not a price
list: the draft room's **Rec bid** recomputes it for your team from the room as it stands, after every buy
(`backend/fantasy_2026_27/bid.py`). Updated 2026-10-08.

## The formula

**Rec bid = $1 + scale × (points over replacement)^1.25**, capped at your safe max.

Every part is re-read from the room after each player is bought:

| Part | What it is, right now |
|---|---|
| **His weekly value** | PROJ MAX (games he's expected to play included), or the TEAM projection for an NBA team |
| **Replacement** | Fill every team's *still-open* roster spots with the players *still available*, best first. Replacement at his position is the best player left over |
| **Points over replacement** | His weekly value minus his position's replacement (0 if below) |
| **Scale** | All teams' *money left*, minus $1 for each open spot, ÷ the sum of (points over replacement)^1.25 for the players who'll fill those spots. The prices of everyone still to be drafted add up to the money still in the room |
| **Your safe max** | Your money left minus $1 for each of your other open spots |
| **Fits** | No Rec bid if he doesn't fit any of your open spots |

**How it moves during the draft:**
- **Stars go cheap:** more money is chasing fewer good players, so the scale goes up and everyone left gets more
  expensive.
- **Stars go expensive:** the scale goes down and bargains appear.
- **Your position fills up:** a second center only fits FLX or bench, and the Rec bid follows. With no fitting spot,
  there's no bid.
- **A position runs dry:** when the good centers are gone, replacement at C falls, so the centers left are worth more.

## When he's on the block

For the player up for bid, the draft room tells you two numbers:
- **The next legal bid:** the high bid plus 4%, rounded up, at least $1. $25 → $26, $26 → $28, $50 → $52,
  $100 → $104, $150 → $156. A star's bidding war from $100 to $180 takes 14 raises at most, against 25 at 2%.
- **Your Rec bid:** the most he's worth to your team right now.

**Keep bidding while the next legal bid is at or under your Rec bid.** Pass once it's over. The API gives
`lot.min_next`, `lot.my_rec` and `lot.my_call` (`bid` / `pass` / `winning`).

## Prices at the start of the draft (empty room, for reference)

These are only where the formula starts; they change after the first buy.
With availability in PROJ MAX (`AVAILABILITY.md`; season-ending injuries left out) and TEAM scoring draft 7 with
roster-built TEAM projections (`TEAM_SCORING.md`), 2026-10-08.

| Teams | Jokić | Wemby | SGA | Luka | Tatum | Embiid | Sengun | OKC | DET |
|---|---|---|---|---|---|---|---|---|---|
| 4 | $145 | $99 | $75 | $60 | $52 | $1 | $24 | $51 | $12 |
| 6 | $162 | $112 | $103 | $85 | $62 | $1 | $30 | $57 | $14 |
| 8 | $173 | $123 | $111 | $94 | $75 | $4 | $41 | $61 | $18 |
| 10 | $180 | $133 | $113 | $96 | $78 | $16 | $55 | $60 | $20 |
| 12 | $181 | $135 | $116 | $100 | $87 | $19 | $58 | $67 | $26 |
| 14 | $162 | $122 | $113 | $99 | $83 | $19 | $53 | $76 | $39 |

Embiid (≈53 games expected) and Luka (≈62) drop the most; Bridges-type iron men (82) hold their value. The ^1.25 bend was fit before
availability was per player (a flat 86% then); it hasn't been re-fit.

## Rules of thumb

1. **Stars are the best buys.** In the mock auctions, the teams built on the top five or six players finished on top.
2. **Jokić isn't worth the whole budget.** Around $160–180 depending on league size.
3. **Don't overpay the next tier of centers or NBA teams.** Teams that paid $55–80 for Sengun, Embiid, Duren or Towns,
   or $45–55 for DET or BOS, finished last (that was under TEAM draft 6; with draft 7 the top TEAMs are fairly
   priced at $40–55 in 8–14 team leagues).
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
