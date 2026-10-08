# TEAM scoring

Every fantasy roster has one **TEAM** spot: you draft a whole NBA team, like a defense in fantasy football. Players already score for what they do (points, rebounds, assists, steals, blocks). **TEAM is where a team's defense shows up.** Seasons are named by the year they end ('26 = 2025-26). Basic box-score stats only this year.

## The scoring (current: draft 5)

Per game:

| What | Points | Games it happens in ('23–'26) |
|---|---|---|
| Every point the opponent finishes under 120 | +1 each | 66% |
| Hold them under 100 | +10 | 11% |
| Every shot clock violation forced | +2 each | 49% |
| Hold them to single-digit fast-break points | +5 | 22% |
| Hold them under 30 points in the paint | +10 | 2% |
| Force 20+ turnovers | +5 | 9% |
| Win the defensive glass by 10+ (our defensive rebounds minus theirs) | +5 | 10% |

**Weekly score = the team's best game of the week**, the same as players.

Example: hold a team to 96 with one shot clock violation and 7 fast-break points → 24 (under 120) + 10 (under 100) + 2 (shot clock) + 5 (fast break) = **41**.

## Why this shape

- **A bread and butter that pays most games**: points under 120. The score is on the screen, and points allowed is the clearest sign of a good defense — the teams that allow the fewest points are the teams with the best defensive ratings (0.87 out of 1, '23–'26).
- **A line to root for late in a game**: under 100. Rare, and worth a lot.
- **Moments to cheer one at a time**: every shot clock violation forced.
- **Bonuses that don't come every week**, even for good defenses: fast break, paint, turnovers, glass.
- **It follows real defense**: a team's average weekly score lines up with its defensive rating at 0.84 and repeats next season at 0.58, so a TEAM can be drafted like a player.

Where a weekly score comes from: points under 120 65%, shot clock violations 6%, under 100 13%, the four bonuses 16%. A weekly score averages **24**, give or take 15 — about a star player's best game.

## Last season (2025-26)

| # | Team | Weekly score | Weeks of 50+ | Games at 0 | Best game | Held under 100 | Defensive rating |
|---|---|---|---|---|---|---|---|
| 1 | OKC | **36.8** | 14% | 3% | 55 | 21% | 106.5 |
| 2 | BOS | **36.8** | 29% | 3% | 69 | 24% | 111.7 |
| 3 | DET | **34.4** | 24% | 1% | 67 | 16% | 108.9 |
| 4 | LAC | **31.7** | 10% | 15% | 59 | 16% | 115.2 |
| 5 | NYK | **30.8** | 5% | 12% | 84 | 20% | 112.3 |
| 6 | CHA | **29.4** | 5% | 13% | 56 | 23% | 113.5 |
| 7 | PHX | **29.2** | 0% | 5% | 44 | 16% | 112.9 |
| 8 | SAS | **29.1** | 10% | 8% | 58 | 14% | 110.4 |
| 9 | HOU | **29.0** | 0% | 4% | 48 | 18% | 112.1 |
| 10 | TOR | **28.2** | 5% | 9% | 60 | 15% | 112.1 |
| 11 | GSW | **28.2** | 14% | 15% | 62 | 15% | 114.4 |
| 12 | CLE | **24.5** | 10% | 12% | 63 | 11% | 114.2 |
| 13 | MIN | **24.2** | 5% | 7% | 54 | 8% | 112.5 |
| 14 | ATL | **22.8** | 0% | 11% | 48 | 11% | 112.9 |
| 15 | DEN | **22.1** | 5% | 21% | 63 | 8% | 116.0 |
| 16 | MIL | **21.8** | 0% | 20% | 47 | 8% | 118.3 |
| 17 | LAL | **21.7** | 5% | 15% | 50 | 8% | 115.5 |
| 18 | MIA | **21.6** | 0% | 9% | 48 | 8% | 113.6 |
| 19 | ORL | **21.0** | 5% | 14% | 51 | 9% | 113.6 |
| 20 | BKN | **20.7** | 14% | 11% | 57 | 7% | 118.3 |
| 21 | POR | **20.1** | 5% | 16% | 71 | 8% | 113.6 |
| 22 | PHI | **20.1** | 0% | 8% | 41 | 5% | 114.4 |
| 23 | DAL | **18.5** | 0% | 20% | 49 | 4% | 115.5 |
| 24 | MEM | **18.4** | 0% | 19% | 46 | 7% | 118.5 |
| 25 | NOP | **18.0** | 0% | 16% | 42 | 5% | 117.6 |
| 26 | IND | **16.0** | 0% | 19% | 49 | 5% | 117.9 |
| 27 | CHI | **14.8** | 0% | 23% | 43 | 3% | 117.5 |
| 28 | SAC | **14.5** | 0% | 20% | 37 | 3% | 120.3 |
| 29 | WAS | **14.0** | 0% | 23% | 46 | 4% | 121.5 |
| 30 | UTA | **13.5** | 0% | 31% | 49 | 3% | 120.8 |

