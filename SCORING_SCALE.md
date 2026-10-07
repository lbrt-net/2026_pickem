# Player scoring scale — halving points, adding clutch (running log, started 2026-10-07)

The question: points carry most of a player's fantasy score, so stars who only score dominate. Proposal
(commissioner): **cut points in half**, and **add clutch-time scoring** so the end of close games matters. Measured on
2024-25 (the season with play-by-play on disk). Nothing changed in the app yet. FANTASY_SCORING.md is still the
locked scoring; this is the analysis for changing it.

## The proposal tested
- **Points: half value** (0.5 per point). Everything else as now: missed shot −0.5, own shot blocked −0.5, three made
  +0.5, missed free throw −1, offensive rebound 1.5, defensive rebound 0.5, assist 1, steal 2, block 1.5, turnover −2.
- **Clutch time** = 4th quarter or overtime, 5 minutes or less left, score within 5 (the NBA's definition). In clutch:
  - points **×2** (back to 1.0 per point) — also tested **×3** (1.5 per point)
  - made free throws 1.0 each (full value, so still more than the halved 0.5)
  - turnovers **double loss** (−4), steals ×2 (4), blocks ×2 (3), offensive rebounds ×2 (3)
  - assists, defensive rebounds, everything else: no clutch bonus

## What halving points does
- **Everything shrinks to about 60%.** The top 12 players' average weekly score (best game of the week) goes from
  **40.8 to 25.4**; a typical player's from 19.9 to 13.0. Per game, a typical player goes 13.2 → 8.4.
- **Jokić stays #1** (49.1 → 33.4), and the gap to #2 grows (SGA 46.9 → 27.5): his rebounds and assists don't get
  cut.
- **All-around players and bigs move up**, pure scorers move down (rank by weekly score among the top 60):
  - Up: Walker Kessler 54 → 11, Ivica Zubac 29 → 9, Josh Hart 48 → 19, Jarrett Allen 38 → 18, Bam Adebayo 37 → 21,
    Josh Giddey 50 → 24, Amen Thompson 52 → 29, Jimmy Butler 49 → 27.
  - Down: Jalen Green 60 → 114, Zach LaVine 51 → 101, RJ Barrett 59 → 91, Jordan Poole 42 → 71, LaMelo Ball 34 → 61,
    Kyrie Irving 39 → 62, CJ McCollum 30 → 53.

## What clutch adds
- **Clutch time is short**: a few minutes in about half the games. In '25 the whole league scored 9,775 clutch points,
  1,031 clutch turnovers, 613 steals, 451 blocks, 1,034 offensive rebounds. A top-50 player scores **0.8 clutch points
  a game** on average.
- So at the proposed size it's a small spice: **×2 adds 0.6 a game** for a typical top-50 player (4% of his score),
  at most 1.2 (Maxey). Biggest clutch gainers: Maxey, Brunson, Jokić, Adebayo, Hunter, DeRozan, Kessler, Edwards,
  Monk, Durant.

| Clutch points multiplier (of the halved value) | Per clutch point | Adds per game (typical top-50) | Most | Share of his score |
|---|---|---|---|---|
| ×2 | 1.0 | 0.6 | 1.2 | 4% |
| ×3 | 1.5 | 1.0 | 1.9 | 6% |
| ×5 | 2.5 | 1.8 | 3.6 | 10% |
| ×8 | 4.0 | 3.0 | 6.1 | 15% |

- **×2 and ×3 barely change who's on top.** For clutch to be something people feel, it needs to be bigger (×5 or
  more) — and it stays swingy either way, because whether a game is close at the end is luck.

## Scale next to TEAM
With points halved, a top player's weekly score is about **26** and a typical one's about **13**. TEAM scoring draft 2
averages **19** a week (OKC 32): TEAM would then be worth more than most players. TEAM's scale gets set after this one.

## Data
- '25 clutch from play-by-play (`scripts/projection_study/scoring_scale.py`).
- For '23, '24, '26 and projections: NBA.com's player clutch stats (LeagueDashPlayerClutch), pulled one game day at a
  time (~165 requests a season) — queued after the team pulls (one stats.nba.com pull at a time).

## 2026-10-07 (commissioner): points stay 1x; clutch points are an extra category worth 2 per point
Halving points is off. Instead: **every point scored in clutch time (field goals and free throws) earns 2 extra**, so
a clutch point is worth 3. No other clutch changes. On 2024-25:
- **Scale barely moves**: top 12 players' weekly score 40.8 → **45.6**; typical player 19.9 → 20.8.
- **Size**: adds about **2.2 a game** for a typical top-50 player (7.5% of his score). Most per game: Brunson 4.8,
  Maxey 4.5, Trae Young 4.4, Jokić 3.7, Edwards 3.6, DeRozan 3.5, Morant 3.4, Durant / Fox / Curry 3.2.
- **Big nights get bigger**: the largest single-game bonus was +32 (CJ McCollum vs Sacramento, Feb 13: 16 clutch
  points, 43.5 → 75.5). Brunson's 55-point game at Washington: 53 → 85.
- **Top 12 by weekly score**: Jokić 55.0, SGA 50.1, Brunson 47.7, Giannis 46.2, Wembanyama 44.6, Luka 44.4, Trae 43.9,
  Davis 43.8, Tatum 43.4, Edwards 43.1, Maxey 42.8, LeBron 41.8.
- **Who moves** (rank by weekly score, top 60): closers up — DeRozan 43 → 22, Miles Bridges 46 → 32, RJ Barrett 59 → 46,
  McCollum 30 → 20, Trae Young 17 → 7, Garland 40 → 30, Fox 32 → 23. Bigs and role players down — Anunoby 47 → 64,
  Mobley 26 → 40, Hart 48 → 60, Allen 38 → 49, Jalen Williams 36 → 47, Towns 8 → 17.
