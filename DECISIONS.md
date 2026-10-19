# Decisions

Every call the commissioner has made about how the league and the site work, with the date. **Read this before
changing behavior.** If a decision changes, edit its entry (new date, what changed) — and the check that protects it
in the same commit. "Protected by" names the automated check (`tests/`); none = only this page remembers it.

---

## Matchup schedule

**2026-10-14 · Balanced by 3-season win % is the default** (League Settings → Season → Matchups; round robin is the
other choice). When the draft completes, the regular-season matchups are set so every team's opponents average about
the same strength: a manager's average win % over the last 3 seasons on record, a missed season = .400, new = .400;
byes as even as possible, extra byes on the strongest teams. Past seasons are data the commissioner edits (League
Settings → Past seasons, seeded from the 2023-24 / 2024-25 / 2025-26 standings); "Balance every week" reruns it. *Protected
by:* tests/integration/test_schedule_history.py, tests/test_schedule_balance.py.

## Player page

**2026-10-14 · Player pages are back** (they were pop-up only from 2026-10-11): `/players/:id`, built from the approved
design — card front · stats panel · card back, sections printed on the panel's frame (Overview · Game Log ·
Transactions · Availability · Extras = the LED shot chart, 2026-27 only like the stats panel). For this year's pool: the starting pool is the 616
players rostered when it was built (preseason rosters with two-ways and camp invites); it never shrinks, and anyone who
plays a game joins it. NBA teams (TM) get the same page and pop-up (2026-10-15): plain team-color frame, logo, the 7 TEAM scoring parts in place of the wheel; sections Overview, Game Log, Transactions. Card tier by career honors: MVP > All-NBA > All-Star > All-Defense > Plain. The stats panel shows MAX and AVG only (FLOOR / CEILING dropped 2026-10-15: they mostly repeat each other); the draft list keeps its MAX low – MAX high bar. The stats panel and the wheel show this season only (2026-27), blank until he plays; past seasons live in the tables below. Every percentile
counts only players with **20+ games, 20+ MPG and 500+ total minutes** that season (2026-10-15; was 10 / 10 / 250). Games
and minutes scale with how much of the season has been played (a quarter in: 5 games, 125 minutes); MPG doesn't.
Projected percentiles rank against the top 120 players by projected MAX (who get drafted and picked up), so a
100th-ranked player sits near the bottom. *Protected by:*
tests/integration/test_player_page.py.

## League rules

**2026-10-08 · Auction all-in is allowed.** A team can spend everything on one player. Once it can't afford the
minimum bid it's done; its roster is only who it won — nothing is filled in. Not a bug, don't flag it.
*Protected by:* `test_auction_and_pool.py` (no money / full roster → no bidding).

**2026-10-08 · Max bid = all the money you have left.** "Safe max" (keep the minimum for each other open spot) is
guidance only. *Protected by:* `test_max_bid_is_everything_left`.

**2026-10-08 · Minimum raise: a % of the high bid, rounded up, at least $1** (league setting, default 4%).
*Protected by:* `test_minimum_raise`.

**2026-10-08 · Add/drop is instant, through a review step.** Adds and drops collect into Moves, then a review pop-up
checks the roster after the moves is legal (no more players than spots, everyone fits a spot; going under is fine).
*Protected by:* integration `test_cannot_add_someone_elses_player_or_overfill`.

**2026-10-08 · Locks only affect moving players between spots (Roster page).** Any player can be dropped, locked or
not. A week's lineup is etched as each player locks (5 min before his first game; the test league treats the whole
game day as played): dropped after locking → still counts that week; added after his lock → counts from next week.
*Protected by:* `test_lineup_lock.py`, integration `test_dropped_after_his_lock…`, `test_added_after_his_lock…`.

**2026-10-09 · Waivers: 2 days.** A drop is real once the player was drafted or locked into one of your weekly
lineups; a real drop puts him on waivers for 2 days (live: 48 hours; test league: 2 days of its clock). Nobody can
just add him — not even the team that dropped him. Claims (optional drop if it wins) settle when the 2 days are up:
the team lowest in the standings wins (worst record, then fewest points). Unclaimed → free agent. Add-then-drop before
any lock isn't a real move: it leaves the log and he's a free agent straight away. Free agents are instant.
*Protected by:* integration `test_real_drop_goes_to_waivers…`, `test_add_then_drop_before_any_lock…`.

