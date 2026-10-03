// Which fantasy pages are switched on for the current testing round. Core features only for
// now; everything else comes back one at a time as sandbox testing needs it ("organic growth").
// Off pages disappear from the nav (nav.js filters on this) and their routes show a
// "not in this round" page (App.jsx). Flip a flag to bring a page back.
export const FEATURES = {
  "/draft/recap": false,
  "/recap": false,
  "/trades": false,
  "/transactions": false,
  "/tenure": false,
};

// Paths not listed are on.
export const isOn = path => FEATURES[path] !== false;

// Features *inside* pages, same idea. (Waivers, roster caps, trades etc. aren't built at all,
// so there's nothing to switch off for them yet.)
export const PAGE_FEATURES = {
  playerGameLog: false, // game-by-game stat history + weekly totals on the player page
  pastSeasons: false,   // season pickers for 2022-23 → 2025-26 (Schedule shows 2026-27 only)
};

export const featureOn = name => PAGE_FEATURES[name] !== false;
