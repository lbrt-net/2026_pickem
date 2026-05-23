import { getTeamStyle } from "../utils/helpers";

const COL_TO_ROUND = [0, 1, 2, 3, 2, 1, 0];
const TOTAL_H = 460;

const ABBR = {
  "Oklahoma City": "OKC", "LA Lakers": "LAL", "Houston": "HOU",
  "Denver": "DEN", "Minnesota": "MIN", "Phoenix": "PHX",
  "San Antonio": "SAS", "Portland": "POR", "Detroit": "DET",
  "Cleveland": "CLE", "Philadelphia": "PHI", "New York": "NYK",
  "Atlanta": "ATL", "Boston": "BOS", "Toronto": "TOR", "Orlando": "ORL",
};

function abbr(name) { return ABBR[name] || name || "TBD"; }

function MiniCard({ matchup, conf, onClick }) {
  const sA = getTeamStyle(matchup.team_a || "", conf);
  const sB = getTeamStyle(matchup.team_b || "", conf);
  const aWon = !!matchup.winner_result && matchup.winner_result === matchup.team_a;
  const bWon = !!matchup.winner_result && matchup.winner_result === matchup.team_b;

  const winsA = aWon ? 4 : (bWon && matchup.games_result ? matchup.games_result - 4 : matchup.wins_a || 0);
  const winsB = bWon ? 4 : (aWon && matchup.games_result ? matchup.games_result - 4 : matchup.wins_b || 0);

  const row = (team, seed, wins, s, elim) => (
    <div style={{ display: "flex", alignItems: "center", gap: 5, padding: "7px 8px", background: s.seedBg, minWidth: 0, opacity: elim ? 0.55 : 1 }}>
      <span style={{ fontSize: 10, color: "rgba(255,255,255,0.6)", width: 12, flexShrink: 0 }}>{seed}</span>
      <span style={{ fontSize: 11, fontWeight: 700, color: "#fff", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", letterSpacing: "0.02em" }}>
        {abbr(team)}
      </span>
      <div style={{ display: "flex", gap: 2, flexShrink: 0 }}>
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} style={{ width: 5, height: 5, borderRadius: "50%", background: i < wins ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.2)" }} />
        ))}
      </div>
    </div>
  );

  return (
    <div onClick={onClick} className="mini-card" style={{ overflow: "hidden" }}>
      {row(matchup.team_a, matchup.seed_a, winsA, sA, bWon)}
      <div style={{ height: 1, background: "rgba(0,0,0,0.5)" }} />
      {row(matchup.team_b, matchup.seed_b, winsB, sB, aWon)}
    </div>
  );
}

function BracketCol({ matchups, conf, colIdx }) {
  return (
    <div style={{
      flex: 1, minWidth: 90, maxWidth: 180,
      height: TOTAL_H,
      display: "flex", flexDirection: "column",
      justifyContent: matchups.length === 1 ? "center" : "space-around",
    }}>
      {matchups.map(m => (
        <MiniCard key={m.id} matchup={m} conf={conf} onClick={() => {}} colIdx={colIdx} />
      ))}
    </div>
  );
}

export default function BracketOverview({ cols, onZoom }) {
  if (cols.length < 7) return null;

  const left   = cols.slice(0, 3);
  const center = cols[3];
  const right  = cols.slice(4);

  const makeCol = ([matchups, conf], colIdx) => (
    <div key={colIdx} style={{
      flex: 1, minWidth: 90, maxWidth: 180,
      height: TOTAL_H,
      display: "flex", flexDirection: "column",
      justifyContent: matchups.length === 1 ? "center" : "space-around",
    }}>
      {matchups.map(m => (
        <MiniCard key={m.id} matchup={m} conf={conf} onClick={() => onZoom(COL_TO_ROUND[colIdx])} />
      ))}
    </div>
  );

  const [centerMatchups, centerConf] = center;

  return (
    <div style={{ display: "flex", gap: 4, overflowX: "auto", paddingBottom: 16 }}>
      {left.map((col, i) => makeCol(col, i))}

      {/* Extra gap around Finals */}
      <div style={{ width: 20, flexShrink: 0 }} />
      <div style={{
        flex: 1, minWidth: 90, maxWidth: 180,
        height: TOTAL_H,
        display: "flex", flexDirection: "column",
        justifyContent: "center",
      }}>
        {centerMatchups.map(m => (
          <MiniCard key={m.id} matchup={m} conf={centerConf} onClick={() => onZoom(3)} />
        ))}
      </div>
      <div style={{ width: 20, flexShrink: 0 }} />

      {right.map((col, i) => makeCol(col, i + 4))}
    </div>
  );
}
