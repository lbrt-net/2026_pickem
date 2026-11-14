# Mid-Season Report redesign (mockups, 2026-11-12 → 11-14)

Approved looks, built as standalone HTML/PNG mockups from a report work folder. **Not wired into `aw.js` yet.**

- **Awards (ballot cards):** `card.sh GROUP` → `mock.py` → `sc_g.py` (percentile band) → `flair2/3g/4/9g.py` (team panel color,
  knockout logo mark from `kit/`, two-color strips). Groups: Scoring, Playmaking, Boards, Stocks, Most improved, Top rookie, Sixth man.
  Percentiles = the player page's (`/players/{id}/page?actual=true`, `fetchpages.sh`): 20+ games, 20+ MPG, 500+ min, scaled to the season.
- **All-Fantasy:** `af.py` → full team-color tiles, knockout mark, small position chip, points block in the team's second color,
  owner band (icon + name, acquisition + weeks on roster).
- **Superlatives (comic look, superlatives only):** `sup.py` (Best game on the bench), `sup_big.py` (Biggest game),
  `stickers.py` (one fixed comic sticker per scoring category; red numbers only for negatives). Titles are designed one by one
  (blob sticker + starburst, Permanent Marker big words / Caveat Brush filler words 2px smaller / Kalam in the starburst).
- `alt.py` = the first rounded/sticker exploration (no pills, no tilts — see memory).
- `kit/` = team colors (`kit.json`) + logo marks/knockouts (`build_kit.py`, `knock.py`). City skylines are **not** here (shelved).
- `mocks/` = the last rendered PNG of each.

Run from a folder `S` holding `work3/` (from `run.py --work S/work3`) and `hs/` (headshots; `card.sh` downloads them):
`cd S && bash <repo>/scripts/midseason_report/redesign/card.sh Boards` (screenshots with headless Chrome).
