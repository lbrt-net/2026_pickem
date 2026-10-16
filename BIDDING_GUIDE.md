# Bidding guide

Auction draft, lineup **G / F / C / TM / FLX + 2 bench** (FLX = any player or an NBA team), **$200** budget, **$1**
minimum bid, raises of at least **4% of the high bid** (rounded up, $1 minimum). The draft room's **Rec bid** is what a
player is worth to *your* team right now, recomputed after every buy (`backend/fantasy_2026_27/bid.py`).
Rebuilt 2026-10-15 (DECISIONS.md "Bid guide").

## The formula

**Rec bid = $1 + your spare money × his gap ÷ (his gap + a typical gap at each of your other open starting spots)**,
never under $1, never over your safe max.

| Part | What it is, right now |
|---|---|
| **His weekly value** | The draft list's rank value (the number RK sorts by) |
| **Your spare money** | Your money left minus $1 for each of your open spots |
| **Starter replacement** | At each position (G / F / C / TM): fill every team's open spots at that position with the best left; the next one is replacement |
| **True replacement** | The players beyond the starters fill every team's open Flex spots; the next one is the true replacement |
| **His gap** | Your spot for him still open → his value − that position's starter replacement. That spot filled → he's a Flex: his value − the true replacement. Flex filled too → bench only → $1 |
| **Typical gap** | For each of your other open starting spots: the middle of the players the room will take for that spot, minus the same replacement |
| **Your safe max** | Your money left minus $1 for each of your other open spots |

**Why the typical gap:** you won't land the best player at every spot, so a player's share of your money is measured
against what you'd realistically get elsewhere. That's what makes a star worth more than a straight split, without a
curve.

**What moves it:** only who's left and your own roster. Other teams' money never does: a team that overpaid for Jokić
can't bid on Luka, so Luka's number doesn't drop.

It's what he's worth to you, not a guess at what the room will pay. Stars often go above it. Whether to chase is your
call.

## When he's on the block

- **The next legal bid:** the high bid plus 4%, rounded up, at least $1. $25 → $26, $50 → $52, $100 → $104.
- **Your Rec bid:** the most he's worth to your team right now.

**Keep bidding while the next legal bid is at or under your Rec bid.** Pass once it's over. The API gives
`lot.min_next`, `lot.my_rec` and `lot.my_call` (`bid` / `pass` / `winning`).

## At the start of a 10-team draft (for reference, 2026-10-15)

Jokić $150 · Wembanyama $142 · Sengun $109 · Duren / Towns $96 · Embiid $95 · SGA $92 · Luka $86 · OKC $85 · Tatum $77 ·
Adebayo $77. Centers and OKC rank high because their gaps over replacement are the biggest; guards and forwards are
deep, so their gaps are small. Each number assumes typical players at your other spots — they don't add up to $200.

## How it was checked

An offline auction simulator (10 teams, these settings): one team follows the guide, the other 9 are bot managers with
personalities (stars and scrubs, ceiling chaser, value grinder, hype buyer, roster planner, contrarian), 200 auctions
with rotating seats, scored on the starters' weekly value.

| | Average finish | Top 3 | Money left |
|---|---|---|---|
| Old guide (^1.25 curve, room-wide price) | 3.5 | 62% | $40 |
| **This guide** | **1.9** | **90%** | **$5** |

The bots' values come from the same projections, so this checks the method, not the real room.

The final live test draft (2026-10-15) showed why gaps matter: the seven teams that spent all their money finished
within about 7 points a week of each other, and three teams of $1 players were only about 20 points behind.
Replacement players are good in a 10-team league, so the money belongs where the gaps are.
