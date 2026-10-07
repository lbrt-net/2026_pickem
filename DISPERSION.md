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
- Decision at the time: no per-player spread factor. **Superseded the same day** (below): for established players it
  repeats at ~0.4 and is now used.

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

### 2026-10-07: spread by scoring part; spread is a trait for established players (`disp5.py`)
- Commissioner's direction: a player's spread comes from what his game is made of (self-creating jump shooters vs bigs;
  outside shooters vs mid/paint maestros; turnover machines without the assists). The average of maxes isn't the max
  of averages, so build from whole games, not parts.
- Best of 3 games ÷ the part's own average (median, '23–'25, 10+ FP/G): BLK 2.21, STL 1.93, OREB 1.92, 3PM 1.73,
  AST 1.58, DREB 1.51, PTS 1.43, total FP 1.45. In the best game of a 3-game week (+7.3 over avg), PTS carry 62%,
  STL/AST/OREB 7–8% each, TOV +6% (fewer), FG− ~0 (more makes come with more misses).
- Volatile by category ('24–'26, 20+ FP/G): FGA swing — bigs (Mark Williams, Ayton, Allen, Gobert, Zubac, Jokić);
  steadiest FGA — Luka, Kawhi, Tatum, SGA, LeBron. Steals — Kawhi, SGA, Maxey, Fox. Turnovers — Cade, Durant, Jokić,
  LeBron, Trae. Blocks — Wembanyama. Threes — Curry.
- **Correction to the earlier "weak 0.2" persistence**: for established players (20+ FP/G, 60+ GP both seasons) spread
  repeats at r = 0.45 ('23→'24) and 0.40 ('24→'25). Of 35 established players, 9 were above expected all three
  seasons (Haliburton, Maxey, Luka, Mitchell, Booker, Curry, Davis, Lillard, Brunson) and 10 below (Sabonis, SGA,
  Siakam, Bam, Vučević, Sengun, Gobert, Kyrie, Tatum, Jaylen Brown); luck would give ~4 each.
- Real weekly ranges (3-game weeks, best game above avg, 25th / 90th pct): Curry +4.2 / +23.1, Durant +5.1 / +15.6,
  Haliburton +1.3 / +23.4, Sabonis +2.9 / +11.8, Jokić +3.2 / +23.2.

### 2026-10-07: player-specific PROJ MAX (`disp6.py` archetypes, `disp7.py` model) — USED
Data extended back to 2020-21. Checks on '23, '24, '25 (dev) and '26.
1. Volume: SD = 3.42 × mean^0.33.
2. Archetype prior (median spread ratio by archetype × FP band, '21–'25): Big = 6'9"+ with rim+paint ≥ 50% of FGA,
   < 35% threes, < 20% mid; self-creator = usage ≥ 25% or ≥ 45% of makes unassisted; outside = ≥ 40% of FGA from 3;
   else assisted. Priors: self-creator outside <15 FP/G +14%, 15–25 +3%, 25+ +5%; self-creator mid/paint <15 +8%;
   big 15–25 −6%, 25+ −4% (after the height rule: −2%); assisted 25+ −8%. (First pass mislabeled Durant as a big by
   height and Cade/Barnes/Amen by shot location; fixed with the height floor + usage rule.)
   Turnover-heavy without assists (2.5+ TOV, TOV/AST ≥ 0.45): **no effect** on spread (median 1.00 both ways).
3. Own record: his 3-season spread ratio, weight w = 0.5 × min(games/200, 1), log scale.
4. Shape: weekly best simulated from his own standardized games (weight min(games/300, 1)), else the pooled shape of
   players at his level (<12 / 12–20 / 20+ FP/G; one pooled shape had overshot ceilings by ~4 FP).
5. **Asymmetric downside** (commissioner): steady players (factor < 1) have the bottom half of their weekly-best range
   shifted down 0.2 SD per 0.1 of (1 − factor). Whole-range shift fixed floors but pushed ceilings over (16–18%);
   bottom-half-only keeps ceilings. Grid 0 / 0.1 / 0.2 / 0.3 chosen on '23–'25.
- Calibration (share of weeks above the 90th-pct ceiling / below the 25th-pct floor; volume-only → player):
  volatile above ceiling '24 13.4 → 9.6%, '25 13.5 → 10.1%; steady below floor '24 32.4 → 25.0%, '25 34.1 → 26.2%,
  '26 check 32.2 → 27.0%. Volatile players' floors inconsistent across seasons (left alone). Expected-best error
  '24 1.78 → 1.69, '25 1.36 → 1.29, '26 1.76 → 1.69.
- 2026-27 effect at 3 games: Luka passes SGA, Haliburton passes Mitchell/Cade, Edwards up; Durant, Sabonis down; Jokić #1.
- Write-up: sections 9–14 of https://claude.ai/artifact/NqAqKgGzV1BeV9VtZnxd8W

### 2026-10-07: in the app (`pmax27.py` → `proj_week_2026_27.json` → `scripts/load_projections.py`)
- Each pool player gets his weekly-best curve for 1..10 games (fused 2-week periods hold 6–8): expected best, bad
  week (25th pct), big week (90th pct), from the player-specific model above. A 1-game week's expected best = PROJ
  AVG exactly (the steady-player downside shift had pulled it below the mean). Rookies: volume + level shape only.
- At load, the server applies the curve once to the 2026-27 schedule (league default week rules): each week his NBA
  team's game count picks the point; PROJ MAX = average over the season's 21 weeks. NBA Cup games not yet scheduled
  (placeholders + makeups) are filled into the Cup final week so each team has 82 (in 2025-26 that week still had only
  56 team-games). No availability yet (every scheduled game counts).

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
