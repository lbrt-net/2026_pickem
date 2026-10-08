# TEAM scoring

Every fantasy roster has one **TEAM** spot: you draft a whole NBA team, like a defense in fantasy football. Players already score for what they do (points, rebounds, assists, steals, blocks). **TEAM is where a team's defense shows up.** Seasons are named by the year they end ('26 = 2025-26). Basic box-score stats only this year.

## The scoring (current: draft 4)

Per game:

| What | Points | Games it happens in ('23–'26) |
|---|---|---|
| Every point the opponent finishes under 125 | +1 each | 78% |
| Hold them under 100 | +10 | 11% |
| Hold them under 90 | +15 more | 2% |
| Each time violation forced (shot clock, 8-second, 5-second) | +5 each | 51% |
| Hold them to single-digit fast-break points | +5 | 22% |
| Hold them under 30 points in the paint | +10 | 2% |
| Force 20+ turnovers | +5 | 9% |
| Win the defensive glass by 10+ (our defensive rebounds minus theirs) | +5 | 10% |

**Weekly score = the team's best game of the week**, the same as players.

Example: hold a team to 96 with one shot clock violation and 7 fast-break points → 29 (under 125) + 10 (under 100) + 5 (violation) + 5 (fast break) = **49**.

Open: violations forced +5 **each** (as scored here) or +5 once a game.

## Why this shape

- **A bread and butter that pays most games**: points under 125. The score is on the screen, and points allowed is the clearest sign of a good defense — the teams that allow the fewest points are the teams with the best defensive ratings (0.87 out of 1, '23–'26).
- **Lines to root for late in a game**: under 100, under 90. Rare, and worth a lot.
- **Moments to cheer one at a time**: every time violation forced.
- **Bonuses that don't come every week**, even for good defenses: fast break, paint, turnovers, glass.
- **It follows real defense**: a team's average weekly score lines up with its defensive rating at 0.82 and repeats next season at 0.56, so a TEAM can be drafted like a player.

Where a weekly score comes from: points under 125 62%, violations 14%, the under-100 / under-90 lines 13%, the four bonuses 11%. A weekly score averages **33**, give or take 18 — about a star player's best game.

## Last season (2025-26)

| # | Team | Weekly score | Weeks of 50+ | Games at 0 | Best game | Held under 100 | Defensive rating |
|---|---|---|---|---|---|---|---|
| 1 | OKC | **47.7** | 43% | 3% | 74 | 21% | 106.5 |
| 2 | BOS | **47.5** | 43% | 0% | 91 | 24% | 111.7 |
| 3 | DET | **46.2** | 43% | 0% | 93 | 16% | 108.9 |
| 4 | NYK | **40.9** | 38% | 5% | 104 | 20% | 112.3 |
| 5 | LAC | **40.1** | 33% | 5% | 71 | 16% | 115.2 |
| 6 | CHA | **38.3** | 38% | 7% | 79 | 23% | 113.5 |
| 7 | TOR | **37.4** | 19% | 3% | 83 | 15% | 112.1 |
| 8 | HOU | **36.9** | 24% | 4% | 64 | 18% | 112.1 |
| 9 | SAS | **36.8** | 29% | 4% | 63 | 14% | 110.4 |
| 10 | PHX | **36.6** | 10% | 3% | 53 | 16% | 112.9 |
| 11 | GSW | **36.6** | 14% | 5% | 91 | 15% | 114.4 |
| 12 | CLE | **34.2** | 19% | 11% | 86 | 11% | 114.2 |
| 13 | MIN | **33.4** | 14% | 5% | 77 | 8% | 112.5 |
| 14 | ATL | **32.2** | 19% | 9% | 68 | 11% | 112.9 |
| 15 | BKN | **31.8** | 14% | 7% | 77 | 7% | 118.3 |
| 16 | DEN | **31.3** | 19% | 14% | 86 | 8% | 116.0 |
| 17 | POR | **30.2** | 14% | 5% | 103 | 8% | 113.6 |
| 18 | MIL | **29.9** | 14% | 12% | 56 | 8% | 118.3 |
| 19 | LAL | **29.2** | 5% | 5% | 63 | 8% | 115.5 |
| 20 | MIA | **29.0** | 10% | 5% | 59 | 8% | 113.6 |
| 21 | ORL | **28.8** | 14% | 9% | 59 | 9% | 113.6 |
| 22 | PHI | **26.9** | 0% | 5% | 49 | 5% | 114.4 |
| 23 | DAL | **26.5** | 5% | 11% | 57 | 4% | 115.5 |
| 24 | NOP | **25.6** | 5% | 12% | 56 | 5% | 117.6 |
| 25 | MEM | **24.9** | 10% | 14% | 54 | 7% | 118.5 |
| 26 | IND | **23.5** | 5% | 15% | 69 | 5% | 117.9 |
| 27 | WAS | **22.3** | 5% | 19% | 66 | 4% | 121.5 |
| 28 | SAC | **21.8** | 0% | 14% | 47 | 3% | 120.3 |
| 29 | CHI | **20.9** | 0% | 14% | 48 | 3% | 117.5 |
| 30 | UTA | **20.1** | 5% | 24% | 57 | 3% | 120.8 |

