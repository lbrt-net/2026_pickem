import { needsOutline, textOnColor } from "./teamColors";

// A team's icon: its uploaded logo, or a square of the team's color with its abbreviation
// (letters only from 24px up — below that they're unreadable). Square corners to match the site;
// people's avatars are the round ones. Colors come from the API (see teamColors.js).
export default function TeamIcon({ team, size = 24 }) {
  const box = { width: size, height: size, flexShrink: 0, boxSizing: "border-box", display: "inline-flex", verticalAlign: "middle" };
  if (team?.logo_url) return <img src={team.logo_url} alt="" style={{ ...box, objectFit: "cover" }} />;
  const color = team?.color;
  return (
    <span aria-hidden="true" style={{
      ...box,
      alignItems: "center",
      justifyContent: "center",
      background: color || "var(--surface-2)",
      color: textOnColor(color),
      border: needsOutline(color) ? "1px solid var(--border)" : 0,
      fontFamily: "var(--font-display)",
      fontSize: Math.round(size * 0.36),
      fontWeight: 700,
      letterSpacing: "0.03em",
      lineHeight: 1,
    }}>
      {size >= 24 && team?.abbreviation}
    </span>
  );
}