Defensive rating = points allowed per 100 possessions (lower is better), for comparison.

### Every game, every team

One line per team, every game October → March. `|` starts a new fantasy week (21; the All-Star week and the final are 2-week periods). Each character is one game: `·` = **0**, `▁▂▃▄▅▆▇█` = higher (each step about 7.5 points; `█` = 52+). Before the line: average weekly score, share of games at 0. 13% of games score 0, but only 0.5% of weeks do.

```
OKC 36.8   3% |▃·▄|▆▃▃▃|▃▁▄▄|▄▆▇|▄▅▃▅|▅▂▁|▃▃▄|▇▂|▄▂|▅·▁▃|▁▆█▄|▂▁▂▂|▆▆▂|▃▃▂▃|▅▁▃|█▂▂|▂▃▃▇▁|▄▁▁▆|▃▃▆|▁▃▄|▃▆▂▃▁▁▄|
BOS 36.8   3% |▁▄▁|▇▄▂▂|▃▃·▂|▃▇▂|▆▂▁|▁▂▁|▁▄▃▁|▁|▂▂▆|▇·▃|▁▃▂|▄▃▁▃|▆▁▃|▃▄▁▁|▅▁▆█|▃▇▅▂|▃▃▇|█▃▂▆|█▁▃▅|▁▃▄|▃▅▂▃▂▄▆|
DET 34.4   1% |▂▂▂|▂▁▃|▃▃▄▃|▁▂▃|▃▃▁|▁▂▂▁|▆▂▂▂|▃|▃▁█|▄▁▁▃|▃▂▂|▇▅▆|▃█|▃▃▃▂|▂▂·█|▁▁█|▆▅▂▃|▂▃▂▆|▂▁▃▁|▆▂▃▁|▂█▅▂▁▃▇|
LAC 31.7  15% |▁▄▃|▅·|·▁▃▂|▃▁▂·|▂▁▁▁|·▂▂|·▆▃▂|▁|·▁▇|▃▃▅|▆▃·|▄▂▃▇|▂▃▁|▃·▃▇|▄▁█|▁·▂▆|▃▄▁·▂|▆▁|▄▃▁·|▂▁▃▂|▂▁▃▁█▅▂▂|
NYK 30.8  12% |▂▆▁|·▂▁|▄▁▅|▁··|▂▂▁|▃▄▂▆|·▃▂▃|▃·|▁▃·|▁·▁|▁·▂▁|▁▂▃▁|▂·▄|▁█▂|▆▆▆▄|▃▁▁▇|▁▇▁▃▅|▃▇▇|▆▅▄▂|▁▁▇▃|▂▆▂▁▂▂|
CHA 29.4  13% |▂·▁|···▃|▁·|·▄▁▂|▂▁▁▂|▁▁▂|▁▁█▁|▁▂|·▂|·▃▃|▁▁·▅|▇▅▃▆|▂▂▁▇|▇▆▃|▆▅·▃|▆▅▁|▂▂▃▁▂|▆▃▆|▆▇▁▂|▃▃▂|▂▂▄▇▄▁▃|
PHX 29.2   5% |▁▁·|▁▁▆▁|▁▃▃|▆▃▅·|▃▄▄|▂▄·▁|▄▂|▄▁▂|▆▂|▃▃▁|▃▁▄▄|▄▅▃▆|·▃▅|▁▂▃▂|▅▅▂▁|▁▄▂|▂▁▁▂▆|▆▃|▃▃▁▅|▂▃▁|▁▂▃▃▆▁▂|
SAS 29.1   8% |█▂▅|▃▄▁|▂▃▁|▁▃▄▃|▄▁▂|▄▁▁|▁▂▁|·▁▂|▇▆▁|▃▄▁|▂·▂▁|▄▆▆▃|▁▄·|▂▂▂▃|▆▃▄|▄·▁|▂▂▇▁|▃▃▂▂|▇▂▂·|▁·▄|▁▄▃▂▂▅▇|
HOU 29.0   4% |▁▁|▃▂▄|▃▂▁▂|▂▂▂|▃▂|▇▄▄|·▇▆▁|▂|▁·▃▁|▁▆▃|▁▆▂|▆▃▂▃|▃▂▃▂|▃·▃|▅▂▆▃|▂▃▃▃|▅▃▄▃|▃▅▂▁|▂▂▅▁|▅▁▃|▃▁▆▁▂▂▃▃|
TOR 28.2   9% |▂▁▁|▂▁▄▃|▄▆▁|▃▂▂|▂▂▃▂|▅▅▁▁|▁·▂·|▁|▅▅▂▆|▆·▁|▃▃▁|▃▅▁▂|▂▄·▂|▂▃▆▃|▁·▅|·▃▃|▂▄▇|▂▂▁|▂▁▆|▁▁▁▂|▃·▁▁▁▃█|
GSW 28.2  15% |▄·▁|▁█▁▁|▂·▁█|▁▁▃▃|·▂▂|▁▃▅|·▅▆▆|▁▁|▅▁|▅▁▁|▂·▁▁|▃▂▃▁|▆▂▁|▂▁▁█|▃·▁|▂▆▃|▂▁·▁|▁▂·|▁▂▅|▁▁▁▂|▂·▂·▂▃·▁|
CLE 24.5  12% |▁▂▂|▆▁▂▃|▁▂▁|·▂▁▃|▃▁▂▃|▂▁▁|▁▁▂▅|·▁|▁·|▁▁·▁|▃▂▃▂|▃·▁|▁▂▁|▁▇▁▃|▅▅▂▃|▆·|▁▃█▃·|▆▁▁▃|▂▃|▄·▃▁|▂▂▃▁▁·|
MIN 24.2   7% |▂▁▂|▁▁▃|▃·▆▁|▁▂▁|▆▂▂|▁▂▂▂|▁▁▃|▃·▃|▁▃▄|▃·▁|▃▁▁▁|▆▁▁▃|▄▂▁|▁▁▂|█▃▂▂|▁·▁▂|▁▄▂▁|▁▆▃|▃▃▂|▁·▂▁|▅▃▂▆▃▃|
ATL 22.8  11% |·▃▁|▂▂▃▁|▂▂▅|▄▆▁▁|▁▁▇▃|▁··|▆▁·▂|▁▁|▁▁▁|·▁▁|▁▃▅·|▁▃▇▂|▁▁▁|▂▁▃|▁▃▃▁|▁▁▁|·▄▃▁▄|▅▆▄|▂▂|▂▆▆|▂▁▂▃▃·▃▁|
DEN 22.1  21% |▁▃|▃▇▂|·▂▃▅|▂▂▂|·▁▃▁|▁▁▂|··▁▂|▃|·▁▁|▂▁▁·|▁▃▂·|·▃▂▃|▂▂▁▂|▁▆▄|▂▃▃·|·▁▁|▁▂▂▅▁|█·▁|·▁▁|·▆▁▁|▆·▁▃▁··▆|
MIL 21.8  20% |·▁▂|▂▃▁|▁▁▂▁|▂▃·▁|▁··|▂▂▁▇|·▃▃▁|▅▁|▂▃|▅▁▃|▁▁·▅|▁▃▃|▁▁|▂·▃|▁▂▃|▁·▅|▁▄▇▁▁|▁▂▁·|▂·▆·|▁▂·▁|▁▂▃·▁··|
LAL 21.7  15% |▁▃▁|▁▁▂·|▁▂·|▃·▃▅|·▂|▂▁·|··▁▂|▁▂|▁▃|▁▁▃|▂▁▂|▄▃▃|▁▂▁▁▆|▄▃▂|▁▁▃▂|▃▁▅|▂▁▃·▂|▃▂▄▃|▃·▁▅|▃▁▁|▇▁·▃▁·▆|
MIA 21.6   9% |·▃▃|▂▂▁|▁▁▂▁|▂▁▁|▂▇▃▁|▃▃▁|▁▁▃▁|▁|▄▅▁▁|▂▂▂|▁▃▁▄|·▁▁|▁▁▁|▁▁▂▂▃|·▂▁▆|·▆▃|▂▂▆▁|▁·▃|▅▃▁▃|▂▃▁|▁▂··▃▁▁|
ORL 21.0  14% |▁▂▃|▁▁▃▆|▁▂▂|▃▃▆▁|▁▄··|▃▃|▂▂▃▂|▂·|▁·|▁▂▁·|▂▂▁·|▁▅▃▁|▂·|·▁|▂·▁▂|▁▅▂|▆▂▆▂▂|▃▁▃|▃▁▆▇|▁▁▂|▁▂▁▃▁·▁▁|
BKN 20.7  11% |▁▁▁|▁▁·|▁▃··|▁▃▃|▃▃▁|▁▁▂|▃▃▁▃|▁█|▂█|▃▂|▁·▁▁|▃▁▃|▂▁▂▁|▁·▁·|▂▃▅▁|·▂▂|▂▂▂▃▂|▁▁▁▃|·▁▃|▂▁▂▃|▂▁█▁▂▃▂▅|
POR 20.1  16% |▁▁▂|▃▁▃|▁▁▁|▁▂··|▁·▁·|▃▁·|·▂▁▂|▁·|·▇|▂▂▃▂|·▁▂▂|▁▃▃·|▁▄▂▂|▃▂|▃▁▁▁|▁▁▁|▁▁▁▁█|·▃▃▁|▁▃▃|▃▁▃|▅▁▃·▇▆▄▇|
PHI 20.1   8% |▁▁|·▁▂▃|▁▁▁▂|▃▂|▂▁▁·|▁▃▂|▃▅▄▂|▃▁|▃▁|▂▂▁|▁▂▁|▁▃▆▁|▃▁▁|▅▂▁▂|▂·▃▁|▂▆▁▅|··▁▁▃|▂▁▃|▁▃▁|▁▂·▅▃|▁▂▂▁▁▂|
DAL 18.5  20% |▁▁▁|▃▃▁|▂▄▁▃|▂·▂▁|▁▁▁▄|▃▁▂|▁▃·▄|▂|·▂▁|▁··▁|▁▁▃|▅▁▁|▃▁▁·|▆▂▂|▁·▂|▃▁▁|▁▁·▁|▂▁·▃|▁▁▁·|▁▂··|··▁▁·▇|
MEM 18.4  19% |▁▁▃|·▂▁▁|▂·▃▂|▁▁▄|▂▇▅|·▁▂▃|▁▅▇|▁|▃▃·|▁·▅▁|▁▂·|▃▁▂▅|▁▃|▁·|▃▄▂▁|····|▂▁▂·|·▁▄▃|▁▁▁|▁▁▁▁|▁▁▂▁·▁▁▁|
NOP 18.0  16% |·▁|▁··▁|▃▅·|▁·▁▁|▂▁▁▁|·▁▄▁|·▁▃|▁▁▃|▂▃|▂·▁▁|▁▁▁▁|▂▂▃▁|▁▂·▁|▃·▅|▃▃·|▃▁▂|▆▁▁▂|▄▁▃▁|▃·▂▁|▂▂|▂▂▆▂▁▁▁▁|
IND 16.0  19% |·▁▂|▂·▂|▁▂▁▁|▁·▁|▁▁·|▁▆▇▃|▁▁▃|▃▁▃|▁▁|▃▂▁▁|▂▂▁▁|·▂▅|▆▁▁·|▂▂▂|·▂▁|▂▁▃▁|·▃▂▁·|·▁▁|·▁▁|▁▁▄·|·▁▁·▁▂▁|
CHI 14.8  23% |▂▅|▁▁▁·|▂·▁|·▁·|·▁··|▂▁▄|▁▂▁▁|▁▂|▂▁·|▁▄▂|▁▁▁▂|▁▂▃|▁·▂▃|▂▁▂|▁▂▁▁▁|▁·▁|▂·▂·▃|▁·▆|▁▃▁|·▁▁|▃·▂··▁▁|
SAC 14.5  20% |·▄·|▂▁·|▁▁·▁|▁▂▁▁|▁▁▁|▂▂▁▃|▁▂|▁·▁|▂▅▁|·▃▁|·▁·▁|▃▁▅|▂▄▂▁|·▁▁▁|▄▂▂▁|·▂▁|·▁·▁|▂▂▁▁|▁▁▃|▃▁▃▂|··▁▁▁·▁|
WAS 14.0  23% |·▃▁|▁·▁|▁▂·▂|▁▁▁|▁▁·|▂▁|▁▁▁▁|·▇|▁·▁|▁▂▂|▁▂▅·|▂·▁▂|▁▁▁|▃▄▁|▂▅▁▂|·▁··|▁▃▁·|▁▁▁|▂▁▁·|▁·▃|▁▁▁··▃▁·|
UTA 13.5  31% |▃▄|·▁▂▁|▃▁▁|▁▁▁·|·▁▂|·▁▁|·▃▁▁|·|▁··|▁··▂|▁▁▁|▁·▂▁|▃···|▁·▁▁|▁▁▃▃|···|▂▇▂·|▁·▁|·▃▂▁|▂▁▁▂|·▆·▁▁▁▁|
```

