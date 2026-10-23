# Nightly box scores + play-by-play (built 2026-10-14: `backend/nba/nightly.py`)

The overnight job that keeps the site's NBA data complete and correct during the season. **Read this before touching
it or any NBA data loader.** This page is its manual.

**Built (2026-10-14):**
- `backend/nba/nightly.py`: the job.
- `backend/nba/shot_fields.py`: the shot chart math, the one copy, also used by `scripts/build_shot_fields.py`.
- The `nba_game_loads` table.
- A scheduler entry at 4:00 AM Central, catching up on boot if the last good run is over 26 hours old.
- `POST /nba/admin/nightly` for manual runs.
- A "nightly box scores current" line on the check-up page.
- `tests/integration/test_nightly.py`: load + clean rerun, a correction, a bad feed writing nothing, shot fields.
- `GET /nba/admin/live-probe` now also tests the play-by-play.

Left out on purpose: clearing the player page cache (its 2026-27 numbers already refresh every 30 minutes).

## Why it's needed

During games, the live loop (`backend/nba/live.py`, built 2026-10-12) already writes everything the site reads, every 30
seconds, from the NBA's CDN. It stops 15 minutes after a game goes final. Three things fall through:

1. **Missed games:** if the server is down or restarting while a game finishes (deploys happen at night too), that game
   never gets its final line.
2. **Stat corrections:** the NBA edits box scores for days after a game (an assist or rebound moves, a block
   is credited to someone else). Our rows keep whatever the feed said 15 minutes after the final.
3. **Things built from the data:** the player page's shot chart (Extras) is built from the play-by-play, and nothing
   builds it yet.

## What the site needs, and who reads it

| Data | Table | Read by |
|---|---|---|
| Player lines: minutes, makes and misses, rebounds, assists, steals, blocks, turnovers, fouls, DNP reason | `nba_player_games` | scoring, Matchup, Roster, player page, history, pool detection |
| Own shots blocked (BLKD), fouls drawn | `nba_player_games.blkd / pfd` | scoring (BLKD is a category) |
| Clutch points (NBA definition: last 5 min of the 4th / OT, within 5) | `nba_player_games.clutch_pts` | scoring (+2 per clutch point) |
| Team defense: opp fast-break and paint points, opp turnovers, rebounds, shot-clock violations forced | `nba_team_game_stats` | TEAM scoring (draft 6) |
| Score and status | `nba_games` | everything with a result |
| Raw final box score (latest copy) | `nba_live_raw` | re-parsing later |
| Each game's shots (player, spot, two / three, points), from the play-by-play | `nba_game_shots` | the shot chart |
| Shot chart fields | `nba_shot_fields` | player page Extras (2026-27 only) |

All of it comes from two CDN files per game, which the live loop already parses (`live.pull_game`):
- `https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json`
- `https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json`

The CDN needs the full browser header set in `live.HEADERS`. Thin headers get a 403, and the stats.nba.com `Host` line
makes it redirect forever. **Only the CDN is used:** Railway reads it fine (proven 2026-10-12), while stats.nba.com
often blocks cloud servers, and everything above is in the CDN files. The play-by-play has each shot's spot
(`xLegacy` / `yLegacy`, tenths of a foot, hoop at 0,0), `actionType` 2pt / 3pt and `shotResult`. Those are the
coordinates the shot chart method uses.

## What already runs (inside the web app, `backend/nba/scheduler.py`)

- 3:00 AM CT: schedule sync (`schedule.sync`), then the weekly recap snapshots.
- Injuries from ESPN: Mondays every 15 minutes, other days 5 PM.
- Lock etching: 5 minutes before each tip-off.
- Live games: every 30s while one is on.

## The nightly job

**Where:** inside the web app's scheduler like the others, at **4:00 AM CT** (after the 3 AM schedule sync, before
anyone's morning). One instance at a time: take a Postgres advisory lock, since two containers can overlap during a
deploy. Log each run in `nba_sync_runs` (kind `nightly`), the way the schedule sync does.

