# Cleared pages & variants

What the commissioner has tested and signed off on. Only the commissioner clears an item —
building it, or Claude testing it, doesn't count. Mark `[x]` with the date when cleared; if a
later change touches a cleared item, un-check it and note why.

Cleared 2026-10-03: Join, League settings, Home.
Cleared 2026-10-11: Draft (before / room / complete), Recap (Draft Grades, Draft Value, weekly), Rules, Team Settings,
League settings (re-cleared), Join (re-cleared), and after the row-font pass: Matchup, Home, Standings, Recap, Playoffs; Roster. Not cleared: Players, Rules (prize pool re-check), Roster drag + Drop button (built after the clear).

## Players page + pop-up refresh (2026-10-14)
- [ ] Players: no count line; tabs = the view, recessed switches = filters; team-color row edge; pages instead of Show more; LED week badge (in season)
- [ ] Player pop-up (one screen, never scrolls): tier frame border; the player header's stats panel (MAX / AVG / FLOOR / CEILING, season cloud) and wheel — this season only, blank until games; next 8 weeks' schedule strip. Tabs + tables only for NBA teams now

## Player page — `/fantasy/2026_27/players/:id` (back 2026-10-14; from a name's new-tab link or the pop-up's "Player page →")
- [ ] Header: card front (tier by career honors, team frame, All-NBA chrome) · stats panel · card back (wheel, trophy case)
- [ ] Overview (seasons, last 10, next 10; Fantasy points / Box score)
- [ ] Game Log ('27–'23; OUT rows; weekly best underlined)
- [ ] Transactions (this league's moves)
- [ ] Availability (status + per-season strip)
- [ ] Extras: LED shot chart (season switch; empty board until his fields are built)

## Join — `/fantasy/2026_27/join` (from Home's Join button; not in the sidebar)
- [x] Logged out (can't join, prompted to log in)
- [x] Not a member, joining open → join view (note at top, your team only, no other teams/links)
- [ ] Join view: name + abbreviation prefilled, Join as-is (Discord name, auto abbreviation, Discord avatar) — un-checked 2026-10-29: join controls lost their gold (orange button, lighter selected fill)
- [ ] Join view: picture = upload image (Join waits for a file; ≤ 512 KB) — un-checked 2026-10-29: join controls lost their gold
- [ ] Join view: picture = glyph + color (preview updates; icon shows in standings) — un-checked 2026-10-29: join controls lost their gold
- [x] League full (join blocked)
- [x] Draft started (join locked)
- [x] Already in / logged out / closed → sends you to Home
- [x] After Join → lands on Home
- [x] Season dropdown ↔ "2025-26 (test league)": same page under /fantasy/2025_26/..., shared links open the right league

## Team settings — `/team/settings` — cleared 2026-10-11
- [x] Name, short, picture (upload / Discord / icon), color, Save
- [x] Leave the league
## Draft room — `/fantasy/2026_27/draft` — cleared 2026-10-11 (before the draft, the room, complete)
- [x] Before the draft — commissioner (Start now / Randomize / Draft settings), member view
- [ ] Start time in your time zone + UTC, LED countdown; "Not scheduled yet" — un-checked 2026-10-29: draft start now shows Central time with CT
- [x] Draft order panel (scrolls), Draft details, Roster rules
- [x] Snake: you're up (gold bar, LED clock, red under a minute), Draft buttons
- [x] Snake: someone else up — commissioner panel (Pick for X, Auto-pick now, Autopick switch)
- [x] Snake: clock runs out → auto-pick; Autopick team picks instantly
- [x] Auction: nominate (opening bid stepper), bidding (Bid +1 / +5 / custom / All in), budget section, Budgets table
- [x] Auction: team out of money sits out; when nobody can bid the auction ends, open spots stay empty
- [x] Auction: commissioner Acting as / Close bidding now
- [ ] Draft room on a phone (2026-10-15): Available list fits (player, MAX, Rec bid, Queue / Nominate), board as one card per team, pick history, roster, bid buttons — desktop unchanged
- [x] Auction: Rec bid rebuilt 2026-10-15 (one ratio, value to you) — signed off 2026-10-15
- [x] Complete view (team columns, pick # or price, auto)
- [x] Phone: tabs (Available / Board / Roster / Budgets), compact clock bar, bid buttons
- [x] Available list restyled 2026-10-15 to match Players (tabs for views, recessed switches, team-color row edge, numbered pages) — signed off 2026-10-15

## League settings (commissioner) — `/fantasy/2026_27/league-settings` — re-cleared 2026-10-11 (incl. auto playoffs, IR, matchups grid)
- [ ] League name (saves; shows as Home's title) — un-checked 2026-10-29: League settings controls lost their gold; "Member · you" row removed
- [ ] Teams: team limit (2–16), team list, Remove before the draft (team gone) / after it starts (becomes a bot) — un-checked 2026-10-29: "Member · you" gold row removed
- [x] Roster spots — CHANGED 2026-10-03: now G / F / C / TM / FLX / Bench (no "any player"; old ones became FLX), bench takes anyone and doesn't score, draft rounds cover the whole roster
- [x] Save bar: Unsaved changes, Discard, Load defaults (keeps the name), errors from the server
- [x] Draft: type, pick clock, per-round clocks, missed-pick rule, scheduled start
- [x] Draft: auction budget, minimum bid, nomination time, bid clock
- [x] Playoffs: teams, rounds, weeks per round
- [x] Season: cutoff, All-Star fusing, matchup schedule
- [x] Week layout preview
- [ ] NEW 2026-10-03: Draft order — Randomize, Set order (click teams in pick order), scrolls, locked once the draft starts — un-checked 2026-10-29: settings controls lost their gold
- [x] NEW 2026-10-03: Scheduled start shows your time zone + the UTC line

## My Team — `/fantasy/2026_27/team` (rebuilt 2026-10-04: facelift v2)
- [ ] Scorebug: your color | score | opponent (pictures, readable text on light colors), Final / Day x of 7 / Projected
- [ ] Lock clock (LOCKS IN 3 D → 14 H → 22 M → 41 S, then Locked)
- [ ] Rows: spot as a plain row label (G / F / C / TM / FLX / Bench), headshots / team logos, player's position at the end of the small line, best game + box line, projected best game for future weeks; heavier line where the bench starts
- [ ] Opens on next week once all your starters have locked; future weeks default to Schedule; past weeks read-only
- [ ] Moving players: Move here / Swap, live (no undo), locked players → counts next week
- [ ] Player / NBA team tap opens the pop-up card (Esc / tap outside closes; Full page →)
- [ ] Phone layout (2026-10-16): plates side by side, scoreboard under; rows = player · score · spot · score · player (no headshots / schedules / best-game bars on phones)

## Other real pages
- [ ] Players list (tabs, search, links)
- [ ] Player / NBA team pop-up card (the only player view — no page)
- [ ] Schedule (weeks, games per team)
- [ ] Rules page (cleared 2026-10-11; un-checked same day: prize pool section filled in — re-check)
- [ ] Team page (roster by slot, team switcher)
- [ ] Replay controls (admin)
- [ ] Site Map (admin)

## Home — `/fantasy/2026_27`
- [ ] Home (cleared 2026-10-03; re-cleared 2026-10-11 after the row-font pass) — un-checked 2026-10-29: Best buy → Best value, NBA nicknames, recap links, Central draft date, one entry per playoff period

## Matchup — `/matchup`
- [ ] Matchup view — cleared 2026-10-11 (scores strip with arrows, scoreboard banner with inset plates and recessed 3-digit LED windows, NBA-color rows, best-game bar with callouts + hover zoom + date, Bench/IR section) — un-checked 2026-10-29: phone: Schedule tab shows the Scoring table, switch hidden
- [x] All teams view (Standings table look; rows open that matchup; no scores strip) — cleared 2026-10-11
- [ ] Test league date picker (admin, 2025-26 pages)

## Facelift in the Matchup look (canvas "Standings v2" / "Roster v2" / "Home v2")
- [ ] Standings (real results, Last 5 circles; Home-card look, playoff line, Start step) — re-cleared 2026-10-11 after the row-font pass — un-checked 2026-10-29: records follow W-T-L only when the league has a tie
- [ ] Roster — un-checked 2026-10-27 (IR pop-up now shows his own last IR week); was cleared 2026-10-11: scoreboard-housing header (switcher + lock window), NBA-color rows, Bench/IR sections, Fantasy Points stat bar with Projected / Actual (real weeks) / past seasons, Schedule with score · minutes, opens on next week
- [ ] Roster: drag to shuffle spots + plain Drop button (no ⋯ menu, no move button) — built right after the clear, not yet checked. Phone (2026-10-15): press and hold a player, then drag; swipes scroll; banner stacks; Fantasy Points and Schedule keep every column and scroll sideways, spot pinned
- [ ] Home: compact standings, this week's matchup cards (current scores + win %) — re-cleared 2026-10-11 — un-checked 2026-10-29: records follow W-T-L only when the league has a tie

## Skeleton pages (projected numbers — not ready to clear)
Playoffs.

## Switched off this round (features.js)
Trades, Transactions, Recap, Draft Recap, Team History, player game log, past seasons.

## Recap — `/recap` — cleared 2026-10-11, re-cleared same day after the row-font pass
- [ ] Draft Grades (auction / snake), frozen at draft completion — revised 2026-10-11 (no top 3, headshot award cards, standings-style team table, unspent strip, fit-to-width names, intensity-scaled roster cells) and re-cleared — un-checked 2026-10-29: Best buy → Best value, names link, NBA nicknames; 2026-10-30: Timing section (sales by stretch, money left after the first stretch, Should have waited)
- [ ] Draft Value (after Week 1) — un-checked 2026-10-30: index tiles retitled "Draft Grades (Projected)" / "Draft Value (Live)", small line above every tile title removed
- [ ] Weekly report tabs (results, players of the week, free agents, versus projection, optional awards, standings + games behind) — un-checked 2026-10-29: names link, "+" on NBA team scores, — for missing numbers

## Playoffs — Standings → Playoffs tab — cleared 2026-10-11, re-cleared same day after the row-font pass
- [ ] Bracket (2 / 4 / 6 teams), two-leg championship (W1 / W2 / Tot), 3rd place, losers faded, champion frame; tab opens at the season's halfway point — un-checked 2026-10-29: bracket colors moved to theme tokens

## Account — `/account` (not reviewed — doesn't matter)
