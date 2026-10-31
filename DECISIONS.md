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
**THE ROSTER LOCK RECORD — carved in metal** (2026-10-24). Every spot locks when its player's first game of the week tips off (5 min before), IR spots the same; a spot with no player, or whose player's team has no game that week, locks when the week's last NBA team tips off its first game. At that moment one line is written to the lock record (fantasy_lock_ledger): week, fantasy team, spot, who was in it, when. Nothing else is ever written there, and in the live league the database refuses any edit, deletion or emptying, and refuses a second player in a spot. Every locked spot on every page and in scoring is read from that record alone. *Protected by:* integration `test_live_lock_record_can_never_be_changed_or_deleted`, `test_a_locked_spot_never_takes_a_second_player`. **A locked spot is permanent** (2026-10-24): no swap, add, drop or trade can write a player who joined after his lock into that week or push a locked player out of it (a Roster swap with a locked player did, from 2d77cbf until fdd9525 — Ty Jerome over James Harden). *Protected by:* `test_lineup_lock.py`, integration `test_dropped_after_his_lock…`, `test_added_after_his_lock…`, `test_swap_with_a_locked_player_never_writes_a_late_pickup…`, `test_lock_job_removes_a_late_pickup_row`.

**2026-10-26 · The week under way vs the roster** (Cody: LaMelo locked at G and dropped; Deni moved FLEX → G for week 3
fell out of week 2). (1) A locked spot never changes, even after a drop. (2) A player not locked yet keeps his spot this
week; only a move on this week's view changes it — moves for next week never touch this week. (3) A drop removes him
from both weeks; if he wasn't locked, his spot this week goes empty. (4) An add whose first game hasn't started takes an
open spot this week he can play (position, Flex, Bench), else starts next week. (5) An empty spot is always legal; only
the roster (next week on) must be full and valid. He locks in the spot he holds that week. *Protected by:* integration
`test_the_week_under_way_keeps_its_spots`.

