import { NBA_TEAMS } from "../../components/fantasy/nbaTeams";
import { WNBA_TEAMS, inWnba } from "./wnbaTeams";

// A stats table row's left edge in the player's team color (the row style carries it as --tc; 2026-10-16).
// A team whose main color is too dark to see on the page (Denver / Clippers / Pacers navy, Nets black) uses its
// second color instead; only if both are dark is the main color brightened.
const lum = hex => {
  const h = (hex || "").replace("#", "");
  if (h.length !== 6) return 0;
  const [r, g, b] = [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16));
  return 0.299 * r + 0.587 * g + 0.114 * b;
};
export const teamEdge = team => {
  const c = (inWnba() ? WNBA_TEAMS : NBA_TEAMS)[(team || "").split("/").pop()];
  if (!c) return undefined;
  const pick = lum(c.primary) >= 45 ? c.primary
    : lum(c.secondary) >= 45 ? c.secondary
      : `color-mix(in srgb, ${c.primary} 60%, white)`;
  return { "--tc": pick };
};
