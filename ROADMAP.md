# Roadmap — Fantasy 2026-27

The plan of attack, decisions made, and decisions still open. Update this file as things land.
Target: everything working (all features, not a minimum) before the 2026-27 season starts.

## The core idea

A **league** = season + calendar date + phase (`pre_draft → draft → regular_season → playoffs → done`).
- **Live league:** season 2026-27, date = today.
- **Test league (sandbox):** season 2025-26 (only option for now), date moved by an admin.

Pages only see stats up to the league's date, so a test can't see the future. Testing a 2025-26 replay
exercises the exact same code as the live league — no separate mock path.

## Phases of work

1. **Shared NBA data layer** (`backend/nba/`, season-agnostic)
   - [x] Schedule: `nba_games` + daily 3 AM CT sync + change log (see "Schedule" below)
   - [x] Historical schedules 2022-23 → 2025-26: `scripts/load_historical_schedules.py --post` (from nba-pipeline / nba_api_tests parquet; needs pandas + pyarrow locally) → `POST /nba/admin/schedule/history`
   - [ ] Players + teams tables
   - [x] Box scores table `nba_player_games` + `scripts/load_historical_boxscores.py --post` (2022-23 → 2025-26 from local parquet)
   - [ ] Pull only the 2025-26 games missing from both local sources (list printed by the loader)
   - [ ] Load all of 2025-26 (schedule + box scores) — already pulled locally in `~/PycharmProjects/nba_api_tests/data/` (parquet per game_id), load from there instead of re-pulling
   - [ ] ~2 prior seasons for draft rankings / "historical average"
   - [x] Real pool: `refresh_pool()` builds players (per-game averages, stats season = latest loaded) + 30 NBA teams from box scores; runs at boot while the pool is dummy, or `POST /fantasy/2026_27/admin/pool/refresh`. Refuses if live has rosters.
   - [x] Per-entity game log: actual fantasy points for played games, projection for scheduled ones (season avg after 10 games, else last season's), per-week totals — `GET /fantasy/2026_27/entity/{id}/games?season=`, shown on the player page
   - [x] Schedule page (`/fantasy/2026_27/schedule`): real games by fantasy week, games per NBA team
2. **League engine**
   - [ ] League table: season, current date, phase; live + test leagues share code
   - [x] Fantasy weeks as date ranges (`fantasy_2026_27/weeks.py`, `GET /weeks?season=`); a game's week is derived from `game_date` at read time
   - [ ] Standings/Matchup/Recap/Playoffs still use the fixed 19-week placeholder — switch them to `/weeks`
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

Already defined in `~/PycharmProjects/nba-pipeline/fantasy/` — **confirm these still apply**:
- **Scoring** (`fantasy_scoring.py`): pts +1, missed FG −0.5, made 3 +0.5, missed FT −0.5, oreb +1.5, dreb +0.5, ast +1, stl +2, blk +1.5, tov −2. Future: blocked −0.5, flagrant −2, ejection −5.
- **Weeks** — built in `weeks.py`: Mon–Sun; week 1 = Monday on/before opening night; All-Star week + the week after fused into one (Fantrax); playoffs = Quarterfinals 1 wk, Semifinals 1 wk, Championship 2 wks (Fantrax). 2026-27 → 18 regular weeks (Oct 19 – Feb 28), playoffs Mar 1 – Mar 28.
  - **Confirm:** season end = "tankathon cutoff" from `fantasy_period_defn.py` (last regular-season game − 14 days, back to a Sunday → Mar 28, 2027) vs. running to the NBA's last day (Apr 11). Change `CUTOFF_DAYS` in `weeks.py`.
  - All-Star week for future schedules is detected from the no-games gap (verified against 2024-25) until the NBA lists the game.

Still open:
- [ ] How NBA team slots score
- [ ] Lineups: all 11 slots count every day (current), or bench + daily/weekly lineup lock?
- [ ] IR: how many slots, who qualifies (NBA "Out" status? source for injury status?)
- [ ] Adds: waivers (priority order?) or first-come free agency
- [ ] Trades: commissioner approval or league veto; trade deadline
- [ ] Playoffs: 6 teams with byes for 1 & 2 (current placeholder)? Which weeks? Standings tiebreakers?
- [ ] Draft: order, pick timer, auto-pick
- [ ] Team abbreviation auto-generation / collisions
