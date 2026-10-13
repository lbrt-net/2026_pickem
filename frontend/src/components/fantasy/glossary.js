// Terms beyond everyday NBA box-score talk, used across fantasy pages. The Rules page lists them all; tables
// that use some show a "?" (GlossaryButton) with just theirs.
export const TERMS = {
  MAX: "A player's best single game in a fantasy week — his score for that week.",
  AVG: "Fantasy points per game played.",
  TOTAL: "A past season's weekly maxes added up — rewards the weeks he actually played.",
  "PROJ MAX": "Expected MAX in the weeks he plays, under the 2026-27 schedule. Games he sits here and there are in it; weeks he's out entirely aren't (PROJ GP shows those).",
  RK: "Ranked by value per week across the season: his PROJ MAX in the weeks he plays, plus a replacement-level player in the weeks he's out. The bid guide and auto-pick use the same value.",
  "PROJ AVG": "Expected fantasy points per game.",
  "MAX low / high": "A bad week (25th percentile) and a big week (90th percentile). The draft list's bar runs low → high with a dot at MAX and a thin line at AVG.",
  "Weeks by games": "A player's weeks grouped by how many games his NBA team plays that week.",
  FPTS: "Fantasy points.",
  "FG-": "Missed field goals.",
  "FT-": "Missed free throws.",
  "3PTM": "3-pointers made (on top of the points).",
  BLKD: "His own shot blocked.",
  "Δ": "Difference: an NBA team's point margin, or MAX minus PROJ MAX.",
  CLUTCH: "Points scored in clutch time (4th quarter or overtime, 5:00 or less left, score within 5), on top of the point.",
  TM: "An NBA team spot. It scores its defense: points allowed, shot clock violations forced and bonuses (see Rules).",
  GP: "Games played.",
  "PROJ GP": "Games he's expected to play, scaled to a full 82 (injuries and availability included).",
  "Rec bid": "Auction only: the bid we recommend for your team, from the same value as RK. Only you see yours.",
};
export const GLOSSARY = Object.entries(TERMS);
export const pick = keys => keys.map(k => [k, TERMS[k]]);