**Which games:**
- every regular-season game (`game_type = 'regular'`, and `cup_final` for the record) whose date is from **7 days ago
  through yesterday**, every night: the correction window;
- plus each game once more on the night it turns **14 days** old: the last word on late corrections;
- plus any older 2026-27 game marked final with no raw final feed or no player rows: the catch-up.

**For each game, in order:**
1. Fetch the box score and play-by-play (with retries and backoff; the CDN is sometimes slow right after games).
2. Skip it if the feed doesn't say final (`gameStatus = 3`). Postponed games are the schedule sync's job.
3. **Check before writing:**
   - each team's player points add up to its final score;
   - both teams have players with minutes;
   - the play-by-play has actions;
   - the score matches `nba_games` (or we update it).
   If a check fails: write nothing, record why, and try again the next night.
4. **Write**, using `live.pull_game`'s parsing (one parser for live and nightly, never two). Every write is an upsert,
   so a second run changes nothing unless the NBA changed something:
   - player lines, BLKD, fouls drawn, clutch points → `nba_player_games`;
   - team defense → `nba_team_game_stats`;
   - score → `nba_games`;
   - **raw box score → `nba_live_raw`, replaced with the latest copy**;
   - **the play-by-play's shots → `nba_game_shots`.** The raw play-by-play itself is not kept (commissioner,
     2026-10-14: ~370 KB a game, ~450 MB a season), only the raw box score.
5. **Record the load in a new table, `nba_game_loads`** (game id, last pulled, checks passed, what changed: player
   lines that differ from the last load, attempts, last error). That gives "games corrected this week" for free, and
   tells the check-up page what's missing.

