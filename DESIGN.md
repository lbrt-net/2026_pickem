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
- **Two faces:** `--font-display` (Barlow Condensed, 600/700, UPPERCASE, letter-spaced) for page
  titles, section labels, nav, big numbers; `--font-body` (system sans) for everything else.

## Shapes
- **Slanted cuts**, not rounded corners: blocks and buttons use `clip-path` parallelograms
  (≈8–18 px slant). Square corners elsewhere; only people's avatars are round.
- **Gold (`--accent-gold`) means "current / you":** the active sidebar link (gold notch), the
  section-label tick before a heading, "YOU" tags, your row highlighted with a gold tint
  (`color-mix(… gold 12–16%, surface)`).
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
- **NBA team squares**: the tricode on the team's official primary color with a secondary-color
  stripe along the bottom (`nbaTeams.js`, from trucolor.net), same size as the position badge.
- **Names on two lines**: first / LAST for players, city / NICKNAME for NBA teams.
- **Join button** is the one exception to the gold accent: a blue→violet→pink gradient (`--join-*`).

## Numbers & tables
- Big numbers (scores, records, ranks) in the display face, `tabular-nums`.
- Records read **W-L**; **W-T-L** only when some team in the league has a tie.
- No projected numbers anywhere until there's a real projection method.

## Placeholders
- Features that aren't built show an **"Under construction"** block: diagonal stripes of
  `--surface`/`--bg`, dashed border, gold-outlined label. Never fake data.
