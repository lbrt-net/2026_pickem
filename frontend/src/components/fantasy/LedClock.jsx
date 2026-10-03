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
  const { on, off, w, h } = useMemo(() => {
    const lit = [], dim = [];
    let x0 = 0;
    for (const ch of String(text)) {
      if (ch === ":") {
        lit.push([x0 + step * 1.5, 5 * step], [x0 + step * 1.5, 11 * step]);
        x0 += step * 4;
        continue;
      }
      const segs = SEGS[ch] || "";
      for (const s of "abcdefg") for (const [x, y] of segDots(s)) (segs.includes(s) ? lit : dim).push([x0 + x * step, y * step]);
      x0 += step * 13;
    }
    return { on: lit, off: dim, w: Math.round(x0 - step * 2 + r * 2 + 8), h: Math.round(16 * step + r * 2 + 8) };
  }, [text, step, r]);
  const dot = ([x, y], i) => <circle key={i} cx={x + r + 4} cy={y + r + 4} r={r} />;
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} role="img" aria-label={label || `${text} left`}>
      <defs>
        <filter id={`glow-${id}`} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="2.4" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      <g fill="var(--led-off)">{off.map(dot)}</g>
      <g fill={urgent ? "var(--led-red)" : "var(--led-on)"} filter={`url(#glow-${id})`}>{on.map(dot)}</g>
    </svg>
  );
}
