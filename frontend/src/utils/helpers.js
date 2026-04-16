export const API = "";

// ---------------------------------------------------------------------------
// Team colors — full multi-zone system
//   bg:      row background tint when selected (primary ~15-20% opacity)
//   border:  left border stripe (primary or most distinctive color)
//   text:    team name when selected (readable on dark bg)
//   seed:    seed number color (secondary accent — small, punchy)
//   accent:  checkmark + games button border+text when selected
//   lockBar: top lock-time strip background (subtle tertiary tint)
//   divider: mdiv line color between teams
// ---------------------------------------------------------------------------
export const TEAM_COLORS = {
  // ── West ──────────────────────────────────────────────────────────────────
  "LA Lakers": {
    bg:      "rgba(85,37,130,0.20)",   // purple field
    border:  "#552583",                 // purple stripe
    text:    "#f9a01b",                 // gold name
    seed:    "#f9a01b",                 // gold seed
    accent:  "#f9a01b",                 // gold checkmark + game btn
    lockBar: "rgba(85,37,130,0.35)",
    divider: "#552583",
  },
  "Houston": {
    bg:      "rgba(206,17,65,0.16)",
    border:  "#ce1141",
    text:    "#ffffff",
    seed:    "#c4ced4",                 // silver seed
    accent:  "#c4ced4",
    lockBar: "rgba(206,17,65,0.25)",
    divider: "#ce1141",
  },
  "Denver": {
    bg:      "rgba(139,33,49,0.25)",    // flatiron red bg — navy too close to app bg
    border:  "#8b2131",                 // flatiron red stripe
    text:    "#fec524",                 // sunshine yellow name
    seed:    "#fec524",
    accent:  "#fec524",
    lockBar: "rgba(139,33,49,0.40)",
    divider: "#8b2131",
  },
  "Minnesota": {
    bg:      "rgba(12,35,64,0.55)",     // midnight field
    border:  "#236192",                 // lake blue stripe
    text:    "#78be20",                 // aurora green name — the pop
    seed:    "#78be20",                 // aurora green seed
    accent:  "#78be20",
    lockBar: "rgba(35,97,146,0.30)",
    divider: "#236192",
  },
  "Oklahoma City": {
    bg:      "rgba(0,122,193,0.18)",    // thunder blue field
    border:  "#007ac1",
    text:    "#fdbb30",                 // yellow name
    seed:    "#ef3b24",                 // sunset orange seed — accent pop
    accent:  "#fdbb30",
    lockBar: "rgba(0,45,98,0.40)",      // navy bar
    divider: "#007ac1",
  },
  "San Antonio": {
    // Two-color team: silver + black. No tertiary to invent.
    // Strategy: use silver as the accent pop on dark structural bg.
    // lockBar stays near-black — using silver there would look washed out.
    bg:      "rgba(196,206,211,0.12)",  // silver field
    border:  "#c4ced4",                 // silver stripe
    text:    "#c4ced4",                 // silver name
    seed:    "#c4ced4",                 // silver seed
    accent:  "#c4ced4",                 // silver checkmark + btn
    lockBar: "rgba(20,20,20,0.60)",     // near-black — structural, not decorative
    divider: "#c4ced4",
  },
  "Portland": {
    // Two-color: red + black. Same rule as Spurs — no invented tertiary.
    bg:      "rgba(224,58,62,0.18)",
    border:  "#e03a3e",
    text:    "#ffffff",
    seed:    "#e03a3e",                 // red seed
    accent:  "#e03a3e",
    lockBar: "rgba(20,20,20,0.65)",     // near-black structural bar
    divider: "#e03a3e",
  },
  // ── East ──────────────────────────────────────────────────────────────────
  "Boston": {
    bg:      "rgba(0,122,51,0.18)",
    border:  "#007a33",
    text:    "#ffffff",
    seed:    "#ba9653",                 // gold seed — jersey trim color
    accent:  "#4ade80",                 // bright green checkmark/btn
    lockBar: "rgba(0,122,51,0.30)",
    divider: "#007a33",
  },
  "Philadelphia": {
    bg:      "rgba(0,107,182,0.18)",    // blue field
    border:  "#006bb6",
    text:    "#ffffff",
    seed:    "#ed174c",                 // red seed — Sixers red pop
    accent:  "#ed174c",                 // red checkmark + btn
    lockBar: "rgba(0,43,92,0.65)",      // navy bar — third color doing real work
    divider: "#006bb6",
  },
  "New York": {
    bg:      "rgba(0,107,182,0.18)",    // Knicks blue field
    border:  "#006bb6",
    text:    "#f58426",                 // orange name
    seed:    "#f58426",                 // orange seed
    accent:  "#f58426",
    lockBar: "rgba(0,107,182,0.30)",
    divider: "#f58426",                 // orange divider — distinctive
  },
  "Atlanta": {
    bg:      "rgba(224,58,62,0.18)",    // red field
    border:  "#e03a3e",
    text:    "#ffffff",
    seed:    "#c1d32f",                 // volt green seed — jersey pop
    accent:  "#c1d32f",                 // volt green checkmark + btn
    lockBar: "rgba(38,40,42,0.60)",     // charcoal bar
    divider: "#e03a3e",
  },
  "Cleveland": {
    bg:      "rgba(134,0,56,0.25)",     // wine field
    border:  "#860038",
    text:    "#ffffff",
    seed:    "#fdbb30",                 // gold seed
    accent:  "#fdbb30",
    lockBar: "rgba(4,30,66,0.70)",      // navy bar — second color, contrasts wine
    divider: "#860038",
  },
  "Detroit": {
    bg:      "rgba(29,66,186,0.20)",    // royal blue field
    border:  "#1d42ba",
    text:    "#ffffff",
    seed:    "#c8102e",                 // red seed — Pistons red pop
    accent:  "#c8102e",
    lockBar: "rgba(0,45,98,0.45)",      // navy bar
    divider: "#1d42ba",
  },
  "Toronto": {
    bg:      "rgba(206,17,65,0.18)",    // red field
    border:  "#ce1141",
    text:    "#ffffff",
    seed:    "#a1a1a4",                 // silver seed — subtle contrast
    accent:  "#b4975a",                 // gold checkmark + btn — warm accent
    lockBar: "rgba(20,20,20,0.65)",     // black structural bar (their second color)
    divider: "#ce1141",
  },
};

