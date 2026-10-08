import { useId } from "react";

// MAX low – MAX high as an orange band (fading in from the low end) with a white dot at MAX. The list passes
// one `scale` (0 → its biggest MAX high) so every row shares it: a wide spread and a tight one compare at a
// glance, and the bottom of the pool still reads.
export default function RangeBar({ low, mid, high, width = 220, scale = 100 }) {
  const id = useId().replace(/:/g, "");
  if (low == null || high == null) return null;
  const x = v => 6 + (Math.max(0, Math.min(scale, v)) / scale) * (width - 12);
  return (
    <svg width={width} height="18" role="img" aria-label={`${low} to ${high}`} style={{ display: "block", margin: "0 auto" }}>
      <defs>
        <linearGradient id={`rb-${id}`} x1="0" x2="1">
          <stop offset="0" stopColor="var(--accent)" stopOpacity="0.35" />
          <stop offset="1" stopColor="var(--accent)" stopOpacity="1" />
        </linearGradient>
      </defs>
      <line x1="6" y1="9" x2={width - 6} y2="9" stroke="color-mix(in srgb, var(--text) 14%, transparent)" strokeWidth="2" strokeLinecap="round" />
      <rect x={x(low)} y="4" width={Math.max(3, x(high) - x(low))} height="10" rx="5" fill={`url(#rb-${id})`} />
      {mid != null && <circle cx={x(mid)} cy="9" r="5" fill="var(--text)" stroke="var(--bg)" strokeWidth="1.5" />}
    </svg>
  );
}
