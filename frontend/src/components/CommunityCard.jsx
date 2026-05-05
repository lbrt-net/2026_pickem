import { getTeamStyle, netRatingToWinProb, computeSeriesProbs, isLocked, isTBD } from "../utils/helpers";

const GRAY = {
  field: "#1a1a1a", seedBg: "#4a4a4a",
  stripe1: "#555555", stripe2: "#333333", pipFill: "#555555",
};

function Stripes({ s, height = 60 }) {
  return (
    <svg width="60" height={height} viewBox={`0 0 60 ${height}`} xmlns="http://www.w3.org/2000/svg"
      style={{ flexShrink: 0, display: "block" }}>
      <rect width="60" height={height} fill={s.field} />
      <polygon points={`0,0 16,0 36,${height} 20,${height}`} fill={s.stripe1} />
      <polygon points={`16,0 32,0 52,${height} 36,${height}`} fill={s.stripe2} />
    </svg>
  );
}

function PipsRow({ wins, total = 4, pipFill, field }) {
  return (
    <div style={{ width: 72, flexShrink: 0, background: field, display: "flex", alignItems: "center", justifyContent: "center", gap: 4 }}>
      {Array.from({ length: total }).map((_, i) => (
        <div key={i} style={{
          width: 10, height: 10, borderRadius: "50%",
          background: i < wins ? pipFill : "rgba(255,255,255,0.08)",
          border: i < wins ? "none" : `1px solid ${pipFill}44`,
        }} />
      ))}
    </div>
  );
}

function Avatar({ user, size = 14 }) {
  if (!user) return null;
  return user.avatar_url
    ? <img src={user.avatar_url} style={{ width: size, height: size, borderRadius: "50%", outline: "1.5px solid rgba(255,255,255,0.2)", flexShrink: 0 }} />
    : <div style={{ width: size, height: size, borderRadius: "50%", background: "#4a5568", outline: "1.5px solid rgba(255,255,255,0.2)", flexShrink: 0 }} />;
}

// ── Per-person points distribution (shown after result is set) ───────────────
function pickPoints(pick, matchup) {
  let pts = 0;
  const winnerCorrect = pick.winner && pick.winner === matchup.winner_result;
  if (winnerCorrect) pts += 2;
  if (pick.games != null && matchup.games_result != null) {
    if (winnerCorrect) {
      const dist = Math.abs(pick.games - matchup.games_result);
      if (dist === 0) pts += 2;
      else if (dist === 1) pts += 1;
    } else {
      // Chart-adjacency: wrong-winner dist = |15 - pick_games - result_games|
      const dist = Math.abs(15 - pick.games - matchup.games_result);
      if (dist <= 2) pts += 1;
    }
  }
  if (pick.stat_leader && matchup.stat_leader_result) {
    const leaders = matchup.stat_leader_result.split(",").map(s => s.trim().toLowerCase());
    if (leaders.includes(pick.stat_leader.trim().toLowerCase())) pts += 1;
  }
  return Math.min(pts, 5);
}

