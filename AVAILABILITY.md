# Availability: how many games a player plays

Built 2026-10-08. Code: `scripts/projection_study/availability.py` → nba-pipeline `data/raw/availability_2026_27.json`,
applied by the server in `backend/fantasy_2026_27/projections.py` (`week_projection`). It changes **PROJ MAX** (and
MAX low / high, the draft ranking and Rec bid). **PROJ AVG doesn't change**: it's per game played.

## Rule: season-ending injuries are left out

Any run of **25+ straight team games missed**, and any season missed entirely, is removed from a player's history and
from the outcomes the model is fit on. That covers Wemby's 2025 blood clot, Haliburton's 2025-26, Tatum's 2025-26 and
Chet's long 2024-25 absence. Nobody can predict those, and the projection shouldn't charge every player a share of
them. So the numbers mean "games he plays if no season-ending injury hits," and they run high on purpose: in the 2025-26
check they averaged 64.3 games against 62.2 actual.

## 1. Expected games

- **The question:** how many of 82 games will he play next season?
- **What we look at:** how many games he played in each of his recent seasons, up to the last three. Jokić played 79,
  70 and 65, an average of 71 a season. Season-ending injuries don't count.
- **What we learned from past players:** for every regular player (20+ minutes a game) from 2022-23 to 2024-25, we
  compared that average with the games he played the next season. Two things matter: how high the average is, and how
  many seasons it's built on. One great season can be luck; three in a row isn't.
- **Reading the table:** find how many games a season he's been playing (rows) and how many seasons of him we have
  (columns). The cell is the games to expect next season.

| He's been playing (games a season) | 1 season of him | 2 seasons | 3 seasons |
|---|---|---|---|
| 57 | 65 | 62 | 58 |
| 74 | 70 | 68 | 68 |
| 78 | 71 | 69 | 73 |
| 82 | 72 | 80 | **82** |

- **82 every year, three years running** (Bridges): expect 82. Iron men stay iron men.
- **82, but only one season of him:** expect 72. One healthy year doesn't prove much.
- **About 74 a season:** expect 68. Pretty durable players usually miss more the next year.
- **57 a season, three years running:** expect 58, he's injury-prone. With one season at 57, expect 65, because one bad
  year can be bad luck.
- **Rookies** have no seasons, so they get what the 40 regular players closest to them in height and weight played.
- **How good is it?** On the 2025-26 check it missed by about 15 games on a typical player, the same as guessing the
  league average for everyone. Injuries are mostly random. What the model does is keep iron men and the injury-prone
  apart.

| Player | Counted seasons | Expected games |
|---|---|---|
| Mikal Bridges | 82 every season | **82** |
| Shai Gilgeous-Alexander | 68 / 75 / 76 / 68 | 68 |
| Anthony Edwards | 79 / 79 / 79 / 61 | 68 |
| Nikola Jokić | 69 / 79 / 70 / 65 | 67 |
| Victor Wembanyama | 71/82, 46/52 (clot run removed), 64/82 | **65.5** (similar builds: 61) |
| Luka Dončić | 70 / 50 / 64 | 60 |
| Joel Embiid | 39/53, 19/56, 38/82 | 44 |

## 2. How missed games fall: clustered, not random

From about 22,000 rotation player-weeks, '23–'26:

- **Whole weeks:** zero-game weeks happen about 3× as often as random misses would give (10% against 3.4%).
- **Partial weeks:** in weeks a player plays at all, he plays about 89% of his team's games.
- **Fit**, with long-injury weeks removed: **zero-game week share = (share of games missed)^1.6**. In the other weeks
  he plays each game with chance **q = (1 − missed) ÷ (1 − zero)**, so the season total still matches.

| Share of games missed | Zero-game weeks |
|---|---|
| 10% | 2.5% |
| 20% | 7.6% |
| 30% | 14.6% |

## 3. PROJ MAX

For each fantasy week with n team games, the chance he plays k of them is: zero with chance *zero*, else
Binomial(n, q). His weekly value is the weekly-best curve at each k (k = 0 scores 0), weighted by those chances.
PROJ MAX averages that over the season.

- **Known injuries:** an ESPN Out with a return date zeroes every week that ends before that date (for example, Jimmy
  Butler until Jan 2).
- **MAX low / high:** the curve's 25th and 90th percentiles get the same weighting. That's an approximation, not exact
  percentiles.
- **Rec bid:** the flat 0.86 is gone, because availability is now per player inside PROJ MAX.

| Player | PROJ MAX before | After |
|---|---|---|
| Jokić | 53.5 | 48.7 |
| Wemby | 48.9 | 43.8 |
| SGA | 47.1 | 43.3 |
| Luka | 47.0 | 39.7 |
| Edwards | 40.4 | 36.9 |
| Bridges | 30.0 | 30.0 |
| Embiid | 39.0 | 25.6 |
| Butler | 33.4 | 15.1 |
