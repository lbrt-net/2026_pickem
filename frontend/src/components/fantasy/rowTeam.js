import { tc } from "../../pages/fantasy/player/art";

// A list row's style: its NBA team's primary color for the left-edge wash (rows get className "lc-row", ListControls.css).
export const rowTeam = code => ({ "--tc": (tc(code) || [])[2] || "transparent" });
