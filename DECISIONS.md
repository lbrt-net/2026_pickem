# Decisions

Every call the commissioner has made about how the league and the site work, with the date. **Read this before
changing behavior.** If a decision changes, edit its entry (new date, what changed) — and the check that protects it
in the same commit. "Protected by" names the automated check (`tests/`); none = only this page remembers it.

---

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

**2026-10-09 · Every draft start has a 10-second warm-up.** The draft is on (everyone's pulled into the room) but no clock runs and no pick, nomination or bid counts until it ends; the page shows "The draft starts in 0:10". *Checks: tests/integration/test_draft_warmup.py.*

**2026-10-09 · Auction bid bar: one button (the minimum raise), anything else typed** and refused outside minimum raise … most you can bid. No double raise, no All-in button.

**2026-10-09 · Draft picks count as transactions** (they're entries in the Transaction Log).

**2026-10-09 · The draft pool only holds players / teams that fit at least one spot** under the league's roster
rules. *Protected by:* `test_pool_only_holds_entities_that_fit_a_spot`.

**2026-10-09 · Schedule: even round robins.** Set automatically, every team plays exactly once a week (odd leagues:
one bye a week, spread evenly); every pair meets about equally often. The commissioner can set any week by hand.
*Protected by:* `test_schedule.py`.

**2026-09-28 · Weekly lock:** rosters lock 5 minutes before each player's first game of the fantasy week.

**2026-09-28 · Trades:** no review, no veto. Deadline = the lock of the last regular-season week (confirm).

**2026-09-28 · Notifications:** in-site only, every category off by default.

**2026-09-28 · Playoffs scale with the number of teams** (bracket and byes from league size; follow League Settings).

**2026-10-09 · IR.** IR spots are a league setting (0–3, default 1), extra on top of the roster (not drafted, never score). Only a player with a red or yellow dot (Out / Out For Season / Day-To-Day) can move there, and only after a confirm pop-up. Moving in locks him on IR for the 4 weeks after the current one (before the season: through Week 4): no moves, no drop. After that he moves out like anyone. *Checks: tests/integration/test_ir.py.* **Trades: maybe.**

**2026-10-09 · Players traded mid-season showing their old NBA team until they play for the new one is fine.**

**2026-10-09 · No commissioner "are you sure" safeguards** (e.g. nominating for whoever's up). Instead: a list of
features to hide / strip back / lock behind higher permission levels.

## Scoring

**Scoring rules are data** (`scoring.py`; per league). A player's week = his best game; an NBA team's week = its best
game (both "best_game" today). *Protected by:* `test_scoring.py` (recomputes 10 player + 3 team games from the current
rules — change the rules and the checks follow).

**2026-10-08 · Clutch: +2 per clutch point** (3 total for a clutch point, with the point itself).

**2026-10-09 · NBA teams, points allowed: +1 per point under 125, only down to 100 (at most +25), then +5 under 100.**
TEAM draft 7 bonuses (commissioner's cutoffs 2026-10-08): fast break ≤12, paint ≤40, 15+ turnovers forced, glass +10.

**When scoring rules change, rebuild:** player + team projections and team curves (`scripts/build_projections.py --post`),
then '23–'26 history (`POST /admin/history/build`); `scripts/check_site.py` flags anything missed.
*Protected by:* `test_version_stamp_follows_the_rules` + the check-up (GET /admin/health).

## Win probability

**2026-10-09 · Simulated, back-tested.** The rest of the week is played out thousands of times: each starter keeps his
best game so far, plays each remaining game with his chance to play (0 if the injury report has him out, else his
share of his team's last 20 games), each game drawn from his own game scores. NBA-team spots likewise. Opponent
strength and week-to-week form were tested and left out (no gain). Back-test on 2025-26: average miss 0.078 vs the old
projected-gap method's 0.145 (`WINPROB.md`, `scripts/backtest_winprob.py`).
*Protected by:* `test_winprob.py` (0–100%, sides add to 100%, decided weeks exact, can't-catch-up = 0, more lead / games
never hurt, out games count for nothing, identical teams ≈ 50%, calibrated on made-up weeks).

## Bid guide (Rec bid)

**2026-10-08 · Personal.** The spot he'd fill for you sets the bar (his position's leftovers; Flex = the best leftover
of any position). Your share of your spendable money across your open starting spots caps it. Rec bid = the lower of
market price and your share, never under the minimum, never over your safe max.

**2026-10-09 · A bench-only player is valued like a Flex — but a Flex/bench-only player is never recommended above the
best player still available for any of your open G / F / C / TM spots** (spots whose best is only replacement level
don't count). *Protected by:* `test_rec_bid.py` (never over safe max, better ≥ worse, open spots first, full roster →
none), across league setups.

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