## 2026-27 projections

Each team's projected weekly score under its real 2026-27 schedule: start from its '26 games, pull its average back toward the league by the part that doesn't carry over (about 4 in 10 of the gap, measured '23→'24 and '24→'25), and take the best game for each week's real game count (NBA Cup games filled in, the same as players).

| # | Team | Projected weekly | '26 weekly |
|---|---|---|---|
| 1 | BOS | **33.8** | 36.8 |
| 2 | DET | **32.2** | 34.4 |
| 3 | OKC | **31.8** | 36.8 |
| 4 | NYK | **31.4** | 30.8 |
| 5 | CHA | **30.0** | 29.4 |
| 6 | LAC | **28.8** | 31.7 |
| 7 | SAS | **28.3** | 29.1 |
| 8 | HOU | **27.7** | 29.0 |
| 9 | TOR | **27.4** | 28.2 |
| 10 | PHX | **26.9** | 29.2 |
| 11 | GSW | **26.8** | 28.2 |
| 12 | ATL | **25.4** | 22.8 |
| 13 | CLE | **24.7** | 24.5 |
| 14 | MIN | **24.0** | 24.2 |
| 15 | POR | **23.8** | 20.1 |
| 16 | ORL | **23.4** | 21.0 |
| 17 | DEN | **23.2** | 22.1 |
| 18 | LAL | **22.8** | 21.7 |
| 19 | BKN | **22.2** | 20.7 |
| 20 | MIA | **22.0** | 21.6 |
| 21 | MIL | **22.0** | 21.8 |
| 22 | MEM | **21.1** | 18.4 |
| 23 | PHI | **20.8** | 20.1 |
| 24 | NOP | **19.3** | 18.0 |
| 25 | DAL | **18.9** | 18.5 |
| 26 | IND | **18.6** | 16.0 |
| 27 | SAC | **16.7** | 14.5 |
| 28 | CHI | **16.5** | 14.8 |
| 29 | UTA | **16.4** | 13.5 |
| 30 | WAS | **16.4** | 14.0 |

