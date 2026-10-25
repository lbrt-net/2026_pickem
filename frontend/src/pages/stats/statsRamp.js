// The stats pages' shared 0–100% color ramp (2026-10-20): dark purple → purple (25%) → red (50%) → orange (75%) →
// yellow (100%), so 25 / 50 / 75% read as different colors. Lineups (share of games on the floor), Standings (odds).
const STOPS = [[0, [42, 22, 66]], [0.25, [110, 40, 140]], [0.5, [205, 52, 72]], [0.75, [246, 136, 40]], [1, [252, 232, 110]]];
export function ramp(v) {
  for (let n = 1; n < STOPS.length; n++) if (v <= STOPS[n][0]) {
    const [x0, c0] = STOPS[n - 1], [x1, c1] = STOPS[n], k = (v - x0) / (x1 - x0);
    return `rgb(${c0.map((c, i) => Math.round(c + (c1[i] - c) * k)).join(",")})`;
  }
  return `rgb(${STOPS[STOPS.length - 1][1].join(",")})`;
}
export const RAMP_CSS = `linear-gradient(90deg, ${STOPS.map(([x, c]) => `rgb(${c.join(",")}) ${x * 100}%`).join(", ")})`;
// text that stays readable on a ramp color: dark on the bright end (orange / yellow), the one text color elsewhere
export const rampInk = v => (v >= 0.62 ? "#1a1208" : undefined);

// win chance (2026-10-25, commissioner: "red good, blue bad … 45 should be damn near white … get rid of the teal and
// yellow, just white to blue or orange"; "why are you making orange so prominent"): white at 50, near white 45–55,
// white → light red → red → deep red (pink tint only near 100) up, white → light blue → blue → indigo → purple down
const WIN = [[0, [52, 28, 110]], [0.1, [55, 50, 160]], [0.2, [50, 95, 200]], [0.3, [110, 150, 225]], [0.4, [186, 204, 240]],
  [0.45, [235, 239, 247]], [0.5, [247, 246, 243]], [0.55, [250, 236, 234]], [0.6, [244, 190, 186]], [0.7, [232, 120, 112]],
  [0.8, [214, 60, 52]], [0.9, [190, 30, 50]], [1, [214, 32, 100]]];
const winRgb = v => {
  const x = Math.max(0, Math.min(1, v));
  for (let n = 1; n < WIN.length; n++) if (x <= WIN[n][0]) {
    const [x0, c0] = WIN[n - 1], [x1, c1] = WIN[n], k = (x - x0) / (x1 - x0);
    return c0.map((c, i) => Math.round(c + (c1[i] - c) * k));
  }
  return WIN[WIN.length - 1][1];
};
export const winRamp = v => `rgb(${winRgb(v).join(",")})`;
// dark text on the light middle of the scale, the one text color on the dark ends
export const winInk = v => { const [r, g, b] = winRgb(v); return 0.299 * r + 0.587 * g + 0.114 * b > 150 ? "#1a1208" : undefined; };