// Fallback conf colors
const CONF_FALLBACK = {
  west:   { bg: "rgba(59,130,246,0.15)",  border: "#3b82f6", text: "#60a5fa", seed: "#60a5fa", accent: "#60a5fa", lockBar: "rgba(59,130,246,0.10)", divider: "#3b82f6" },
  east:   { bg: "rgba(239,68,68,0.15)",   border: "#ef4444", text: "#f87171", seed: "#f87171", accent: "#f87171", lockBar: "rgba(239,68,68,0.10)", divider: "#ef4444" },
  finals: { bg: "rgba(251,191,36,0.15)",  border: "#fbbf24", text: "#fbbf24", seed: "#fbbf24", accent: "#fbbf24", lockBar: "rgba(251,191,36,0.10)", divider: "#fbbf24" },
};

export function getTeamStyle(teamName, conf) {
  return TEAM_COLORS[teamName] || CONF_FALLBACK[conf] || CONF_FALLBACK.east;
}


export const ROUNDS = ["First round", "Conf semis", "Conf finals", "NBA Finals"];
export const COMP_W = 54;
export const GAP = 6;
export const N_COLS = 7;
export const ACTIVE_COLS = [[0, 6], [1, 5], [2, 4], [3]];

export function isLocked(matchup) {
  if (!matchup.lock_time) return false;
  return new Date(matchup.lock_time) <= new Date();
}

export function isTBD(matchup) {
  return !matchup.team_a || !matchup.team_b;
}

export function formatLockTime(lock_time) {
  if (!lock_time) return null;
  const dt = new Date(lock_time);
  const now = new Date();

  const local = dt.toLocaleString("en-US", {
    month: "short", day: "numeric",
    hour: "numeric", minute: "2-digit",
    hour12: true,
  });

  const diffMs = dt - now;
  if (diffMs <= 0) return null;

  const diffMins = Math.floor(diffMs / 60000);
  const days = Math.floor(diffMins / 1440);
  const hours = Math.floor((diffMins % 1440) / 60);
  const mins = diffMins % 60;

  let relative;
  if (days > 0) relative = `${days}d ${hours}h`;
  else if (hours > 0) relative = `${hours}h ${mins}m`;
  else relative = `${mins}m`;

  return `${local} · ${relative}`;
}

export function groupMatchups(matchups) {
  const buckets = {
    "west-1": [], "west-2": [], "west-3": [],
    "finals-4": [],
    "east-3": [], "east-2": [], "east-1": [],
  };
  for (const m of matchups) {
    const conf = (m.conference || "").toLowerCase();
    const round = m.round || 1;
    let key;
    if (conf === "finals" || round === 4) key = "finals-4";
    else if (conf === "west") key = `west-${round}`;
    else if (conf === "east") key = `east-${round}`;
    if (key && buckets[key]) buckets[key].push(m);
  }
  return [
    [buckets["west-1"], "west",   "West · R1"],
    [buckets["west-2"], "west",   "West · R2"],
    [buckets["west-3"], "west",   "West CF"],
    [buckets["finals-4"], "finals", "Finals"],
    [buckets["east-3"], "east",   "East CF"],
    [buckets["east-2"], "east",   "East · R2"],
    [buckets["east-1"], "east",   "East · R1"],
  ];
}

export function pickClass(conf) {
  return conf === "west" ? "wp" : conf === "east" ? "ep" : "fp";
}

export function dotClass(conf) {
  return conf === "west" ? "dw" : conf === "east" ? "de" : "df";
}

export function computeWidths(activeRound, containerWidth) {
  const active = new Set(ACTIVE_COLS[activeRound]);
  const nActive = ACTIVE_COLS[activeRound].length;
  const nComp = N_COLS - nActive;
  const totalGaps = (N_COLS - 1) * GAP;
  const compTotal = nComp * COMP_W;
  const activeW = (containerWidth - totalGaps - compTotal) / nActive;
  return Array.from({ length: N_COLS }, (_, i) => (active.has(i) ? activeW : COMP_W));
}