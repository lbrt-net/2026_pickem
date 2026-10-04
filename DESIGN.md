# Design principles (lbrt.net)

The settled look, written down so the canvas can drop the boards it came from. The code is
the source of truth: `frontend/src/theme.css` (tokens), `components/shared/MainNav.css` (top
bar), `components/shared/nav.css` (sidebar + tabs), `components/fantasy/teamColors.js`
(team palette). Work in progress lives on the "lbrt.net Design" canvas.

## Ground rules
- **Dark mode only.** Every color comes from a `theme.css` token — no inline hex. Team colors
  are data from the API (the one exception).
- **One text color** (`--text`, near-white). Never dim or gray text; hierarchy comes from size,
  weight and the display face, not lowered contrast.
- **Two faces (2026-10-04):** `--font-body` is **Barlow** (everything); `--font-display` is **Barlow
  Condensed** (800, uppercase) only for impact: page titles, team names, scores, big numbers.

## Shapes
- **Slanted cuts**, not rounded corners: blocks and buttons use `clip-path` parallelograms
  (≈8–18 px slant). Square corners elsewhere; only people's avatars are round.
- **Orange (`--accent`) is the brand / primary color (2026-10-04):** the top-bar slash, section-label
  ticks, the active sidebar link, and main action buttons (text in `--accent-ink`).
- **Gold (`--accent-gold`) means "you" only:** "YOU" tags, your row / column, "you're up".
- **Section label:** small gold slanted tick + condensed uppercase label (13–15 px, 0.14em).
- Panels: `--surface` with a 1 px `--border`; nested rows separated by `--border`.

## Top bar & sidebar (built)
- Top bar: slanted home block with the menu button and "LBRT", a gold slash, product name,
  season pill (slanted, bordered), user block on the right with a gold-ringed avatar.
- Sidebar: sections with the gold tick label; the current page gets the gold notch + tinted
  slanted background; everything else plain.

## Team identity
- A fantasy team's icon is its uploaded logo, else a **square in the team color with a line-art
  glyph** (basketball, swish, ref jersey, whistle, sneaker, jersey — `glyphs.js`), assigned at
  random per team and kept. Glyphs are **line work, not solid silhouettes**: one connected outline
  where shapes join, no lines running through joins, thinner strokes on bigger icons. Default team
  colors come from the 26-color palette (`teamColors.js`), unique per league.
- **Position badges** (`RosterBits.jsx`): square, G blue / F green / C orange / TM purple
  (`--pos-*`); TM = an NBA team slot.
- **NBA imagery (2026-10-04):** team **logos** (NBA CDN, dark-background version) wherever an NBA
  team mark shows, falling back to the tricode square in official colors; player **headshots**
  (NBA CDN transparent cutouts, by NBA person id) on a soft glow of the team color, sitting on the
  row's bottom edge (`RosterBits.jsx` Headshot / NbaTeamSquare, `media.js`). Private league only —
  check licensing before going public. (Akamai blocks headless browsers; screenshot with a normal UA.)
- **Names on two lines**: first / LAST for players, city / NICKNAME for NBA teams.
- **Join button** is the one exception to the gold accent: a blue→violet→pink gradient (`--join-*`).

## Numbers & tables
- Big numbers (scores, records, ranks) in the display face, `tabular-nums`.
- Records read **W-L**; **W-T-L** only when some team in the league has a tie.
- **Projections (2026-10-04):** only the projected best game — the expected best single game over a
  player's games that week (order statistics over his game scores this season, plus last season's
  while thin); NBA team = average margin × games. Shown for future weeks / games still to play.

## Rules learned from the draft room (2026-10-03)
**One visual signal = one meaning.** Never reuse the same treatment for different purposes —
if everything pops the same way, nothing does.
- **Gold** (border, tint, edge) = *you* / *your turn* only: your row, your column, "you're up".
  Never a button, never a selected filter, never an admin control.
- **Blue solid button** (`--accent-blue`) = the one main action on screen (Draft, Bid, Nominate,
  Start, Join's equivalent). **Secondary buttons** = solid `--surface-3` with a visible light edge,
  so they never blend into the panel behind them. Disabled = faded, not hidden.
- **Filters / toggles / tabs** = a quiet segmented control (selected = lighter fill + bold).
  Not gold, not a button look.
- **Commissioner / admin controls** = a plain solid panel with a shield icon and the word
  "Commissioner". No gold, no dashed borders (dashed reads as half-built).
- **Urgency** = red only when it's real (clock under a minute).

**Keep containers visibly distinct** — blocky, not artsy, but every zone reads as its own thing:
- Each zone (board, list, your roster, budget…) is a panel with a **header strip**
  (`--surface-2`) over its body (`--surface`); filled cells are a third tone (`--surface-3`).
- Labels (row/column headers) sit on the panel background with no fill, so they never look like cells.
- **Empty / open spots** = graphite (`--slot-empty`) with a dashed edge — never the page background,
  never navy.
- Your own panel can carry your **team color** as a top edge.

**Type has a budget.** The display face (Barlow, uppercase) is for impact moments only: page
title, clocks, the high bid, a start time. Section titles, table headers, labels and budgets are
the body font. Info is a **plain list** (label · value) — no explainer blurbs, badges or extra
decoration unless asked.

**Clocks** are LED dot digits (`LedClock.jsx`) sitting in the bar — no dark box, no label; lit
dots glow, unlit segments faint; red under a minute. Countdowns are the same for everyone;
times show in the viewer's time zone with UTC spelled out.

**Small pieces:** names on boards = first initial + last ("S. Gilgeous-Alexander"); NBA squares
get a faint light edge; long lists (16 teams) scroll inside their panel.

**Phones are designed, not an afterthought:** one column, tabs for the zones (Available / Board /
Roster), the main action full width, nothing wider than 390px.

## Placeholders
- Features that aren't built show an **"Under construction"** block: diagonal stripes of
  `--surface`/`--bg`, dashed border, gold-outlined label. Never fake data.