**2026-10-15 · Resetting the draft clears its recap and Autopick switches.** Draft Grades (and any week recaps) go with
the rosters; Autopick switches are reset. Draft queues and the draft order stay (2026-10-17: queues are kept so a reset
for someone running late doesn't wipe everyone's queue; briefly cleared 2026-10-15–17). *Checks: tests/integration/test_draft_reset_recap.py.*

**2026-10-15 · Chess-clock bidding.** A lot opens with the full bid clock; each bid adds the league's "Time added per
bid" (default 3 seconds) to what's left, never past the full clock (it used to restart in full on every bid). *Checks: tests/test_draft_clock.py.*

**2026-10-15 · End-of-draft nomination time.** Once no team still drafting has more than 25% of the starting budget left ($50 of $200), nominations use
the league's "End-of-draft nomination time" (default 15 seconds) instead of the normal one. *Checks:
tests/test_draft_clock.py.*

**2026-10-17 · Randomize order shuffles on screen.** Everyone watching the draft lobby sees ~7 seconds of the teams shuffling before they land in the new order (it plays once, only right after the commissioner presses Randomize).

**2026-10-09 · Every draft start has a warm-up (20 seconds since 2026-10-15; was 10).** The draft is on (everyone's pulled into the room) but no clock runs and no pick, nomination or bid counts until it ends; the page shows "The draft starts in 0:20"; an auction also shows a short Rec bid card (what it is, when it changes, what it doesn't do). *Checks: tests/integration/test_draft_warmup.py.*

**2026-10-09 · Draft room live updates.** The server pings every open draft room the moment the draft changes (a click or a clock running out) and each page reads its own copy; a slow poll stays as a backup (backend/fantasy_2026_27/live.py).

**2026-10-09 · When a draft clock runs out, the next starts 1 second later.** The page holds 0:00 for that second, then shows the new clock from its full time. Cosmetic: the clock that ran out isn't extended and nothing can be done in the gap.

**2026-10-09 · No adds, drops or claims until the draft is done** (Players page shows no buttons; the server refuses them).

**2026-10-10 · Bidding opens in draft order.** After a nomination, the next team in the draft order can bid right away, then each team after waits 0.25 s more (league setting "Bidding opens in order", 0–1 s, 0 = all at once). The head start rotates with the nominator. Bids also can't land before the lot opens. *Checks: tests/test_bid_opens.py.*

