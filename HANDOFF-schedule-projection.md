# Handoff: projected totals in the My Team Schedule view

For: a fresh thread picking this up. Read CLAUDE.md, ROADMAP.md, DESIGN.md first.

## What to build

In **My Team → Schedule view** (`frontend/src/pages/fantasy/TeamManagement.jsx`):

1. Two columns per row after the day columns: **Proj** (projected best game for the week) and
   **Best** (the week score so far).
2. A **starters total row** at the bottom: projected week total and actual week total.
3. **Projected score by week:** the same projected team total for upcoming weeks (and the
   opponent's), so a manager can see future weeks at a glance.

## Scoring definitions (don't get these wrong)

- A **player's week score = his single best game** of the week — the **max**, not a sum or average.
- An **NBA team slot's week = its point margins added up** over its games that week.
- A **fantasy team's week = sum over starters** (G / F / C / TM / FLX). **Bench doesn't score.**
- All-Star break: a fused 2-week period (more days in the week). Playoff weeks have their own rounds.

## What already exists

Backend — `backend/fantasy_2026_27/lineup.py`:
- `expected_best(scores, n, floor)` — projected best of n games: expected maximum of n draws from the
  player's own game scores (order statistics), never below his best already this week.
- `week_view(cur, scenario, team_id, week_no)` → per entry: `games` (date, opp, home, played,
  points), `week_score` (best so far / margin total), `projected`, `games_left`, `box_line`,
  `season_ppg`, `locked`; plus `starters_score`, `starters_projected`, `opponent`, `lock`, `weeks`.
  Projection input = this season's game scores up to the league's as-of date, plus last season's
  when he has fewer than 10. NBA team projection = (margin so far) + average margin × games left.
- Route: `GET /fantasy/2026_27/team/{team_id}/week?scenario=&week=` (`routes.py`).
- Supporting: `engine.py` (`league`, `as_of`, `weeks_for_league`, `pairings`, `results`),
  `logic.py` (`player_points`, `team_game_points`), `weeks.py` (`season_weeks`, `week_for`,
  `league_settings`, `slot_list`).
- Data: `nba_games` (schedule, scores, `tipoff_utc`), `nba_player_games` (box scores),
  `fantasy_rosters` (current lineup), `fantasy_lineups` (saved weekly lineups — which spot each
  player was in for a week that has started; use it so bench/starter is right per week).

Frontend: `TeamManagement.jsx` already fetches the week view (and the opponent's same week for the
scorebug); the Points view shows `projected`, `week_score`, `box_line`. The Schedule view has the
day grid but no Proj/Best columns or totals row yet.

## What's missing (the list)

1. **Frontend, Schedule view:** add Proj + Best columns and the starters total row (data is already
   in the week view). Totals exclude Bench.
2. **Backend, projections by week:** a cheap way to get projected team totals for several weeks.
   Calling `week_view` once per week is heavy (several queries each). Options: a new endpoint, e.g.
   `GET /team/{team_id}/projections?scenario=&weeks=N`, that loads game scores once and returns
   `[{week, starters_projected, opponent, opponent_projected}]`.
3. **Caching:** season score lists per (scenario, as-of date) — the same history feeds every
   player's projection; recomputing per request is wasteful.
4. **Lineup per week:** future weeks use the current roster (`fantasy_rosters`); started weeks use
   `fantasy_lineups`. Make the projection follow the same rule.
5. **Edge cases:** players with no history (rookies) → no projection (show "—"); DNPs count as no
   game; postponed games (`nba_games.missing_since`) excluded; players traded mid-season (schedule
   uses `fantasy_players.nba_team`; tabled); injuries (no data yet; tabled).
6. **Replay / no peeking:** in the 2025-26 test league, only use this season's games up to the
   league's as-of date (`engine.as_of`) — never later games.

## Testing

No local Postgres. Check endpoints on the live site (`https://lbrt.net/fantasy/2026_27/...`, the
test league is `scenario=replay`); check pages with a throwaway Vite config that serves fake JSON
for the endpoints you're changing (don't commit it). Screenshot with a normal user agent — the
NBA's CDN (headshots/logos) blocks headless Chrome's default one.

## House rules

- Design rules: DESIGN.md (gold = you, orange = primary, display font only for big numbers, no
  dim text, phones designed too).
- Stage only your own files (parallel sessions); never `git add -A`.
- Update CLEARED.md (add unchecked items) when you change a page.
