# Design principles (lbrt.net)

The settled look. The code is the source of truth (`frontend/src/theme.css` for tokens); work in
progress lives on the "lbrt.net Design" canvas. Updated 2026-10-04.

## Ground rules
- **Dark mode only.** Every color comes from a `theme.css` token — no inline hex. Team colors are
  data from the API (the one exception).
- **Text color:** one text color, `--text` (near-white). **Faded / gray text is banned.** Hierarchy
  comes from size, weight, case and the display face. The only clear exceptions: a disabled control,
  and unlit LED segments. Bench numbers are **not** faded — the bench is labeled, not dimmed.
- **Two faces:** `--font-body` is **Barlow** for everything. `--font-display` is **Barlow Condensed**
  (800, uppercase) for exactly this list: **page titles, team names, scores, records, ranks, bids,
  start times.** Section labels and table headers are the **body** face (small, bold, uppercase,
  letter-spaced). Clocks use LED digits, not a font.
- **Fewer formats:** one format per data type across the site (a game, a score, an opponent, a date,
  a time). Don't invent a new way to show the same thing on a new page.

## Color roles — one signal, one meaning
- **Orange (`--accent`)** = the brand: top-bar slash, section-label ticks, the active sidebar link,
  and the main commit action on a screen (Draft, Bid, Save — solid, text in `--accent-ink`).
- **Different kinds of actions get different looks** — never one button style for everything.
  Filters, pagination, add / wishlist, drop, and the main action each get their own treatment
  (e.g. orange solid for the main action, blue `--accent-blue` for add / queue-type actions,
  segmented control for filters, plain outlined for pagination, red outline for drop / remove).
  Pick per feature and keep it consistent site-wide.
- **Gold (`--accent-gold`)** = **you**: "YOU" tags, your row / column, "you're up", your avatar ring
  in the top bar, and the Under construction label. Never a button, a filter, or an admin control.
- **Your team color** (picked in Team settings) is your accent across the site — scorebug, team
  headers, draft board — and applies even when the team has a picture.
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
  teams) in roster and list rows; **initial + last** ("S. Gilgeous-Alexander") on grids and boards.
  Long names truncate with an ellipsis and show the full name on hover.

## Numbers
- Numbers in tables are right-aligned with `tabular-nums`; headers align with their values.
- Records read **W-L**; **W-T-L** only when some team in the league has a tie.
- **Projections:** only the projected best game — the expected best single game over a player's games
  that week (order statistics over his game scores this season, plus last season's while thin);
  NBA team = average margin × games. **Projected numbers are marked** with a distinct numeral
  treatment (italic digits), never a pill. Projected and actual never share a column without it.
- The best game can carry its **box line** beneath it in small text (32 PTS · 9 REB · 11 AST).

## Clocks and times
- **Clocks** are LED dot digits sitting in their bar — no dark box, no label; lit dots glow, unlit
  segments faint (the other allowed fade); red under a minute. Countdowns are the same for everyone.
- **Lineup lock countdown** ("LOCKS IN" + one LED unit: 3 D → 14 H → 22 M → 41 S, then "Locked"):
  each player locks 5 minutes before his NBA team's first game of the week. *(Section to be expanded
  once the behavior settles.)*
- **Times** show in the viewer's zone with its abbreviation ("7:30 PM CT"), with no explanatory copy.
  UTC appears only in admin and replay tools.

## Scorebug (My Team header)
Your team color fills the left block (icon + monogram), the opponent's the right; large score digits
in the center with "Week N · Day x / 7", "Final" or "Projected"; faint court lines behind; text on a
light team color switches to dark. *(Section to be expanded once the behavior settles.)*

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
