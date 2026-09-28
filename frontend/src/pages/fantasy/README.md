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

## Real vs. mock data, as of this write-up

Only **Players** and **Standings** (partially) pull real data, from the new
`backend/fantasy_2026_27/` module (dummy player stats: minutes, pts, games played,
off/def rebounds, ast, stl, blk, seeded across 10 dummy teams + a handful of free
agents; fantasy points computed server-side with a placeholder formula since the
league's real scoring categories aren't decided yet). Every other page below is
still fully hardcoded mock arrays in the component file itself.

## Page-by-page

**Home** (`Home.jsx`) — the landing view once inside fantasy: a league-wide pulse
(top standings, this week's matchup, next week's opponent, suggested pickups,
your own roster) rather than just a roster page. *Mock.* Components: none beyond
`FantasyShell`; plain `<table>`/`<div>` markup and a `react-router-dom` `Link` to
Standings/Matchup/Players/Team.

**Standings** (`Standings.jsx`) — league table with a Regular Season / Playoffs
Bracket tab toggle, a week picker, and a link into Recap. *Partially real:* `PF`
column is real (`GET /fantasy/2026_27/teams`, summed from actual rostered dummy
players); Record/PA and "this week's results" stay mock — no weekly matchup
schedule exists yet. Components: `Fragment`/`useState`/`useEffect` only, no
sub-components; fetches directly with `fetch`.

**Matchup** (`Matchup.jsx`) — head-to-head box score for a week, with a toggle
between the lineup-vs-lineup view and a weekly leaderboard (whoever scores most
that week wins a side prize). *Mock.* No sub-components.

**Players** (`Players.jsx`) — doubles as stats research and free agency/waivers;
filter tabs (My Team/Drafted/Free Agents/By NBA Team) plus search. *Real*, the
one page fully wired: fetches `GET /fantasy/2026_27/players`, filters/sorts
client-side by real `team_name`/`nba_team` fields. "My Team" is hardcoded to
"Baseline Bandits" since there's no real user↔team link yet — noted as a
follow-up, not solved here. No sub-components.

**DraftRoom** (`DraftRoom.jsx`) — live draft board: snake order strip, pick
clock, available players (projected points + historical avg, no ADP), your
queue, recent picks. *Mock — and the mock data itself is disconnected from the
real dummy players in `fantasy_players`.* Would need real work to become
functional (an actual draft-state machine), not just a data-source swap. No
sub-components.

**DraftRecap** (`DraftRecap.jsx`) — post-draft steals/reaches + per-team letter
grades. *Mock.* Already flagged in an earlier pass as "not quite right,"
deprioritized. No sub-components.

**Trades** (`Trades.jsx`) — propose-trade builder (starts empty, player-for-player
only, no picks), pending trades (all public, not just yours), trade history.
*Mock.* No sub-components.

**Transactions** (`Transactions.jsx`) — league-wide activity feed with filter
pills and a rolled-up weekly summary. *Mock.* No sub-components.

**TeamManagement** (`TeamManagement.jsx`) — the actual lineup/roster management
page (start/bench players) — distinct from TeamSettings, which is branding only.
*Mock.* No sub-components.

**TeamSettings** (`TeamSettings.jsx`) — team name, abbreviation, picture, and
notification toggles (no email — Discord/in-app only). Abbreviation
auto-generation/collision handling is explicitly unresolved (noted inline in the
component). *Mock.* No sub-components.

**Tenure** (`Tenure.jsx`) — "team history": every player who's ever been on this
team's roster and when, an alumni record that's meant to grow across future
seasons. *Mock,* though the display strings deliberately use the hyphenated
`2026-27` form (see naming convention) even though nothing else here is real yet.

**Playoffs** (`Playoffs.jsx`) — top-6-seed bracket, byes for 1 & 2, drawn as plain
bordered boxes (no SVG bracket lines yet, unlike pickem's bracket component).
*Mock.* No sub-components.

**Recap** (`Recap.jsx`) — one template reused for both weekly and season-end
recaps (team of the week, biggest blowout/closest matchup, standings movers, a
stat ticker); takes `?week=` as a query param from Standings' Recap link. *Mock.*
No sub-components.

## What's genuinely next, functionality-wise

The vertical slice that's real today (player stats → roster assignment → team
total) is the seam to pull on next: Matchup and DraftRoom are the two pages most
worth connecting to the same `fantasy_players`/`fantasy_rosters` tables, since
unlike Standings they currently reference a completely disjoint set of mock
player names/stats rather than the real dummy data.
