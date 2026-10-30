# Design principles (lbrt.net)

The settled look. The code is the source of truth (`frontend/src/theme.css` for tokens); work in
progress lives on the "lbrt.net Design" canvas. Updated 2026-10-09. League / site rulings (not design)
live in `DECISIONS.md`.

## Ground rules
- **Dark mode only.** Every color comes from a `theme.css` token — no inline hex. Team colors are
  data from the API (the one exception).
- **Text color:** one text color, `--text` (near-white). **Faded / gray text is banned.** Hierarchy
  comes from size, weight, case and the display face. The only clear exceptions: a disabled control,
  and unlit LED segments. Bench numbers are **not** faded — the bench is labeled, not dimmed.
- **Type (2026-10-11).** One size scale and a few roles, all tokens in `theme.css` (`--fs-*`,
  `--type-*`); no font rule invents its own size.
  - **Body face (Barlow)** for everything read or counted: text, table cells, counts, prices, small
    numbers in tables and queues, tags.
  - **Display face (Barlow Condensed, bold, uppercase)** only for **headings** (page title
    `--type-title`, section label `--type-heading`) and **big standalone numbers** (scores, ranks,
    the bid on the block, start times: `--type-stat` and up). Never for table cells, counts or tags.
  - **Labels** (table headers, field labels, tags like Commissioner): `--type-label`, small bold body
    caps, letter-spaced.
  - **Meta lines** ("G · LAL", schedule counts): `--type-meta`, the condensed face at regular weight.
  - Clocks use LED digits, not a font.
- **Fewer formats:** one format per data type across the site (a game, a score, an opponent, a date,
  a time). Don't invent a new way to show the same thing on a new page.
- **Show, don't tell:** no footnotes, legends, explainers, flavor text or "proj" labels. If something
  needs explaining, change its design. (2026-10-05, again 2026-10-08)

## Color roles — one signal, one meaning
- **Orange (`--accent`)** = the brand: top-bar slash, section-label ticks, the active sidebar link,
  and the main commit action on a screen (Draft, Bid, Save — solid, text in `--accent-ink`).
- **Different kinds of actions get different looks** — never one button style for everything.
  Filters, pagination, add / wishlist, drop, and the main action each get their own treatment
  (e.g. orange solid for the main action, blue `--accent-blue` for add / queue-type actions,
  segmented control for filters, plain outlined for pagination, red outline for drop / remove).
  Pick per feature and keep it consistent site-wide.
- **Gold (`--accent-gold`)** = **you**: "you're up", your avatar ring in the top bar, and the Under
  construction label. Never a button, a filter, or an admin control.
- **Never mark your own team** in standings, leaderboards or boards — no YOU pill, chip or frame
  (2026-10-08).
- **Your team color** (picked in Team settings) is your accent across the site — team headers,
  matchup rows, draft board — and applies even when the team has a picture. Every team carries its
  color (stripes, bars); very dark colors are lifted toward the text color so they show, light ones get
  dark text on top.
- **Red** = urgency only when it's real (a clock under a minute).
- **Team colors** are the only other hues: fantasy team colors (icons, scorebug, team headers) and
  NBA team colors (logo fallback squares, headshot glows).
- **Lineups:** the spot is a plain **row label** (G / F / C / TM / FLX / **Bench** — always the word
  "Bench", never "BN"). The player's own position sits at the end of the small line above his name
  ("Cade · DET · G").
- **Join button** is the one exception to orange: a blue → violet → pink gradient (`--join-*`).

## Controls
- **Main action** = solid orange. **Secondary** = transparent or `--surface-3` with a visible light
  edge, so it never blends into the panel behind it. **Disabled** = faded (one of the two allowed
  fades), never hidden.
- **Filters / toggles / tabs** = a quiet segmented control (selected = lighter fill + bold).
- **Row actions** (move, swap) = ghost buttons that brighten on hover; on touch, always outlined.
- **Buttons sit at the bottom left of whatever they affect** — one Save per section, under all the
  settings it saves; a destructive button under its explanation (2026-10-09).
- **Commissioner / admin controls** = plain solid panel or nav items with a shield icon and the word
  "Commissioner"; in the sidebar they sit pinned at the bottom, visible only to the commissioner.
- In-page links (players, NBA teams, games) open a **pop-up card**, not a new page — only the sidebar
  and top bar navigate (`LINKS.md` tracks every in-page link).

## Shapes and containers
- **Slants only on solid-fill elements:** buttons, the active nav item, header strips, the TM badge,
  the top-bar slash and section-label ticks. (`clip-path` cuts off borders, so bordered panels never
  slant.) Bordered panels, icons and other badges are square or softly rounded; avatars are round.
- **One level of containment per section:** a card with faint row dividers — no box per row.
  Spacing separates groups.
- **Zones read as their own thing:** a header strip (`--surface-2`) over the body (`--surface`);
  filled cells a third tone (`--surface-3`). Row / column labels sit on the panel background with no
  fill, so they never look like cells.
- **Empty / open spots** = graphite (`--slot-empty`) with a dashed edge.
- Your own team can carry its **team color** (a top edge or a header block).

## Team and player identity
- **Fantasy team icon:** the uploaded logo, else a square in the team color with a line-art glyph
  (basketball, swish, ref jersey, whistle, sneaker, jersey), assigned at random and kept. Glyphs are
  **line work**: connected outlines, no lines through joins, thinner strokes on bigger icons.
  Default colors come from the 26-color palette, unique per league.
