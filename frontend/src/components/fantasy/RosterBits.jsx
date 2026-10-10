import { useState } from "react";
import { NBA_TEAMS } from "./nbaTeams";
import { headshotSrcSet, headshotUrl, logoUrl } from "./media";
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
// NBA team mark: the team's real logo (NBA CDN, dark-background version); if it can't load, the
// tricode square in official colors (primary fill, secondary stripe).
export function NbaTeamSquare({ tricode, size = 34 }) {
  const [failed, setFailed] = useState(false);
  const t = NBA_TEAMS[tricode];
  if (!t) return <span style={{ width: size, height: size, flexShrink: 0 }} />;
  const src = logoUrl(tricode);
  if (src && !failed) {
    return (
      <img src={src} alt="" title={`${t.city} ${t.nickname}`} width={size} height={size} loading="lazy" onError={() => setFailed(true)}
        style={{ width: size, height: size, flexShrink: 0, objectFit: "contain" }} />
    );
  }
  return (
    <span title={`${t.city} ${t.nickname}`} style={{
      width: size, height: size, flexShrink: 0, boxSizing: "border-box", display: "inline-flex", alignItems: "center",
      justifyContent: "center", background: t.primary, color: textOnColor(t.primary),
      border: "1px solid color-mix(in srgb, var(--text) 18%, transparent)", boxShadow: `inset 0 -4px 0 ${t.secondary}`,
      fontFamily: "var(--font-display)", fontSize: Math.round(size * 0.4), fontWeight: 700, letterSpacing: "0.03em",
    }}>
      {tricode}
    </span>
  );
}

// Player headshot: the NBA's transparent cutout on a soft glow of his team's color, bottom-aligned
// so it can sit on a row's bottom edge. (A player without a photo gets the NBA's own silhouette.)
export function Headshot({ playerId, tricode, width = 64, height = 47 }) {
  const color = NBA_TEAMS[tricode]?.primary || "var(--surface-3)";
  return (
    <span className="headshot" style={{ position: "relative", width, height, flexShrink: 0, display: "inline-block" }}>
      <span aria-hidden="true" style={{
        position: "absolute", left: "12%", right: "12%", bottom: 0, height: "72%", borderRadius: "999px 999px 0 0", opacity: 0.6,
        background: `radial-gradient(ellipse at 50% 100%, ${color} 0%, transparent 70%)`,
      }} />
      <img src={headshotUrl(playerId)} srcSet={headshotSrcSet(playerId)} alt="" loading="lazy" width={width} height={height}
        style={{ position: "absolute", left: 0, bottom: 0, width, height, objectFit: "contain", objectPosition: "bottom" }} />
    </span>
  );
}
