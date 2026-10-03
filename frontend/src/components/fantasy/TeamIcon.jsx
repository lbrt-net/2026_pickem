import { needsOutline, textOnColor } from "./teamColors";
import { GLYPHS, glyphStroke } from "./glyphs";

// A team's icon: its uploaded logo, or a square of the team's color with its line-art glyph
// (one of six, assigned per team — see glyphs.js / DESIGN.md). Square corners to match the site;
// people's avatars are the round ones. Colors and glyph come from the API.
export default function TeamIcon({ team, size = 24 }) {
  const box = { width: size, height: size, flexShrink: 0, boxSizing: "border-box", display: "inline-flex", verticalAlign: "middle" };
  if (team?.logo_url) return <img src={team.logo_url} alt="" style={{ ...box, objectFit: "cover" }} />;
  const color = team?.color;
  const d = GLYPHS[team?.glyph] || GLYPHS.basketball;
  const inner = Math.round(size * 0.62);
  return (
    <span aria-hidden="true" style={{
      ...box,
      alignItems: "center",
      justifyContent: "center",
      background: color || "var(--surface-2)",
      color: textOnColor(color),
      border: needsOutline(color) ? "1px solid var(--border)" : 0,
    }}>
      <svg width={inner} height={inner} viewBox="0 0 24 24">
        <path d={d} stroke="currentColor" strokeWidth={glyphStroke(size)} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  );
}
