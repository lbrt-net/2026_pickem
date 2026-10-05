import { useId, useMemo } from "react";

// Big matchup score (design: canvas "Matchup v6"): 5×7 dot-matrix digits, lit dots in the team's
// color pushed to full brightness with a glow, unlit dots barely there (5%). Digits, ".", "+", "-".
const F5 = {
  0: ["01110", "10001", "10011", "10101", "11001", "10001", "01110"], 1: ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
  2: ["01110", "10001", "00001", "00010", "00100", "01000", "11111"], 3: ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
  4: ["00010", "00110", "01010", "10010", "11111", "00010", "00010"], 5: ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
  6: ["00110", "01000", "10000", "11110", "10001", "10001", "01110"], 7: ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
  8: ["01110", "10001", "10001", "01110", "10001", "10001", "01110"], 9: ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
  ".": ["0", "0", "0", "0", "0", "0", "1"],
  "-": ["000", "000", "000", "111", "000", "000", "000"],
  "+": ["000", "000", "010", "111", "010", "000", "000"],
};

// An LED at full brightness: the hue's strongest channel maxed, then lifted toward white.
// Gray / black team colors light up white.
function ledColor(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex || "");
  if (!m) return "var(--text)";
  let [r, g, b] = [0, 2, 4].map(i => parseInt(m[1].slice(i, i + 2), 16));
  const mx = Math.max(r, g, b) || 1;
  [r, g, b] = [r, g, b].map(c => Math.min(255, Math.round((c * 255) / mx)));
  if (Math.max(r, g, b) - Math.min(r, g, b) < 60) return "var(--text)";
  const lift = c => Math.round(c + (255 - c) * 0.22);
  return `rgb(${lift(r)}, ${lift(g)}, ${lift(b)})`;
}

export default function LedScore({ text, color, pitch = 6.6, r = 2.75, label }) {
  const id = useId().replace(/:/g, "");
  const { on, off, w, h } = useMemo(() => {
    const lit = [], dim = [];
    let x0 = 0;
    for (const ch of String(text)) {
      const g = F5[ch];
      if (!g) continue;
      g.forEach((row, y) => [...row].forEach((bit, x) => (bit === "1" ? lit : dim).push([x0 + x * pitch + pitch / 2, y * pitch + pitch / 2])));
      x0 += g[0].length * pitch + pitch * 0.6;
    }
    return { on: lit, off: dim, w: Math.max(1, Math.round(x0 - pitch * 0.6)), h: Math.round(7 * pitch) };
  }, [text, pitch]);
  const lit = ledColor(color);
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} role="img" aria-label={label || String(text)} style={{ overflow: "visible", display: "block" }}>
      <defs>
        <filter id={`g-${id}`} x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur stdDeviation="2.2" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      <g style={{ fill: "color-mix(in srgb, var(--text) 5%, transparent)" }}>{off.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={r} />)}</g>
      <g fill={lit} filter={`url(#g-${id})`}>{on.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={r} />)}</g>
    </svg>
  );
}
