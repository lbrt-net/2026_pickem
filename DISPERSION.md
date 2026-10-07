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

(Next steps from here were done 2026-10-07, below.)

### 2026-10-07: spread vs the commissioner's axes (`scripts/projection_study/disp2.py`)
PlayerGameLogs, every game played, league scoring incl. BLKD; player-seasons with 40+ games; dev '22–'25 (1,419).
- **Spread = 3.45 × mean^0.33** (FP SD): 10 FP/G → ±7.3, 25 → ±9.9, 40 → ±11.6.
- Holding the mean fixed (spread ÷ expected, median per group), the axes barely matter:
  usage <15% −6%, 15–19 +1%, 19–23 +4%, 23–27 +2%, 27%+ +2%; minutes −1% to +2%; PIE −2% to +1%; age 32+ −4%;
  share of FP from points, lowest to highest fifth −6% → +4%; from rebounds +4% → −4%; G +3% vs F/C −2%.
  Together (3PT-points share, usage, points share) R² 0.08.
- **A player's extra spread repeats weakly**: r = 0.21 / 0.23 / 0.23 / 0.19 season to season ('22→'26).
- Steadiest (20+ FP/G, 3+ seasons): Durant −15%, Chris Paul −13%, Bam −12%, Gobert, Siakam, Sabonis −9%. Most
  volatile: Curry +13%, Booker, Maxey, Haliburton +9%, Davis, Luka +8%. Three-point-heavy scorers swing; bigs and
  mid-range scorers don't.
- Decision: no per-player spread factor for now (worth ≤ ~1 FP in a 3-game week). If added later: keep ~20% of his
  prior-season extra spread.

### 2026-10-07: weekly best game (PROJ MAX) tested on real weeks (`disp3.py`, `disp4.py`)
Every player-week Mon–Sun; each model gets his actual season mean (tests the spread only).
- Projected − actual best game, avg of '24 + '25, by games he played that week (1 / 2 / 3 / 4):
  average only +2.3 / −3.5 / −6.8 / −9.0; normal +2.3 / +1.0 / +0.2 / −0.5; league shape +2.3 / +1.0 / +0.3 / −0.2;
  his own prior-season games +2.3 / +0.9 / +0.2 / −0.3. |error| ≈ 5.6 for every spread model (one week's noise) vs 7.6
  average-only. '26 check the same.
- **League shape** E[best of n] in SDs above the mean, n = 1..5: **0, 0.557, 0.859, 1.063, 1.215** (normal: 0, 0.564,
  0.846, 1.029, 1.163). **PROJ MAX = PROJ AVG + 3.45 × PROJ AVG^0.33 × that.**
- **Missed-game weeks**: when he played every team game, bias is ~0 (n=2–4: −0.2 to +0.3, all seasons). When he
  missed one, his other games are 1.5–2.5 FP worse (n=1 +2.1 to +2.6, n=2 +1.5 to +1.9). → availability model: a
  questionable / just-back player needs a lower expected game, not just fewer games.
- Per player, '26 check, 3-game weeks where he played every game (6+ weeks): 161 of 193 within 3 FP of his actual
  average best.
- Write-up: https://claude.ai/artifact/NqAqKgGzV1BeV9VtZnxd8W

**Next**: availability (chance he plays + lower game when hurt), opponent / home-away / height-weight matchup, the
small player spread factor, win probability by simulated draws.

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
