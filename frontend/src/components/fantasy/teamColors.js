// Team color palette (keep in sync with TEAM_COLORS in backend/fantasy_2026_27/settings.py,
// which assigns the defaults). Grouped for the Team Settings picker; `order` is the default order.
// Owners can also pick any other color, so helpers below work on any hex.
export const TEAM_COLOR_GROUPS = [
  { label: "Vivid", colors: [
    ["Electric Blue", "#357dfa"], ["Blaze", "#e55006"], ["Hot Pink", "#f32292"], ["Aqua", "#089284"],
    ["Violet", "#9d61f7"], ["Neon Green", "#119639"], ["Scarlet", "#f43643"], ["Cyan", "#058db0"],
  ] },
  { label: "Deep", colors: [
    ["Cobalt", "#1942e5"], ["Brick", "#a42d1b"], ["Orchid", "#952199"], ["Emerald", "#0b6544"],
    ["Grape", "#802bb8"], ["Forest", "#1e661e"], ["Berry", "#a91c4f"], ["Ocean", "#0c5c92"],
  ] },
  { label: "Muted", colors: [
    ["Slate", "#52637b"], ["Dusty Rose", "#8c4f63"], ["Sage", "#4e684e"], ["Mauve", "#74577e"],
    ["Clay", "#865641"], ["Taupe", "#6d5f4f"], ["Denim", "#466482"], ["Olive Drab", "#5e653d"],
  ] },
  { label: "Neutral", colors: [["Near Black", "#1f2430"], ["Near White", "#eceff3"]] },
];

export function teamColorName(hex) {
  const h = (hex || "").toLowerCase();
  for (const g of TEAM_COLOR_GROUPS) for (const [name, c] of g.colors) if (c === h) return name;
  return null;
}

// WCAG relative luminance / contrast, for colors owners pick themselves.
function luminance(hex) {
  const c = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map(v => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
function contrast(a, b) {
  const x = luminance(a), y = luminance(b);
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}
const TEXT = "#e6edf3", BG = "#0f1117"; // theme.css --text / --bg

const isHex = hex => /^#[0-9a-f]{6}$/i.test(hex || "");

// Letters on a team color: the site text color, or dark when that wouldn't be readable.
export const textOnColor = hex => (!isHex(hex) || contrast(hex, TEXT) >= 3 ? "var(--text)" : "var(--bg)");

// Colors too close to the page background get an outline so the badge doesn't vanish.
export const needsOutline = hex => !isHex(hex) || contrast(hex, BG) < 1.6;