**2026-10-10 · Open pages reload themselves when a new version goes live** (checked every minute, when a tab comes back into view, and when the draft room reconnects after a restart; not while someone's typing).

**2026-10-09 · Auction bid bar: one button (the minimum raise), anything else typed** and refused outside minimum raise … most you can bid. No double raise, no All-in button.

**2026-10-10 · Draft Value (the recap's second draft tab, labeled "Drafting value based on the actual results of the 2026-27 NBA season"; the first is "Draft Grades", labeled "Draft grades based off the projected value"): actual points added, and a dropped player only counts while he was yours** (provisional; not built yet). Each pick: draft-day projection next to actual points added a week; color = actual − projected. A drafted player who's dropped (or, later, traded) credits the drafting team only through the week he left ("dropped Wk 4 · +2.1 a week, 4 weeks"); what he does afterwards counts for no one's draft (a pickup is a waiver move). "Biggest regret" callout = the dropped player who did most since — shown, never graded.

**2026-10-10 · Draft grades are in fantasy points — the only metric** (built 2026-10-11: `recap.py`, frozen the moment the draft completes; test leagues preview from their rosters. *Protected by:* `test_recap_draft.py`). Points added = a player's projected weekly MAX − the best player still free at his position after the draft (Jokić 45 vs 20 → +25 a week; 23 / 24 / 28 → +3 +4 +8 = +15); a team's is the plain sum of its starters'. The team list is "Team grades", never "Standings" (standings are real wins and losses). Price / pick is context only. The cell's color = points added − what that resource usually buys at that moment, also in points (auction: the money actually spent on the rest of the draft — not money that ended up unspent, which is its own ding — ÷ the points bought with it, on a curve — now 1.25 — so a big package can cost more per point, but more points always grades higher; snake: what that pick number normally gets — the Nth-best player by projection — so a better player falling to you is green (Wembanyama at 3 behind a Jokić / Wembanyama / Dončić ranking) and pick 1 can only be 0 or negative). Both drafts use the same yardstick: what that resource normally gets. Awards show the top 3 (#1 in full, #2–3 brief) and always lead with the player's value (points added a week); money or pick only explains it: Best buy (worth − paid; "paid $18 · worth $44"), Best buy under 10% of the budget (by value), Deepest bench (the team's two bench-spot players by value, shown by name), Biggest overpay (paid − worth; "$90 usually gets +10.3"), Worst drafted player (fewest points added; "vs J. Embiid"); snake: Best pick / Best late pick / Biggest reach ("R3·5 usually gets +1.5"). Roster cells: value, then "$84 vs fair $86" (auction) or vs pick (snake). The team table is "Draft Value (Projected)", no rank numbers. Unspent money is a separate ding. A 50-auction test found no curve clearly better than another (+0.41–0.48 agreement with projected standings).

**2026-10-10 · League activity (Home) shows impactful moves, not the latest ones** (provisional; the value may switch to draft value later). Only moves that happened: a real drop shows when it's made; an add shows once the player locks into the lineup. One entry per team per week (lock to lock), its net change: players who came and went inside the week never appear (drop Jokić, add Edey, swap to Capela, then CHA → "− Jokić / + CHA"). Rank = the biggest value among the players in the entry, not the sum (nobody for a big name = big; nobody for nobody = nothing; Jokić for Wembanyama isn't double). A player's value = PROJ MAX blended with his actual MAX over his last 4 weeks *before the move's week* (1/6 more actual per earlier week) — frozen once the week starts, so later games never re-rank an old move. Every entry halves at the same moment, each time a new week starts (weeks since its week), so two moves' relative weight never changes (an old move never jumps a newer one); only new moves slot in. top 6 show, newest first. The draft is one entry (its three biggest picks). The impact number is never shown; it may also feed the weekly recap. Top 15 show. *Checks: tests/integration/test_activity.py.*

**2026-10-09 · Draft picks count as transactions** (they're entries in the Transaction Log).

**2026-10-09 · The draft pool only holds players / teams that fit at least one spot** under the league's roster
rules. *Protected by:* `test_pool_only_holds_entities_that_fit_a_spot`.

**2026-10-09 · Schedule: even round robins.** Set automatically, every team plays exactly once a week (odd leagues:
one bye a week, spread evenly); every pair meets about equally often. The commissioner can set any week by hand (League Settings → Matchups: a team × week grid of opponents, hand-set weeks underlined; click a week to edit it).
*Protected by:* `test_schedule.py`.

**2026-09-28 · Weekly lock:** rosters lock 5 minutes before each player's first game of the fantasy week.

**2026-09-28 · Trades:** no review, no veto. Deadline = the lock of the last regular-season week (confirm).

**2026-09-28 · Notifications:** in-site only, every category off by default.

**2026-10-11 · A 2-week playoff round is two legs:** each calendar week is its own week (its own lineup lock and best
game) and the round's score is the two legs added up — so the second week still matters. The All-Star break is the
opposite: two calendar weeks fused into ONE week (one best game). *Checks: tests/test_auto_playoffs.py.*

**2026-10-11 · Automatic playoffs (League Settings → Playoffs → Automatic, on by default):** fewer than 4 teams → a 1-week final; 4–6 → top 4 (Semifinals 1 week, Championship 2 weeks); 7+ → top 6 (Quarterfinals, Semifinals, Championship 2 weeks; top 2 seeds skip the first round). Counted from the teams in the league (none yet → the team limit). Off = set by hand. *Checks: tests/test_auto_playoffs.py.*

**2026-10-09 · IR.** IR spots are a league setting (0–3, default 1), extra on top of the roster (not drafted, never score). Only a player with a red or yellow dot (Out / Out For Season / Day-To-Day) can move there, and only after a confirm pop-up. Moving in locks him on IR for the 4 weeks after the current one (before the season: through Week 4): no moves, no drop. **2026-10-11:** once his last IR week is under way, he can be moved (or dropped) for the next week — e.g. IR in Week 1 → frozen through Week 5; during Week 5, looking at Week 6, he's free for Week 6, and Week 5 stays IR in the history. *Checks: tests/integration/test_ir.py.* **Trades: maybe.**

**2026-10-09 · Players traded mid-season showing their old NBA team until they play for the new one is fine.**

**2026-10-11 · Devices (Account page): every login is listed and can be logged out.** The device name comes from the page itself (an iPhone or iPad in desktop mode claims to be a Mac, and Firefox / Chrome on iOS claim to be Safari). Each login is a server-side record (device from the browser, Discord or phone code, when, last active); the cookie points at it, so "Log out" on a device ends it on that device's next request (checked at most a minute late). "Log out everywhere else" keeps this one. Logins from before 2026-10-11 aren't listed but still expire on their own date. *Checks: tests/integration/test_devices.py.*

**2026-10-11 · Log in on your phone: a QR code from a logged-in computer** (account menu → "Log in on your phone"). The code is a one-time link (10 minutes, one use); it opens a confirm page and is only spent when you press Log in, so link previews and scanners can't burn it. Same session as Discord login. No Discord bot or server (the commissioner has none; bots can only DM people in a shared server). Logins last ~10.5 months (320 days). *Checks: tests/integration/test_phone_login_links.py (once, expiry, logged-in only).*

**2026-10-09 · No commissioner "are you sure" safeguards** (e.g. nominating for whoever's up). Instead: a list of
features to hide / strip back / lock behind higher permission levels.

## Scoring

**Scoring rules are data** (`scoring.py`; per league). A player's week = his best game; an NBA team's week = its best
game (both "best_game" today). *Protected by:* `test_scoring.py` (recomputes 10 player + 3 team games from the current
rules — change the rules and the checks follow).

**2026-10-08 · Clutch: +2 per clutch point** (3 total for a clutch point, with the point itself).

**2026-10-09 · NBA teams, points allowed: +1 per point under 125, only down to 100 (at most +25), then +5 under 100.**
TEAM draft 7 bonuses (commissioner's cutoffs 2026-10-08): fast break ≤12, paint ≤40, 15+ turnovers forced, glass +10.

**2026-10-11 · NBA team bonuses worth more the rarer they are:** 15+ turnovers +2 (48% of games), fast break ≤12 +3
(37%), paint ≤40 +4 (21%), glass +10 +5 (10%). Projections rebuilt (OKC PROJ MAX 33.6 → 35.9; order unchanged).

**When scoring rules change, rebuild:** player + team projections and team curves (`scripts/build_projections.py --post`),
then '23–'26 history (`POST /admin/history/build`); `scripts/check_site.py` flags anything missed.
*Protected by:* `test_version_stamp_follows_the_rules` + the check-up (GET /admin/health).

## Win probability

**2026-10-10 · Showing a chance (win %, 1+ Game %): the two sides always pair up.** Exact 0 / 100 → "0%" / "100%"; above 0 but under 1% → "<1%" with the other side ">99%"; otherwise whole numbers adding to exactly 100 (never 99 or 101). A 0.9% chance never reads 0% or 1%. One helper: `winText` in frontend/src/components/fantasy/teamWeeks.js.


**2026-10-09 · Simulated, back-tested.** The rest of the week is played out thousands of times: each starter keeps his
best game so far, plays each remaining game with his chance to play (0 if the injury report has him out, else his
share of his team's last 20 games), each game drawn from his own game scores. NBA-team spots likewise. Opponent
strength and week-to-week form were tested and left out (no gain). Back-test on 2025-26: average miss 0.078 vs the old
projected-gap method's 0.145 (`WINPROB.md`, `scripts/backtest_winprob.py`).
*Protected by:* `test_winprob.py` (0–100%, sides add to 100%, decided weeks exact, can't-catch-up = 0, more lead / games
never hurt, out games count for nothing, identical teams ≈ 50%, calibrated on made-up weeks).

**2026-10-11 · Weekly recap (built):** a tab per finished regular week, frozen when first built. Best / worst team,
biggest / closest win, players of the week (best starter at G / F / C / TM; a flex starter competes at his own position),
best free agents (top 4, only if they beat a starter), versus projection (frozen weekly projection scaled by games
played), optional awards only when they qualify — Improbable win (winner under 25% before some day), Buzzer Beater
(behind after Saturday, won Sunday, no starter whose only game was Sunday), Left on the bench (one team), Pickup of the
week (an add that beat the player he replaced) — then standings with games behind over the last 8 weeks. `recap.py`.
*Protected by:* `test_recap_week.py`.

**2026-10-11 · Recap snapshots are saved, not rebuilt:** each matchup's win probability before every day's games
(3 AM job, plus on boot; first snapshot of a day kept, none once the day's first game tips) and each week's projections,
frozen when the week starts: per-game mean = preseason PROJ AVG blended with the season so far by games played (the
one rule, "Weekly projections" 2026-10-18), scaled at recap time by games actually played (0 games → 0). `snapshots.py`.
*Protected by:* `test_recap_snapshots.py` (unit + integration).

**2026-10-11 · Free-agent advisor (designed, not built):** two levels — better player (rest of season: streak-aware
level × availability; an injured star keeps his level, never a drop) and better this week (expected best game with next
week's games, +2 or more). Shown only to teams at least 3.5 games behind the leader. Lives on the Roster page (redesign
first). Study: PROJECTIONS.md "Free-agent study".

## Weekly projections

**2026-10-18 · Set in stone: projections blend into what he's actually done, by games PLAYED** (replaces the
2026-10-17 calendar rule, +25% a week). A week's projection = the projection model's expected best game for the games
his team has left, weighted by his chance of playing each (availability), never below his best this week. Every game
he plays this season moves 1/14 of the weight from the preseason model onto his own games; after 14 games it's all his
own games. Weeks passing alone change nothing: a player out injured has no new games, so his projection stays the
preseason one. One rule (`projections.blend` / `season_weight`) for every blended number: the week total, the number
under each game on Roster (preseason PROJ AVG → his season average; it used to be his raw last-season average), NBA
teams the same way, and the recap's frozen weekly projection. No model (test leagues): his own game scores.
*Protected by:* `tests/integration/test_week_projection.py` (week-1 games already count; no games = no change in week
3), `tests/test_recap_snapshots.py`.

## The draft record

**2026-10-17 · The draft is kept for good.** Every pick is written to a permanent record (fantasy_draft_picks) when it's
made; drops and trades never touch it (they used to delete the roster row that carried the pick). Draft results and
Draft Grades read from it. The three picks lost to drops on draft night were restored from a copy saved during the
draft. *Checks: tests/integration/test_draft_reset_recap.py.*

## Trades

**2026-10-17 · Trades go through the Trades page only, and the commissioner approves them.** A team proposes (players
out, players in, its own drops); the other team accepts (with its drops) or declines; the proposer can cancel. Both
rosters must end up legal (same rule as add/drop checkout) when sent, when accepted and again when the commissioner
approves; nothing moves until approval. Everyone sees every trade. Logged as adds / drops "via trade". A trade's drops happen only on approval. A player locked on IR through week N can't be traded until week N (the next roster lock is his first free week); counteroffers mark the original Countered. *Checks:
tests/integration/test_trades.py.*

## One truth per fact

**2026-10-18 · Every fact has one source; every page agrees (DATA.md).** Positions and NBA teams come from the season
pool, copied to the old player table by `truth.sync` (startup, any pool change, nightly; real trades move a player's
NBA team to his latest game's team). Projections shown anywhere use `shown_max`. Ownership and spots come from the live
rosters; the draft from its permanent record; team identity from `fantasy_teams`. *Checks:*
`tests/integration/test_one_truth.py` (CI) and `scripts/data_audit.py` (run by `check_site.py` after every deploy).

## Positions

**2026-10-17 · One position per player: the season pool's (role-based).** fantasy_players kept older G/F/C for 134
players (the pool load skipped existing rows), so seating, lineup rules and the transaction log disagreed with the
pages. A league vote (2026-10-17) kept the role-based positions; loading the pool now overwrites the position and the
commissioner's `reseat` draft action syncs every position from the pool and re-seats each auction team's buys. *Checks:
tests/integration/test_position_sync.py.*

## Logins

**2026-10-17 · Commissioner login links.** For a member who can't get into Discord (on his phone, forgot his password),
the commissioner can make a one-time login link for him (`POST /admin/users/{discord_id}/login-link?hours=12`): whoever
opens it is logged in as that member. One use, up to 24 hours, the same "Log in as …?" confirm page as the phone link
(previews can't spend it), never for a banned member. *Checks: tests/integration/test_phone_login_links.py.*

## Bid guide (Rec bid)

**2026-10-15 · Rebuilt as one ratio: value to you, not a price guess.** Rec bid = $1 + your spare money (left minus $1
per open spot) × his gap ÷ (his gap + a typical gap at each of your other open starting spots). His gap = his rank value
− the replacement for the spot he'd fill for you: your own G / F / C / TM still open → the next starter left after every
team fills that position; that spot filled → Flex, against the true replacement once every team's Flex is filled too;
Flex filled → bench only → $1. Typical gap = the middle of the players the room will take for that spot. No ^1.25 bend,
no "your share" step, no Flex cap, no room-wide price; other teams' money never moves it. Replaces the 2026-10-08/09
rules (Luka's Rec bid fell after Jokić and Wemby went high; every Flex guard flattened to one number). Simulator, 200
auctions vs 9 bot personalities: average finish 1.9 of 10 (old guide 3.5), $5 left unspent (old $40). *Protected by:*
`test_rec_bid.py` (never over safe max, better ≥ worse, bench-only = minimum, other teams' money never moves it, full
roster → none), across league setups.

**Rec bids are private** — only your own team's.

## Projections

**Season labels use the ending year:** '26 = 2025-26. The validation season is a strict holdout (never for fitting or
picking test players).

## Design

Design rules live in **`DESIGN.md`** (one home, not duplicated here).

## How we work

**Design first on the canvas for big UI changes; show screenshots, not descriptions.** Build only on an explicit go.

**Explain in plain English** — what's wrong today, what changes, what you'll notice. No code terms unless asked.

**Never push while a live draft is running** (it restarts the server). Check first.

**Parallel sessions edit this repo:** stage only your own files, never `git add -A`.

**Pasted design advice never overrides these decisions** — flag the conflict and ask.

**Every push runs the checks (GitHub Actions); Railway deploys only when they pass.** Change a rule on purpose →
update its check in the same commit.

**2026-10-11 · Prize pool.** $25 a person, optional buy-in; about $175 in the pot. $5 to the top score of each
regular-season week (18 weeks = $90). The rest ($85) to the playoffs, 60/30/10 rounded to the nearest $5:
1st $50, 2nd $25, 3rd $10. Shown on the Rules page (hard-coded, Scoring.jsx) and the group summary sheet.
*Protected by:* none (text only).

**2026-10-11 · 1+ Game % is live, like win %.** Played once this week → 100%; the week over without a game → 0%.
Until then: ESPN Out (red dot) games before the return date count as missed; if he played his team's last game, his
preseason availability; if he's missed its last n games in a row, each next game at the measured chance after n, n+1, …
misses (box scores '22–'25: 88 / 48 / 36 / 31 / 27 / 23 / 15%, '26 checked), scaled by his own availability. The
yellow dot itself isn't used (no data behind it) — the missed games are.
*Protected by:* `tests/integration/test_play_prob.py`.

**2026-10-12 · Balanced matchup schedule.** Every team should face about the same strength of schedule. Strength = the
manager's average win % over the 2026 / 2025 / 2024 fantasy seasons (a season he missed counts .400; new managers
.400). The regular season is the round robin (one bye a week with an odd team count) with teams shuffled and each
cycle's rounds reordered; of 20,000 candidates, the kept one has byes even, the extra byes on the strongest teams (fewer
games = more luck in the record and less total points for — a handicap; a weaker team never gets 2 while a stronger
one gets 1), then the smallest spread in average opponent strength; it's saved as the week-by-week matchups. Runs when the draft completes; League Settings can rerun it.
*Protected by:* `tests/test_schedule_balance.py`.

**2026-10-12 · Two kinds of missing time in projections.** Games a player misses here and there (his availability)
lower every week's projection. Weeks he's ruled out for entirely (a known return date) are left out of the PROJ MAX /
MAX low / MAX high shown on the draft list and player card — those say how good his weeks are when he's active. The
season value (fantasy_pool.proj_max, which counts those weeks as zero) still drives ranking and the bid guide; EXP.
GAMES shows the missing time.

**2026-10-12 · Draft list rank value.** The list shows PROJ MAX as a player's weeks when he plays and ranks by a season
value where a whole week out counts as a replacement player (the best one left after every team fills its roster),
not zero — lineups are weekly, so a team starts someone else (and an IR stash costs no roster spot). Only while his
active weeks beat that replacement. The bid guide keeps the plain season value (commissioner: numbers, not the guide).