Defensive rating = points allowed per 100 possessions (lower is better), for comparison.

### Every game, every team

One line per team, every game October → March. `|` starts a new fantasy week (21; the All-Star week and the final are 2-week periods). Each character is one game: `·` = **0**, `▁▂▃▄▅▆▇█` = higher (each step about 7.5 points; `█` = 52+). Before the line: average weekly score, share of games at 0. 8% of games score 0, but only 0.2% of weeks do.

```
OKC 47.7   3% |▄·▅|▇▄▄▄|▄▃▆▅|▅▇█|▅▅▄▇|▇▃▂|▄▄▄|█▂|▅▃|▇·▂▄|▁▇█▅|▂▁▂▃|▇█▂|▄▄▃▃|▇▂▄|█▃▃|▃▄▄█▂|▄▂▂█|▃▅█|▁▄▆|▄▇▃▅▂▂▅|
BOS 47.5   0% |▂▇▁|█▅▃▃|▄▄▁▃|▄▇▃|▇▃▁|▂▃▃|▃▄▄▃|▂|▃▃▆|█▁▃|▁▄▃|▅▅▂▄|▇▂▄|▃▅▁▂|▆▂▇█|▄█▆▂|▄▄█|█▄▃▇|█▂▄▇|▁▃▅|▄▅▃▄▃▄▇|
DET 46.2   0% |▃▂▃|▃▂▄|▄▃▅▄|▁▃▃|▄▄▃|▂▄▃▁|▇▃▄▃|▃|▄▂█|▅▁▁▅|▄▃▃|▇▆▇|▄█|▄▅▄▂|▃▃▁█|▂▂█|█▇▂▃|▅▄▃▇|▃▂▄▂|▇▃▅▃|▃█▆▃▁▃█|
NYK 40.9   5% |▃▇▂|▁▃▂|▅▂▆|▂▁·|▃▃▁|▄▄▃▇|▁▄▂▅|▄▁|▂▄·|▂▁▁|▁·▂▁|▂▃▄▂|▄·▄|▂█▃|█▇▆▅|▄▂▂█|▁█▁▄▅|▃▇█|█▆▅▃|▁▂█▄|▃▆▃▂▃▄|
LAC 40.1   5% |▁▅▄|▅▁|▁▁▄▃|▄▁▃▁|▃▁▂▃|·▃▃|▁▇▄▃|▃|▁▂█|▃▃▅|▇▄·|▄▃▄█|▃▃▂|▄·▃█|▅▂█|▁▁▂▇|▅▅▂·▂|▇▂|▆▄▂▁|▃▁▄▃|▃▁▄▁█▆▃▃|
CHA 38.3   7% |▃·▂|·▁▁▄|▂·|▁▅▁▃|▃▁▂▃|▁▂▃|▂▁█▂|▁▃|·▃|·▃▄|▁▁▁▆|█▆▄▇|▂▂▁█|█▆▃|▇▆▁▄|▇▅▁|▃▃▃▂▂|▇▃▇|▇█▁▄|▄▄▃|▃▃▄▇▅▁▄|
TOR 37.4   3% |▃▂▁|▃▂▅▅|▆█▁|▄▃▃|▃▃▄▃|▅▆▂▂|▁▁▃▁|▂|▆▅▄▇|▇▁▂|▄▄▂|▅▆▃▃|▃▅▁▃|▃▄▇▄|▃·▇|·▅▄|▃▆█|▄▃▂|▄▃▇|▃▂▃▃|▃▁▃▃▂▄█|
HOU 36.9   4% |▁▃|▅▂▄|▄▃▂▃|▂▃▃|▃▃|█▅▅|·█▇▂|▃|▁·▄▁|▂▆▅|▂▆▃|█▄▂▄|▃▃▅▃|▄·▄|▆▂█▄|▃▄▅▄|▇▅▄▄|▅▆▃▃|▃▃▇▁|▆▁▃|▅▁█▂▃▄▃▄|
SAS 36.8   4% |█▄▆|▄▄▁|▃▄▂|▂▃▅▃|▄▁▂|▄▁▂|▁▂▁|·▁▃|█▇▂|▅▄▁|▃·▃▂|▆▆▇▃|▁▄▁|▃▂▃▄|█▄▅|▄▁▁|▃▃█▂|▄▄▃▃|█▃▃▁|▂·▆|▃▅▄▃▃▆█|
PHX 36.6   3% |▂▂·|▁▂▆▁|▂▄▄|▇▄▆▁|▅▅▄|▃▅▁▂|▅▄|▅▁▃|▇▃|▃▃▂|▄▁▅▅|▆▅▄▇|·▃▅|▂▃▃▄|▆▆▃▂|▁▅▃|▂▁▂▃▇|█▄|▃▄▂▇|▃▃▂|▂▃▄▄▇▁▃|
GSW 36.6   5% |▅·▁|▁█▄▂|▃▁▁█|▂▂▄▄|▁▃▃|▂▃▆|▁▅▇▇|▁▁|▅▂|▆▂▁|▃·▁▂|▄▃▄▂|▆▃▂|▂▂▂█|▃▁▂|▃▆▅|▃▁▁▂|▂▃▁|▂▃▅|▁▂▂▃|▂▁▃·▃▄·▂|
CLE 34.2  11% |▂▃▃|▇▁▄▄|▂▃▂|·▂▁▄|▄▂▃▅|▃▂▄|▁▂▃▆|·▃|▁·|▂▁·▃|▄▃▄▃|▅·▁|▃▃▃|▂█▁▃|▆▅▃▄|▇·|▂▄█▄▁|▇▂▃▄|▃▅|▆·▅▁|▂▃▄▂▃·|
MIN 33.4   5% |▃▂▃|▂▂▄|▄·▇▃|▂▃▁|▇▃▃|▂▃▃▂|▁▂▄|▃▁▃|▂▄▆|▃·▁|▄▂▃▂|▇▂▁▃|▅▄▁|▁▂▂|█▅▃▃|▁·▁▃|▂▅▂▁|▂█▄|▃▄▃|▃·▃▂|▇▄▃▆▄▄|
ATL 32.2   9% |·▄▂|▃▃▄▃|▄▃▆|▅▇▂▂|▃▁█▄|▁▁·|▇▂·▃|▂▂|▂▁▁|·▂▂|▁▅▆·|▃▄█▃|▂▂▁|▂▂▄|▂▄▄▁|▃▃▂|·▅▄▁▅|▆▆▄|▃▄|▃▆█|▂▂▃▄▅·▄▂|
BKN 31.8   7% |▁▁▃|▁▂·|▁▅··|▂▃▄|▄▄▁|▂▃▃|▅▃▁▅|▁█|▃█|▄▃|▂▁▂▃|▄▂▄|▃▂▃▂|▁▁▂·|▃▄▅▂|·▄▃|▃▃▃▄▃|▂▁▁▄|▁▂▅|▃▁▃▃|▃▂█▂▃▃▄▅|
DEN 31.3  14% |▂▄|▄█▃|▁▃▄▅|▃▃▂|·▁▄▁|▂▁▂|·▁▂▄|▃|·▃▂|▂▁▂·|▁▃▃·|▁▃▃▅|▂▃▂▃|▃▆▅|▃▅▃▁|▁▁▂|▂▂▃▅▃|█·▂|·▂▁|·▇▁▁|▆·▂▄▁··▇|
POR 30.2   5% |▁▂▄|▅▂▅|▁▂▁|▂▃·▁|▃▁▁▁|▃▂▁|▁▃▂▃|▂·|·█|▄▃▄▃|▁▁▃▃|▂▄▃▁|▁▆▂▃|▃▃|▄▃▁▁|▁▂▃|▂▁▁▁█|▁▄▃▂|▂▄▄|▄▂▄|▇▂▃·▇▇▅█|
MIL 29.9  12% |▁▂▃|▃▅▂|▃▁▃▂|▃▄·▃|▃▁·|▄▃▂█|·▄▄▁|▆▁|▃▃|▆▁▃|▂▂▁▅|▃▄▅|▁▂|▃▁▄|▁▃▄|▂·▆|▁▅▇▂▂|▂▂▁▁|▃·▇·|▁▃▁▁|▁▃▃·▂··|
LAL 29.2   5% |▂▃▃|▂▂▂▁|▂▂▁|▄▁▄▆|·▃|▃▁▁|·▁▂▃|▂▃|▁▅|▁▂▄|▃▂▃|▅▄▄|▃▂▁▁▇|▄▄▃|▁▂▄▄|▃▃▇|▃▁▄▁▃|▄▃▅▄|▄▁▂▆|▄▁▁|█▂·▅▂·▇|
MIA 29.0   5% |·▃▄|▃▃▁|▃▂▃▁|▃▂▁|▃█▄▂|▄▄▁|▂▃▄▁|▂|▆▇▂▁|▃▃▂|▁▄▁▅|▁▂▁|▂▂▂|▁▂▃▂▄|·▃▂▇|·▇▄|▃▂▆▂|▁▁▄|▆▄▂▅|▃▃▂|▁▃▁·▄▁▁|
ORL 28.8   9% |▂▂▅|▁▁▄▇|▃▃▂|▄▄▇▂|▂▄▁·|▄▃|▃▃▄▃|▃·|▂·|▂▃▃·|▃▃▂·|▂▆▄▃|▂·|▁▃|▃▁▂▄|▁▅▂|▇▃▇▃▃|▃▂▄|▅▂▇█|▂▁▃|▁▄▁▃▂·▃▁|
PHI 26.9   5% |▂▂|▁▁▃▄|▂▁▃▃|▅▃|▃▂▂·|▁▃▃|▄▆▆▂|▃▂|▄▂|▃▃▁|▁▃▁|▂▃▇▂|▄▁▂|▆▂▂▃|▃▂▄▂|▃▇▂▆|··▂▁▄|▃▂▄|▂▄▁|▃▂·▆▄|▁▃▂▁▁▃|
DAL 26.5  11% |▁▃▂|▄▅▂|▃▆▃▃|▂▁▃▂|▂▂▂▅|▄▂▃|▂▄·▅|▂|·▃▂|▂··▂|▂▁▄|▆▂▂|▄▁▂▁|▆▃▃|▁▁▃|▄▁▂|▂▁▁▂|▃▁▁▅|▂▂▃▁|▁▃·▁|··▁▁·█|
NOP 25.6  12% |·▂|▂▁·▂|▄▅·|▂·▂▁|▃▁▂▂|·▁▅▁|·▂▅|▂▂▃|▃▃|▃·▃▁|▁▂▂▁|▃▄▄▂|▂▃·▁|▄·▇|▃▄▁|▄▁▃|█▁▂▃|▅▁▄▁|▄▁▃▂|▃▃|▃▃▇▃▂▂▂▂|
MEM 24.9  14% |▂▂▃|·▃▃▂|▃▁▄▃|▁▁▅|▃█▆|·▁▃▄|▂▆█|▁|▄▃·|▂·▅▂|▂▂▂|▃▃▂▆|▁▃|▁·|▃▆▃▁|···▁|▃▂▃·|▁▂▅▄|▃▂▁|▂▁▃▁|▁▁▃▁·▁▁▁|
IND 23.5  15% |·▂▃|▃·▃|▂▄▃▂|▁·▂|▁▂▁|▂▆█▄|▁▁▅|▃▃▃|▂▂|▄▃▂▁|▃▂▂▁|▁▃▅|▆▃▂▁|▃▃▃|·▃▁|▃▁▅▃|·▄▂▁·|·▁▁|·▁▂|▂▂▅·|·▁▂·▁▃▁|
WAS 22.3  19% |·▄▁|▁·▂|▁▃·▂|▂▂▂|▂▁▁|▃▅|▁▂▁▃|·█|▁▁▁|▁▂▂|▂▃▆·|▂·▃▄|▃▁▂|▃▆▂|▃▆▁▂|·▂··|▁▄▂·|▂▁▁|▃▁▂·|▁·▄|▂▁▂··▄▁▁|
SAC 21.8  14% |▂▅·|▃▁·|▂▂·▁|▂▃▂▁|▂▁▁|▂▄▂▃|▂▂|▂·▂|▃▆▂|·▅▁|▁▃·▂|▅▂▇|▂▄▃▂|·▂▂▁|▆▃▂▂|·▃▁|▁▂·▁|▃▃▂▁|▂▁▃|▃▃▃▂|··▂▂▂▁▂|
CHI 20.9  14% |▂▆|▁▂▁·|▂·▁|▁▁·|·▂·▁|▃▂▅|▁▃▂▂|▁▃|▃▁·|▂▅▄|▂▁▂▃|▃▃▄|▁·▂▄|▃▂▃|▂▃▂▁▁|▁▁▁|▃▁▃·▃|▁▁▇|▂▄▂|▁▁▁|▄·▄▁·▁▁|
UTA 20.1  24% |▄▅|·▂▃▂|▄▂▁|▂▁▂·|·▁▃|·▁▂|·▄▁▁|·|▁··|▁··▃|▂▂▁|▁·▃▁|▄···|▁▁▁▁|▂▁▃▅|▁▁▁|▃█▃▁|▂·▂|·▄▂▂|▃▂▁▂|·▆·▂▁▁▁|
```

