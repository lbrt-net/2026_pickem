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
   - [ ] Box scores: one row per player-game and per team-game
   - [ ] Load all of 2025-26 (schedule + box scores) — already pulled locally in `~/PycharmProjects/nba_api_tests/data/` (parquet per game_id), load from there instead of re-pulling
   - [ ] ~2 prior seasons for draft rankings / "historical average"
   - [ ] Replace the 80 fake players with real ones
2. **League engine**
   - [ ] League table: season, current date, phase; live + test leagues share code
   - [ ] Fantasy weeks as date ranges (rules below); a game's week is derived from `game_date` at read time
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

## Data notes

- Store the whole traditional box score per player-game even if scoring uses less: minutes, pts, FG/3PT/FT made+attempted, oreb, dreb, ast, stl, blk, tov, pf, +/-, started, DNP.
- Size: a season of box scores ≈ 27k player rows ≈ 10 MB — trivial for Railway Postgres. Play-by-play ≈ 100–200 MB/season; skip for fantasy (only buys shot charts — maybe badges later).
- stats.nba.com: patient backoff 30→60→120s, never concurrent pulls (`nba_api_tests/CLAUDE_CHECKLIST.md`). Often blocks cloud IPs — bulk history loads run locally.

## Decisions

Already defined in `~/PycharmProjects/nba-pipeline/fantasy/` — **confirm these still apply**:
- **Scoring** (`fantasy_scoring.py`): pts +1, missed FG −0.5, made 3 +0.5, missed FT −0.5, oreb +1.5, dreb +0.5, ast +1, stl +2, blk +1.5, tov −2. Future: blocked −0.5, flagrant −2, ejection −5.
- **Weeks** (`fantasy_period_defn.py`): Mon–Sun; week 1 = Monday on/before opening night; All-Star break merges two calendar weeks into one; season ends at the last regular-season game minus 14 days, rounded back to a Sunday.

Still open:
- [ ] How NBA team slots score
- [ ] Lineups: all 11 slots count every day (current), or bench + daily/weekly lineup lock?
- [ ] IR: how many slots, who qualifies (NBA "Out" status? source for injury status?)
- [ ] Adds: waivers (priority order?) or first-come free agency
- [ ] Trades: commissioner approval or league veto; trade deadline
- [ ] Playoffs: 6 teams with byes for 1 & 2 (current placeholder)? Which weeks? Standings tiebreakers?
- [ ] Draft: order, pick timer, auto-pick
- [ ] Team abbreviation auto-generation / collisions
