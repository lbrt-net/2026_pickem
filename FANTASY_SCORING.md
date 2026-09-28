# Fantasy Scoring — Design (locked 2026-09-28, revisit anytime)

## Format: max value per game

- An entity's (player's or NBA team unit's) **weekly score = its single best game that week**, not its total and not its average.
- A fantasy team's week = the sum of its 11 slots' best games. Head-to-head.
- Why: totals reward volume, and in the load-management era volume is noise. Averages (tried on Fantrax last year) punish a bad extra game. The best game rewards ceiling and makes every game a free shot at it.
- Weeks: Mon–Sun, All-Star break fused into one 2-week period, Championship 2 weeks (`backend/fantasy_2026_27/weeks.py`).

## Basic score (v1 — decides matchups)

Traditional box score only. Settles nightly at 3 AM CT.

| Category | Stat | Weight | Source |
|---|---|---|---|
| Scoring | PTS | +1.0 | box (loaded) |
| | Missed FG (FGA − FGM) | −0.5 | box (loaded) |
| | Own shot blocked (BLKD) | −0.5 | misc box `blocksAgainst` or play-by-play — **not loaded yet, counts 0** |
| | 3PM | +0.5 | box (loaded) |
| | Missed FT (FTA − FTM) | −1.0 | box (loaded) |
| Other | OREB | +1.5 | box |
| | DREB | +0.5 | box |
| | AST | +1.0 | box |
| | STL | +2.0 | box |
| | BLK | +1.5 | box |
| | TO | −2.0 | box |

Examples: made 3 = **3.5**; 2 of 3 FT = **1.0**; missed layup blocked by Wemby = **−1.0**.

Deferred (Misc): Flagrant −2, Ejection −5 — need play-by-play.

Implemented in `backend/fantasy_2026_27/logic.py` (`SCORING`, `player_points`).

## Advanced score (v2 — sub-components)

The basic score stays the base. Advanced stats are **sub-components tied to a basic category**: each one rewards the individual skill behind that category. Not every category gets one. Each sub-component weight is ≤ 1. Exact weights: later.

Rule for inclusion: stats that are **attributable to one player as an individual act**. No abstract tracking (speed/distance, touches, possessions).

| Parent category | Advanced sub-component | Source | Availability (per `nba_api_tests` notes) |
|---|---|---|---|
| PTS / shooting | Shot distance profile (rim / midrange / 3, per shot) | play-by-play (primary) | same night |
| PTS / shooting | Drives | tracking (Drives) | Second Spectrum — can lag |
| AST | Potential assists | tracking (Passing) | Second Spectrum — can lag |
| AST | Secondary assists | tracking (Passing) | Second Spectrum — can lag |
| AST | Screen assists | hustle | date-filtered; lag unclear |
| OREB / DREB | Contested rebounds | tracking (Rebounding) | Second Spectrum — can lag |
| OREB / DREB | Box outs | hustle | date-filtered; lag unclear |
| STL | Deflections | hustle | date-filtered; lag unclear |
| BLK | DFG− = DFGA − DFGM (misses forced as closest defender) | defense dashboard (Defensive Impact) | likely Second Spectrum — can lag |

More candidates that pass the "individual act" test (suggestions, not locked):
- **Charges drawn** (hustle) → STL
- **Loose balls recovered** (hustle) → STL
- **Contested shots** (hustle) → BLK
- **Fouls drawn** (misc box) → PTS/FT
- **And-ones** (play-by-play) → PTS
- **Rim DFG−** (defense dashboard, < 6 ft) as a sharper version of DFG− → BLK
- **FT assists** (tracking Passing) → AST

Excluded on purpose: Synergy playtype (lags, unreliable), AWS gravity/leverage/shot difficulty (season-to-date only, not per game), speed/distance and other abstract tracking.

### Handling delay

- Basic score settles at 3 AM and decides matchups.
- Advanced sub-components settle per game date only once the data exists for the teams that played (the readiness check from `NBA_STATS_TRACKING.md`), re-checked nightly; a week's advanced total finalizes when every date in it is ready.
- Start advanced as a **shadow score** shown next to basic (leaderboards, player pages) — measure real lag for a few weeks before letting it decide anything.

## Tools the site needs for max-per-game (to build)

- **Projected weekly best:** expected best of N games = the expected max of N draws from the player's game-by-game distribution (this season after 10 games, else last season), N = team games left that week; floor = best game already played.
- **Weekly best average** (historical): the average of a player's weekly best games — the draft/pickup number, replacing plain per-game average.
- **Best game / ceiling** columns, and **games this week** (more games = more shots at a best game).
- **Scoring calculator** (enter a stat line → points) and the rules table on one page.
- **Top single games** leaderboard per week (who set the week's best games, and whose team they're on).
- Matchup view: each slot's best game so far, games left, projected best.
