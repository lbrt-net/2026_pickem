import { NBA_TEAMS } from "../../components/fantasy/nbaTeams";
import { accent } from "../../components/fantasy/standings";

// A stats table row's left edge in the player's team color (the row style carries it as --tc; 2026-10-16).
export const teamEdge = team => {
  const c = NBA_TEAMS[(team || "").split("/").pop()];
  return c ? { "--tc": accent(c.primary) } : undefined;  // very dark colors lifted so the edge shows
};
