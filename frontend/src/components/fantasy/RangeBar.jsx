// MAX low – MAX high as a bar with a dot at MAX, on one 0–100 scale for every player, so a wide spread
// (Dončić) and a tight one (Jokić) compare at a glance, and the bottom of a 200-player pool still reads.
const SCALE = 100;

export default function RangeBar({ low, mid, high, width = 100 }) {
  if (low == null || high == null) return null;
  const x = v => 4 + (Math.max(0, Math.min(SCALE, v)) / SCALE) * (width - 8);
  return (
    <svg width={width} height="16" role="img" aria-label={`${low} to ${high}`} style={{ display: "block", margin: "0 auto" }}>
      <line x1="4" y1="8" x2={width - 4} y2="8" stroke="color-mix(in srgb, var(--text) 12%, transparent)" strokeWidth="2" />
      <rect x={x(low)} y="4" width={Math.max(2, x(high) - x(low))} height="8" rx="4" fill="color-mix(in srgb, var(--text) 45%, transparent)" />
      {mid != null && <circle cx={x(mid)} cy="8" r="4" fill="var(--text)" />}
    </svg>
  );
}