**How valuable a TEAM is**: the average starting TEAM and the best TEAM over the best one left undrafted, next to the player spots (1 G / 1 F / 1 C; DRAFT_GUIDE.md):

| Teams in the league | TEAM avg starter / best | G | F | C | Best C (Jokić) |
|---|---|---|---|---|---|
| 4 | +2.3 / +3.8 | +3.6 | +2.3 | +6.3 | +13.4 |
| 8 | +3.1 / +6.4 | +2.8 | +1.7 | +6.3 | +17.6 |
| 12 | +4.5 / +9.1 | +4.6 | +1.7 | +7.2 | +21.2 |

About as valuable as a guard spot, closer to a center spot in bigger leagues. No rescaling needed.

## What a TEAM is worth in the draft (draft 5, 2026-10-07)

One draft board with every player and every NBA team, ranked by value over replacement (projected weekly score minus the best one left undrafted at that spot), for the default lineup G / F / C / TEAM. One point a week over replacement is worth about **2.6% of a weekly win** in this lineup.

| League size | Where the TEAMs go (overall pick, + points a week over replacement) |
|---|---|
| 4 teams | BOS #6 (+3.8), DET #7 (+2.2), OKC #9 (+1.7), NYK #10 (+1.3) |
| 8 teams | BOS #5 (+6.4), DET #8 (+4.8), OKC #10 (+4.3), NYK #12 (+3.9), CHA #15 (+2.6), LAC #19 (+1.3), SAS #23 (+0.9), HOU #30 (+0.2) |
| 12 teams | BOS #5 (+9.1), DET #9 (+7.6), OKC #10 (+7.1), NYK #13 (+6.7), CHA #15 (+5.3), LAC #20 (+4.1), SAS #23 (+3.6), HOU #28 (+3.0), TOR #29 (+2.7), PHX #32 (+2.2), GSW #33 (+2.1), ATL #43 (+0.7) |

