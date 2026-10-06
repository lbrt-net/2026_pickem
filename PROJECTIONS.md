# Projection model — decisions and known failures

Working notes for the fantasy projection system (weekly score = a player's best single game).
Seasons are named by their ending year: '25 = 2024-25. **'26 (2025-26) is the validation season**:
never fit on it, never use it to pick test players. Study scripts so far live outside the repo (session scratchpad);
numbers below are from those runs on 2026-10-06.

## Chain

FG points/G = poss/G × FGA per 75 / 75 × Σ_zone (zone share × zone FG% × 2 or 3)
poss/G = MPG × pace / 48

## Data on disk (nba-pipeline/data/raw/)

| What | Seasons | Source |
|---|---|---|
| Traditional box scores | '22–'26 ('21 in progress) | boxscoretraditionalv3 per game |
| Shot zones, league-wide | '21–'26 | LeagueDashPlayerShotLocations (By Zone) |
| Player / team advanced (POSS, PACE, USG_PCT) | '21–'26 | LeagueDashPlayerStats / LeagueDashTeamStats, Advanced, Totals |
| Bios (age, height, weight, draft) | '20–'26 | LeagueDashPlayerBioStats |
| Team rosters | 2025-26, 2026-27 | CommonTeamRoster |
| '26 opening rosters | '26 | first-game team from box scores |

Gotchas: advanced `MIN` is per game even with PerMode=Totals (season minutes = MIN × GP); `POSS` is a season total.
My box-score possession estimate matches NBA `POSS` within ±1.5% (median ratio 0.998).

## Settled (good enough)

| Piece | Method | '26 error | Baseline |
|---|---|---|---|
| Zone share | 5 seasons, each season weighted 5× the one before, no trend | 8.8% of shots in wrong zone | 9.0% "same as '25" |
| Zone FG% | '23–'25 attempt-weighted, k=25 toward league zone %, no pull at 200+ zone attempts | within 0.3–0.9 pp of the noise floor | — |
| Pace | player's own on-court PACE (recency-weighted) | 1.84 | 2.14 with team pace |
| MPG | '25 MPG, keep 70% of distance from ~26.9 | 3.03 min | 3.20 |
| Usage (stayers) | resplit: prior USG on the new roster, raw prior MPG, scaled so team = 100%, cap 40%, minus bias | 1.75 pp | 1.88 |

## Known failures (taken as-is for now)

- **Usage for players who change teams.** Resplit has no skill (corr of predicted vs actual change +0.10, n=70 over
  '22→'26); "same as last year" is better (2.74 vs 2.89 pp). Movers regress to the middle: <17% usage movers gain
  +1.6, >21% lose −1.7. Not modeled.
- **Shot-mix development** (Adebayo, Turner moving to 3s faster than their trend). A linear trend for everyone adds
  noise; the tuning picks no trend.
- **Minutes role changes** (Tre Mann, Agbaji, Tyus Jones, Capela, Ivey collapsing; Porter Jr. jumping). Biggest
  single source of volume error. Roster competition not modeled yet.
- **Team continuity weighting** didn't help shot share (continuity ≈ recency; rosters turn over too fast).
- Players with no prior NBA data (rookies) get placeholders: 18% usage, 15 MPG.
