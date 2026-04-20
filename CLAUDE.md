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

Required env vars: `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_REDIRECT_URI`, `SECRET_KEY`, `DATABASE_URL`, `ADMIN_DISCORD_IDS` (comma-separated Discord user IDs).

## Architecture

**Single-file backend** (`main.py`) — FastAPI app serving both the API and the React SPA. In production, `frontend/dist/` is built into the Docker image and served by the catch-all route. In dev, Vite proxies API requests to the FastAPI server.

**Frontend** (`frontend/src/`) — Vite + React 19 SPA, no state management library.

- `App.jsx` — router: `/` → CommunityBoard, `/picks/me` and `/picks/:username` → PickemBoard, `/admin` → AdminPage
- `pages/PickemBoard.jsx` — main pick submission UI; handles own picks (editable) vs others' (readonly after lock). `/picks/me` redirects to `/picks/:loggedInUsername` via Navigate.
- `pages/CommunityBoard.jsx` — aggregate view showing community pick distribution after lock
- `pages/AdminPage.jsx` — admin CRUD for matchups, results, wins, stat logs, rosters
- `components/MatchupCard.jsx` — the interactive card for a single series (pick winner, games, stat leader; shows series odds via `computeSeriesProbs`)
- `utils/helpers.js` — all shared constants and pure functions: `groupMatchups` (7-column bracket layout), `computeWidths` (responsive column sizing), `computeSeriesProbs` (DP series probability), `TEAM_COLORS`, lock/TBD helpers

**Database** — PostgreSQL. Schema is created/migrated inline in `init_db()` at startup using `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. No migration framework.

**Auth** — Discord OAuth2 → signed cookie via `itsdangerous`. Admin status is determined by whether the Discord ID is in `ADMIN_DISCORD_IDS` env var, re-evaluated on every login.

## Scoring

Per series: correct winner = 2 pts, games within 1 = 1 pt (exact = 2 pts), correct stat leader = 1 pt. Cap 5 pts/series × round multiplier (R1×1, R2×2, CF×4, Finals×8). Scores are recalculated from scratch for all affected users whenever a result is set or cleared (`_recalculate_scores_for_matchup`).

## Matchup management

`game_time` is always **Central Time** (`YYYY-MM-DDTHH:MM`, no tz suffix). `lock_time` is auto-computed as 1 hour before tip-off in UTC. Never set `lock_time` directly — always POST to `/admin/matchups` with `game_time`. See `readme.md` for curl examples and first-round seeding data.

## Bracket layout

The 7-column grid is: `[West R1, West R2, West CF, Finals, East CF, East R2, East R1]`. `ACTIVE_COLS` in `helpers.js` controls which columns are expanded vs compressed for each round tab.

## API key endpoints

| Method | Path | Auth |
|--------|------|------|
| GET | `/me` | session cookie |
| GET/POST | `/picks/me` | session cookie |
| GET | `/picks/user/:username` | public (locked only) |
| GET | `/matchups` | public |
| GET | `/matchups/aggregate` | public (locked only) |
| POST | `/admin/matchups` | admin |
| POST | `/admin/matchups/:id/result` | admin |
| DELETE | `/admin/matchups/:id/result` | admin |
| POST | `/admin/matchups/:id/wins` | admin |
| POST | `/admin/matchups/:id/stat-log` | admin |
| POST | `/admin/rosters` | admin |
