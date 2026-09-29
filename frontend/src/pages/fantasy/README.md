# Fantasy pages — guide for design work

What each page shows, where its data comes from, and what's real vs. not built yet — so
design can restyle pages without re-deriving the data plumbing. Backend details live in
`backend/fantasy_2026_27/` and `backend/nba/`; the plan in `/ROADMAP.md`; scoring in
`/FANTASY_SCORING.md`.

## Ground rules

- **Dark mode only.** All colors from `src/theme.css` tokens — no inline hex, one text color
  (`--text`), no dim/gray text; hierarchy from size and weight. (Team colors are data from the
  API, not styling, so they're the one exception.)
- **Pages never compute scores.** The server sends raw stats + `fantasy_points` (+ a
  per-category `breakdown` where useful). Scoring rules come from `GET /scoring`.
- **Every team name** goes through `TeamLink`, **every player / NBA team unit name** through
  `EntityLink` (`components/fantasy/links.jsx`), so links stay consistent.
- Season id is `2026_27` in code/URLs, shown as `2026-27`. NBA seasons in the data layer are `2025-26` style.
- Other sessions edit these files in parallel — stage only your own files when committing.

## Shared building blocks

| File | What it is |
|---|---|
| `components/fantasy/FantasyShell.jsx` | Wrapper every page renders through: top bar (`MainNav`) + sidebar + title/tabs + content. Pages pass `title`, `season`, children. |
| `components/fantasy/nav.js` | The fantasy nav: sections, links, and tab groups (e.g. My Team → Lineup/History/Settings). Add pages here. |
| `components/fantasy/FantasySidebar.jsx` | Renders `nav.js`; admin-only sandbox switcher at the bottom. |
| `components/fantasy/data.js` | `useFantasyApi(name)` fetch hook (applies the admin sandbox; `undefined` = loading, `null` = failed), path helpers, roster slot order, and the **projected** schedule/standings helpers (see "Stand-ins"). |
| `components/fantasy/links.jsx` | `TeamLink`, `EntityLink`. |
| `components/fantasy/TeamIcon.jsx` + `teamColors.js` | Team icon: uploaded logo, else the abbreviation on the team color. |
| `components/fantasy/GameLog.jsx` | Per-player/NBA-team game log + weekly table (used on the player page). |
| `components/shared/MainNav.jsx` | Site-wide top bar (all products). |

## API the pages use (all under `/fantasy/2026_27`)

Endpoints marked *sandbox* take `?scenario=` (admins only; everyone else always gets `live`).

| Endpoint | Returns (key fields) |
|---|---|
| `GET /teams` *sandbox* | Teams sorted by strength: `id`, `name`, `abbreviation`, `color`, `logo_url`, `owner_user_id`, `total_fantasy_points`, `roster[]` (`kind` player/nba_team, `id`, `name`, `position`, `nba_team`, `slot`, `fantasy_points`). |
| `GET /players` *sandbox* | Every draftable player: `id` (NBA player id), `name`, `position` (G/F/C or null), `nba_team`, per-game `games_played`, `minutes`, `pts`, `off_reb`, `def_reb`, `ast`, `stl`, `blk`, `fgm`/`fga`/`fg3m`/`ftm`/`fta`/`tov`, `fantasy_points`, `stats_season`, plus owner fields `team_id`, `team_name`, `owner_user_id`, `slot` (null = free agent). |
| `GET /nba-teams` *sandbox* | The 30 NBA team units: `id` (tricode), `name`, `games_played`, `wins`, `pts`, `opp_pts`, `fantasy_points`, owner fields. |
| `GET /draft` *sandbox* | `order[]` (teams in round-1 order), `rounds`, `picks[]` (`pick`, `round`, team, entity, `slot`, `fantasy_points`, `pool_rank`). |
| `GET /league` *sandbox* | `phase` (pre_draft / post_draft), `slots`. |
| `GET /scoring` | `format` (`best_single_game_per_week`), `rules[]` (`key`, `label` e.g. "FG-", `name`, `points`), `pending` notes. |
| `POST /scoring/preview` | Body: a raw stat line → `breakdown` per category + `fantasy_points`. |
| `GET /weeks?season=` *sandbox* | Fantasy weeks (laid out by the league's settings): `week`, `start`, `end`, `kind` (regular/playoffs), `label`, `calendar_weeks`, `all_star`, `round`. |
| `GET /league/settings` *sandbox* | Commissioner settings: `settings` (`playoff_teams`, `playoff_rounds[]` {`name`, `weeks`}, `cutoff_days`, `fuse_all_star`, `matchup_schedule`), `playoff_byes`, `weeks`. **Pages should read playoff size/rounds from here, not hardcode them** (data.js `PLAYOFF_TEAMS = 6` is a stand-in). Commissioner edits them at `/league-settings` (`PUT /admin/league/settings`). |
| `GET /results` *sandbox* | Real weekly results from box scores up to the league's date: `weeks[]` (matchups with each slot's score), `standings`, `as_of`, `current_week`, `settings`. Used by the Replay page today; the real-matchup pages will switch to it. |
| `GET /schedule?season=&week=` | One fantasy week of real NBA games (`game_date`, `tipoff_utc`, `time_tbd`, `status`, teams, scores, `game_type`) + `team_counts` (games per NBA team that week). |
| `GET /entity/{id}/games?season=` | One player (numeric id) or NBA team (tricode): `games[]` (actual line + `fantasy_points` + `breakdown`, or `projected` for future games), `weeks[]` (per fantasy week: games, played, actual, remaining, projected_total), `projection_per_game`, `projection_basis`. |
| `GET /teams/{team_id}/settings` · `PUT` | `name`, `abbreviation`, `color`, `logo_url`. PUT any subset; owner or admin. |
| `PUT` / `DELETE /teams/{team_id}/logo`, `GET` | Upload (raw image body: PNG/JPEG/GIF/WebP ≤ 512 KB) / remove / serve. |
| `GET` / `PUT /notifications/settings` | Per-person on/off: `injuries`, `ir_reminders`, `trade_offers`, `league_trades`, `claims`, `weekly_recap`, `draft_reminders` (all off by default). |

Site-wide: `GET /me` → `discord_id`, `username` (display name), `handle` (Discord username, used in URLs), `is_admin`, `avatar_url`.

## Stand-ins until real weekly scoring exists

The format is **best single game per week** (see `/FANTASY_SCORING.md`), but weekly matchup
results aren't built yet. Until then `data.js` projects: each team's weekly score =
`total_fantasy_points` (sum of per-game averages), schedule = round-robin, and a fixed
19-week season. Standings, Matchup, Recap, Playoffs, and Home are built on that. Real weeks
(`GET /weeks`) and real game logs exist; switching these pages over is on the roadmap.

## Pages

| Page | Route | Data | State |
|---|---|---|---|
| Home | `/fantasy/2026_27` | teams, players | Real teams/players; matchup numbers projected |
| Standings | `/standings` | teams | Projected records |
| Matchup | `/matchup?week=&team=&view=` | teams | Projected |
| Schedule | `/schedule?season=&week=` | schedule | **Real** NBA schedule, 2022-23 → 2026-27 |
| Scoring | `/scoring` | scoring, scoring/preview | **Real** — rules, format explanation, calculator |
| Players | `/players` | players, nba-teams | **Real** 2025-26 per-game stats |
| Player / NBA team detail | `/players/:id` | players, nba-teams, draft, entity games | **Real** stats + game log + projections |
| Draft Room | `/draft` | draft, players, nba-teams | Real order/pool; making picks not built |
| Draft Recap | `/draft/recap` | draft | Real (from the draft) |
| Trades | `/trades?with=` | teams | Real rosters; sending trades not built |
| Transactions | `/transactions` | draft | Draft picks only (adds/drops/trades not built) |
| My Team / any team | `/team`, `/team/:ownerId` | teams | Real roster; moves not built |
| Team Settings | `/team/settings` | teams, settings endpoints | Backend ready (save, logo, color, notifications); page hookup pending |
| Team History | `/tenure?team=` | draft | Real (draft only so far) |
| Playoffs | `/playoffs` | teams | Projected seeds |
| Recap | `/recap?week=` | teams | Projected |

Not built anywhere yet: live drafting, adds/drops/waivers, trade sending, the notification
bell, weekly matchup results from real games.

Admin **Site Map** (`/admin/sitemap`, user menu) is generated from the code on every build —
it shows every page, its links, the data it reads, and any broken links.