**After the games:**
6. **Shot chart fields** (`nba_shot_fields`, 2026-27 only; method = `scripts/build_shot_fields.py` =
   nba-pipeline/analysis/shot_chart.py):
   - The season's shots come from `nba_game_shots`, pulled out of each game's play-by-play when it loaded: every action
     with `isFieldGoal = 1`, its `xLegacy` /
     `yLegacy`, 3 points if `actionType` is 3pt, made if `shotResult` = Made. Leave out heaves (verify how the CDN marks
     them; the pipeline's 2025-26 play-by-play had them separately; a cutoff around 40 ft is the fallback).
   - Rebuild the league's points-per-shot map from all of them.
   - Rebuild every pool player with 50+ shots this season. The league map moves every night, so rebuild everyone,
     not just last night's players.
   - **Needs numpy on the server** (decision below). The math moves from the script into `backend/nba/shot_fields.py`;
     the script keeps a `--local` mode for checking.
7. **Clear caches:** the player page's 2026-27 season cache (`player_page._cache`) and anything else keyed on this
   season's games, so the first morning visitor gets fresh numbers.
8. **Check-up:** add "box scores current" (every final game from the last 7 days loaded and passing checks) and "shot
   charts built" to the site's check-up page (`fantasy_2026_27/health.py`), with the games that failed.

**Manual runs:** `POST /nba/admin/nightly` (admin) with optional `from` / `to` dates. It reruns any range (a backfill
after an outage, or one game) and returns the per-game summary. It's the same code as the 4 AM run.

## Not in this job

- **Schedule changes and postponements:** the 3 AM schedule sync.
- **Injuries:** ESPN sync.
- **Projections, history, past seasons:** offline scripts. Past seasons never change.
- **Stats that only stats.nba.com has** (hustle, tracking, shot areas): not needed by any page today. If one is ever
  needed, it runs from the Mac (`scripts/pull_*.py`) and POSTs, because Railway can't count on reaching stats.nba.com.
- **Playoff games (`004`)** for pick'em: a separate module, if wanted.

## Decisions

1. **numpy on the server** for the shot chart (commissioner, 2026-10-14). `numpy==2.4.6` is in requirements.txt: the
   newest release that supports the server's Python 3.11.
2. **Correction window** (commissioner, 2026-10-14): every game from the last **7 days** re-pulled every night, plus
   one last re-pull at **14 days**. ("7 and 114 days" read as 7 and 14; confirm.)
3. **Run time: 4:00 AM CT** (commissioner, 2026-10-14).

## How to build and test it (when the time comes)

- **Saved feeds:** `tests/integration/data/live_box_0012600042.json` and `live_pbp_0012600042.json` (a real preseason
  game) drive integration tests for:
  - the checks (a doctored box where the points don't add up → nothing written);
  - idempotency (run twice → no changes the second time);
  - a correction (change one assist → the row updates and `nba_game_loads` records it);
  - shot field building from the play-by-play.
- **Before the season:** run `POST /nba/admin/nightly` against the 2026-27 preseason games (game ids `0012600…`,
  written under a test season label, never the real one). Compare a few players' lines with NBA.com.
- **First week of the season:** watch the check-up page every morning.

## Stats pages refresh (2026-10-15) — runs on the commissioner's Mac, not the server

The stats pages (`/stats/shooting`, `/stats/playmaking`) are built by the nba-pipeline models, which live on the Mac,
so their nightly refresh runs there: `~/Library/LaunchAgents/net.lbrt.nightly-stats.plist` → `nba-pipeline/scripts/
nightly_stats.sh 2026-27` at 05:30 Central every day (the Mac must be awake; first useful run Wed 2026-10-21 after
the opener). Steps: pause the manifest queue → `nba_api_tests/pull_day.py` (season game log, yesterday's play-by-play
from stats.nba.com, the day's player lines) → resume the queue → possession walk without lineups → play contexts →
shot value v9 with 2025-26's coefficients applied (`--apply-from`) → skill/residual vs 2025-26 → shooting export →
Box Creation → `scripts/upload_stats_json.py` POSTs both to `POST /nba/admin/stats-json`. The server keeps one row
per page in `nba_stats_json`; the three `/nba/stats/*` routes serve that row when present, else the static file in
`backend/nba/`. Rebounding stays on 2024-25 (it needs lineups). Logs: `nba-pipeline/data/nightly_stats.log` (steps)
and `nightly_stats.launchd.log` (launchd). Manual run: `/bin/zsh nba-pipeline/scripts/nightly_stats.sh 2026-27`.
To stop it: `launchctl unload ~/Library/LaunchAgents/net.lbrt.nightly-stats.plist`.

Rebounding is in the chain too (2026-10-15, late): `pull_day.py` also pulls each game's traditional box score and the
season bios; `process/box_from_games.py` builds the season box file; `process/lineups_v3.py` resolves lineups
(incremental: games already in `data/processed/<season>/lineup_segments_v3.parquet` are skipped); the walk runs with
`--segments --box`; `models/rebounding_v2.py --season` and `rebounding_tables.py --season` build the json; it is
posted as `rebounding`. Everything processed is derived from the raw pulls on disk and rebuilt nightly from scratch,
except the lineup segments: after a resolver fix, delete that season's segments file and the next run redoes every game.
Raw pulls are never deleted by the job.


## Live pull backup (2026-10-22)
cdn.nba.com started answering our Railway server with 403 Forbidden mid-game. Two safety nets:
1. **Storage fallback** (`live.fetch`): any CDN failure retries the same file from the NBA's storage copy
   (nba-prod-us-east-1-mediaops-stats.s3.amazonaws.com/NBA/liveData).
2. **Relay from the commissioner's machine** (`scripts/live_relay.py`): every 30 s it reads `GET /nba/admin/live-health`;
   when the server's pull is failing (or quiet 2+ minutes with games on) it downloads the feeds itself and posts them to
   `POST /nba/admin/live-push`, loaded by the same parser. `--always` pushes regardless. Moves to our own box later.
One game failing no longer stops the others (`pull_today` isolates each game); `POST /nba/admin/live-pull` returns the error.
3. **Feed Log** (commissioner page /fantasy/2026_27/feed-log, table `nba_feed_log`, kept 60 days): every 10 minutes the
   server tries the main feed and the backup; every live pull records which answered. The record for moving to our own box.