function PointsDist({ matchup, aggregate }) {
  if (!matchup.winner_result || !aggregate?.picks?.length) return null;
  const byPts = {};
  for (const pick of aggregate.picks) {
    const pts = pickPoints(pick, matchup);
    if (!byPts[pts]) byPts[pts] = [];
    byPts[pts].push(pick);
  }
  const rows = [5, 4, 3, 2, 1, 0].filter(p => byPts[p]?.length);
  if (!rows.length) return null;
  return (
    <div style={{ padding: "10px 12px", borderTop: "1px solid #1f2937", background: "#0d1421" }}>
      <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>Points</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {rows.map(pts => (
          <div key={pts} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: pts >= 4 ? "#4ade80" : pts >= 2 ? "#fbbf24" : "#f87171", width: 20, flexShrink: 0 }}>{pts}</span>
            <div style={{ display: "flex", gap: 3, flexWrap: "wrap" }}>
              {byPts[pts].map((u, i) => <Avatar key={i} user={u} size={18} />)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Series probability bar chart ─────────────────────────────────────────────
function SeriesBars({ matchup, conf, aggregate }) {
  const { home_net_rating_a, home_net_rating_b, wins_a = 0, wins_b = 0,
          team_a, team_b, winner_result, games_result } = matchup;
  if (home_net_rating_a == null || home_net_rating_b == null) return null;

  const locked = isLocked(matchup);
  const hasResult = !!winner_result;

  const probHomeA = netRatingToWinProb(home_net_rating_a);
  const probHomeB = netRatingToWinProb(home_net_rating_b);
  const probs = computeSeriesProbs(probHomeA, probHomeB, wins_a, wins_b);

  const sA = getTeamStyle(team_a, conf);
  const sB = getTeamStyle(team_b, conf);

  // Left bars: A wins in 4,5,6,7 | Right bars: B wins in 7,6,5,4 (mirrored — close games in center)
  const leftKeys  = ["A-4", "A-5", "A-6", "A-7"];
  const rightKeys = ["B-7", "B-6", "B-5", "B-4"];
  const allKeys   = [...leftKeys, ...rightKeys];

  const maxProb = Math.max(...allKeys.map(k => probs[k] || 0), 0.001);
  const BAR_H = 48;
  const AVATAR_ZONE = 36;

  // Group aggregate picks by outcome key (only shown post-lock)
  const byOutcome = {};
  if (locked && aggregate?.picks) {
    for (const p of aggregate.picks) {
      if (!p.winner || !p.games) continue;
      const side = p.winner === team_a ? "A" : "B";
      const k = `${side}-${p.games}`;
      if (!byOutcome[k]) byOutcome[k] = [];
      byOutcome[k].push(p);
    }
  }

  const maxPickCount = hasResult
    ? Math.max(...allKeys.map(k => byOutcome[k]?.length || 0), 1)
    : 1;

  // Points earned for picking a given winner+games outcome (stat leader excluded)
  function outcomePoints(side, games) {
    const winner = side === "A" ? team_a : team_b;
    const winnerCorrect = winner === winner_result;
    let pts = winnerCorrect ? 2 : 0;
    if (games_result != null) {
      if (winnerCorrect) {
        const dist = Math.abs(games - games_result);
        if (dist === 0) pts += 2;
        else if (dist === 1) pts += 1;
      } else {
        const dist = Math.abs(15 - games - games_result);
        if (dist <= 2) pts += 1;
      }
    }
    return Math.min(pts, 4);
  }

  function Bar({ k, color }) {
    const [side, gStr] = k.split("-");
    const games = parseInt(gStr);
    const avatars = byOutcome[k] || [];

    const MAX_SHOW = 6;
    const shown = avatars.slice(0, MAX_SHOW);
    const overflow = avatars.length - MAX_SHOW;
    const rows = [];
    for (let i = 0; i < shown.length; i += 2) rows.push(shown.slice(i, i + 2));

    let h, barBg, labelColor, sublabel;
    if (hasResult) {
      const count = avatars.length;
      h = count > 0 ? Math.max((count / maxPickCount) * BAR_H, 3) : 0;
      const isActual = (side === "A" ? team_a : team_b) === winner_result && games === games_result;
      const pts = outcomePoints(side, games);
      const ptsColor = pts >= 4 ? "#4ade80" : pts >= 3 ? "#fbbf24" : pts >= 2 ? "#e2e8f0" : "rgba(255,255,255,0.25)";
      barBg = h > 0 ? color : "rgba(255,255,255,0.04)";
      labelColor = isActual ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.65)";
      sublabel = <div style={{ fontSize: 11, fontWeight: 700, color: ptsColor }}>+{pts}</div>;
      if (!isActual && h > 0) barBg = `${color}55`;
    } else {
      const p = probs[k] || 0;
      h = p > 0 ? Math.max((p / maxProb) * BAR_H, 3) : 0;
      const pct = Math.round(p * 100);
      barBg = p > 0 ? color : "rgba(255,255,255,0.04)";
      labelColor = p > 0 ? "rgba(255,255,255,0.85)" : "rgba(255,255,255,0.2)";
      sublabel = p > 0
        ? <div style={{ fontSize: 11, color: "#e2e8f0" }}>{pct > 0 ? `${pct}%` : "<1%"}</div>
        : null;
    }

    return (
      <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
        {/* Avatar zone — pyramid anchored to bottom */}
        <div style={{ height: AVATAR_ZONE, display: "flex", flexDirection: "column-reverse", alignItems: "center", gap: 1, overflow: "hidden", width: "100%" }}>
          {locked && rows.map((row, ri) => (
            <div key={ri} style={{ display: "flex", gap: 1, justifyContent: "center" }}>
              {row.map((u, j) => <Avatar key={j} user={u} size={12} />)}
            </div>
          ))}
          {locked && overflow > 0 && (
            <div style={{ fontSize: 8, color: "#e2e8f0", lineHeight: 1 }}>+{overflow}</div>
          )}
        </div>
        {/* Bar */}
        <div style={{ height: BAR_H, display: "flex", alignItems: "flex-end", width: "100%", padding: "0 1px" }}>
          <div style={{ width: "100%", height: h || 2, background: barBg, borderRadius: "2px 2px 0 0" }} />
        </div>
        {/* Label */}
        <div style={{ textAlign: "center", marginTop: 3 }}>
          <div style={{ fontSize: 11, color: labelColor }}>in {games}</div>
          {sublabel}
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: "10px 12px", borderTop: "1px solid #1f2937", background: "#0d1421" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
        <span style={{ fontSize: 10, color: sA.pipFill, fontWeight: 600 }}>{team_a || "TBD"}</span>
        <span style={{ fontSize: 10, color: sB.pipFill, fontWeight: 600 }}>{team_b || "TBD"}</span>
      </div>
      <div style={{ display: "flex", gap: 0, alignItems: "flex-end" }}>
        {leftKeys.map(k => <Bar key={k} k={k} color={sA.pipFill} />)}
        <div style={{ width: 1, height: BAR_H + AVATAR_ZONE + 28, background: "rgba(255,255,255,0.08)", flexShrink: 0, alignSelf: "flex-start" }} />
        {rightKeys.map(k => <Bar key={k} k={k} color={sB.pipFill} />)}
      </div>
      {!locked && (
        <div style={{ fontSize: 10, color: "rgba(255,255,255,0.2)", textAlign: "center", marginTop: 6 }}>
          Picks shown at lock
        </div>
      )}
    </div>
  );
}

// ── Stat leader table ────────────────────────────────────────────────────────
function StatLeaderTable({ matchup, aggregate }) {
  let log;
  try { log = JSON.parse(matchup.stat_game_log || "{}"); } catch { return null; }
  if (!log || Object.keys(log).length === 0) return null;

  // Sum incremental values per player across all games
  const totals = {};
  for (const rows of Object.values(log)) {
    if (!Array.isArray(rows)) continue;
    for (const { name, value } of rows) {
      if (!name?.trim()) continue;
      totals[name.trim()] = (totals[name.trim()] || 0) + (parseFloat(value) || 0);
    }
  }

  if (Object.keys(totals).length === 0) return null;

  const top5 = Object.entries(totals)
    .sort(([a, va], [b, vb]) => vb - va || a.localeCompare(b))
    .slice(0, 5);

  const statPicks = aggregate?.stat_picks || {};

  return (
    <div style={{ padding: "10px 12px", borderTop: "1px solid #1f2937", background: "#0d1421" }}>
      <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>
        {matchup.stat_label || "Stat"} leaders
      </div>
      {top5.map(([name, total], i) => {
        // Case-insensitive lookup for pickers
        const pickers = Object.entries(statPicks)
          .find(([k]) => k.toLowerCase() === name.toLowerCase())?.[1] || [];
        return (
          <div key={name} style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 0", borderBottom: i < top5.length - 1 ? "1px solid rgba(255,255,255,0.07)" : "none" }}>
            <span style={{ fontSize: 13, color: "#94a3b8", width: 16, flexShrink: 0 }}>{i + 1}</span>
            <span style={{ fontSize: 13, color: "#f1f5f9", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{name}</span>
            <span style={{ fontSize: 12, fontWeight: 700, color: "#fbbf24", marginRight: 4 }}>{total % 1 === 0 ? total : total.toFixed(1)}</span>
            {/* Stacked avatars of users who picked this player */}
            <div style={{ display: "flex" }}>
              {pickers.slice(0, 4).map((u, j) => (
                <div key={j} style={{ marginLeft: j > 0 ? -4 : 0 }}>
                  <Avatar user={u} size={16} />
                </div>
              ))}
              {pickers.length > 4 && (
                <div style={{ width: 16, height: 16, borderRadius: "50%", background: "#2a3347", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 8, color: "#e2e8f0", marginLeft: -4 }}>
                  +{pickers.length - 4}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── CommunityCard ────────────────────────────────────────────────────────────
export default function CommunityCard({ matchup, conf, aggregate }) {
  const locked = isLocked(matchup);
  const tbd = isTBD(matchup);

  const teamA = matchup.team_a || "TBD";
  const teamB = matchup.team_b || "TBD";
  const sA = getTeamStyle(teamA, conf);
  const sB = getTeamStyle(teamB, conf);
  const aWins = matchup.wins_a || 0;
  const bWins = matchup.wins_b || 0;
  const aWon = !!matchup.winner_result && matchup.winner_result === teamA;
  const bWon = !!matchup.winner_result && matchup.winner_result === teamB;

  // ── TBD ───────────────────────────────────────────────────────────────────
  if (tbd) {
    return (
      <div className="matchup tbd">
        {[{ s: sA, seed: matchup.seed_a }, { s: sB, seed: matchup.seed_b }].map((t, i) => (
          <div key={i}>
            {i > 0 && <div style={{ height: 2, background: "#fff" }} />}
            <div style={{ display: "flex", height: 60, alignItems: "stretch", opacity: 0.4 }}>
              <div style={{ width: 44, flexShrink: 0, background: "#333", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ fontSize: 22, fontWeight: 700, color: "#888" }}>{t.seed}</span>
              </div>
              <div style={{ flex: 1, background: "#111", display: "flex", alignItems: "center", padding: "0 12px" }}>
                <span style={{ fontSize: 14, fontWeight: 500, color: "#555" }}>TBD</span>
              </div>
              <Stripes s={{ field: "#111", stripe1: "#333", stripe2: "#222" }} />
              <div style={{ width: 72, background: "#111" }} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  const renderTeamRow = (team, seed, wins, s, eliminated) => {
    const es = eliminated ? GRAY : s;
    return (
      <div style={{ display: "flex", height: 60, alignItems: "stretch", opacity: eliminated ? 0.75 : 1 }}>
        <div style={{ width: 44, flexShrink: 0, background: es.seedBg, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <span style={{ fontSize: 22, fontWeight: 700, color: "#fff" }}>{seed}</span>
        </div>
        <div style={{ flex: 1, background: es.field, display: "flex", alignItems: "center", padding: "0 12px", gap: 6 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: eliminated ? "#888" : "#fff", flex: 1 }}>
            {team}
          </span>
        </div>
        <Stripes s={es} />
        <PipsRow wins={wins} pipFill={es.pipFill} field={es.field} />
      </div>
    );
  };

  return (
    <div className={`matchup${locked ? " locked" : ""}`}>
      {renderTeamRow(teamA, matchup.seed_a, aWins, sA, bWon)}
      <div style={{ height: 2, background: "#fff" }} />
      {renderTeamRow(teamB, matchup.seed_b, bWins, sB, aWon)}

      <SeriesBars matchup={matchup} conf={conf} aggregate={aggregate} />
      <StatLeaderTable matchup={matchup} aggregate={aggregate} />
    </div>
  );
}