## 2026-27 projections

Each team's projected weekly score under its real 2026-27 schedule: start from its '26 games, pull its average back toward the league by the part that doesn't carry over (about 4 in 10 of the gap, measured '23→'24 and '24→'25), and take the best game for each week's real game count (NBA Cup games filled in, the same as players).

| # | Team | Projected weekly | '26 weekly |
|---|---|---|---|
| 1 | BOS | **43.3** | 47.5 |
| 2 | DET | **43.1** | 46.2 |
| 3 | OKC | **41.4** | 47.7 |
| 4 | NYK | **40.7** | 40.9 |
| 5 | CHA | **38.8** | 38.3 |
| 6 | LAC | **37.0** | 40.1 |
| 7 | TOR | **36.2** | 37.4 |
| 8 | SAS | **36.0** | 36.8 |
| 9 | GSW | **35.7** | 36.6 |
| 10 | HOU | **35.4** | 36.9 |
| 11 | PHX | **34.3** | 36.6 |
| 12 | ATL | **34.1** | 32.2 |
| 13 | CLE | **33.8** | 34.2 |
| 14 | POR | **33.4** | 30.2 |
| 15 | MIN | **32.9** | 33.4 |
| 16 | DEN | **32.1** | 31.3 |
| 17 | BKN | **31.8** | 31.8 |
| 18 | ORL | **30.7** | 28.8 |
| 19 | LAL | **30.6** | 29.2 |
| 20 | MIL | **29.8** | 29.9 |
| 21 | MIA | **29.6** | 29.0 |
| 22 | MEM | **28.3** | 24.9 |
| 23 | PHI | **28.1** | 26.9 |
| 24 | NOP | **27.2** | 25.6 |
| 25 | DAL | **26.4** | 26.5 |
| 26 | IND | **26.3** | 23.5 |
| 27 | WAS | **24.3** | 22.3 |
| 28 | SAC | **24.0** | 21.8 |
| 29 | CHI | **23.6** | 20.9 |
| 30 | UTA | **23.3** | 20.1 |

