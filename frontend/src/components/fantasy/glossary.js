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
  "Rec bid": "Auction only: what he's worth to your team. Your spare money, split by how far he is above the player who'd replace him in the spot he'd fill for you. A player who'd only sit on your bench is $1. Only you see yours.",
};
export const GLOSSARY = Object.entries(TERMS);
// The draft room's short Rec bid card (warm-up) and its "?" by the bidding (BIDDING_GUIDE.md).
export const REC_BID_HELP = [
  ["What it is", "What a player is worth to your team: your spare money, split by how far he is above the player who'd replace him in your lineup."],
  ["When it changes", "After every sale, as players leave the board and your money and open spots change."],
  ["What it doesn't do", "Predict what the room will pay, or look at other teams' money. Stars often go higher."],
];
export const pick = keys => keys.map(k => [k, TERMS[k]]);
