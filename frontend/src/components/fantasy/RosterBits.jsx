import { NBA_TEAMS } from "./nbaTeams";
import { textOnColor } from "./teamColors";

// Small roster pieces shared by Home / My Team (DESIGN.md): the position badge (G/F/C/TM),
// the NBA team abbreviation square in official colors, and two-line names.

// Position colors (theme.css --pos-*): G blue, F green, C orange; TM (NBA team slot) purple.
const POSITION_COLORS = { G: "var(--pos-g)", F: "var(--pos-f)", C: "var(--pos-c)", TM: "var(--pos-tm)" };

export function PositionBadge({ entry, size = 34 }) {
  const label = entry?.kind === "nba_team" ? "TM" : entry?.position || "—";
  const bg = POSITION_COLORS[label];
  return (
    <span style={{
      width: size, height: size, flexShrink: 0, display: "inline-flex", alignItems: "center", justifyContent: "center",
      background: bg || "var(--surface-2)", fontFamily: "var(--font-display)", fontSize: Math.round(size * 0.47),
      fontWeight: 700, letterSpacing: "0.04em",
    }} title={{ G: "Guard", F: "Forward", C: "Center", TM: "NBA team slot" }[label] || "Position unknown"}>
      {label}
    </span>
  );
}

// NBA team square: primary-color fill, secondary-color stripe (trucolor.net colors).
export function NbaTeamSquare({ tricode, size = 34 }) {
  const t = NBA_TEAMS[tricode];
  if (!t) return <span style={{ width: size, height: size, flexShrink: 0 }} />;
  return (
    <span title={`${t.city} ${t.nickname}`} style={{
      width: size, height: size, flexShrink: 0, boxSizing: "border-box", display: "inline-flex", alignItems: "center",
      justifyContent: "center", background: t.primary, color: textOnColor(t.primary),
      // Light edge on every square; the secondary color is a stripe inside it, so the shape stays square.
      border: "1px solid color-mix(in srgb, var(--text) 18%, transparent)", boxShadow: `inset 0 -4px 0 ${t.secondary}`,
      fontFamily: "var(--font-display)", fontSize: Math.round(size * 0.4), fontWeight: 700, letterSpacing: "0.03em",
    }}>
      {tricode}
    </span>
  );
}
