# TEAM slot scoring — rework (running log, started 2026-10-07)

The TEAM slot is being rebuilt from scratch. **Point margin is out** (it's offense + defense, and it made TEAM
twice as valuable as a center: DRAFT_GUIDE.md). Goal, in the commissioner's words: TEAM is where **defensive
strength** shows, like D/ST in fantasy football. Players already carry individual defense (steals, blocks); TEAM
should reward what a defense does as a unit, and may dip into other box-score / tracking stats. Append every test,
result and decision here, dated.

## What fantasy football does (D/ST)
- **Points allowed, in tiers** (one common setup): 0 → +10, 1–6 → +7, 7–13 → +4, 14–20 → +1, 21–27 → 0, 28–34 → −1,
  35+ → −4. Rewards a shutdown game, punishes a blowout.
- **Takeaways**: interception +2, fumble recovery +2. **Sacks** +1. **Big plays**: defensive / return TD +6, safety
  +2, blocked kick +2.
- So: a base from points allowed, plus counting stats for disruptive plays, plus rare big-play bonuses. A good
  defense scores ~8–12 in a typical week, a bad one ~0–5, with occasional 20+ weeks.

## Candidates (brainstorm)
Points allowed (the base)
- **Points allowed tiers** (commissioner): held under 100 → +10, held under 110 → +5 (separate bonuses, so under
  100 earns both?), maybe a penalty for 130+.
- **Pace-adjusted**: defensive rating (points allowed per 100 possessions) — the same idea without rewarding slow
  games. Tiers on DEF_RATING instead of raw points.
Disruption (takeaways / sacks)
- Team **steals**, team **blocks** (player stats summed — players already score them; TEAM would count them again
  as a unit).
- **Opponent turnovers forced** (all of them: steals + shot clock violations, offensive fouls, travels, bad passes
  out of bounds). Shot clock violations themselves are only in play-by-play.
- **Charges drawn** (hustle), **deflections** (hustle), **loose balls recovered** (hustle), **contested shots**
  (hustle).
Holding the opponent down
- Opponent **points in the paint** (e.g. under 40 → bonus), opponent **fast-break points**, **second-chance
  points** (defensive rebounding), **points off turnovers**.
- Opponent **eFG%**, opponent **3P%** (mostly luck — test it), opponent **FT rate** (fouling).
- **No opponent scores 30** (commissioner) — holding every scorer under 30.
- **Defensive rebound %** (ending possessions).
Big plays (rare bonuses)
- Shutout-like nights: held under 90; opponent under 40% FG; a quarter held under 15; a 10+ steal or 10+ block game.

## How each candidate gets judged
On '22–'26 team-games, using only seasons before the one being checked when choosing anything:
1. **Separates defenses** — the spread between teams' season averages vs the game-to-game noise. If every team
   averages the same, drafting a TEAM means nothing.
2. **Tracks real defense** — correlation with season defensive rating.
3. **Defense, not just a good team** — correlation with offense (offensive rating) and with point margin should be
   low; the commissioner wants defensive strength to shine, not winning.
4. **Carries over** — a team's average one season vs the next (so TEAM can be drafted, like players).
5. **Week to week** — a weekly score's swing, compared with a player slot (±9–10 in a 3-game week).

## How big TEAM should be (DRAFT_GUIDE.md)
- Average starting TEAM about **+3 to +5 over the replacement TEAM**; the best NBA team about **+6 to +10** (like the
  best G or F, not Jokić). Current margin scoring: +9.8 to +11.8 — too big.
- 1 point a week ≈ +2% weekly win probability.

