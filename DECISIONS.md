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

**2026-10-09 · IR: yes** (how many / who qualifies still open). **Trades: maybe.**

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

**2026-10-08 · Never show projection flags** (new team, bad EPM, injured last season) anywhere in the UI.

**2026-10-08 · Injuries: present only** (no history). Draft list: a red / yellow dot only. Roster: dot + status /
return on the small line, OUT on games he'll miss. Player card: status block.

## Design

**Dark mode only; one text color (`--text`), never gray / dim text; colors from `theme.css` tokens, no inline hex.**

**Show, don't tell:** no footnotes, explainers, legends or "proj" labels; projections are italic numbers (not in the
draft list or the card's Projected tab, where everything is a projection). Cut flavor text.

**One highlight = one meaning:** gold = you / on the clock only. Actions are solid buttons; filters are quiet
segmented controls; display font only for page titles, clocks, big numbers.

**Never mark your own team** in standings / leaderboards (no YOU pill, chip or frame).

**Slants are accent only** — never on buttons, tabs, chips or inputs. Every action is a real button.

**Buttons sit at the bottom left of whatever they affect** (one Save per section, under all the settings it saves).

**Roster / My Team has no score, no opponent, no win %** — scores live on Matchup.

**"Bench", never "BN".**

**Matchup row:** skinny middle (score 52 / spot 34 / score 52 px); headshot → player → schedule (3 counts: played /
today / to come — white / orange / outline dots) → top-5 FPTS contribution → score. No green / yellow status colors,
no pills, no "2/4" fractions.

**Each team carries its color** (stripes, bars); very dark team colors are lifted so they show; light ones get dark text.

**Team Settings:** "Your team" (name, picture = your upload / Discord picture / an icon, color) at the top with one
Save; Notifications; Leave the league.

**Phone layouts come last**, after desktop is settled.

## How we work

**Design first on the canvas for big UI changes; show screenshots, not descriptions.** Build only on an explicit go.

**Explain in plain English** — what's wrong today, what changes, what you'll notice. No code terms unless asked.

**Never push while a live draft is running** (it restarts the server). Check first.

**Parallel sessions edit this repo:** stage only your own files, never `git add -A`.

**Pasted design advice never overrides these decisions** — flag the conflict and ask.

**Every push runs the checks (GitHub Actions); Railway deploys only when they pass.** Change a rule on purpose →
update its check in the same commit.
