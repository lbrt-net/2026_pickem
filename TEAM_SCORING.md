# TEAM scoring

Every fantasy roster has one **TEAM** spot: you draft a whole NBA team, like a defense in fantasy football. This file is how a TEAM scores, why, and what it looks like on last season (2025-26). Seasons are named by the year they end ('26 = 2025-26). Running log at the bottom.

## The idea

Players already score for what they do: points, rebounds, assists, steals, blocks. **TEAM is where a team's defense shows up.** The old TEAM scoring was point margin (how much a team won by). That's out: it rewards good offense as much as defense, and it made TEAM worth about twice a top center.

It also has to be **easy to root for** while you watch, even when the math is complicated: "please hold them under 105", "please force another turnover", "please get another shot clock violation".

## How a TEAM scores (draft 2)

Built to be **exciting and swingy**: a few big lines to hold the opponent under, a play-by-play thing to cheer for, and bonuses that even great defenses don't get every week. Per game:

- **Hold them under 100: +15. Under 95: +10 more. Under 90: +10 more.** A great night is worth +35; most nights, nothing here.
- **Every violation forced: +5.** Shot clock, 8-second, 5-second: the defense made the offense run out of time. About 0.7 a game; two in a night is a highlight.
- **+10 bonuses**, each one rare:
  - **Force 20+ turnovers**
  - **Hold them to 6 or fewer fast-break points**
  - **Hold them to 32 or fewer points in the paint**
  - **Win the defensive glass by 30+** (your defensive rebounds minus their offensive rebounds)

Weekly score = **the team's best game of the week**, the same as players. How big TEAM is next to the player spots is decided later.

What it looks like on 2025-26: a TEAM's best game of the week averages **19**, but it swings a lot (give or take about 14): only 3% of weeks are a zero, and 23% of weeks are a big one (30+). It still follows real defense closely: the order of teams matches defensive rating at 0.80 (out of 1).

**Draft 1** (earlier, too smooth): +5 for every line under 120 / 115 / 110 / 105 / 100 / 95 / 90, +1 per turnover forced, +2 per violation forced. Weekly score 35 ± 11: it paid out something every game, so there was little to sweat.

## Why these

- **Points allowed is what good defense looks like**: across '22–'25 the teams that allow the fewest points are the teams with the best defensive ratings (0.89 out of 1). The score is on the screen, so it's easy to root for.
- **Few, harsh lines** because it lines up with defense so well: holding a team under 100 happens in about 1 game in 7, under 95 in 1 in 14, under 90 in 1 in 33. The best defenses do it about twice as often as the worst.
- **Violations forced** are the most purely defensive turnovers: nobody on offense made a mistake on their own.
- **The four bonuses** are the commissioner's: things a defense does that you can see, rare enough to be a big moment.
- **Not in**: shooting percentages (too abstract next to a count), steals and blocks (players already score them), and plain rebounds (partly about the offense) — the rebounding bonus is a margin instead.

How often each line and bonus happens ('22–'25), the chance a team gets it at least once in a 3-game week, and how much more often the best defenses get it ('26's best five vs worst five):

| Line or bonus | Games it happens in | Weeks with at least one | Best 5 defenses, per game | Worst 5, per game | Goes with good defense (0–1) |
|---|---|---|---|---|---|
| Hold them under 100 | 14% | 36% | 18% | 5% | 0.80 |
| Under 95 | 7% | 19% | 9% | 1% | 0.75 |
| Under 90 | 3% | 8% | 3% | 0% | 0.68 |
| Force 20+ turnovers | 8% | 22% | 14% | 10% | 0.31 |
| 6 or fewer fast-break points | 11% | 30% | 12% | 4% | 0.43 |
| 32 or fewer paint points | 5% | 14% | 13% | 4% | 0.52 |
| Defensive glass by 30+ | 16% | 41% | 17% | 9% | 0.51 |

## What it looks like on 2025-26

Every team: average weekly score (best game of the week), how much it swings, how often a week was a big one (30+), its single best game, how often it held opponents under 100, violations forced per game, and how often it got each bonus. Defensive rating (points allowed per 100 possessions, lower is better) for comparison.

| # | Team | Weekly score | Swing (±) | Big weeks (30+) | Best game | Under 100 | Violations forced | 20+ TOV | FB ≤ 6 | Paint ≤ 32 | Glass 30+ | Defensive rating |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | OKC | **32.1** | 13 | 67% | 60 | 21% | 0.84 | 27% | 19% | 16% | 16% | 106.3 |
| 2 | DET | **30.7** | 19 | 48% | 70 | 16% | 0.88 | 28% | 8% | 20% | 8% | 108.7 |
| 3 | BOS | **27.9** | 16 | 48% | 60 | 24% | 0.61 | 4% | 12% | 19% | 15% | 111.5 |
| 4 | LAC | **24.8** | 16 | 43% | 50 | 16% | 0.65 | 15% | 9% | 4% | 12% | 115.1 |
| 5 | NYK | **24.5** | 17 | 43% | 65 | 20% | 0.47 | 8% | 13% | 12% | 15% | 112.2 |
| 6 | CHA | **22.4** | 15 | 38% | 50 | 23% | 0.44 | 8% | 7% | 4% | 15% | 113.8 |
| 7 | TOR | **22.4** | 12 | 29% | 50 | 15% | 0.96 | 14% | 12% | 5% | 16% | 112.1 |
| 8 | PHX | **21.9** | 10 | 33% | 40 | 16% | 0.73 | 23% | 11% | 3% | 4% | 112.9 |
| 9 | SAS | **21.7** | 13 | 33% | 45 | 14% | 0.64 | 4% | 9% | 11% | 32% | 110.1 |
| 10 | ATL | **21.2** | 13 | 24% | 55 | 11% | 0.93 | 19% | 15% | 3% | 15% | 113.1 |
| 11 | CLE | **21.2** | 13 | 29% | 60 | 11% | 0.89 | 12% | 9% | 5% | 7% | 113.9 |
| 12 | GSW | **21.0** | 16 | 14% | 60 | 15% | 0.61 | 20% | 4% | 5% | 3% | 113.7 |
| 13 | HOU | **19.0** | 13 | 24% | 55 | 18% | 0.68 | 5% | 5% | 3% | 14% | 112.2 |
| 14 | POR | **18.8** | 17 | 19% | 75 | 8% | 0.70 | 13% | 5% | 5% | 8% | 113.6 |
| 15 | BKN | **18.8** | 16 | 14% | 60 | 7% | 0.99 | 7% | 4% | 1% | 8% | 117.9 |
| 16 | MIL | **18.6** | 10 | 19% | 35 | 8% | 0.73 | 4% | 4% | 11% | 8% | 118.3 |
| 17 | ORL | **18.3** | 12 | 24% | 50 | 9% | 0.70 | 15% | 7% | 3% | 11% | 114.2 |
| 18 | MIN | **17.9** | 14 | 24% | 50 | 8% | 0.77 | 9% | 8% | 1% | 9% | 112.2 |
| 19 | MIA | **16.7** | 10 | 14% | 35 | 8% | 0.76 | 20% | 8% | 0% | 13% | 112.8 |
| 20 | DEN | **16.7** | 17 | 19% | 70 | 8% | 0.57 | 1% | 3% | 4% | 16% | 116.0 |
| 21 | NOP | **16.2** | 10 | 14% | 40 | 5% | 0.83 | 16% | 4% | 4% | 9% | 117.5 |
| 22 | LAL | **16.0** | 12 | 14% | 55 | 8% | 0.68 | 11% | 4% | 3% | 9% | 115.7 |
| 23 | PHI | **14.3** | 11 | 14% | 45 | 5% | 0.65 | 15% | 3% | 7% | 3% | 114.8 |
| 24 | SAC | **14.0** | 8 | 5% | 30 | 3% | 0.70 | 9% | 9% | 1% | 8% | 120.3 |
| 25 | WAS | **13.8** | 10 | 10% | 45 | 4% | 0.68 | 9% | 4% | 4% | 5% | 120.7 |
| 26 | IND | **13.6** | 9 | 5% | 35 | 5% | 0.69 | 0% | 8% | 0% | 11% | 118.2 |
| 27 | DAL | **13.1** | 11 | 14% | 40 | 4% | 0.72 | 5% | 4% | 0% | 7% | 115.0 |
| 28 | UTA | **13.1** | 9 | 10% | 40 | 3% | 0.59 | 9% | 3% | 3% | 12% | 120.8 |
| 29 | MEM | **12.6** | 9 | 10% | 30 | 7% | 0.61 | 18% | 1% | 1% | 9% | 117.1 |
| 30 | CHI | **12.1** | 9 | 5% | 35 | 3% | 0.57 | 5% | 1% | 3% | 19% | 117.2 |

Biggest single games of '26:
- **POR held PHX to 77** (Feb 22): **75** — 4 violations forced, 23 turnovers forced, PHX had 6 fast-break and 34 paint points, glass +21
- **DET held CHA to 86** (Dec 20): **70** — 1 violation forced, 24 turnovers forced, CHA had 24 fast-break and 28 paint points, glass +32
- **DEN held BOS to 84** (Feb 25): **70** — 1 violation forced, 14 turnovers forced, BOS had 6 fast-break and 28 paint points, glass +31
- **DET held BKN to 77** (Feb 01): **65** — 2 violations forced, 25 turnovers forced, BKN had 9 fast-break and 30 paint points, glass +28
- **NYK held BKN to 66** (Jan 21): **65** — 0 violations forced, 14 turnovers forced, BKN had 4 fast-break and 20 paint points, glass +44

## Draft 3 — one steady category + the swingy part (2026-10-07, to lock)

The commissioner's correction to draft 2: not everything should be swingy. One **bread-and-butter** category that pays every game, then the swingy lines and rare bonuses on top.

**Swingy part (same in both versions)**, per game: hold them under 100 +15, under 95 +10 more, under 90 +10 more; +5 per violation forced; +10 each for 20+ turnovers forced, 6 or fewer fast-break points allowed, 32 or fewer paint points allowed, defensive glass +30.

**Bread and butter, two versions:**
- **A: +1 per turnover forced.** About 14 a game, never zero; you cheer every one.
- **B: +1 for every point the opponent finishes under 125.** Hold them to 110 → +15; to 100 → +25 (plus the line).

Weekly score = best game of the week. Checked on every week of '23–'26:

| | Weekly score | Steady part's share of it | Follows defense (0–1) | Repeats next season (0–1) | '26 best | '26 worst |
|---|---|---|---|---|---|---|
| A | 35.6 ± 15 | 45% | 0.78 | 0.55 | OKC 51.3, DET 49.7, LAC 41.2 | DAL 28.5, IND 28.3, CHI 26.9 |
| B | 38.7 ± 23 | 52% | 0.84 | 0.58 | OKC 59.0, DET 54.8, BOS 53.8 | WAS 24.9, CHI 24.1, UTA 23.9 |

- **A** keeps points allowed as pure excitement (the lines) and makes the steady part a play-by-play cheer.
- **B** leans harder on points allowed: follows defense a bit better and spreads teams further apart, but its steady part is a smooth points scale again.
- Neither has zero weeks.

### Hustle stats and violations, tested as candidates ('23–'26)

Per game, last season's best team, whether teams' averages follow good defense, and whether they repeat:

| Stat | Per game | '26 range (worst–best team) | Best '26 | Follows defense | Repeats |
|---|---|---|---|---|---|
| Turnovers forced | 14.1 | 11.8–16.9 | DET | 0.34 | 0.61 |
| Deflections | 15.5 | 13.8–20.8 | OKC | 0.38 | 0.51 |
| Contested shots | 42.1 | 35.1–46.3 | OKC | 0.18 | 0.61 |
| Charges drawn | 0.4 | 0.1–0.7 | LAL | 0.07 | 0.44 |
| Loose balls recovered (def) | 2.4 | 1.8–2.8 | DET | 0.35 | 0.42 |
| Box outs (def) | 4.8 | 3.1–5.7 | MIA | 0.43 | 0.52 |
| Violations forced | 0.7 | 0.5–1.0 | TOR | 0.04 | 0.35 |
| Offensive fouls forced | 1.6 | 0.6–2.8 | POR | 0.21 | 0.56 |
| Steals | 7.8 | 6.8–10.4 | DET | 0.38 | 0.56 |
| Blocks | 4.9 | 3.8–6.4 | DET | 0.27 | 0.49 |
| Points allowed | 114.6 | 107.2–126.0 | BOS | 0.87 | 0.58 |

- **Violations forced are mostly luck**: they barely follow defense (0.04) and only partly repeat (0.35). Fun to cheer for, so they stay as a +5 swing, but they shouldn't carry the scoring.
- Deflections and defensive box outs follow defense about as well as turnovers forced, but nobody sees them on a box score. Charges drawn are rare and don't follow defense. Contested shots barely follow defense.
- Check on the matching: a team's violations forced = its opponent's own violations that day. On '25, forced shot clock violations from the violations table match play-by-play in all 2,460 team-games (1,828).

### 2026-27 TEAM projections

Each NBA team's projected weekly score (its best game of the week) under its real 2026-27 schedule. How it's made: start from its '26 games; pull its average back toward the league by the part that doesn't carry over (about 4 in 10 of the gap, measured '23→'24 and '24→'25); simulate the best game for each week's real game count (NBA Cup games filled in, the same as players).

| # | Team | A: projected weekly | B: projected weekly | '26 actual weekly (A) |
|---|---|---|---|---|
| 1 | DET | **46.3** | 51.7 | 49.7 |
| 2 | OKC | **45.0** | 50.6 | 51.3 |
| 3 | NYK | **41.0** | 49.2 | 39.5 |
| 4 | BOS | **40.1** | 50.3 | 40.9 |
| 5 | TOR | **38.9** | 42.4 | 40.8 |
| 6 | LAC | **38.9** | 43.7 | 41.2 |
| 7 | ATL | **38.3** | 39.7 | 39.2 |
| 8 | GSW | **37.8** | 40.6 | 39.0 |
| 9 | PHX | **37.5** | 39.9 | 39.8 |
| 10 | CHA | **37.4** | 45.0 | 36.3 |
| 11 | POR | **37.2** | 37.7 | 35.9 |
| 12 | SAS | **37.0** | 42.5 | 36.8 |
| 13 | CLE | **36.3** | 38.6 | 38.2 |
| 14 | ORL | **35.7** | 37.0 | 35.3 |
| 15 | MIA | **35.5** | 34.4 | 34.9 |
| 16 | MIN | **35.5** | 37.7 | 33.2 |
| 17 | BKN | **34.9** | 36.4 | 34.3 |
| 18 | HOU | **34.2** | 39.9 | 34.7 |
| 19 | NOP | **33.7** | 31.9 | 32.8 |
| 20 | LAL | **33.3** | 34.8 | 32.8 |
| 21 | PHI | **33.0** | 31.9 | 32.0 |
| 22 | MIL | **33.0** | 34.6 | 33.0 |
| 23 | DEN | **32.9** | 36.3 | 31.3 |
| 24 | MEM | **32.6** | 31.4 | 31.5 |
| 25 | SAC | **31.1** | 27.7 | 29.7 |
| 26 | UTA | **30.8** | 27.2 | 29.4 |
| 27 | WAS | **30.6** | 27.8 | 28.9 |
| 28 | DAL | **30.6** | 29.1 | 28.5 |
| 29 | CHI | **29.3** | 27.2 | 26.9 |
| 30 | IND | **29.3** | 29.1 | 28.3 |

**How valuable a TEAM is**: the average starting TEAM and the best TEAM, over the best TEAM left undrafted, next to the player spots (1 G / 1 F / 1 C, DRAFT_GUIDE.md):

| Teams | A: avg starter / best | B: avg starter / best | G avg starter | F | C | Best C (Jokić) |
|---|---|---|---|---|---|---|
| 4 | +4.1 / +7.3 | +5.5 / +6.7 | +3.6 | +2.3 | +6.3 | +13.4 |
| 8 | +3.3 / +8.8 | +6.3 / +11.0 | +2.8 | +1.7 | +6.3 | +17.6 |
| 10 | +2.9 / +9.1 | +5.7 / +11.8 | +4.4 | +1.7 | +7.6 | +20.4 |
| 12 | +3.3 / +9.9 | +6.0 / +13.1 | +4.6 | +1.7 | +7.2 | +21.2 |

- **A makes TEAM about as valuable as a guard spot; B about as valuable as a center spot** (the most valuable player spot). Neither needs rescaling to land in that range, and a TEAM's weekly score (about 37–50 at the top) is about a star player's best game — TEAM matters in a matchup either way.
- **To lock**: A or B. Scripts: `team_full.py`, `team_draft3.py`, `team_proj.py` in scripts/projection_study/.


## What else we looked at

Each stat: last season's best team, league average and worst team (per game), whether it goes with good defense (how closely teams' averages line up with defensive rating, 0 to 1), and whether teams repeat it the next season (0 to 1).

