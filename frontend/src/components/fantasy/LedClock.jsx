import { useId, useMemo } from "react";

// Shot-clock style digits (design: canvas "Draft clock — states"): seven segments drawn as rows
// of dots, unlit segments faint (--led-off), lit dots glow (--led-on, or --led-red when urgent).
// Plain SVG, no images. `text` is digits and ":" (e.g. "8:42").
const SEGS = { 0: "abcdef", 1: "bc", 2: "abged", 3: "abgcd", 4: "fgbc", 5: "afgcd", 6: "afgedc", 7: "abc", 8: "abcdefg", 9: "abcdfg" };

function segDots(seg) {
  if ("agd".includes(seg)) {
    const y = { a: 0, g: 8, d: 16 }[seg];
    return [1, 2, 3, 4, 5, 6, 7].map(x => [x, y]);
  }
  const x = "fe".includes(seg) ? 0 : 8;
  const ys = "fb".includes(seg) ? [1, 2, 3, 4, 5, 6, 7] : [9, 10, 11, 12, 13, 14, 15];
  return ys.map(y => [x, y]);
}

export default function LedClock({ text, step = 4.4, r = 1.8, urgent = false, label }) {
  const id = useId().replace(/:/g, "");
  // Every dot is drawn in both layers on every frame; only which ones are lit changes. The glowing layer keeps the
  // same shape whatever the digits, so the browser never has to re-measure its glow — some graphics cards skipped
  // repainting when it shrank (8 → 7 held the 8 on screen for an extra second).
  const { dots, w, h } = useMemo(() => {
    const dots = []; // [x, y, lit]
    let x0 = 0;
    for (const ch of String(text)) {
      if (ch === ":") {
        dots.push([x0 + step * 1.5, 5 * step, true], [x0 + step * 1.5, 11 * step, true]);
        x0 += step * 4;
        continue;
      }
      const segs = SEGS[ch] || "";
      for (const s of "abcdefg") for (const [x, y] of segDots(s)) dots.push([x0 + x * step, y * step, segs.includes(s)]);
      x0 += step * 13;
    }
    return { dots, w: Math.round(x0 - step * 2 + r * 2 + 8), h: Math.round(16 * step + r * 2 + 8) };
  }, [text, step, r]);
  const dot = (show) => ([x, y, lit], i) => <circle key={i} cx={x + r + 4} cy={y + r + 4} r={r} opacity={show(lit) ? 1 : 0} />;
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} role="img" aria-label={label || `${text} left`}>
      <defs>
        <filter id={`glow-${id}`} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="2.4" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      <g fill="var(--led-off)">{dots.map(dot(lit => !lit))}</g>
      <g fill={urgent ? "var(--led-red)" : "var(--led-on)"} filter={`url(#glow-${id})`}>{dots.map(dot(lit => lit))}</g>
    </svg>
  );
}
