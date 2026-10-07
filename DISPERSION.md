# Dispersion, uncertainty, PROJ MAX — running log

Everything about the *spread* of a player's games (not the per-game mean, which is `PROJECTIONS.md`). **Append every
experiment and every significant idea here as it happens**, with the date, what was tried, the result and the
decision. Don't make anyone reconstruct it later.

## Why it matters (the league's scoring)
A player's weekly score is his **best single game** that week, not a total or an average. So the number that drafts
and lineups need is **PROJ MAX**, the expected best game given how many games he plays that week. That depends on his
mean (PROJ AVG) *and* the spread of his games.

## Commissioner's ideas (from the 2026-10 sessions, keep)
- PROJ MAX is the expected max of a random slate of games. Show it as something like a 75th-percentile or IQR of
  outcomes, not one number.
- **Games that week matter a lot**: 5 chances vs 2 makes a 90th-percentile game far more likely. The mean max grows
  with game count.
- **Opponent**: lean into who the opponent is: pace, fantasy points allowed, and the matchup by height/weight (bios).
  **Home / away.**
- **Chance he plays**: needs an availability model (injury report feed, injury-type durations). It's separate from
  dispersion but feeds PROJ MAX (a game he misses isn't a chance).
- **Win probability for a fantasy team**: simulate by drawing random games from past seasons of players with similar
  expected output and similar uncertainty, then count wins.
- **Measure heteroscedasticity against other axes, not only the mean**: usage, minutes played, good vs bad player.
  That is how to test it.
- Uncertainty ranges are not shown in the report (dropped 2026-10-07). They live here.

## Built already (app)
- `backend/fantasy_2026_27/lineup.py`: `expected_best` (projection math for a week's best game) and `week_view`
  (per-player projection, weekly score, team totals), served at `GET /team/{id}/week`.

## Experiments

### 2026-10-06: homoscedasticity, first look (`scripts/projection_study/dispersion.py`)
Per player-season ('23–'25, 40+ games of 10+ min), SD ∝ mean^b across players:
- Per-game counts are **not homoscedastic**: b ≈ 0.5 (counting noise) for REB, AST, STL, BLK, TOV, 3PM, FTA, OREB,
  DREB. STL/BLK/TOV/AST are almost exactly Poisson (variance ÷ mean 1.01–1.16). PTS (3.0) and FTA (2.1) are
  over-dispersed (points come in 2s and 3s, FTs in pairs).
- **FP per 75 possessions is close to homoscedastic** (b = 0.11, R² 0.03), and so is FGA per 75 (0.17). Per game, FP
  SD grows slower than the mean (b = 0.39): ±6.9 at 10 FP/G, ±9.8 at 26 FP/G. Stars are relatively steadier.
- Short games are noisier per possession. REB matches pure counting noise (1.57× under 40 possessions vs 70+); PTS
  and AST only 1.23× (role and game script, not just counting).
- Paused there by the commissioner.

**Next when resumed**
1. Spread vs **usage**, vs **minutes**, vs **good/bad player** (commissioner's axes), not only vs the mean.
2. Split each player's FP spread into possessions-per-game vs FP-per-possession, and player-specific vs role-driven.
3. Then the max-of-N-games math against real weekly bests ('26 weeks, Mon–Sun).

### Uncertainty of the per-game mean ('23–'25 → '26 validation; moved from PROJECTIONS.md 2026-10-07)
Middle 50% / 80% of actual − projected FP/G (computed before the 2026-10-07 changes: 30-game base, young minutes,
shooting rules; recompute before using):

| Group | Middle 50% | 80% |
|---|---|---|
| Everyone | −2.8 to +2.6 | −5.4 to +4.9 |
| Projected 24+ | −2.0 to +2.3 | −3.9 to +4.2 |
| Projected 18–24 | −3.0 to +1.4 | −4.0 to +2.9 |
| Projected 12–18 | −3.6 to +1.8 | −6.5 to +3.7 |
| Projected under 12 | −2.0 to +3.7 | −4.9 to +5.7 |
| Age ≤ 23 | −1.4 to +4.0 (median +1.6) | |
| Age 32+ | −3.8 to +1.5 (median −1.1) | |
| Changed teams | −4.5 to +2.4 (median −1.6) | |
| Rookies, picks 1–5 | +1.5 to +7.1 | |

`projections_2026_27.csv` still carries `lo` / `hi` from these rows (vets by projected FP/G, rookies by pick). They
aren't shown anywhere now.
