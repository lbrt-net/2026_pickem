# Roadmap — Fantasy 2026-27

The plan of attack, decisions made, and decisions still open. Update this file as things land.

## How we build now: core first, then one feature per round (2026-09-29)

Boil it down to the basics, test them in the replay sandbox until confident, then add **one**
feature, nitpick it, get confident, add the next. Everything else is switched off in
`frontend/src/components/fantasy/features.js` (off pages leave the nav and show "not in this
round"; in-page features too).

**Round 1 — core only:**
- Draft
- Players
- Roster, with **add/drop free and instant — no waivers** for this round (the weekly-waiver rules
  under "Decisions" wait for a later round)
- Scoring
- Schedule, matchups, standings
- Playoffs

**Off for now:** Trades, Transactions, Recap, Draft Recap, Team History, Team Settings,
notifications, player game-log/stat history, past-season pickers. Not built at all: waivers,
roster-cap rules beyond slot fit, IR, injuries, mid-season NBA transactions.

**TODO — design rules follow-ups (DESIGN.md 2026-10-04):** code still to match the doc — monochrome
position badges (TM slanted; position text only on FLX / BN), italic projected numerals, distinct button
looks per action type (main / add / filter / page / drop), section labels in the body face, times as
"7:30 PM CT" without UTC copy on the draft page, re-check gold vs orange leftovers.

**TODO — easter egg:** when LaMelo Ball is drafted, blast LaMelo's "Tweaker" from the right part of the
song.

**TODO — player first/last names:** two-line names split at the first space for now. Store the
NBA's own `firstName`/`familyName` (in the nba_api_tests box score files and the daily feed).

**TODO — projections:** no projected scores anywhere (Home, Matchup, Standings) until there's a real
projection method. When it exists, projections go into the matchups view.

**Round 1 still to build:** make draft picks (any team, in the sandbox), instant add/drop, and
point Standings / Matchup / Playoffs / Home at the real results engine instead of projections.

## The core idea

A **league** = season + calendar date + phase (`pre_draft → draft → regular_season → playoffs → done`).
- **Live league:** season 2026-27, date = today.
- **Test league (sandbox):** season 2025-26 (only option for now), date moved by an admin (date picker above every 2025-26 page, admins only: ‹ › day, +1 week, or pick a date).

Pages only see stats up to the league's date, so a test can't see the future. Testing a 2025-26 replay
exercises the exact same code as the live league — no separate mock path.

## Phases of work

1. **Shared NBA data layer** (`backend/nba/`, season-agnostic)
   - [x] Schedule: `nba_games` + daily 3 AM CT sync + change log (see "Schedule" below)
   - [x] Historical schedules 2022-23 → 2025-26: `scripts/load_historical_schedules.py --post` (from nba-pipeline / nba_api_tests parquet; needs pandas + pyarrow locally) → `POST /nba/admin/schedule/history`
   - [ ] Players + teams tables
   - [x] Box scores table `nba_player_games` + `scripts/load_historical_boxscores.py --post` (2022-23 → 2025-26 from local parquet). 2023-24 had silently failed (All-Star exhibition rows with garbage minutes); loader now skips All-Star games, 2023-24 loaded 2026-10-05.
   - [ ] **2021-22 backfill (5th season, for projections):** `nba-pipeline/pull/pull_schedule.py 2022` then `pull_box_score_traditional.py 2022` (stats.nba.com, ~2h), then `load_historical_schedules.py --post --season 2021-22` and `load_historical_boxscores.py --post --season 2021-22`. Older seasons (2020-21 short COVID season, 2019-20 bubble) skipped for now.
   - [ ] Pull only the 2025-26 games missing from both local sources (list printed by the loader)
   - [ ] Load all of 2025-26 (schedule + box scores) — already pulled locally in `~/PycharmProjects/nba_api_tests/data/` (parquet per game_id), load from there instead of re-pulling
   - [ ] ~2 prior seasons for draft rankings / "historical average"
   - [ ] Every attribute in FANTASY_SCORING.md (misc, hustle, tracking, defense dashboard, clutch, play-by-play) for **all loaded seasons (2022-23 → 2025-26)**, not just the live one — so advanced/historical scores can be computed for older years
   - [x] Real pool: `refresh_pool()` builds players (per-game averages, stats season = latest loaded) + 30 NBA teams from box scores; runs at boot while the pool is dummy, or `POST /fantasy/2026_27/admin/pool/refresh`. Refuses if live has rosters.
   - [x] Per-entity game log: actual fantasy points for played games, projection for scheduled ones (season avg after 10 games, else last season's), per-week totals — `GET /fantasy/2026_27/entity/{id}/games?season=`, shown on the player page
   - [x] Schedule page (`/fantasy/2026_27/schedule`): real games by fantasy week, games per NBA team
   - [x] Draft pool + projections for 2026-27 (2026-10-07; on prod 2026-10-07): `fantasy_pool` holds PROJ AVG, position, flags and each player's weekly-best curve; loading (`scripts/load_projections.py --post`) applies the curve to the 2026-27 schedule once and stores PROJ MAX + per-week projection (projections are made once, before the season). NBA Cup December games not yet scheduled are filled into the Cup week (each team to 82). Draft ranks on PROJ MAX. `GET /players` has `proj_avg` / `proj_max`.
   - [x] Player history '23–'26 (`history.py`, `fantasy_history`, `GET /players/{id}/history`, rebuild `POST /admin/history/build`): average weekly max, FP/G, best-game breakdown by category, weeks by game count, with the league's week rules. Players only; NBA teams later.
   - [x] BLKD (own shots blocked) for '23–'26 box scores from PlayerGameLogs (`load_historical_boxscores.py` now posts blkd/pfd). Prod done 2026-10-07: box scores '23–'26 reloaded with BLKD, history built (21 weeks/season, 522–573 players), 2026-27 pool + projections loaded (616 players, 552 with PROJ MAX).
   - [ ] Frontend: PROJ AVG / PROJ MAX in the draft room with a short glossary under the table; history + 2026-27 projection on the player page (handed to design)
   - [x] **Projections linked to the scoring rules (2026-10-08)**: one command, `python3 scripts/build_projections.py [--status | --post | --rules local]` — rules from the site's GET /scoring, rebuilds the changed side (~25 s), loads players + NBA teams (with MAX low/high) stamped with the rules; site table `fantasy_proj_builds`, GET /scoring → `projections: {player, team: {stale, changes}}`. Open: show the stale notice to admins on a page.
   - [ ] **For the front-end thread — auction raises (2026-10-08):** raises must be at least 4% of the high bid (rounded up, $1 min; setting `auction_min_raise_pct`). The backend rejects smaller bids. DraftRoom's `next = lot.high_bid + 1` and "Bid +$5" buttons should use `lot.min_next` (smallest legal bid). The lot also carries `my_rec` (viewer's Rec bid for him) and `my_call` (`bid` / `pass` / `winning`); `auction.min_raise_pct` for the rules line.
   - [x] **Availability in PROJ MAX (2026-10-08)**: AVAILABILITY.md — expected games per player (season-ending injuries left out), clustered misses, current ESPN Out weeks zeroed; PROJ MAX / MAX low-high / draft rank / Rec bid include it, PROJ AVG doesn't. `proj_weeks[]` rows now carry `plays` (expected games he plays that week); `proj_week.avail` = {games, zero, q}.
   - [x] **Current injuries (2026-10-08)**: `backend/nba/injuries.py` pulls ESPN's injury feed — Mondays every 15 min 7 AM–11 PM CT, other days 5 PM CT (present state only; each sync replaces the table, unlisted = healthy), matched to our player ids. **For the front-end thread:** `GET /nba/injuries` (everyone listed) or `GET /nba/injuries?player_id=…` (`[]` = healthy) → `{status: Out / Day-To-Day / …, short: OUT / GTD, injury, return_date, comment, reported_at, synced_at}` — for the player card / draft list. Manual sync: `POST /nba/admin/injuries/sync`. **Injury-aware week (backend only, not on the pages yet):** `GET /fantasy/2026_27/team/{id}/week/outlook` = the `/week` view plus each player's `injury`, games marked `out` (Out, before ESPN's estimated return date; every game when there's none), `games_out`, and `projected` / `games_left` counting only games he's expected to play (Day-To-Day projects as usual). `/week` itself is unchanged.
   - [ ] **Handoff to the backend thread (2026-10-07)**: (1) reload prod projections with clutch — now `python3 scripts/build_projections.py --post` (was load_projections.py) (proj_week JSON now has `avg` with +2 per projected clutch point; SCORING_SCALE.md); (2) clutch as a scoring category in the app (`logic.SCORING`, FANTASY_SCORING.md) + nightly clutch pull (`scripts/pull_player_clutch.py` logic, by game day); (3) TEAM scoring draft 6 in the engine + TEAM projections (TEAM_SCORING.md, `team_draft4.py` / `team_proj` method) replacing point margin — per-team weekly-best curves now exported to nba-pipeline `data/raw/team_proj_week_2026_27.json`, keyed by team abbreviation, same shape as the players' proj_week (`e`/`p25`/`p90` for 1..10 games, `avg` = per-game projection), so TEAMs can go through `apply_schedule` and get MAX low/high; (4) ~~Rec bid in the draft room~~ done 2026-10-08 (`bid.py`: $1 + scale × (points over replacement)^1.25, fit to a whole-team mock auction; BIDDING_GUIDE.md) (formula + per-league replacement levels and going rate, `bid_guide.py`).
   - [ ] **TABLED — mid-season NBA transactions** (trades, signings, waivers): today a player's NBA team = team in his latest box score, so it lags until he plays for the new team. Plan: `nba_player_teams` history (player, team, effective date, source manual/box score); admin "player X → team Y from date Z" when a trade is announced; box scores auto-add the change as a backstop; new players join the pool on first game or by admin. Fantasy ownership unaffected. Replay gets 2025-26 trades from box scores for free.
2. **League engine**
   - [ ] League table: season, current date, phase; live + test leagues share code
   - [x] Fantasy weeks as date ranges (`fantasy_2026_27/weeks.py`, `GET /weeks?season=`); a game's week is derived from `game_date` at read time
   - [x] Matchup on real weeks + results (canvas v6, 2026-10-05)
   - [x] Standings, Home, Roster facelift on real results (2026-10-05)
   - [ ] Recap/Playoffs still use the fixed 19-week placeholder — switch them to `/weeks`
   - [ ] Weekly scoring from real box scores; replace the "projected per-game" stand-in in `frontend/src/components/fantasy/data.js`
   - [ ] Finalized weeks are frozen (results snapshotted) so later stat corrections / moved games don't rewrite history
3. **Sandbox controls (admin)**
   - [ ] New test league (pick season: 2025-26)
   - [ ] Advance to week N / rewind / reset
   - [ ] "Act as team X" — make any team's decisions at any phase
4. **Actions**
   - [ ] Draft: make picks (any team in test), auto-pick, draft order
   - [ ] Lineups / IR
   - [ ] Add / drop (waivers or free agency — see decisions)
   - [ ] Trades: propose / accept / reject, public
   - [ ] Team settings save (name, abbreviation, logo)
   - [ ] Playoffs: bracket from final standings, weeks, champion
   - [ ] Notifications (in-website only, instant, all off by default; prefs saved via `/notifications/settings`): injuries, IR reminders, trade offers to you, league trades, your claims, weekly recap (league activity + results; end-of-regular-season and playoffs recaps too), draft reminders. No matchup alerts, no announcements, no Discord DMs, no digests. The bell + notification list itself is still to build.
5. **Go live**
   - [ ] Daily box score job for 2026-27 (same 3 AM slot as the schedule)
   - [ ] Mock draft with the whole group in a test league
   - [ ] Reset live league, real draft

## Schedule (built)

- Source: NBA CDN full-season feed `scheduleLeagueV2_1.json` (same as `nba_api_tests/update_schedule.py`).
- Daily at **3:00 AM Central** inside the web app (`backend/nba/scheduler.py`); catch-up on boot if the last success is >24h old; Postgres advisory lock so only one instance syncs. `NBA_SYNC_DISABLED=1` turns it off.
- Moving games: upsert by `game_id`; date/time changes, TBD teams/times filled in, postponed/cancelled status all logged to `nba_game_changes`. Games missing from the feed are flagged (`missing_since`), never deleted, and restored if they come back. A feed with <90% of the stored games is refused (nothing written). Each sync is all-or-nothing.
- Unscheduled games (NBA Cup knockouts etc.) exist as rows with NULL teams/time until the feed fills them in.
- Admin: `GET /nba/admin/schedule/status`, `POST /nba/admin/schedule/sync`. Public: `GET /nba/schedule?season=&start=&end=&team=`.
- **Open risk:** cdn.nba.com returned 403 from the dev Mac on 2026-09-27. If Railway is blocked too, fallback is `python3 scripts/pull_nba_schedule.py --post` from a machine that can reach it (posts to `/nba/admin/schedule/ingest`). Check `nba_sync_runs` after the first deploy.

## Scoring engine (built 2026-10-07)
Scoring is data (`backend/fantasy_2026_27/scoring.py`): each league has its own player and team rulesets
(`fantasy_leagues.scoring`; NULL = today's rules), so a later season can score differently. A ruleset = a week mode
(`best_game` | `sum`) + components (`per_stat` stat × points, `threshold` / `bonus` with `below` or `at_least`).
One scorer (`score_game`) for every game; stat lines come from input sources (`player_line`: box score + any
`clutch_*` columns; `team_line`: score + `extra` defensive stats). A component whose stat isn't loaded scores 0 and
is reported as missing. Results, the week view and `/scoring` use the league's rules.
- [x] Default rules = player weights + clutch (+2 per clutch point) and TEAM draft 6 (best game) (2026-10-08).
  Inputs: `nba_player_games.clutch_pts`, `nba_team_game_stats`; `scripts/load_team_clutch.py` loads '23–'26 from
  nba-pipeline raw files + 2026-27 TEAM projections (`fantasy_team_pool`) from team_draft4.json. NBA teams have
  history, are on the draft list and in auto-pick, and have player-card tabs.
- [ ] Prod: run `load_team_clutch.py --post --team-proj …`, then POST /admin/history/build, then reload player
  projections with clutch (`load_projections.py --post`)
- [ ] Nightly in season: violations by day, TeamGameLogs Misc/Opponent, player clutch by day (pullers exist)
- [ ] TEAM weekly curve (per games-in-week) so teams get MAX low / high and per-week projections
- [ ] History, PROJ MAX and the draft board are still built with the default rules; rebuild per ruleset version
  when a league's rules change
- [ ] Pages: build Matchup contributions / Roster Points / player card / Rules columns from `/scoring` components
  (team rows show team components instead of Δ)

## Matchups (built 2026-10-07)
Round robin by default; the commissioner can set any regular-season week by hand in League Settings → Matchups
(`fantasy_leagues.matchups`, used by results, standings, Home and the week view).

## Box scores (plan)

Never re-pull what we already have. Every game is pulled at most a few times, ever.
- **History, loaded once from local files** (same source endpoint, `boxscoretraditionalv3`, full game only):
  - 2022-23, 2023-24, 2024-25: `nba-pipeline/data/raw/box_scores_traditional/trad_box_scores_YYYY_YY.parquet` — complete (1323–1327 games each).
  - 2025-26: union of `nba-pipeline` (827 games, through ~Mar 7) + `nba_api_tests/data/boxscore/traditional/<game_id>/players_p0.parquet` (1089 games). Then pull **only** the final games neither source has (Nov 8–27 gap, ~10 March games, play-in, playoffs) — not the whole season.
- **Daily (2026-27), right after the 3 AM schedule sync:** a `nba_box_pulls` table (game_id, pulled_at, pulls) tracks what's been fetched. Pull games that are `final` in `nba_games` and not yet pulled — usually 0–15 a night.
- **Stat corrections:** re-pull each game once more ~48h after it goes final, then it's frozen. Admin can force a re-pull of one game.
- **Where it runs:** stats.nba.com usually blocks cloud IPs; first try from Railway, and if blocked, a scheduled local script posts the rows (same pattern as the schedule fallback). Backoff 30→60→120s, 5s between requests, never concurrent.

## Data notes

- Store the whole traditional box score per player-game even if scoring uses less: minutes, pts, FG/3PT/FT made+attempted, oreb, dreb, ast, stl, blk, tov, pf, +/-, started, DNP.
- Size: a season of box scores ≈ 27k player rows ≈ 10 MB — trivial for Railway Postgres. Play-by-play ≈ 100–200 MB/season; skip for fantasy (only buys shot charts — maybe badges later).
- stats.nba.com: patient backoff 30→60→120s, never concurrent pulls (`nba_api_tests/CLAUDE_CHECKLIST.md`). Often blocks cloud IPs — bulk history loads run locally.

## Decisions

**Scoring + format: locked in [FANTASY_SCORING.md](FANTASY_SCORING.md)** — weekly score = each player's best single game; basic box score decides matchups; advanced sub-components (hustle/tracking/defense/pbp) planned as a shadow score first.


Already defined in `~/PycharmProjects/nba-pipeline/fantasy/` — **confirm these still apply**:
- ~~Scoring~~ → superseded by FANTASY_SCORING.md (missed FT now −1.0, blocked −0.5 added).
- **Weeks** — built in `weeks.py`: Mon–Sun; week 1 = Monday on/before opening night; All-Star week + the week after fused into one (Fantrax); playoffs = Quarterfinals 1 wk, Semifinals 1 wk, Championship 2 wks (Fantrax). 2026-27 → 18 regular weeks (Oct 19 – Feb 28), playoffs Mar 1 – Mar 28.
  - **Confirm:** season end = "tankathon cutoff" from `fantasy_period_defn.py` (last regular-season game − 14 days, back to a Sunday → Mar 28, 2027) vs. running to the NBA's last day (Apr 11). Change `CUTOFF_DAYS` in `weeks.py`.
  - All-Star week for future schedules is detected from the no-games gap (verified against 2024-25) until the NBA lists the game.

Decided 2026-09-28:
- **NBA team slots:** point margin, totaled over the week. Balance vs. player points later.
- **Weekly lock:** rosters lock 5 minutes before the first game of each fantasy week; changes after the lock take effect the next week (server-enforced). Saved roster per week.
- **Adds are weekly — no instant pickups.** Waivers *and* free-agent adds both process once a week, at the same obscure overnight hour as the NBA sync (3 AM CT), before the week locks.
- **Claim order:** reverse standings.
- **Trades:** no review (no commissioner approval, no veto). Trade deadline = through the last week of the regular season (exact cutoff: the lock of the final regular-season week — confirm).
- **Notifications:** every category off by default. No exceptions.
- **IR slots will exist** — count and eligibility TBD (note only for now). Eligibility needs injury data, which is **tabled** with the injury feed.

- **Waivers:** a dropped player sits on waivers for 1 week. Waiver claims process **Saturday morning** (3 AM CT).
- **Free agents:** unclaimed players become free agents, and free-agent adds process **Sunday night / Monday morning** (3 AM CT Monday), before the new week locks.
- **Playoffs scale with the number of teams** — bracket size and byes are derived from league size, not fixed (design detail for when playoffs get built; 6 teams → current 6-team, byes-for-1-&-2 layout).

Still open (design detail, not blocking):
- [ ] IR: how many slots, who qualifies
- [ ] Draft: order, pick timer, auto-pick
- [ ] Team abbreviation auto-generation / collisions