- **The top four defenses (Boston, Detroit, OKC, Knicks) are early picks**: the first TEAM goes around 5th–6th overall, worth +4 to +9 a week (10–23% of a weekly win) — about half a Jokić, as big as a top guard or forward.
- **After them TEAMs flatten fast**: the fifth-best is barely better than the last one taken. Take an elite TEAM in round 1–2, or wait.
- The average starting TEAM (+2.3 to +4.5) matches an average starting G / F / C (+3.6 to +4.5): TEAM is as important as a player spot, not more. (`scripts/projection_study/team_value` numbers from team_draft4.py + draft_guide.py.)

## How we got here

- **Point margin** (the old TEAM scoring): out. It rewards offense as much as defense and made TEAM worth twice a center.
- **Draft 1**: +5 for every line under 120 / 115 / 110 / 105 / 100 / 95 / 90, +1 per turnover forced. Followed defense well, but too smooth — it paid something every game, nothing to sweat.
- **Draft 2**: big lines (under 100 / 95 / 90) and rare bonuses only. Exciting, but everything was swingy.
- **Draft 3**: one steady category plus the swingy part; tested turnovers forced vs points under 125 as the steady one.
- **Draft 4**: the commissioner's numbers — +1 per point under 125, +10 under 100, +15 more under 90, +5 per time violation (shot clock, 8-second, 5-second), and the four bonuses. Paint and glass cutoffs adjusted from the first ask (under 25 paint points happens in 0.5% of games; the glass is our defensive rebounds minus theirs, by 10).
- **Draft 5** (current, above): points start at 120, no under-90 bonus, +2 for each shot clock violation (8- and 5-second violations out).

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

- **Violations forced are mostly luck** (follow defense 0.04): fun to cheer, so shot clock violations stay at +2 each — a size that doesn't decide things.
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
- Commissioner: draft 5 — +1 per point under 120, +10 under 100 (no under-90 bonus), +2 for each shot clock violation forced; bonuses unchanged.
