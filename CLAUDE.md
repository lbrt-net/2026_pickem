# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

NBA playoff pick'em app for a small private group. Users log in via Discord, submit picks for each series (winner, games, stat leader), and earn points. A community board shows aggregate picks after series lock.

## Commands

### Backend
```bash
# Run dev server (from repo root)
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install       # first time
npm run dev       # Vite dev server on :5173
npm run build     # production build → frontend/dist/
npm run lint      # ESLint
```

### Production (Docker)
```bash
docker build -t pickem .
docker run -p 8000:8000 --env-file .env pickem
```

Required env vars: `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_REDIRECT_URI`, `SECRET_KEY`, `DATABASE_URL`, `ADMIN_DISCORD_IDS` (comma-separated Discord user IDs), `INTERNAL_API_KEY` (used by scripts for admin auth without session cookie).

## Architecture

**Single-file backend** (`main.py`) — FastAPI app serving both the API and the React SPA. In production, `frontend/dist/` is built into the Docker image and served by the catch-all route. In dev, Vite proxies API requests to the FastAPI server.

**Frontend** (`frontend/src/`) — Vite + React 19 SPA, no state management library.

- `App.jsx` — router: `/` → CommunityBoard, `/picks/me` and `/picks/:username` → PickemBoard, `/user/:username` → UserPicksPage, `/admin` → AdminPage
- `pages/PickemBoard.jsx` — own picks only (editable). Redirects to `/user/:username` if viewing another user. Fetches `/stat-guide` and passes to MatchupCard.
- `pages/UserPicksPage.jsx` — readonly view of any user's picks, linked from Leaderboard. Has its own `pickPoints` scoring function and `pickStatus` fallback for locked-but-unreturned picks.
- `pages/CommunityBoard.jsx` — aggregate view showing community pick distribution after lock. Defaults to Conf Semis tab.
- `pages/AdminPage.jsx` — admin CRUD for matchups, results, wins, stat logs, rosters. Defaults to R2 filter.
- `components/MatchupCard.jsx` — interactive card for a single series. Shows stat guide (collapsible, clickable to fill pick) when not readonly/locked. Uses `wins_a`/`wins_b` from matchup for pip dots.
- `components/CommunityCard.jsx` — community aggregate card with pick distribution bars and `outcomePoints` scoring.
- `utils/helpers.js` — all shared constants and pure functions: `groupMatchups` (7-column bracket layout), `computeWidths` (responsive column sizing), `computeSeriesProbs` (DP series probability), `TEAM_COLORS`, lock/TBD helpers.

**Database** — PostgreSQL. Schema is created/migrated inline in `init_db()` at startup using `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. No migration framework. Tables: `users`, `matchups`, `picks`, `scores`, `rosters`, `stat_guide`.

**Auth** — Discord OAuth2 → signed cookie via `itsdangerous`. Admin status is determined by whether the Discord ID is in `ADMIN_DISCORD_IDS` env var, re-evaluated on every login. Scripts use `X-Internal-Key` header with `INTERNAL_API_KEY` env var for admin endpoints without a session cookie.

## Scoring

Per series: correct winner = 2 pts, games within 1 = 1 pt (exact = 2 pts), correct stat leader = 1 pt. Cap 5 pts/series.

**Chart-adjacency formula for wrong-winner game length:**
- Correct winner: `dist = abs(pick_games - result_games)` → 0=+2pts, 1=+1pt
- Wrong winner: `dist = abs(15 - pick_games - result_games)` → ≤2=+1pt

**Round multipliers** (actual code values in `ROUND_MULTIPLIERS`): R1×1, R2×4, CF×8, Finals×16.

Scores are recalculated from scratch for all affected users whenever a result is set or cleared (`_recalculate_scores_for_matchup`). Two scoring functions exist: `_pick_series_pts` (per-pick) and inline logic in `_recalculate_scores_for_matchup` — keep them in sync.

## Matchup management

`game_time` is always **Central Time** (`YYYY-MM-DDTHH:MM`, no tz suffix). `lock_time` is auto-computed as 1 hour before tip-off in UTC. Never set `lock_time` directly — always POST to `/admin/matchups` with `game_time`. `wins_a`/`wins_b` track live series score (updated via `/admin/matchups/:id/wins`).

## Stat guide

One-off script per round: `scripts/stat_guide.py`. Fetches NBA API stats, outputs JSON, POSTs to backend.

```bash
python3 scripts/stat_guide.py --post          # fetch + POST to prod
python3 scripts/stat_guide.py --out guide.md  # also save markdown
```

- Loads `INTERNAL_API_KEY` from `.env` automatically. Default base URL is `https://pickem.lbrt.net`.
- `SERIES` list at top of script is the only hardcoded thing — update teams/stats/`po_rounds` each round.
- `po_rounds`: `[1]` = R1 col only, `[1,2]` = R1+R2, `[1,2,3]` = R1+R2+CF.
- NBA API note: `LeagueHustleStatsPlayer` doesn't support `season_segment_nullable` — use `date_from_nullable="02/16/2026"` for post-ASB splits instead.
- Frontend fetches `/stat-guide` in PickemBoard, matches by team name, shows collapsible table in MatchupCard. Columns render dynamically based on which round keys have non-null data.

## Stat logs (per-game tracking)

`scripts/fetch_stat_logs.py` — fetches per-game box scores from NBA API and POSTs to `/admin/matchups/:id/stat-log`. Only R1 matchup configs are currently in the `MATCHUPS` dict — **add R2 configs (e5, e6, w5, w6) once semis teams are confirmed.**

## Bracket layout

The 7-column grid is: `[West R1, West R2, West CF, Finals, East CF, East R2, East R1]`. `ACTIVE_COLS` in `helpers.js` controls which columns are expanded vs compressed for each round tab.

## API endpoints

| Method | Path | Auth |
|--------|------|------|
| GET | `/me` | session cookie |
| GET/POST | `/picks/me` | session cookie |
| GET | `/picks/user/:username` | public (locked only) |
| GET | `/picks/user/:username/status` | public |
| GET | `/matchups` | public |
| GET | `/matchups/aggregate` | public (locked only) |
| GET | `/stat-guide` | public |
| GET | `/rosters` | public |
| POST | `/admin/matchups` | admin |
| POST | `/admin/matchups/:id/result` | admin |
| DELETE | `/admin/matchups/:id/result` | admin |
| POST | `/admin/matchups/:id/wins` | admin |
| POST | `/admin/matchups/:id/stat-log` | admin |
| POST | `/admin/rosters` | admin |
| POST | `/admin/stat-guide` | admin |
| POST | `/admin/picks/:user_id` | admin (bypasses lock) |
