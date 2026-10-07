# Projection model — rules, decisions, known failures

The fantasy projection system: **per-game** projections for every player (what he does in a game he plays).
Availability (games played), weekly max, win probability and draft value come later and build on this.

Conventions:
- Seasons are named by their **ending year**: '25 = 2024-25, '27 = 2026-27 (the season we project for the draft).
- **'26 (2025-26) is the validation season** when testing: never fit on it, never use it to pick test players.
  When projecting '27 for real, '26 is an ordinary input.
- Per-game FP uses the league scoring in `backend/fantasy_2026_27/logic.py` **minus BLKD** (BLKA game logs are pulled,
  not wired in yet).
- Check list after any change: `nba-pipeline/data/raw/top50_superset_23_26.csv` (87 players who were top 50 in FP/G in
  any of '23–'26), especially the ones injured in '26.

Study scripts live in `scripts/projection_study/` (copied from the session; they hard-code local paths). Output files
are in `nba-pipeline/data/raw/`. Numbers below are from runs on 2026-10-06.

## The chain

```
poss/G      = MPG × pace / 48
FGA/G       = poss/G × FGA per 75 / 75          (FTA, AST, STL, BLK, TOV, OREB, DREB the same way)
FG points   = FGA/G × Σ_zone (zone share × zone FG% × 2 or 3)
points      = FG points + FTA/G × FT%
FP/G        = league scoring over the projected line
```

## Rules

### Which seasons feed a projection
- Rates: the **3 seasons before the target**, weighted by possessions (a season with 0 games drops out on its own).
  Zone mix: 5 seasons.