**How valuable a TEAM is**: the average starting TEAM and the best TEAM over the best one left undrafted, next to the player spots (1 G / 1 F / 1 C; DRAFT_GUIDE.md):

| Teams in the league | TEAM avg starter / best | G | F | C | Best C (Jokić) |
|---|---|---|---|---|---|
| 4 | +3.3 / +4.5 | +3.6 | +2.3 | +6.3 | +13.4 |
| 8 | +3.9 / +7.6 | +2.8 | +1.7 | +6.3 | +17.6 |
| 12 | +4.2 / +9.5 | +4.6 | +1.7 | +7.2 | +21.2 |

About as valuable as a guard spot, closer to a center spot in bigger leagues. No rescaling needed.

## How we got here

- **Point margin** (the old TEAM scoring): out. It rewards offense as much as defense and made TEAM worth twice a center.
- **Draft 1**: +5 for every line under 120 / 115 / 110 / 105 / 100 / 95 / 90, +1 per turnover forced. Followed defense well, but too smooth — it paid something every game, nothing to sweat.
- **Draft 2**: big lines (under 100 / 95 / 90) and rare bonuses only. Exciting, but everything was swingy.
- **Draft 3**: one steady category plus the swingy part; tested turnovers forced vs points under 125 as the steady one.
- **Draft 4** (current): the commissioner's numbers, above. Paint and glass cutoffs adjusted from the first ask (under 25 paint points happens in 0.5% of games; the glass is our defensive rebounds minus theirs, by 10).

