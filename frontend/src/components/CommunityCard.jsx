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
    ? <img src={user.avatar_url} style={{ width: size, height: size, borderRadius: "50%", border: "1px solid #0d1421", flexShrink: 0 }} />
    : <div style={{ width: size, height: size, borderRadius: "50%", background: "#4a5568", border: "1px solid #0d1421", flexShrink: 0 }} />;
}

// ── Series probability bar chart ─────────────────────────────────────────────
function SeriesBars({ matchup, conf, aggregate }) {
  const { home_net_rating_a, home_net_rating_b, wins_a = 0, wins_b = 0, team_a, team_b } = matchup;
  if (home_net_rating_a == null || home_net_rating_b == null) return null;

  const locked = isLocked(matchup);
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
  const AVATAR_ZONE = 36; // space above bars for stacked avatars

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

  function Bar({ k, color }) {
    const p = probs[k] || 0;
    const h = p > 0 ? Math.max((p / maxProb) * BAR_H, 3) : 0;
    const games = parseInt(k.split("-")[1]);
    const pct = Math.round(p * 100);
    const avatars = byOutcome[k] || [];

    return (
      <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
        {/* Avatar zone — stacked vertically, bottom-anchored */}
        <div style={{ height: AVATAR_ZONE, display: "flex", flexDirection: "column-reverse", alignItems: "center", gap: 1, overflow: "hidden" }}>
          {locked && avatars.slice(0, 3).map((u, i) => <Avatar key={i} user={u} size={12} />)}
          {locked && avatars.length > 3 && (
            <div style={{ fontSize: 8, color: "rgba(255,255,255,0.35)", lineHeight: 1 }}>+{avatars.length - 3}</div>
          )}
        </div>
        {/* Bar */}
        <div style={{ height: BAR_H, display: "flex", alignItems: "flex-end", width: "100%", padding: "0 1px" }}>
          <div style={{
            width: "100%", height: h,
            background: p > 0 ? color : "rgba(255,255,255,0.04)",
            borderRadius: "2px 2px 0 0",
          }} />
        </div>
        {/* Label */}
        <div style={{ textAlign: "center", marginTop: 3 }}>
          <div style={{ fontSize: 11, color: p > 0 ? "rgba(255,255,255,0.85)" : "rgba(255,255,255,0.2)" }}>
            in {games}
          </div>
          {p > 0 && (
            <div style={{ fontSize: 11, color: "rgba(255,255,255,0.7)" }}>{pct > 0 ? `${pct}%` : "<1%"}</div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: "10px 12px", borderTop: "1px solid #1f2937", background: "#0d1421" }}>
      {/* Team labels */}
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
        <span style={{ fontSize: 10, color: sA.pipFill, fontWeight: 600 }}>{team_a || "TBD"}</span>
        <span style={{ fontSize: 10, color: sB.pipFill, fontWeight: 600 }}>{team_b || "TBD"}</span>
      </div>
      {/* Bars */}
      <div style={{ display: "flex", gap: 0, alignItems: "flex-end" }}>
        {leftKeys.map(k => <Bar key={k} k={k} color={sA.pipFill} />)}
        {/* Center divider */}
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
      <div style={{ fontSize: 11, color: "rgba(255,255,255,0.55)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>
        {matchup.stat_label || "Stat"} leaders
      </div>
      {top5.map(([name, total], i) => {
        // Case-insensitive lookup for pickers
        const pickers = Object.entries(statPicks)
          .find(([k]) => k.toLowerCase() === name.toLowerCase())?.[1] || [];
        return (
          <div key={name} style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 0", borderBottom: i < top5.length - 1 ? "1px solid rgba(255,255,255,0.07)" : "none" }}>
            <span style={{ fontSize: 13, color: "rgba(255,255,255,0.55)", width: 16, flexShrink: 0 }}>{i + 1}</span>
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
                <div style={{ width: 16, height: 16, borderRadius: "50%", background: "#2a3347", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 8, color: "rgba(255,255,255,0.5)", marginLeft: -4 }}>
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
          {(team === matchup.winner_result) && (
            <span style={{ fontSize: 10, fontWeight: 700, color: s.pipFill, background: `${s.pipFill}22`, padding: "2px 6px", borderRadius: 3 }}>W</span>
          )}
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