- **Base season** (minutes, usage, career features) = most recent input season with **30+ GP**; else 20+; else any.
  (2026-10-07: was 50+. Chosen on the '24/'25 targets: 50 → 457 within 3 FP/G, 40 → 464, 30 → 464, 20 → 466. A 30-game
  season is a real look at how he plays now: Wembanyama '26 28.4 → 33.6 (actual 33.1), Zion 27.1 → 22.2 (22.4).
  Embiid still too high: base '24, 32.1 vs 28.0.)
  Injury-shortened seasons don't set the base. Age = base-season age + the seasons in between.
- **Missing time to injury does not lower the per-game projection** (age still applies). Injury effects belong in the
  availability model. Known cost: a young player's real breakout in a short season gets under-weighted (Brandon Miller
  '25), and an old player's real decline in a short season too (Paul George '25). Open idea: GP-weighted blend of
  recent seasons instead of one base season.

### Late-season jumps (tank runway)
Principle (commissioner): teams that are trying to win don't give bad players minutes; late-season minutes on a team
that has stopped trying aren't real, and the fantasy season ends before the NBA's anyway.
- Use the **whole season** by default (for good players it doesn't matter).
- A player-season is a **late jump** if, in the **final fifth** of the schedule, he played **15+ minutes per team game**
  after **nothing** in the first 80%: under 10 MPG in games played (5+ games), or under 5 games and he wasn't an
  established player the year before (prior-season MPG under 20). Injury returns (Tatum, Herro, Kyrie) are excluded
  by that second test.
- For those player-seasons the **final fifth counts at 1/10 weight** (games, minutes, possessions, box totals), so the
  projection follows his first-80% role.
- '26 validation: neutral overall (FP/G error 3.09 both ways). Helped McLaughlin, Juzang, AJ Johnson; hurt
  Mamukelashvili and Gillespie (their late runway was real). Drew Timme ('25: 0 → 15.9 in the final fifth) no longer
  gets a veteran projection at all.

### Minutes (MPG)
- Base MPG = base-season MPG, pulled toward bench minutes (16) when he has **under 60 games over the 3 input seasons**
  (share kept = games / 60), **downward only** (2026-10-06 fix: the pull used to lift deep-bench players toward 16;
  McCullar 7 → 19.6 projected, actual 7.4. Now a short history can lose minutes, never gain them; '26 bias +0.86 → +0.46).
  Stars are untouched.
- **Young minutes** (2026-10-07): under 24 in the projected season → **+1.5 MPG**. Under-24s beat their projection
  every season (FP/G +1.6 '24, +1.6 '25, +1.5 '26 holdout; minutes +1.1 / +2.2 / +0.6). After: +1.0 / +0.8 / +0.7;
  all-player within 3 FP/G 223 → 225 ('24), 241 → 246 ('25), 229 → 232 ('26).
- Plus a **career model** for next-season change, additive bands, trained only on **healthy** transitions
  (50+ GP in the prior, base and next season) that end before the target season:
  age band, years in the league, production tier (usage × MPG, fifths), prior-year minutes trend,
  **team quality** (point differential of the team he earned the minutes on), **moved** (on a different team in the
  target season, from the roster), and **bad team + low impact** (team ≤ −4/G and PIE below median).
- Evidence for the team-quality terms ('22→'26, 15+ MPG): minutes earned on a tank team (≤ −8/G) drop 2.5 the next
  year (4.4 if he moves); on a +4 team they rise 0.2. Bad team + low PIE: −3.3.

### Bad players: EPM flag ('27 only, temporary)
- Players with **'26 EPM ≤ −2.5** (hand-entered list) lose **2.5 FP/G**, applied as a minutes cut (every counting stat
  scales). Evidence: in '26 those players came in 2.6 FP/G under their projections; everyone else +0.5. Roughly flat
  across EPM bands, so it's a flag, not a slope. **Uncalibrated** (needs '25 EPM to size it properly).
- PIE (box-score impact) and on-court net rating did **not** identify these players (Capela, Cam Thomas looked good by
  PIE; Olynyk top on net rating) — tested and dropped.

### Pace, possessions
- Pace = the player's own on-court PACE ('24–'26 style 3-season window, minutes-weighted, recency ×3/season).
  Treated as a team stat in spirit; own on-court pace tested better than the team's (1.84 vs 2.14).
- Possessions from NBA `POSS`. (A box-score estimate matched it within ±1.5%.)

### Usage
- **Resplit** each target roster: every player's base-season usage and MPG, team scaled to 100% (Σ usage × MPG = 48),
  cap 40%, excess handed back proportionally.
- Base usage: re-split for **players who stayed**; **own usage for movers** (the re-split has no skill for them).
- Then an **age + usage level + moved** adjustment for everyone (2026-10-06, `usage2.py`): from 31 on players lose 1–2
  points beyond the roster arithmetic; high-usage players drift toward the middle, more after a move. Fit on '22→'25 for
  the '26 test (52 of 95 within 1.5 points vs 48), on all four season changes for '27. Anthony Davis '27: 30.1% → 25.9%.
- **Efficiency does not predict usage**: last season's TS% and eFG% vs zone-expected showed no pattern; left out.
- Usage scales FGA/75 and FTA/75 × (new/old)^0.5 and TOV/75 × (new/old), now for movers too.

### Shooting
- **Zone share**: 5 seasons, each weighted 5× the one before, no trend (trend didn't help).
- **Principle (commissioner, 2026-10-07): volume follows skill, for every shot.** Good at a shot → he takes it often;
  bad at it → he stops. Low volume + bad % is believed, never pulled up (Gobert: 0% from 3, 30.1% paint, 17.6% mid). A
  pull up must be earned by real volume. Low volume + good % is tempered (thin evidence). Real volume + good % is his own
  number — elite shooters are never pulled toward the league or a fixed number. Misses are fine if the method makes sense.
- **Players like him** (`rare_zone_by_ht.json`): zone FG% of players who rarely shoot from that zone (1–19 att in a
  season, '21–'25), by height band (≤6'2", 6'3–6'5, 6'6–6'8, 6'9–6'10, 6'11+). This, never the league, is the comparison:
  - small sample that looks good (under 100 attempts in the window, above that line) → tempered toward it, his own makes
    half weight at 20 attempts (all zones; rim uses the height + assisted line below);
  - small sample that looks bad → his own number;
  - zone never shot from in the window → that line minus 7.5 pts (same logic as FT).
- **Rim FG%**: his own 3-season rate. Height + assisted share of 2PM line = 65.7% at 6'6" / 60% assisted, +0.9 pt per
  inch, +0.69 pt per 10 pts assisted (explains 38% of the between-player gap at the rim); used only to temper a small
  sample that looks better than it.
- **Paint (non-RA) FG%**: his own 3-season rate (height + assisted explain only 5%: touch, not size). Below 38% pulled up
  toward 38% only as far as real volume earns it: none under 100 paint att a season, 65% of the gap at 250+.
- **Young players**: under 24 in the projected season → +1.5 pts at the rim, +2 in the paint (test '24+'25 and holdout '26
  both show under-24s beating their 3-season rate).
- **Mid-range FG%**: 5-season average (1 season carries over at 0.39, 3 at 0.52; 2–4 about equal), then a bracket:
  38–45% untouched; below 38% pulled up toward 38% only as far as volume earns it (none at ≤100 mid attempts over the 5
  seasons, 65% of the gap at 300+); above 45% pulled toward 45% only on thin evidence (halfway at ≤100, none at 300+).
- **FT%**: his own 3 seasons, no pull (3 ≥ 5 seasons: '26 120 vs 117 of 192 within 4 pts). No FT history in 3 seasons →
  FT% of rarely-fouled players (<30 FTA in a season, '21–'25) by height minus 7.5 pts: 69.9 / 68.3 / 65.8 / 62.5 / 59.4
  for ≤6'2", 6'3–6'5, 6'6–6'8, 6'9–6'10, 6'11+.
- **3P%**: on his combined 3s over 3 seasons — below 34% pulled up toward 34% only as far as volume earns it (none under
  50 att/season, 70% of the gap at 250+) × assisted share of his made 3s (half the pull at ≤60% assisted, full at 95%+);
  above 38% pulled toward 38% only on thin volume (halfway at 50 att/season, none at 250+); 34–38% untouched.
  Corner/above-break split kept. 3 seasons beat 2, 4, 5. Rejected: halfway-to-38% at any volume (Curry 40.9 → 39.4),
  league-average pull, credibility weighting toward the league (K ≈ 400), separate corner/above-break caps. 14 "proven"
  shooters for '27 (38%+ on 200+ 3PA each of 3 seasons) keep their number under the volume rule.
- **Assisted share** (LeagueDashPlayerStats Scoring, '21–'26, `player_scoring/`): share of 3PM assisted carries over at
  0.88. No effect on whether good shooters hold; bad shooters (<35%) on mostly-assisted 3s bounce back more (+3.9 test /
  +2.5 holdout at 95%+ assisted vs +1.8 / +0.9 under 85%) — applied in the 3P% rule above.
- '26 validation (100+ attempts in the zone, within 4 pts): rim 132/219 (last season 119), paint 83/145 (68), mid 29/60 (23).
- Low-volume corner specialists: only 5 cases (<150 3PA/season, 40%+ corner share, 38%+), two held, Wallace fell twice.
- Zones: restricted area, paint (non-RA), mid-range, corner 3 (L+R), other 3 (above the break + backcourt).

### Other counting stats (per 75)
| Stat | Recency weight per season | Notes |
|---|---|---|
| FGA, FTA | ×2 | usage-scaled for stayers |
| AST | ×5 | usage didn't help |
| STL | ×1 (pool 3 seasons) | noisy |
| BLK | ×5 | |
| TOV | ×2 | usage-scaled for stayers (full strength) |
| OREB | ×2 | individual — no team adjustment (tested) |
| DREB | ×2 | shared with teammates: −0.62 DREB% per +1 of teammates' minutes-weighted DREB% (prior-season team → target roster), **wired in 2026-10-06**; moved the right way 80 of 129 times in '26 |

### BLKD (own shot blocked) — wired in 2026-10-06 (FP/G now includes −0.5 × BLKD; '26 actuals use game-log BLKA)
- Source: BLKA from season game logs (PlayerGameLogs).
- League block rate per zone from a non-negative fit over '22–'25 player-seasons (200+ FGA):
  RA 10.4%, paint 6.2%, mid 0.3%, corner 3 3.7%, other 3 2.6% (5.4% of all FGA). Zones are collinear and blocks are
  only known as season totals, so the per-zone split isn't literal (mid looks too low); the totals predict well.
- Player factor = (his BLKA + 15) / (zone-expected BLKA + 15) over the input seasons (catch-and-shoot vets ~0.55,
  small drivers ~1.6).
- Projection = projected zone attempts × zone rate × factor. '26: error 0.087 BLKD/G, corr 0.91 (vs 0.112 / 0.87 for
  his own blocked-per-FGA). Typical 0.46/G; most 1.3/G (Zion, Jaylen Brown) → about −0.65 FP/G.

### Rookies
- Separate model, fit on the '22–'26 rookie classes (rookie-year per-game, 10+ GP):
  FP/G and MPG linear in **ln(draft pick)**, **height**, **weight**, and the **point differential (per game) of the
  team he joins, from the season before**. Undrafted = pick 61.
- Bad teams play rookies more: a −10 team vs a +10 team is +4.3 FP/G, +8.6 MPG.
- Misses at both ends (Flagg 16.9 → 24.4; Maluach 13.7 → 5.2). Picks 1–5 beat the projection by +6 on average
  ('26 class, n=5).
- Variants tested leave-one-class-out on '22–'25 (within 3 FP/G of 259): current 143; + top-3 bonus 141; + top-5 141;
  top-3 without height/weight 137; + 6'10"+ outside top 5 marked down 141; pick/team/top-3/tall 139. None kept: the
  '26 top-pick and tall-rookie misses aren't in the earlier classes (`rookie_cv.py`).

### Positions (one per player)
- Role-based, from '26 stats: **C** = top 20% by a size/rebounding score (height, REB% ×2, BLK/75 ×2);
  **G** = top 40% of the rest by a creation score (AST%, 3PA share, −height); **F** = everyone else.
- **Overrides** win: `nba-pipeline/data/raw/position_overrides.csv` (Giannis, Barnes, Mobley → F).
- Rookies / players without '26 stats: the roster's listed position (first letter).
- Box-score starting positions (most frequent start, '23–'26) were the old rule. Only 6 of the '26 top 60 move under the
  role rule (Bane, Amen Thompson, Brandon Miller, Daniels G → F; Avdija, Knueppel F → G), so balance barely changes.
  Starter − replacement ('26 weekly best game, top N per slot): 8 teams G 5.9 / **F 1.3** / C 5.3 / FLX 0.8 / TEAM 9.8;
  10 teams 5.3 / 1.9 / 5.9 / 1.0 / 11.8; 12 teams 5.6 / 2.1 / 5.5 / 0.8 / 11.4. (2026-10-07 correction: the earlier
  "F 3.5" came from a dual-eligibility version, not the final one-position rule.) F is flat because good players are
  mostly forwards. Balance goes through the league guides (commissioner's call).
- TEAM slot (weekly margin total) is worth more than any player slot at 8+ teams (9.8–11.8) — needs its own scaling.

### Uncertainty and dispersion
Moved to `DISPERSION.md` (running log of spread / PROJ MAX experiments and ideas).

## Validation ('23–'25 → '26, 393 players with 20+ GP)
FP/G error **3.09** (median ~2.6), within ±3: 57%, ±6: 88%, bias ≈ 0. Minutes error 4.05.
Biggest misses are all minutes/role changes (Rollins, Porter Jr., Alexander-Walker up; Mogbo, Sochan, Tyus Jones,
Cam Thomas down).

## Data on disk (nba-pipeline/data/raw/ unless noted)

| What | Seasons | Source |
|---|---|---|
| Traditional box scores | '21–'26 (prod: '22–'26) | boxscoretraditionalv3 per game (`nba-pipeline/data/box_scores/`, `raw/box_scores_traditional/`) |
| Season game logs incl. BLKA, PFD | '21–'26 | PlayerGameLogs (`game_logs/`) |
| Shot zones, league-wide | '21–'26 | LeagueDashPlayerShotLocations, By Zone (`shot_locations/`) |
| Player / team advanced (POSS, PACE, USG_PCT, PIE, REB%, AST%) | '21–'26 | LeagueDashPlayerStats / LeagueDashTeamStats, Advanced, Totals |
| Bios (age, height, weight, draft) | '20–'26 | LeagueDashPlayerBioStats (`bios/`) |
| Draft history (incl. 2026 class) | all | DraftHistory (`draft_history.json`) |
| Team rosters | 2025-26, 2026-27 | CommonTeamRoster (`rosters/`) |
| Schedules | '21–'26 | nba-pipeline (`schedules/`) |
| EPM ('26, partial, hand-entered) | '26 | screenshots → `epm_manual_2025_26.csv` (TODO replace) |
| Outputs | | `projections_2026_27.csv`, `rookie_projections_2026_27.csv`, `role_positions_single_2025_26.csv`, `validation_26_all.csv` |

Gotchas: advanced `MIN` is per game even with PerMode=Totals (season minutes = MIN × GP); `POSS` is a season total.

## Known failures / open items
- **Role changes** (minutes up or down with a new role) are the biggest error source. Roster competition (depth
  rank at his position on the target roster) is the next thing to try.
- **Usage for movers**: no skill; they regress to the middle (<17% usage gain +1.6, >21% lose −1.7). Not modeled.
- **Shot-mix development** (Adebayo, Turner to 3s faster than trend). Not modeled.
- **Team continuity weighting** didn't help shot share. Dropped.
- **Decline signal** (last year's minutes trend) is mostly injury noise; on healthy seasons only, a 4+ minute jump
  gives back ~2.6 the next year.
- **Young players beat projections (+1.6), old players miss (−1.1)** beyond the minutes aging — rate-side age
  adjustment proposed, not built.
- '27 board check: top-50-list players outside the projected top 80 are mostly old or moved (DeRozan, Vučević,
  Ayton, Holiday, Beal, Turner); Keyonte George (22) at 20.0 is probably low (young-player under-projection).
- **No projection** for ~60 undrafted rookies / two-ways and a few returners (Hezonja, Zhaire Smith…): they stay in
  the draft list with a **blank projection** (commissioner's call).
- **EPM flag** is uncalibrated and from a partial, hand-entered table.

## Planned (commissioner, 2026-10-07)
- **Clutch-time scoring for players** will be added back to the projection work (not for TEAM).