**2026-10-09 · Waivers: 2 days.** A drop is real once the player was drafted or locked into one of your weekly
lineups; a real drop puts him on waivers for 2 days (live: 48 hours; test league: 2 days of its clock). Nobody can
just add him — not even the team that dropped him. Claims (optional drop if it wins) settle when the 2 days are up:
the team lowest in the standings wins (worst record, then fewest points). Unclaimed → free agent. Add-then-drop before
any lock isn't a real drop: he's a free agent straight away (no waivers). Free agents are instant. **2026-10-27:** "any
lock" = any team's — a player locked into another team's lineup in a week since he joined you (traded for him: Harper
locked on nola's week 2, then dropped in week 2) is a real drop → waivers. *Protected by:* integration
`test_traded_player_locked_on_his_old_team_goes_to_waivers_when_dropped`.
*Protected by:* integration `test_real_drop_goes_to_waivers…`, `test_add_then_drop_before_any_lock…`.
**2026-10-27 · Claim order: resets each scoring period, winners go to the back** (replaces "lowest team always
wins"). At each period's first lock (5 min before its first game, whatever day that is; a 2-week playoff round resets
once) the order is reverse standings — worst record, then fewest points. Within the period, a team that wins a claim
goes to the back of the line (several winners: in the order they won). A claim is settled with the order at the moment
its waiver ended. *Protected by:* integration `test_a_claim_winner_goes_to_the_back_of_the_line`.
**2026-10-29 · The period's base order is frozen at its first lock.** "Reverse standings" = the standings as they were
at the period's first lock: only matchups from earlier weeks count, so a matchup that finishes mid-week (2026-10-25
rule) no longer reshuffles the order inside the period. Sorted like the Standings page (win %, ties = half, then points
for, then name), turned around. The Transaction Log's Waiver order tab shows that frozen record and PF. *Protected by:*
integration `test_claim_order_frozen_inside_a_period` (tests/integration/test_waiver_period.py).
**2026-10-27 · The Transaction Log: every move is kept, ghosts are hidden, one row per move.** Nothing is deleted
any more (the old rule took Hit and Run's Jarrett Allen waiver claim with it when Allen was dropped before locking in;
that claim and its undoing drop were put back by hand — the claim at its waiver's end, 12:27 AM Oct 27, the drop with
the Paul Reed add). Hidden (kept in the table): a free-agent add dropped again before he ever locked in, and that drop
(Kel'el Ware → Diabaté → Reed). A waiver claim always shows, and so does the drop that undid it. The player page and
the recap's pickups hide the same ghosts. A row = one checkout, and a drop on its own joins the same team's next
free-agent add-only checkout in the same week (UNO: Bridges dropped Oct 26 9:50 PM + McDaniels added Oct 27 = one row,
both times shown). Claims, trades and full swaps stay their own rows. *Protected by:* `tests/test_transaction_moves.py`, integration
`test_add_then_drop_before_any_lock…`.
**2026-10-26 · A claim that stops working is cancelled right away** — its drop player left the roster another way, or
the roster no longer has room — checked after every roster move and whenever claims are shown.
*Protected by:* integration `test_a_claim_whose_drop_player_leaves_is_cancelled`.

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

**2026-10-30 · Draft Grades: Timing (auction only).** When the money went, from the frozen draft: the sales in four equal stretches (spent vs fair price); each team's spending in the first stretch, what it had left after it, and how it bought vs fair in the first stretch and after; "Should have waited" = top 8 buys where a later sale at the same position, projected at least as good, went for less (biggest saving per buy). Hindsight on prices, projections on value; shown, never graded. Computed on the page from the draft payload. *Protected by:* lint + build (frontend only, no new data).

**2026-10-10 · Draft Value (the recap's second draft tab, labeled "Drafting value based on the actual results of the 2026-27 NBA season"; the first is "Draft Grades", labeled "Draft grades based off the projected value"): actual points added, and a dropped player only counts while he was yours** (provisional; not built yet). Each pick: draft-day projection next to actual points added a week; color = actual − projected. A drafted player who's dropped (or, later, traded) credits the drafting team only through the week he left ("dropped Wk 4 · +2.1 a week, 4 weeks"); what he does afterwards counts for no one's draft (a pickup is a waiver move). "Biggest regret" callout = the dropped player who did most since — shown, never graded (2026-10-30: a ranked "Biggest regrets" list, top 8 dropped picks by points a week above the replacement player at his spot since he left — 2026-10-31: shown a week and ranked by that same number; dropped before Week 1 reads "before Wk 1"). **2026-10-30 · Live:** it counts every regular-season week that has started, the current week with its games so far (box scores land during games), and stops at the schedule's last regular-season week; no "through week N" label. *Protected by:* `test_draft_value_is_live` (tests/integration/test_recap_week.py).

**2026-10-10 · Draft grades are in fantasy points — the only metric** (built 2026-10-11: `recap.py`, frozen the moment the draft completes; test leagues preview from their rosters. *Protected by:* `test_recap_draft.py`). Points added = a player's projected weekly MAX − the best player still free at his position after the draft (Jokić 45 vs 20 → +25 a week; 23 / 24 / 28 → +3 +4 +8 = +15); a team's is the plain sum of its starters'. The team list is "Team grades", never "Standings" (standings are real wins and losses). Price / pick is context only. The cell's color = points added − what that resource usually buys at that moment, also in points (auction: the money actually spent on the rest of the draft — not money that ended up unspent, which is its own ding — ÷ the points bought with it, on a curve — now 1.25 — so a big package can cost more per point, but more points always grades higher; snake: what that pick number normally gets — the Nth-best player by projection — so a better player falling to you is green (Wembanyama at 3 behind a Jokić / Wembanyama / Dončić ranking) and pick 1 can only be 0 or negative). Both drafts use the same yardstick: what that resource normally gets. Awards show the top 3 (#1 in full, #2–3 brief) and always lead with the player's value (points added a week); money or pick only explains it: Best buy (worth − paid; "paid $18 · worth $44"), Best buy under 10% of the budget (by value), Deepest bench (the team's two bench-spot players by value, shown by name), Biggest overpay (paid − worth; "$90 usually gets +10.3"), Worst drafted player (fewest points added; "vs J. Embiid"); snake: Best pick / Best late pick / Biggest reach ("R3·5 usually gets +1.5"). Roster cells: value, then "$84 vs fair $86" (auction) or vs pick (snake). The team table is "Draft Value (Projected)", no rank numbers. Unspent money is a separate ding. A 50-auction test found no curve clearly better than another (+0.41–0.48 agreement with projected standings).

**2026-10-23 · League activity (Home) shows the most important moves first** (replaces 2026-10-10's ranking). Only moves
that happened: a drop and the add it came with show as soon as they're made (2026-10-25: adds no longer wait for the player to lock in). A move is for the week it's
made in, or the next week once that week's rosters have locked (2026-10-24: Saturday's Jerome-for-Harden is week 2).
One entry per team per period (2026-10-25, restored — replaces the 2026-10-24 one-day bursts): every add / drop a team
makes between one week's roster lock and the next is one line; moves inside one period are linked. Players who came and went inside the week never appear. The box
fills by importance until the room runs out — the last one taken may run past the bottom, which fades it out — then
shows them newest first. A move's importance = its biggest
player's value **above replacement** through the move's week: value = the site's blend (25% preseason PROJ MAX + 75%
his weekly best over the 4 weeks ending with the move's week, once he has 4+ games there) — it moves with that week's
games and locks once the week is over; replacement = the 25th best value at his
role (G / F / C), or the 13th best NBA team; never below 0. Every entry halves each time a new week starts. Listed most
important first (the Home box shows as many as fit; Transaction Log has them all); top 15 kept; the draft is one entry
(its three biggest picks). The number is never shown. *Checks: tests/integration/test_activity.py.*
**2026-10-29 · A period is the matchup unit, not the week:** a 2-week playoff round (Championship) is one period, so
a team's moves in both legs are one entry, filed under the round's first week and named for the round (same as the
claim order's reset). *Protected by:* integration `test_home_activity_one_entry_per_period`
(tests/integration/test_waiver_period.py).

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

**2026-10-09 · IR.** IR spots are a league setting (0–3, default 1), extra on top of the roster (not drafted, never score). Only a player with a red or yellow dot (Out / Out For Season / Day-To-Day) can move there, and only after a confirm pop-up. Moving in locks him on IR for the 4 weeks after the current one (before the season: through Week 4): no moves, no drop. **2026-10-11:** once his last IR week is under way, he can be moved (or dropped) for the next week — e.g. IR in Week 1 → frozen through Week 5; during Week 5, looking at Week 6, he's free for Week 6, and Week 5 stays IR in the history. **2026-10-27 · IR = 4 weeks from the first week he can still be put there** (Banchero): moved before his lock this
week → this week + the next 3 (week 2 → weeks 2–5); after it → the next 4 (3–6). Service Time shows the IR weeks the
moment he moves, before each one locks. Banchero (moved before his week 2 lock under the old count) corrected 6 → 5;
the other IR players were already right (preseason → 1–4; Duren, Missi after their week 1 lock → 2–5). Commissioner
fix: `POST /fantasy/2026_27/admin/ir/{player}/through/{week}`. After his IR weeks, a player still on IR when his week locks is locked there for that week like any spot (lock record; no move for that week). *Checks: tests/integration/test_ir.py.* **Trades: maybe.** *IR count and Service Time: `test_ir.py::test_ir_after_this_weeks_lock_is_the_next_4_weeks`, `::test_service_time_shows_ir_weeks_right_away`, `::test_after_ir_ends_staying_on_ir_locks_like_any_spot`.*

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
**2026-10-26 · Clutch is decided before the play starts:** last 5:00 of the 4th / OT and within 5 on the score before
the shot (a 2 that cuts 7 to 5 isn't clutch). Same as nba.com's clutch stats (210 of 210 players, Oct 23–25).
*Protected by:* `tests/test_live_clutch.py::test_clutch_points_use_the_score_before_the_play`.
**2026-10-26 · A stat correction to a finished week:** re-run the overnight job for its dates, then
`POST /fantasy/2026_27/admin/week/{week}/restat` — the one way to rebuild a frozen weekly recap and refill the projection
check's actuals (returns the old recap). The saved pre-week projections stay as they were. Week 1 restatted for the
clutch recount (no result changed). *Protected by:* `test_recap_week.py::test_restat_rebuilds_a_frozen_week`.

**2026-10-27 · The live pull keeps a finished game for 30 minutes** (was 15), and the live loop stays awake for it even
when it was the night's last game. The NBA's scorers entered Mobley's overtime stats (CLE–MIN, Oct 26) up to 36 minutes
after the buzzer; the 15-minute stop froze him at 29.5 (real 41.5) until the 4 AM nightly.
*Protected by:* `tests/test_live_clutch.py::test_a_final_game_is_pulled_for_30_minutes`.

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

**2026-10-25 · Weekly recap: when it's made, and its awards.** Made (and frozen) once every NBA game of the week is final
— Best free agents needs all of them — or at 2 AM Central the Monday after if a game still isn't marked final. Pickup of
the week = adds that locked into the week, each linked to what it replaced: a drop by the same team in the same period
(lock to lock, same kind), else the player that team moved to IR; a plain open spot doesn't count; the pickup must
outscore who he replaced; top 3, pickups who started first, then by points gained. Left on the bench shows the top 3.
Versus projection rows show each day's points (best in orange, a missed team game OUT) and where the week ranks among
his own weekly scores (last two seasons + this one). Look: see the 2026-10-25 preview (team cards with plates + names,
faded emoji, shared bench / pickup rows). *Checks: tests/integration (recap).*

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

**2026-10-20 · Set in stone: projections blend the preseason with his last 4 weeks** (replaces the 2026-10-18 games-
played rule, 1/14 a game, and the calendar rule before it). Once he's played at least 4 games in the last 4 weeks (this
week and the 3 before), his per-game number = 25% preseason PROJ AVG + 75% his average over those 4 weeks — a moving
window. Fewer than 4 games there (hurt, just signed) = preseason. A week's projection = the expected best game across
the games his team has left, each at that number × the game's factor, his swing (**since 2026-10-27: his own spread
over his games in the last 20 weeks** — this season's weeks so far, the rest from the end of last season — no preseason
blend; under 10 games there = the preseason model's swing. Was model + his 4-week spread: Edwards' first 4 games, one a
34-point clutch night, read as a 0.65 spread and projected 79.6 off a 79; stars beat 2.1× their average in ~1% of games
over 3 seasons, nearly all big clutch nights; *protected by* `tests/test_game_spread.py`), his chance of playing each,
never below his best this week. One rule (`projections.blend` /
`season_weight` / `game_cv`) for the week total, the number under each game, NBA teams, the recap's frozen weekly
projection and the player page header. (Opponent ratings keep their own ramp: league average → own games, 1/14 a game.)
*Protected by:* `tests/integration/test_week_projection.py`, `tests/test_recap_snapshots.py`.

**2026-10-18 · Each game's number knows the opponent.** One game's number = his per-game projection (above) × a factor
for that game: opponent's defensive rating, pace and net rating (from box scores; every team starts at the league
average and moves onto its own games, 1/14 per game it has played, last season not used), home/away and the opponent
playing yesterday (from the schedule, full effect from day 1). Sizes from the backtest (PROJECTIONS.md): +0.89% per
point of opponent defensive rating, +0.87% per possession of pace, −0.23% per point of net rating, home +3.0% vs away,
opponent on a back-to-back +2.2%. The week total is the expected best across each remaining game's own number (not
their average: a 27.1 and a 28.1 beat two 27.6s), with the model's game-to-game spread and his chance of playing each
(`projections.week_best`); the win-probability sim uses the same per-game numbers.
**Availability in a week (2026-10-18): misses stack only for an injury.** One rule (`lineup._chances`) for the weekly
number, 1+ Game % and the win chance. Healthy (played his team's last game, not on the report): each game independently
at his own per-game chance from his scattered misses (availability_patterns, 2026-10-12: Haliburton 96%, Kawhi ~90%),
no "whole week out" chance — the season model's stretch share stays in season value (PROJ MAX ranking, bid guide).
Missed his team's last games: the miss-streak chances. ESPN Out: 0. Week = Σ chance of playing k games × expected best
of those k. Players
only (NBA teams stay 1.0). `opponent.py`. *Protected by:* `test_week_projection.py::test_game_factors`.
**On the injury report is never a sure thing (2026-10-26).** Week 1 check: Knueppel, Lively, Porter Jr. read 100% and
never played (no games yet = no miss streak, and ESPN's return date was taken as certain). Out → his games after ESPN's
estimated return count as first games back after a run of misses (at least 2, plus each game he's out this week);
Day-To-Day → his next game is one after a miss. Healthy players unchanged. *Protected by:*
`test_week_projection.py::test_on_the_injury_report_is_never_a_sure_thing`.

**1+ Game % = chance of a HEALTHY game (2026-10-26).** Jaren Jackson Jr. (10 min) and Markkanen (6 min) left Monday's
game hurt and read 100%. A game counts once he plays 40%+ of his usual minutes (median: this season once he has 3+ games, else this season and last); a shorter
one is "cut short" — only for players who usually play 20+ minutes (the measured group; a bench player's short night is
garbage time). Measured ('21–'25, `scripts/projection_study/injury_exit.py`): 2% of played games are cut short,
worth ~11% of his average; after one he plays his team's next 1 / 2 / 3 games 59 / 64 / 65% (vs 94 / 92 / 90%). So
every game left carries the 2% cut-short chance, and coming off a short game (not already on the report) the next games
use × 0.63 / 0.70 / 0.72. The weekly projection uses the same per-game chances; the projection check scores 1+ Game %
against healthy games played. *Protected by:* `test_play_prob.py::test_a_game_cut_short_isnt_a_healthy_game`,
`test_doomsday_played_once_left_hurt`.

**2026-10-19 · The win chance is a formula on the projections** (replaces the simulation). Margin = team A's projected
total − team B's (the numbers shown); spread = √(sum of every starter's variance), each from the same per-game numbers,
chances and spread as his projected week (`projections.week_dist`); chance = normal curve. It can't disagree with the
totals, and it's instant. Served from the last build (a minute; a roster change rebuilds at once).
*Protected by:* `tests/test_winprob_formula.py`, `tests/integration/test_winprob_served.py`.

**2026-10-18 · One source per projected number (site audit).** League activity values a player at the PROJ MAX the
site shows (`shown_max`), not the raw season column. The pop-up's Projected tab shows the draft list's numbers (board:
MAX, FLOOR, CEILING, games) instead of recomputing them in the browser. The player page's weekly-bests chart plays
each game at his per-game chance (scattered misses), the same definition as the shown MAX. The recap's frozen weekly
projection uses the weekly number's spread (`projections.game_cv`). *Protected by:* `data_audit.py` (pop-up vs draft
list), `test_week_projection.py`.

**2026-10-19 · Projection check.** Every pool player's and NBA team's weekly projection, 1+ Game % and per-game number
are saved on the server before the week's first game (3 AM job and every restart; never once a game has started), and
filled in with what happened once the week is over (`projection_log.py`, page /projection-check: average miss, how
wide misses ran against what the projections said, 1+ Game % against who played). *Protected by:*
`test_projection_log.py`.

**2026-10-19 · Injury weeks follow the current report.** After every injury pull the per-week projections are rebuilt:
weeks ending before an Out player's return date are 0, and his return week counts only the games from that date on.
*Protected by:* `test_week_projection.py::test_return_week_counts_only_games_after_the_return_date`.

**2026-10-19 · One lock countdown.** Home, Roster and Players show the same LockClock from one lock time
(`lineup.first_lock`: 5 min before the week's first game).

**2026-10-21 · Draft Grades are frozen at draft day.** Their projections are the ones saved when the grades were built
after the draft; later injury updates move the draft list's PROJ MAX but never the grades. (`data_audit.py` no longer
compares the two.)

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
**2026-10-29 · A traded player never reads as a free-agent move.** Every moved player carries how he moved — via =
'waivers' (won on a claim), 'trade' (got or sent in a trade) or none (free-agent add, plain drop) — on adds and drops
alike: the Transaction Log, Home's league activity and the player page's Transactions. *Protected by:* integration
`test_trade_moves_carry_via_trade` (tests/integration/test_waiver_period.py).
**2026-10-30 · Injury updates go in Transactions (Injury Updates tab).** Each injury sync compares the old report
with the new one and logs every change for pool players: newly listed, status changed (Day-To-Day → Out), return date
moved, or cleared (off the report). Comment-only edits aren't logged. Syncs run (Mondays
every 15 minutes 7 AM–11 PM, other days noon and 4 PM, every day 1 AM Central); each row
shows the fantasy team that has the player now (FA if nobody). History starts 2026-10-30 — ESPN keeps no history, and players already on the report then get no row (commissioner: no backfill).
Only what matters by default: every status (the red-dot filter = Out / Out For Season / Suspension, yellow dot =
Day-To-Day; a change between them counts for both) and players at 15+ MPG and 20+ AVG, both his projection as the
Players page shows it (fantasy_pool's live blend; 2026-10-30, replacing the this-season-or-last-2-seasons rule so the
filter and the columns are the same number).
Filters: All (default) / red dot / yellow dot, MPG ≥, AVG ≥ (the projection). A ?player= link shows all of that player's updates.
Layout (2026-10-30): Transactions is one sidebar entry with three tabs — Fantasy Transactions (/transactions),
Waiver Order (/waiver-order), Injury Updates (/injuries). Injury Updates is a table: When, Team, Player (headshot with
a dot for his status NOW), Change (cell shaded by where he ended up: green = healthy again, red = Out / out for season / suspended, yellow = Day-To-Day; newly listed reads "Healthy → Day-To-Day" (2026-10-30), same status with the return date moved reads "Out → Out", red when the date moved later, green when sooner), Injury, Return,
Missed so far (2026-10-30: team games he's sat since the report, a running count that grows as games go final), Total out (the whole stint: games sat in a row before the report + missed so far + games still to come before his return date while Out; italic when it includes that estimate; cleared = what he missed before),
MPG and AVG (his projection, italic — the numbers the filters use). From / To date filters (ESPN's day, on the viewer's calendar), empty by default. AVG floor starts at 20. The same
player across syncs is matched by our player id, never ESPN's entry id (an update gets a new one).
The time shown is when ESPN posted the update (its entry's date); our sync's time is kept on record (synced_at).
Coming off the report has no ESPN entry left, so it shows the sync that saw it.
*Protected by:* integration tests/integration/test_injury_log.py.

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

**2026-10-11 · 1+ Game % is live, like win %.** Played once this week (a healthy game, 2026-10-26) → 100%; the week over without a game → 0%.
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
