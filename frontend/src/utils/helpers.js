export const API = "";

export const TEAM_COLORS = {
  "LA Lakers": { field: "#2d1060", seedBg: "#f9a01b", stripe1: "#f9a01b", stripe2: "#552583", pipFill: "#f9a01b", accent: "#f9a01b" },
  "Houston":   { field: "#180008", seedBg: "#ce1141", stripe1: "#ce1141", stripe2: "#c4ced4", pipFill: "#c4ced4", accent: "#c4ced4" },
  "Denver":    { field: "#0d1f3c", seedBg: "#8b2131", stripe1: "#fec524", stripe2: "#8b2131", pipFill: "#fec524", accent: "#fec524" },
  "Minnesota": { field: "#0c2340", seedBg: "#236192", stripe1: "#78be20", stripe2: "#236192", pipFill: "#78be20", accent: "#78be20" },
  "Oklahoma City": { field: "#002d62", seedBg: "#007ac1", stripe1: "#007ac1", stripe2: "#fdbb30", pipFill: "#fdbb30", accent: "#fdbb30" },
  "Phoenix":   { field: "#1d1160", seedBg: "#e56020", stripe1: "#e56020", stripe2: "#1d1160", pipFill: "#e56020", accent: "#e56020" },
  "Orlando":   { field: "#00518a", seedBg: "#0077c0", stripe1: "#0077c0", stripe2: "#c4ced4", pipFill: "#c4ced4", accent: "#c4ced4" },
  "San Antonio": { field: "#141414", seedBg: "#c4ced4", stripe1: "#c4ced4", stripe2: "#888888", pipFill: "#c4ced4", accent: "#c4ced4" },
  "Portland":  { field: "#1a0000", seedBg: "#e03a3e", stripe1: "#e03a3e", stripe2: "#555555", pipFill: "#e03a3e", accent: "#e03a3e" },
  "Boston":    { field: "#003d1a", seedBg: "#ba9653", stripe1: "#ba9653", stripe2: "#007a33", pipFill: "#4ade80", accent: "#4ade80" },
  "Philadelphia": { field: "#001f4d", seedBg: "#006bb6", stripe1: "#ed174c", stripe2: "#006bb6", pipFill: "#ed174c", accent: "#ed174c" },
  "New York":  { field: "#003f7f", seedBg: "#f58426", stripe1: "#f58426", stripe2: "#006bb6", pipFill: "#f58426", accent: "#f58426" },
  "Atlanta":   { field: "#1a0000", seedBg: "#c1d32f", stripe1: "#e03a3e", stripe2: "#c1d32f", pipFill: "#c1d32f", accent: "#c1d32f" },
  "Cleveland": { field: "#041e42", seedBg: "#860038", stripe1: "#860038", stripe2: "#fdbb30", pipFill: "#fdbb30", accent: "#fdbb30" },
  "Detroit":   { field: "#002d62", seedBg: "#1d42ba", stripe1: "#c8102e", stripe2: "#1d42ba", pipFill: "#c8102e", accent: "#c8102e" },
  "Toronto":   { field: "#18000e", seedBg: "#ce1141", stripe1: "#ce1141", stripe2: "#a1a1a4", pipFill: "#b4975a", accent: "#b4975a" },
};

const CONF_FALLBACK = {
  west:   { field: "#0d1f3c", seedBg: "#3b82f6", stripe1: "#3b82f6", stripe2: "#1d4ed8", pipFill: "#60a5fa", accent: "#60a5fa" },
  east:   { field: "#1a0a0a", seedBg: "#ef4444", stripe1: "#ef4444", stripe2: "#b91c1c", pipFill: "#f87171", accent: "#f87171" },
  finals: { field: "#1a1400", seedBg: "#fbbf24", stripe1: "#fbbf24", stripe2: "#d97706", pipFill: "#fbbf24", accent: "#fbbf24" },
};

