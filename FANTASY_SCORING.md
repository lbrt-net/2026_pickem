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

## Advanced score (v2 — draft formula, all weights 1.0 until the data is locked in)

Advanced = basic + the components below, each **+1.0 per unit** for now. Weights/structure get revisited once the data sources are loaded and their lag is measured.

| Ties to | Component | Source | Availability (per `nba_api_tests` notes) |
|---|---|---|---|
| OREB | + contested offensive rebounds | tracking (Rebounding) | Second Spectrum — can lag |
| DREB | + defensive box outs | hustle | date-filtered; lag unclear |
| AST | + potential assists, + secondary assists, + screen assists | tracking (Passing), hustle | tracking can lag |
| STL | + deflections | hustle | date-filtered; lag unclear |
| BLK | + DFG− (DFGA − DFGM as closest defender) | defense dashboard | likely Second Spectrum — can lag |
| Shooting | + shot distance profile (per shot) | play-by-play | same night |
| Shooting | + drives | tracking (Drives) | can lag |
| Misc | + loose balls recovered | hustle | date-filtered; lag unclear |
| Misc | + heave made (big bonus later) | play-by-play | same night — see note |
| Misc | + game winner | play-by-play + final score | same night |
| Misc | BLKD, fouls drawn | misc box score | same night, easy |

**Clutch scoring** (box score only, the NBA's clutch definition: last 5 min of the 4th/OT, score within 5): made FG, STL, BLK, TO count again at **×2 or ×3** of their normal value (multiplier TBD). Source: `leaguedashplayerclutch` per date (same night).

Notes:
- **Heaves:** play-by-play logs *missed* heaves as a team attempt ("ROCKETS Heave", no player), so "heave attempted" can't be credited to a player. *Made* heaves show up as a normal player 3PT make with the distance (e.g. "Black 64' 3PT Jump Shot"), so "heave made" = made FG at the end of a period from beyond a distance cutoff (TBD, e.g. ≥ 40 ft).
- **Game winner:** go-ahead made FG in the 4th or any OT with ≤ 0.3s on the game clock at the make, and the team won. Confirm the clock rule.
- Excluded on purpose: Synergy playtype, AWS season-to-date stats, abstract tracking (speed/distance, touches).

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