- **NBA team marks** are the team's **logo**; if it can't load, the tricode square in official
  colors.
- **Players** show a **headshot** (transparent cutout) on a soft glow of his team color, sitting on
  the row's bottom edge.
- **Names by context:** two lines (first name small / **last name bold**; city / **nickname** for NBA
  teams) in roster and list rows; **initial + last** ("S. Gilgeous-Alexander") on grids and boards; an NBA team in a one-line row is its nickname
  ("Thunder"), the full name only on a heading with room.
  Long names truncate with an ellipsis and show the full name on hover.

## Numbers
- Numbers in tables are right-aligned with `tabular-nums`; headers align with their values.
- Records read **W-L**; **W-T-L** only when some team in the league has a tie (`recordText(r, hasTie(rows))` in
  `components/fantasy/standings.js`).
- A missing value reads **—**; a displayed negative uses the real minus sign (−). An NBA team's score carries its sign (+12.0).
- **Projections:** only the projected best game — the expected best single game over a player's games
  that week (order statistics over his game scores this season, plus last season's while thin);
  NBA team = average margin × games. **Projected numbers are marked** with a distinct numeral
  treatment (italic digits), never a pill. Projected and actual never share a column without it.
- The best game can carry its **box line** beneath it in small text (32 PTS · 9 REB · 11 AST).
- In the draft list and the player card's Projected tab every number is a projection, so no italics there.
- **Never show projection flags** (new team, bad EPM, injured last season) anywhere (2026-10-08).
- **Injuries: current status only**, no history. Draft list: a red (out) / yellow (day-to-day) dot on
  the headshot, nothing else. Roster: the dot + status / expected return on the small line; games he'll
  miss read OUT. Player card: a status block.

## Clocks and times
- **Clocks** are LED dot digits sitting in their bar — no dark box, no label; lit dots glow, unlit
  segments faint (the other allowed fade); red under a minute. Countdowns are the same for everyone.
- **Lineup lock countdown** ("LOCKS IN" + one LED unit: 3 D → 14 H → 22 M → 41 S, then "Locked"):
  each player locks 5 minutes before his NBA team's first game of the week. *(Section to be expanded
  once the behavior settles.)*
- **Times** show on the viewer's own clock with no zone label ("7:30 PM") and no explanatory copy (2026-10-30;
  timestamps are stored with their zone). League dates — a week's days, a game day — are calendar days, the same for
  everyone (`components/fantasy/format.js`). UTC appears only in admin and replay tools.

## Roster and Matchup
- **Roster / My Team has no score, no opponent, no win %** — managing your roster has nothing to do
  with the score; scores live on Matchup (2026-10-08). The team header is a team switcher.
- **Matchup row** (each side mirrored): headshot (~48px) → player (last name, not bold; "G · LAL"
  small; truncates) → schedule (next game + three counts: played / today / to come — white / orange /
  outline dots) → top-5 FPTS contribution (skinny font) → score. The middle is narrow: score 52px /
  spot 34px / score 52px — check rendered widths. No green / yellow status colors, no pills, no "2/4"
  fractions or progress meters.

## Team Settings
"Your team" at the top — a header in the team color with the live look, then Name (name + short),
Picture (your upload / your Discord picture / an icon on your color) and Color; one Save at the bottom
left. Then Notifications, then Leave the league (red button under its sentence).

## Phones
- **Desktop first; phone testing comes at the end** of a feature, after desktop is right.
- Design at **390px**; must work at **360px** with no horizontal page scroll. One column, tabs for the
  zones, the main action full width.

## Placeholders (unchanged — keep them this way)
- Features that aren't built show an **"Under construction"** block: diagonal stripes of
  `--surface` / `--bg`, dashed border, gold-outlined label. Never fake data.

## Implementation notes
- Tokens: `theme.css`; top bar `components/shared/MainNav.css`; sidebar `components/shared/nav.css`;
  team palette `components/fantasy/teamColors.js`; glyphs `glyphs.js`; badges / logos / headshots
  `RosterBits.jsx` + `media.js`; LED digits `LedClock.jsx`; pop-up card `PlayerCard.jsx`.
- NBA imagery comes from the NBA CDN (headshots by NBA person id, logos by NBA team id). Fine for a
  private league; check licensing before going public. The CDN (Akamai) blocks headless browsers —
  screenshot with a normal user agent.

## Stats pages (lbrt.net/stats, 2026-10-16)
The stats product has its own palette and type, set on `.stats-ui` in `frontend/src/pages/stats/StatsNav.css`: warm
graphite surfaces (the site tokens read as GitHub's dark theme), body font for subtitles and headers. Modeled numbers
are italic **lavender** (`--accent-blue` inside `.stats-ui`). Key numbers (points added, effects, net, Box Creation) get
**cell shading, red / pink = good, blue = bad** (`shade.js`, `--good` / `--bad` in `StatsNav.css`; commissioner 2026-10-16, same as the shot charts): centered on the stat's average (0 for anything measured against
the league, else the median), scaled by the stat's own spread across every qualified player (1.4826 × MAD — not
min/max), no color within ±0.5 of a spread, full color at 2.5. Shaded cells keep the one text color. Team abbreviations
carry a square in the NBA team's primary color (`TeamChip`). Every table: player search + team filter, pager under the
table on the right. Shooting holds the breakdown as a tab, not a top-level page.
