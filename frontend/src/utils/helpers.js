export const API = "";

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