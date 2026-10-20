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
