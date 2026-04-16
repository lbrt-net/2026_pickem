export const API = "";

// ---------------------------------------------------------------------------
// Team colors — bg tint, left border, text color for selected rows
// bg should be primary at ~15-18% opacity
// border is the strongest identifiable color
// text must be readable on #0a0f1e dark background
// ---------------------------------------------------------------------------
export const TEAM_COLORS = {
  // West
  "LA Lakers":      { bg: "rgba(85,37,130,0.20)",   border: "#552583", text: "#f9a01b"  }, // purple bg, gold text
  "Houston":        { bg: "rgba(206,17,65,0.18)",    border: "#ce1141", text: "#ff6b8a"  },
  "Denver":         { bg: "rgba(254,197,36,0.13)",   border: "#fec524", text: "#fec524"  }, // gold — navy too close to app bg
  "Minnesota":      { bg: "rgba(12,35,64,0.40)",     border: "#236192", text: "#78bee0"  }, // deep blue bg, light blue text
  "Oklahoma City":  { bg: "rgba(0,125,195,0.18)",    border: "#007dc3", text: "#56b4e9"  },
  "San Antonio":    { bg: "rgba(196,206,211,0.12)",  border: "#c4ced4", text: "#c4ced4"  },
  "Portland":       { bg: "rgba(224,58,62,0.18)",    border: "#e03a3e", text: "#f87171"  },
  // East
  "Boston":         { bg: "rgba(0,122,51,0.18)",     border: "#007a33", text: "#4ade80"  },
  "Philadelphia":   { bg: "rgba(0,107,182,0.18)",    border: "#006bb6", text: "#60a5fa"  },
  "New York":       { bg: "rgba(0,107,182,0.18)",    border: "#006bb6", text: "#60a5fa"  },
  "Atlanta":        { bg: "rgba(224,58,62,0.18)",    border: "#e03a3e", text: "#f87171"  }, // volt green as secondary accent handled separately
  "Cleveland":      { bg: "rgba(134,0,56,0.22)",     border: "#860038", text: "#f5a623"  }, // wine bg, gold text
  "Detroit":        { bg: "rgba(0,45,98,0.30)",      border: "#003a70", text: "#c8102e"  }, // deep blue bg, red text
  "Toronto":        { bg: "rgba(206,17,65,0.18)",    border: "#ce1141", text: "#ff6b8a"  },
};

// Fallback conf colors when team not in TEAM_COLORS yet
const CONF_FALLBACK = {
  west:   { bg: "rgba(59,130,246,0.15)",  border: "#3b82f6", text: "#60a5fa" },
  east:   { bg: "rgba(239,68,68,0.15)",   border: "#ef4444", text: "#f87171" },
  finals: { bg: "rgba(251,191,36,0.15)",  border: "#fbbf24", text: "#fbbf24" },
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