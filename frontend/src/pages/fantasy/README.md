# Fantasy pages

All 13 pages here are skeleton-first: real routing and navigation, minimal/no visual
design pass yet (see `FantasyShell`'s "SKELETON" banner). This doc tracks what each
page is *expected* to do long-term, what it actually does today, and the shared
components it's built from — so future work knows what's real vs. placeholder
without re-deriving it from the code.

## Shared building blocks every page uses

- **`components/fantasy/FantasyShell.jsx`** — the wrapper every page renders through.
  Owns the top bar (`MainNav`: home link, season selector, user dropdown) and lays
  out `FantasySidebar` + page content beneath it. A page only needs to pass `title`
  and `season` and render its own content as `children` — it never assembles its
  own chrome.
- **`components/fantasy/FantasySidebar.jsx`** — product-specific nav only (Home,
  Standings, Matchup, Players, Draft, Trades, Transactions, Team, Team History,
  Playoffs, Recap). No home link, no season selector, no user controls — those
  live in the top bar via `MainNav`, not here.
- **`components/shared/MainNav.jsx`** — shared site-wide across pickem, fantasy,
  landing, and account; not fantasy-specific, documented in the shared components
  themselves, not repeated here.
- Season identifier is `2026_27` in code/routes, displayed as `2026-27` — see the
  naming convention note in the backend (`backend/fantasy_2026_27/`).

## Data model (backend/fantasy_2026_27/)

- **Roster format:** 2 Guards (PG/SG), 2 Forwards (SF/PF), 2 Centers, 2 NBA Teams, 3 Flex (any player or NBA team) = 11 slots. Defined once in `logic.py` (`SLOTS`).
- **Draftable pool (fake for now, shared by every sandbox):** 80 players (per-game GP, MIN, PTS, off/def reb, AST, STL, BLK) and 30 NBA teams as draftable units (GP, wins, pts for/against). Fantasy points use placeholder formulas in `logic.py` until real scoring is decided.
- **Fantasy teams:** one per visible pickem user, owned by their Discord ID. "My Team" = the logged-in user's team.
- **Sandboxes:** `live` (the real league state, starts undrafted), `test_pre` (everything undrafted), `test_post` (simulated snake draft filling all 11 slots). Test sandboxes never touch live. Admins switch sandboxes and reset test ones from the bottom of the fantasy sidebar; everyone else always sees live.
- **Endpoints** (all take `?scenario=`, ignored for non-admins): `GET /players`, `/nba-teams`, `/teams`, `/league`; admin `POST /admin/scenario/{test_pre|test_post}/reset`.

## Links and data

- Every team name renders through `TeamLink` → `/fantasy/2026_27/team/:ownerId`; every player / NBA-team-unit name through `EntityLink` → `/fantasy/2026_27/players/:id` (`components/fantasy/links.jsx`).
- Pages fetch with `useFantasyApi("teams" | "players" | "nba-teams" | "draft")` (`components/fantasy/data.js`), which applies the admin sandbox.
- No real weekly results yet: weekly score = roster's per-game fantasy points total, schedule = round-robin (`weekPairings`), records/standings via `standingsThrough`. Swap these for box-score data later.
- Not built yet (shown as disabled or empty): making draft picks, adds/drops, sending trades, saving team settings.
- Admin **Site Map** (`/admin/sitemap`, in the user menu) is generated from the code by `scripts/gen-sitemap.mjs` on every dev/build — check it for dead links and pages that read no data.

## Styling

Dark theme only, from `src/theme.css` tokens — no inline hex colors, one text color (`--text`), no dim/gray text. Hierarchy comes from size/weight.

## Page-by-page

All pages read real (dummy-pool) data for the selected sandbox; "projected" means per-game averages standing in for weekly results.

- **Home** — top-5 standings, your week 1 / week 2 matchups (projected), best free agents, your roster.
- **Standings** — records and Pts For/Against through a chosen week (projected), playoff line, links to that week's Recap and Matchups.
- **Matchup** — `?week=&team=&view=`: slot-by-slot lineup comparison, or the weekly top-scorer leaderboard.
- **Players** — tabs My Team / Drafted / Free Agents / By NBA Team / NBA Teams; names link to **PlayerDetail** (`/players/:id`: per-game stats, owner, draft slot, NBA teammates).
- **Team** — `/team` (yours) or `/team/:ownerId` (anyone's): roster by slot, rank, links to history/settings/trade. 11 slots all count; no bench.
- **DraftRoom** — real snake order, who's on the clock, best available, picks so far. Making picks isn't built.
- **DraftRecap** — steals/reaches (pick vs. pool rank) and grades (team total rank).
- **Trades** — `?with=`: real rosters to pick from; sending isn't built, so pending/history are empty.
- **Transactions** — feed of draft picks (adds/drops/trades don't exist yet).
- **TeamSettings** — prefilled with your team; saving isn't built. Abbreviation rules undecided.
- **Tenure** — `?team=`: every player on a roster and how they joined (only the draft so far).
- **Playoffs** — top-6 seeds from projected final standings, byes for 1 & 2.
- **Recap** — `?week=`: team of the week, blowout, closest game, standings movers (projected).

## What's genuinely next

Real weekly results from daily box scores (2025-26 replay first) replace the projected weekly score everywhere via `data.js`, then the missing actions: live draft picks, adds/drops, trades, settings saves.