## Weekly score form (open)
- Players score their **best single game** of the week. TEAM options: best defensive game of the week (mirrors
  players; more games = more chances), the week's total (more games = more points — margin worked like this), or the
  weekly average (game count doesn't matter).

## Data
- Have: player box scores (team steals / blocks / DREB / opponent points by summing), schedules with scores, season
  team advanced stats.
- Pulling (2026-10-07): TeamGameLogs per team-game, '22–'26 — Base, Advanced (DEF_RATING, OFF_RATING, PACE), Misc
  (opponent paint / fast-break / second-chance / off-turnover points), Four Factors (opponent eFG%, TOV%, OREB%, FT
  rate), Opponent (the opponent's whole box score).
- Not yet: hustle stats (deflections, charges, contests, loose balls) — per game only (≈170 requests a season by
  date); play-by-play for shot clock violations and quarter scores.

## 2026-10-07: candidates tested ('22–'26 team-games, `team_eval.py`)

Season-level numbers on '22–'25; carry-over also shown into '26. Signs flipped so higher = better defense. *Real spread* = SD of team season averages after removing game noise; *game SD* = one game's swing.

| Candidate | Real spread between teams | One game's swing | Tracks defense (−DEF_RATING) | Tracks offense | Tracks point margin | Carries over ('22–'25 / into '26) |
|---|---|---|---|---|---|---|
| Opponent points (fewer) | 3.70 | 12.00 | +0.89 | +0.14 | +0.62 | 0.58 / 0.63 |
| Held under 100 (+10) | 0.60 | 3.37 | +0.80 | +0.05 | +0.51 | 0.54 / 0.54 |
| Held under 110 (+5) | 0.59 | 2.35 | +0.87 | +0.14 | +0.61 | 0.54 / 0.63 |
| Both tiers (<100: +15, <110: +5) | 1.18 | 4.95 | +0.86 | +0.09 | +0.57 | 0.57 / 0.61 |
| Defensive rating (pts/100 poss, lower) | 2.49 | 11.30 | +1.00 | +0.21 | +0.74 | 0.52 / 0.54 |
| Team steals | 0.66 | 2.83 | +0.32 | +0.04 | +0.22 | 0.58 / 0.49 |
| Team blocks | 0.64 | 2.40 | +0.09 | +0.15 | +0.16 | 0.55 / 0.46 |
| Steals + blocks | 1.02 | 3.71 | +0.28 | +0.12 | +0.25 | 0.53 / 0.47 |
| Opponent turnovers forced | 1.06 | 3.74 | +0.27 | -0.04 | +0.13 | 0.58 / 0.61 |
| Opponent turnover % forced | 0.01 | 0.04 | +0.34 | -0.05 | +0.17 | 0.58 / 0.59 |
| Defensive rebounds | 1.22 | 5.25 | +0.48 | +0.21 | +0.43 | 0.50 / 0.39 |
| Defensive rebound % | 0.01 | 0.07 | +0.41 | +0.11 | +0.32 | 0.46 / 0.23 |
| Opponent paint points (fewer) | 2.75 | 9.88 | +0.76 | +0.08 | +0.51 | 0.50 / 0.61 |
| Opp paint under 40 (bonus) | 0.07 | 0.36 | +0.67 | +0.08 | +0.46 | 0.48 / 0.55 |
| Opponent fast-break points (fewer) | 1.32 | 6.24 | +0.57 | +0.03 | +0.36 | 0.53 / 0.56 |
| Opponent second-chance points (fewer) | 0.84 | 5.67 | +0.49 | +0.11 | +0.37 | 0.34 / 0.45 |
| Opponent points off turnovers (fewer) | 1.44 | 6.14 | +0.55 | +0.47 | +0.65 | 0.50 / 0.64 |
| Opponent eFG% (lower) | 0.01 | 0.07 | +0.87 | +0.23 | +0.67 | 0.44 / 0.46 |
| Opponent 3P% (lower) | 0.01 | 0.08 | +0.63 | +0.07 | +0.42 | 0.14 / -0.18 |
| Opponent 3PA (fewer) | 1.99 | 6.50 | +0.11 | +0.04 | +0.09 | 0.40 / 0.65 |
| Opponent FT rate (lower) | 0.02 | 0.08 | +0.10 | +0.18 | +0.19 | 0.46 / 0.60 |
| No opponent scores 30 (bonus) | 0.06 | 0.42 | -0.26 | +0.34 | +0.08 | 0.47 / 0.51 |
| Point margin (reference — out) | 4.91 | 14.50 | +0.74 | +0.82 | +1.00 | 0.56 / 0.52 |

**Read**
- **Points allowed is the defense signal**: opponent points (0.89 with defensive rating, 0.14 with offense,
  carries over 0.58), the commissioner's under-100 / under-110 bonuses (0.80 / 0.87), opponent paint points (0.76).
- **Turnovers forced is a separate style trait**: barely defense (0.3), no offense, but repeats (0.58) — disruptive
  defenses.
- **Out**: opponent 3P% (luck: carries over 0.14, then −0.18); opponent 3PA and FT rate (not defense); opponent
  points off turnovers (it's offense, 0.47); second-chance points (doesn't repeat); "no opponent scores 30" (−0.26
  with defense — it's about the opponent's stars); team steals / blocks (weakly defensive, and players score them).
- Raw opponent points rewards slow teams (pace); defensive rating is pace-adjusted but separates teams less.

## 2026-10-07: structures × weekly form (`team_calib.py`, fantasy weeks '23–'26)

Draft value: each NBA team projected from its prior season (keeps 60% of its gap from average, like team margin does), then the average starting TEAM and the best TEAM minus the best TEAM left over, at 4 / 8 / 12 teams. *Ratio* = average starter's gap at 8 teams ÷ weekly swing (players at 8 teams, G/F/C: C 0.66, G 0.30, F 0.18).

| Structure | Weekly form | Mean | Weekly swing (SD) | Avg starter over repl. 4 / 8 / 12 | Best over repl. 4 / 8 / 12 | Ratio |
|---|---|---|---|---|---|---|
| A: tiers only | best game | 6.2 | 3.5 | +0.5 / +0.6 / +0.6 | +0.9 / +1.3 / +1.6 | 0.16 |
| A: tiers only | week avg ×3 | 6.7 | 7.5 | +1.1 / +1.6 / +1.7 | +2.7 / +3.9 / +4.6 | 0.21 |
| A: tiers only | week total | 7.9 | 9.1 | +1.4 / +2.2 / +2.1 | +3.4 / +5.1 / +5.8 | 0.24 |
| B: tiers + 0.5 / turnover forced | best game | 14.0 | 4.0 | +0.6 / +0.6 / +0.8 | +1.3 / +1.7 / +2.1 | 0.16 |
| B: tiers + 0.5 / turnover forced | week avg ×3 | 28.0 | 8.6 | +1.7 / +2.1 / +2.0 | +3.7 / +5.2 / +6.0 | 0.24 |
| B: tiers + 0.5 / turnover forced | week total | 33.0 | 14.1 | +2.3 / +2.4 / +2.7 | +4.6 / +6.2 / +7.4 | 0.17 |
| C: B + 3 if opp paint < 40 | best game | 14.7 | 4.4 | +0.6 / +0.7 / +0.9 | +1.3 / +1.8 / +2.3 | 0.16 |
| C: B + 3 if opp paint < 40 | week avg ×3 | 29.3 | 9.2 | +1.9 / +2.4 / +2.3 | +4.2 / +6.0 / +6.8 | 0.26 |
| C: B + 3 if opp paint < 40 | week total | 34.6 | 14.9 | +2.5 / +2.7 / +2.7 | +5.2 / +6.9 / +7.9 | 0.18 |
| D: commissioner's (<100 +10, <110 +5) | best game | 6.8 | 5.7 | +0.6 / +0.9 / +1.1 | +1.2 / +1.9 / +2.5 | 0.15 |
| D: commissioner's (<100 +10, <110 +5) | week avg ×3 | 8.6 | 7.9 | +1.8 / +1.7 / +2.1 | +3.5 / +4.4 / +5.5 | 0.22 |
| D: commissioner's (<100 +10, <110 +5) | week total | 10.2 | 9.7 | +2.1 / +2.2 / +2.3 | +3.8 / +5.1 / +6.1 | 0.23 |
| E: (125 − opp points) / 2 | best game | 10.5 | 4.4 | +0.6 / +0.5 / +0.8 | +1.2 / +1.5 / +1.9 | 0.11 |
| E: (125 − opp points) / 2 | week avg ×3 | 15.7 | 10.2 | +1.5 / +2.2 / +2.2 | +3.3 / +5.0 / +5.8 | 0.22 |
| E: (125 − opp points) / 2 | week total | 18.5 | 13.3 | +2.0 / +2.9 / +2.7 | +4.3 / +6.4 / +7.3 | 0.22 |
| F: (125 − def rating) / 2 | best game | 10.5 | 4.1 | +0.4 / +0.5 / +0.6 | +0.9 / +1.3 / +1.6 | 0.13 |
| F: (125 − def rating) / 2 | week avg ×3 | 16.2 | 9.4 | +1.5 / +1.5 / +2.0 | +3.1 / +4.1 / +5.2 | 0.16 |
| F: (125 − def rating) / 2 | week total | 19.0 | 11.9 | +1.7 / +1.8 / +2.5 | +3.6 / +4.7 / +6.2 | 0.15 |
| G: E + 0.25 / turnover forced | best game | 14.3 | 4.6 | +0.6 / +0.6 / +0.9 | +1.2 / +1.6 / +2.2 | 0.13 |
| G: E + 0.25 / turnover forced | week avg ×3 | 26.3 | 10.6 | +1.6 / +2.6 / +2.5 | +3.7 / +5.9 / +6.7 | 0.24 |
| G: E + 0.25 / turnover forced | week total | 31.1 | 15.6 | +2.5 / +2.7 / +3.1 | +5.1 / +6.8 / +8.3 | 0.18 |

Tiers (A): per game 95− → +12, 95–104 → +8, 105–114 → +4, 115–124 → 0, 125+ → −4.

**What it says**
- **Team defense is noisy game to game.** Every structure and form lands at a ratio of 0.15–0.25 — between a
  forward slot and a guard slot. Scoring choices barely move it; it's a property of team defense. So TEAM can be
  sized to the target importance by **scale**, and its weekly swing comes along (a bit bigger than a player slot's).
- **Best defensive game of the week washes TEAM out** (average starter +0.5 to +1): every team has a good night some
  time in a week. Out.
- **Weekly total keeps team differences** (and games played that week count, like a player's extra chances);
  weekly average ×3 does too, without the game-count effect.
- **Linear points allowed** — (125 − opponent points) / 2 per game, weekly total — has the best ratio and is the
  simplest: +2.9 average starter / +6.4 best at 8 teams, swing ±13. Already close to the DRAFT_GUIDE target
  (+3 to +5 / +6 to +10).
- Turnovers forced and the paint bonus add more noise than signal. The commissioner's under-100 / under-110 bonuses
  work about as well as football-style tiers (both slightly below linear).

**Open (commissioner)**
1. Weekly total vs weekly average (does a 4-game week deserve more TEAM points?).
2. Raw points allowed (simple, rewards slow teams) vs per 100 possessions (pure defense, separates less).
3. Add a style stat anyway (turnovers forced) for flavor, at a small weight?
4. Hustle stats (deflections, charges, contests) not tested yet — need per-game pulls.