export function getTeamStyle(teamName, conf) {
  return TEAM_COLORS[teamName] || CONF_FALLBACK[conf] || CONF_FALLBACK.east;
}

export const STRIPE_POINTS = {
  s1: "0,0 16,0 36,60 20,60",
  s2: "16,0 32,0 52,60 36,60",
};

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

// Bracket display order by home seed: 1 (top) → 4 → 3 → 2 (bottom)
const BRACKET_RANK = { 1: 0, 4: 1, 3: 2, 2: 3 };

function bracketSort(ms) {
  return [...ms].sort((a, b) => {
    const sa = Math.min(a.seed_a ?? 99, a.seed_b ?? 99);
    const sb = Math.min(b.seed_a ?? 99, b.seed_b ?? 99);
    const ra = BRACKET_RANK[sa] ?? 99;
    const rb = BRACKET_RANK[sb] ?? 99;
    if (ra !== rb) return ra - rb;
    return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
  });
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
    [bracketSort(buckets["west-1"]),   "west",   "West · R1"],
    [bracketSort(buckets["west-2"]),   "west",   "West · R2"],
    [buckets["west-3"],                "west",   "West CF"],
    [buckets["finals-4"],              "finals", "Finals"],
    [buckets["east-3"],                "east",   "East CF"],
    [bracketSort(buckets["east-2"]),   "east",   "East · R2"],
    [bracketSort(buckets["east-1"]),   "east",   "East · R1"],
  ];
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
  const activeW = Math.min((containerWidth - totalGaps - compTotal) / nActive, 450);
  return Array.from({ length: N_COLS }, (_, i) => (active.has(i) ? activeW : COMP_W));
}

// ---------------------------------------------------------------------------
// Net rating at home → P(home team wins a single game)
// Logistic calibrated to NBA: +7 NR ≈ 73%, 0 ≈ 50%, -7 ≈ 27%
// ---------------------------------------------------------------------------
export function netRatingToWinProb(homeNetRating) {
  return 1 / (1 + Math.exp(-homeNetRating / 6.5));
}

// ---------------------------------------------------------------------------
// Series outcome probability distribution via DP
//
// probHome  = P(team_a wins) when playing at home (from netRatingToWinProb)
// winsA, winsB = current series score
//
// 2-2-1-1-1 home court schedule (higher seed = team_a):
//   Games 1,2 at A  |  Games 3,4 at B  |  Game 5 at A  |  Game 6 at B  |  Game 7 at A
//
// Returns { "A-4": prob, "A-5": prob, "A-6": prob, "A-7": prob,
//           "B-4": prob, "B-5": prob, "B-6": prob, "B-7": prob }
// Keys where the outcome is no longer reachable will be absent (prob = 0).
// ---------------------------------------------------------------------------
export function computeSeriesProbs(probHomeA, probHomeB, winsA = 0, winsB = 0) {
  const homeGames = new Set([1, 2, 5, 7]); // game numbers where team_a is home (2-2-1-1-1)
  const memo = new Map();

  function dp(wa, wb) {
    // Terminal states
    if (wa === 4) return { [`A-${wa + wb}`]: 1 };
    if (wb === 4) return { [`B-${wa + wb}`]: 1 };

    const k = `${wa},${wb}`;
    if (memo.has(k)) return memo.get(k);

    const gameNum = wa + wb + 1;
    // A at home → use A's home win prob; B at home → use 1 - B's home win prob
    const pA = homeGames.has(gameNum) ? probHomeA : (1 - probHomeB);

    const ifA = dp(wa + 1, wb);
    const ifB = dp(wa, wb + 1);

    const out = {};
    for (const [o, p] of Object.entries(ifA)) out[o] = (out[o] || 0) + p * pA;
    for (const [o, p] of Object.entries(ifB)) out[o] = (out[o] || 0) + p * (1 - pA);

    memo.set(k, out);
    return out;
  }

  return dp(winsA, winsB);
}