## What else we looked at

Per game ('23–'26), whether teams' averages follow good defense (0–1), and whether teams repeat it next season (0–1):

| Stat | Per game | Follows defense | Repeats | Verdict |
|---|---|---|---|---|
| Turnovers forced | 14.1 | 0.34 | 0.61 | in (20+ bonus) |
| Deflections | 15.5 | 0.38 | 0.51 | out — not a basic stat |
| Contested shots | 42.1 | 0.18 | 0.61 | out — not a basic stat |
| Charges drawn | 0.4 | 0.07 | 0.44 | out — rare, not defense |
| Loose balls recovered (def) | 2.4 | 0.35 | 0.42 | out — not a basic stat |
| Box outs (def) | 4.8 | 0.43 | 0.52 | out — not a basic stat |
| Violations forced | 0.7 | 0.04 | 0.35 | in (each one) — but mostly luck |
| Offensive fouls forced | 1.6 | 0.21 | 0.56 | option — the best of the other violations |
| Steals | 7.8 | 0.38 | 0.56 | out — players score them |
| Blocks | 4.9 | 0.27 | 0.49 | out — players score them |
| Points allowed | 114.6 | 0.87 | 0.58 | in (the base) |

- **Violations forced are mostly luck** (follow defense 0.04): fun to cheer, so they stay, at a size that doesn't decide things.
- Not in: shooting percentages (too abstract), rebounds on their own, opponent 3P% (luck: doesn't repeat), "no opponent scores 30" (it's about their star), opponent points off turnovers (it's offense).
- Other violations as forced per game: offensive fouls 1.6 (follows defense 0.21, repeats 0.56); travels 0.8 (not defense); backcourt 0.1; 8- and 5-second about 1 in 50 games each.

## Data and scripts

- Team game logs (NBA.com: base, advanced, misc, four factors, opponent) '22–'26 — `scripts/pull_league_seasons.py`.
- Team violations and hustle by game day, '23–'26 — `scripts/pull_team_daily.py`. A team's violations forced = its opponent's own violations that day; checked against play-by-play on '25: all 2,460 team-games match.
- Analysis: `scripts/projection_study/team_*.py` (`team_draft4.py` current scoring + projections, `team_timeline.py`, `team_md4.py` writes this file, `team_report.py` the page).
- Write-up page: https://claude.ai/artifact/R6rsSPwshQQTizgPRxJzEr

## Log

- 2026-10-07: rework started — point margin out; TEAM = defense, like fantasy football's D/ST.
- Commissioner: weekly score = best game of the week; raw points allowed (simple); TEAM must feel impactful and be easy to root for (lines, turnovers, violations to cheer); weighting later.
- Shot clock violations come from NBA.com's team violations table (MeasureType=Violations), by day, matched to the opponent.
- Draft 1 (smooth, too easy to tune out) → draft 2 (all swingy) → commissioner: one steady bread-and-butter category, the rest swingy → draft 3 (two steady options) → draft 4 (commissioner's numbers).
- Hustle stats pulled and tested; commissioner: basic stats only this year.
- Open: violations forced +5 each or once a game.
