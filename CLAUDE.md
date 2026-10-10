# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Read `ROADMAP.md` first** — the fantasy 2026-27 plan, what's done, and open decisions. Update it when work lands.
**Read `DECISIONS.md` before changing behavior** — every ruling with its date and the check that protects it. Changing a decision = edit its entry and its check in the same commit.
**Checks:** `pytest` (rules; `tests/integration` needs `scripts/test_db.sh start` + `TEST_DATABASE_URL`), run on every push by GitHub Actions; Railway waits for them. After deploys: `python3 scripts/check_site.py`.
**`CLEARED.md`** tracks which pages/variants the commissioner has tested and signed off on. Only the user clears items; un-check an item when a change touches it.

## What this is

NBA playoff pick'em app for a small private group. Users log in via Discord, submit picks for each series (winner, games, stat leader), and earn points. A community board shows aggregate picks after series lock.

## Commands

### Backend
```bash
# Run dev server (from repo root)
uvicorn backend.main:app --reload --port 8000
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

**Backend package** (`backend/`) — one FastAPI app (`backend/main.py`), serving both the API and the React SPA, plus everything mounted into it. This repo is meant to hold pickem for every future playoff year, not just 2026, so the backend is organized by product area/year rather than being one flat file:
- `backend/auth.py` — Discord OAuth2, session cookies, `users` table. The one thing shared across every year and product area — a Discord login persists across seasons.
- `backend/admin.py` — site-wide user moderation (`/admin/users/*`), not scoped to any pickem year.
- `backend/pickem_2026/` — this year's pickem, fully isolated: its own tables (`matchups`, `picks`, `scores`, `rosters`, `stat_guide`), its own routes under `/pickem/2026/*`, its own scoring logic. **Deliberately not generalized** for future years — when pickem-2027 happens, it gets its own new `pickem_2027/` package with its own tables, built by copying/adapting whatever from 2026 is worth reusing, not by making 2026's schema flex to fit rules that don't exist yet.
- `backend/nba/` — shared, season-agnostic NBA data (`nba_games` schedule; box scores next). Daily 3 AM CT schedule sync runs inside the app (`scheduler.py`); see ROADMAP.md "Schedule".
- `backend/fantasy_2026_27/` — the 2026-27 fantasy season (same isolation pattern as pickem): dummy player/NBA-team pool, one fantasy team per visible user, `live`/`test_pre`/`test_post` sandboxes. See `frontend/src/pages/fantasy/README.md`.

**Styling:** dark mode only, all colors from `frontend/src/theme.css` tokens — no inline hex, one text color (`--text`), no dim/gray text. The full settled look (fonts, slanted cuts, gold = you, team blocks, placeholders) is in `DESIGN.md`.

In production, `frontend/dist/` is built into the Docker image and served by the catch-all route in `backend/main.py`. In dev, Vite proxies API requests to the FastAPI server.

**Frontend** (`frontend/src/`) — Vite + React 19 SPA, no state management library.

- `App.jsx` — router: `/` → CommunityBoard, `/picks/me` and `/picks/:username` → PickemBoard, `/user/:username` → UserPicksPage, `/admin` → AdminPage
- `pages/PickemBoard.jsx` — own picks only (editable). Redirects to `/user/:username` if viewing another user. Fetches `/stat-guide` and passes to MatchupCard.
- `pages/UserPicksPage.jsx` — readonly view of any user's picks, linked from Leaderboard. Has its own `pickPoints` scoring function and `pickStatus` fallback for locked-but-unreturned picks.
- `pages/CommunityBoard.jsx` — aggregate view showing community pick distribution after lock. Defaults to Conf Semis tab.
- `pages/AdminPage.jsx` — admin CRUD for matchups, results, wins, stat logs, rosters. Defaults to R2 filter.
- `components/MatchupCard.jsx` — interactive card for a single series. Shows stat guide (collapsible, clickable to fill pick) when not readonly/locked. Uses `wins_a`/`wins_b` from matchup for pip dots.
- `components/CommunityCard.jsx` — community aggregate card with pick distribution bars and `outcomePoints` scoring.
- `utils/helpers.js` — all shared constants and pure functions: `groupMatchups` (7-column bracket layout), `computeWidths` (responsive column sizing), `computeSeriesProbs` (DP series probability), `TEAM_COLORS`, lock/TBD helpers.

**Database** — PostgreSQL. Schema is created/migrated inline in `init_schema()` at startup using `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. No migration framework. `users` lives in `backend/auth.py`; `matchups`, `picks`, `scores`, `rosters`, `stat_guide` live in `backend/pickem_2026/schema.py` and belong only to pickem-2026.

**Auth** — Discord OAuth2 → signed cookie via `itsdangerous`. Admin status is determined by whether the Discord ID is in `ADMIN_DISCORD_IDS` env var, re-evaluated on every login. Scripts use `X-Internal-Key` header with `INTERNAL_API_KEY` env var for admin endpoints without a session cookie.

## Frontend view boundaries

Three distinct contexts render series data. **Do not conflate them** — bugs in one are never in another.

| | PickemBoard + MatchupCard | UserPicksPage | CommunityBoard + CommunityCard |
|---|---|---|---|
| Route | `/picks/me` | `/user/:username` | `/` |
| Data | Own picks (editable) | One user's picks (readonly) | Aggregate across all users |
| Interactivity | Full — click to pick, games, stat leader | None | None |
| Stat guide | Yes (collapsible in MatchupCard) | No | No |
| Scoring fn | None (no results shown) | `pickPoints()` — per-pick, chart-adjacency | `outcomePoints()` — per winner+games outcome |
| Stat leader tracking | No | No | `StatLeaderTable` from game log |
| Pick distribution | No | No | `SeriesBars` with probability/avatar bars |
| pickStatus | No | Yes — fallback for locked-but-API-missing picks | No |

**Key rules:**
- `PickemBoard` only ever renders the logged-in user's own picks. If `/picks/:username` is visited for another user, it redirects to `/user/:username`. Never add readonly logic to PickemBoard.
- `UserPicksPage` has its own `pickPoints` scoring function — changes to scoring must be applied here AND kept in sync with `CommunityCard.outcomePoints` and the backend `_pick_series_pts`.
- `MatchupCard` has a `readonly` prop — it is vestigial, PickemBoard never passes it. Do not use it for new features.

**What aligns across all three:**
- `wins_a`/`wins_b` from matchup for pip dots (never `games_a`/`games_b`)
- `getTeamStyle()` for team colors
- Eliminated team dimming: `opacity: 0.75` on the losing team's row after result is set
- `isLocked()` / `isTBD()` from helpers.js

## Scoring

Per series: correct winner = 2 pts, games within 1 = 1 pt (exact = 2 pts), correct stat leader = 1 pt. Cap 5 pts/series.

**Chart-adjacency formula for wrong-winner game length:**
- Correct winner: `dist = abs(pick_games - result_games)` → 0=+2pts, 1=+1pt
- Wrong winner: `dist = abs(15 - pick_games - result_games)` → ≤2=+1pt

**Round multipliers** (actual code values in `ROUND_MULTIPLIERS`): R1×1, R2×4, CF×8, Finals×16.

Scores are recalculated from scratch for all affected users whenever a result is set or cleared (`_recalculate_scores_for_matchup`). Both scoring functions — `_pick_series_pts` (per-pick) and `_recalculate_scores_for_matchup` — live together in `backend/pickem_2026/scoring.py`, deliberately colocated so they stay in sync.

## Matchup management

`game_time` is always **Central Time** (`YYYY-MM-DDTHH:MM`, no tz suffix). `lock_time` is auto-computed as 1 hour before tip-off in UTC. Never set `lock_time` directly — always POST to `/pickem/2026/admin/matchups` with `game_time`. `wins_a`/`wins_b` track live series score (updated via `/pickem/2026/admin/matchups/:id/wins`).

## Stat guide

One-off script per round: `scripts/stat_guide.py`. Fetches NBA API stats, outputs JSON, POSTs to `/pickem/2026/admin/stat-guide`.

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

`scripts/fetch_stat_logs.py` — fetches per-game stats from NBA API and POSTs to `/pickem/2026/admin/matchups/:id/stat-log`. Uses `nba_api` library with per-game date filters (same fetch functions as stat_guide.py). Update `MATCHUPS` dict each round — R2 configs (e5, e6, w5, w6) are current.

## Bracket layout

The 7-column grid is: `[West R1, West R2, West CF, Finals, East CF, East R2, East R1]`. `ACTIVE_COLS` in `helpers.js` controls which columns are expanded vs compressed for each round tab.

## API endpoints

Global, cross-year (`backend/auth.py` / `backend/admin.py`):

| Method | Path | Auth |
|--------|------|------|
| GET | `/me` | session cookie |
| GET | `/auth/login`, `/auth/callback`, `/auth/logout` | — |
| GET | `/admin/users` | admin |
| POST | `/admin/users/:discord_id/admin` | admin |
| POST | `/admin/users/:discord_id/hidden` | admin |
| POST | `/admin/users/:discord_id/ban` | admin |

Pickem 2026 only (`backend/pickem_2026/`), all under `/pickem/2026`:

| Method | Path | Auth |
|--------|------|------|
| GET/POST | `/pickem/2026/picks/me`, `/pickem/2026/picks` | session cookie |
| GET | `/pickem/2026/picks/user/:username` | public (locked only) |
| GET | `/pickem/2026/picks/user/:username/status` | public |
| GET | `/pickem/2026/matchups` | public |
| GET | `/pickem/2026/matchups/aggregate` | public (locked only) |
| GET | `/pickem/2026/stat-guide` | public |
| GET | `/pickem/2026/rosters` | public |
| GET | `/pickem/2026/scores` | public |
| GET | `/pickem/2026/stats` | public |
| POST | `/pickem/2026/admin/matchups` | admin |
| POST | `/pickem/2026/admin/matchups/:id/result` | admin |
| DELETE | `/pickem/2026/admin/matchups/:id/result` | admin |
| POST | `/pickem/2026/admin/matchups/:id/wins` | admin |
| POST | `/pickem/2026/admin/matchups/:id/stat-log` | admin |
| POST | `/pickem/2026/admin/rosters` | admin |
| POST | `/pickem/2026/admin/stat-guide` | admin |
| POST | `/pickem/2026/admin/picks/:user_id` | admin (bypasses lock) |
