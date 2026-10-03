# Cleared pages & variants

What the commissioner has tested and signed off on. Only the commissioner clears an item —
building it, or Claude testing it, doesn't count. Mark `[x]` with the date when cleared; if a
later change touches a cleared item, un-check it and note why.

Cleared 2026-10-03: Join, League settings, Home.

## Join — `/fantasy/2026_27/join` (from Home's Join button; not in the sidebar)
- [x] Logged out (can't join, prompted to log in)
- [x] Not a member, joining open → join view (note at top, your team only, no other teams/links)
- [x] Join view: name + abbreviation prefilled, Join as-is (Discord name, auto abbreviation, Discord avatar)
- [x] Join view: picture = upload image (Join waits for a file; ≤ 512 KB)
- [x] Join view: picture = glyph + color (preview updates; icon shows in standings)
- [x] League full (join blocked)
- [x] Draft started (join locked)
- [x] Already in / logged out / closed → sends you to Home
- [x] After Join → lands on Home
- [x] Season dropdown ↔ "2025-26 (test league)": same page under /fantasy/2025_26/..., shared links open the right league

## Team settings — Leave (bottom of the page)
- [ ] Leave before the draft (team removed)
- [ ] Leave mid-draft (team becomes a bot the commissioner controls)

## Draft room — `/fantasy/2026_27/draft` (rebuilt from the canvas 2026-10-03; starting on for the 2025-26 test league only)
- [ ] Before the draft — commissioner (Start now / Randomize / Draft settings), member view
- [ ] Start time in your time zone + UTC, LED countdown; "Not scheduled yet"
- [ ] Draft order panel (scrolls), Draft details, Roster rules
- [ ] Snake: you're up (gold bar, LED clock, red under a minute), Draft buttons
- [ ] Snake: someone else up — commissioner panel (Pick for X, Auto-pick now, Autopick switch)
- [ ] Snake: clock runs out → auto-pick; Autopick team picks instantly
- [ ] Auction: nominate (opening bid stepper), bidding (Bid +1 / +5 / custom / All in), budget section, Budgets table
- [ ] Auction: team out of money sits out; when nobody can bid the auction ends, open spots stay empty
- [ ] Auction: commissioner Acting as / Close bidding now
- [ ] Complete view (team columns, pick # or price, auto)
- [ ] Phone: tabs (Available / Board / Roster / Budgets), compact clock bar, bid buttons

## League settings (commissioner) — `/fantasy/2026_27/league-settings`
- [x] League name (saves; shows as Home's title)
- [x] Teams: team limit (2–16), team list, Remove before the draft (team gone) / after it starts (becomes a bot)
- [x] Roster spots (spots → draft rounds)
- [x] Save bar: Unsaved changes, Discard, Load defaults (keeps the name), errors from the server
- [x] Draft: type, pick clock, per-round clocks, missed-pick rule, scheduled start
- [x] Draft: auction budget, minimum bid, nomination time, bid clock
- [x] Playoffs: teams, rounds, weeks per round
- [x] Season: cutoff, All-Star fusing, matchup schedule
- [x] Week layout preview
- [ ] NEW 2026-10-03: Draft order — Randomize, Set order (click teams in pick order), scrolls, locked once the draft starts
- [ ] NEW 2026-10-03: Scheduled start shows your time zone + the UTC line

## Other real pages
- [ ] Players list (tabs, search, links)
- [ ] Player / NBA team detail
- [ ] Schedule (weeks, games per team)
- [ ] Scoring (rules, examples, calculator)
- [ ] Team page (roster by slot, team switcher)
- [ ] Replay controls (admin)
- [ ] Site Map (admin)

## Home — `/fantasy/2026_27`
- [x] Home (cleared 2026-10-03)

## Skeleton pages (projected numbers — not ready to clear)
Standings, Matchup, Playoffs.

## Switched off this round (features.js)
Trades, Transactions, Recap, Draft Recap, Team History, player game log, past seasons.