| Stat | Best team '26 | League | Worst team '26 | Goes with good defense | Repeats next season | Verdict |
|---|---|---|---|---|---|---|
| Opponent points | BOS 107.2 | 115.6 | UTA 126.0 | 0.87 | 0.58 | in (the base) |
| Held under 100 | CHA 23% | 11% | SAC 2% | 0.76 | 0.54 | in (a line) |
| Held under 105 | OKC 43% | 20% | WAS 4% | 0.83 | — | in (a line) |
| Held under 110 | BOS 56% | 32% | WAS 7% | 0.84 | 0.54 | in (a line) |
| Steals | DET 10.4 | 8.4 | DEN 6.8 | 0.36 | 0.58 | out — players already score steals |
| Blocks | DET 6.4 | 4.8 | UTA 3.8 | 0.42 | 0.55 | out — players already score blocks |
| Turnovers forced | DET 16.9 | 14.5 | DEN 11.8 | 0.37 | 0.58 | in |
| Opponent paint points | BOS 40.1 | 49.9 | DAL 56.2 | 0.71 | 0.50 | maybe |
| Opponent fast-break points | OKC 12.0 | 15.2 | UTA 18.2 | 0.75 | 0.53 | maybe |
| Opponent second-chance points | NYK 13.1 | 15.0 | MEM 18.1 | 0.54 | 0.34 | out — doesn't repeat |
| Opponent shooting (eFG%) | DET 52% | 55% | UTA 58% | 0.93 | 0.44 | covered by points allowed |
| Opponent 3P% | DET 34% | 36% | BKN 38% | 0.45 | 0.14 | out — mostly luck (doesn't repeat) |
| Defensive rebound % | SAS 73% | 70% | MEM 66% | 0.43 | 0.46 | out — weak |

Also tested and out: "no opponent scores 30" (it's about the other team's star, not your defense), opponent points off turnovers (it's really offense), opponent 3-point attempts and free-throw rate (not defense).

## Coming next

- **Violations forced** for '25 → '23: being pulled now ('26 done), one request per game day.
- **Hustle stats** (deflections, charges drawn, contested shots, loose balls, box outs): same pull. Then test them the same way and decide what's in.
- **Weighting**: how big TEAM is next to the player spots (DRAFT_GUIDE.md has what a player spot is worth).

## Log

- 2026-10-07: rework started. Point margin out. Defense like fantasy football's D/ST.
- 2026-10-07 (commissioner): weekly score = best game of the week; raw points allowed (simple), not per 100 possessions; TEAM must feel impactful and be easy to root for — lines to hold the opponent under, turnovers and violations to cheer for one at a time; weighting later; pull hustle stats.
- 2026-10-07: shot clock violations aren't in NBA.com's box scores; they're on the team Violations stats page (MeasureType=Violations, same endpoint as the team stats pages), pulled day by day and matched to that day's opponent. In '25 play-by-play, 1,982 shot clock violations, about 0.8 per team per game.
- 2026-10-07: draft 1 written: +5 per line every 5 points, +1 turnover, +2 violation. Orders teams like defense (0.88) but too smooth.
- 2026-10-07 (commissioner): draft 1 is lame — a smooth scale is easy to tune out. TEAM should be exciting and swingy: fewer, harsher lines; high cutoffs that don't happen every week even for good defenses; no shooting % (abstract); rebounding only as a margin; fast-break, paint and turnovers as one bonus each. (Players: clutch-time scoring to be added back to the projection work.)
- 2026-10-07: draft 2 (above). Weekly 19 ± 14, follows defense 0.80. Cutoffs measured in `team_cutoffs.py`.
- Scripts: `scripts/projection_study/team_draft1.py` (draft 1 on '26), `team_eval.py` / `team_show.py` (stats tested), `scripts/pull_team_daily.py` (violations + hustle by day), `scripts/pull_league_seasons.py` (team game logs).
- 2026-10-07 (commissioner, for the next draft — nothing redone yet): **not every category should be swingy.** One **bread-and-butter** category that pays steadily most games, then the rest as the swingy lines and rare bonuses.
- 2026-10-07: hustle + violations pulled for '23–'26 (`scripts/pull_team_daily.py`). Draft 3 written with two bread-and-butter versions (A turnovers forced, B points under 125) and 2026-27 TEAM projections. Violations forced found to be mostly luck.
