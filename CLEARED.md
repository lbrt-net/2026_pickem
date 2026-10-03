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

## Draft room — `/fantasy/2026_27/draft`
- [ ] Not started, no scheduled time
- [ ] Not started, scheduled time shown → starts on its own at that time
- [ ] Draft order: move up/down, Randomize (before the draft), order locked while running
- [ ] Snake: owner picks own team on the clock
- [ ] Snake: commissioner picks for a bot / fake user
- [ ] Snake: clock runs out → auto-pick
- [ ] Normal (linear) order
- [ ] Snake with 3rd-round reversal order
- [ ] Per-round pick clocks
- [ ] Auction: nominate (owner / commissioner acting as a team), opening bid
- [ ] Auction: bidding, +1 / +5 / custom, clock resets on each bid, high bidder wins
- [ ] Auction: max-bid limit, can't bid without an open spot that fits
- [ ] Auction: nomination clock runs out → auto-nominate
- [ ] Commissioner buttons: Start, Reset, Auto-pick / Close bidding, Auto-draft / Finish auction
- [ ] Spectator (not a member) view
- [ ] Complete

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
