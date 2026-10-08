// Terms beyond everyday NBA box-score talk, used across fantasy pages. The Rules page lists them all; tables
// that use some show a "?" (GlossaryButton) with just theirs.
export const TERMS = {
  MAX: "A player's best single game in a fantasy week — his score for that week.",
  AVG: "Fantasy points per game played.",
  TOTAL: "A past season's weekly maxes added up — rewards the weeks he actually played.",
  "PROJ MAX": "Expected MAX under the 2026-27 schedule, averaged over the season's weeks. The draft ranks and auto-picks on this.",
  "PROJ AVG": "Expected fantasy points per game.",
  "MAX low / high": "A bad week (25th percentile) and a big week (90th percentile). The draft list's bar runs low → high with a dot at MAX.",
  "Weeks by games": "A player's weeks grouped by how many games his NBA team plays that week.",
  FPTS: "Fantasy points.",
  "FG-": "Missed field goals (−0.5 each).",
  "FT-": "Missed free throws (−1 each).",
  "3PTM": "3-pointers made (+0.5 each, on top of the points).",
  BLKD: "His own shot blocked (−0.5 each).",
  "Δ": "Difference: an NBA team's point margin, or MAX minus PROJ MAX.",
  CLUTCH: "Points scored in clutch time (4th quarter or overtime, 5:00 or less left, score within 5): +2 each on top of the point.",
  TM: "An NBA team spot. It scores its defense: points allowed, shot clock violations forced and bonuses (see Rules).",
  GP: "Games played.",
  "Rec bid": "Auction only: the bid we recommend for your team. Only you see yours.",
};
export const GLOSSARY = Object.entries(TERMS);
export const pick = keys => keys.map(k => [k, TERMS[k]]);
