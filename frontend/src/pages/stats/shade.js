// Cell shading for good / bad numbers (2026-10-16). Objective and balanced:
//  - centered on what "average" means for the stat (0 for anything measured against the league, else the median),
//  - scaled by the stat's own spread across every qualified player (robust: 1.4826 × median absolute deviation),
//    not by the min and max on screen, so one outlier can't wash out everyone else and red and blue use the same yardstick,
//  - a neutral band: within ±0.5 of a spread, no color at all; full color at 2.5 spreads.
export function makeShade(values, { center = 0 } = {}) {
  const v = values.filter(x => Number.isFinite(x));
  if (!v.length) return () => undefined;
  const med = a => { const s = [...a].sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
  const c = center === "median" ? med(v) : center;
  const spread = 1.4826 * med(v.map(x => Math.abs(x - c))) || 1;
  return x => {
    if (!Number.isFinite(x)) return undefined;
    const z = (x - c) / spread, a = Math.abs(z);
    if (a < 0.5) return undefined;
    const t = Math.min(1, (a - 0.5) / 2);
    const pct = Math.round(10 + t * 45);
    return { background: `color-mix(in srgb, var(${z > 0 ? "--good" : "--bad"}) ${pct}%, transparent)` };
  };
}
