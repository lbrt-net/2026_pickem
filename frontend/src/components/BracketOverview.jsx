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
    <div style={{ display: "flex", alignItems: "stretch", opacity: elim ? 0.72 : 1 }}>
      <div style={{ width: 24, flexShrink: 0, background: s.seedBg, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: "#fff" }}>{seed}</span>
      </div>
      <div style={{ flex: 1, background: s.field, display: "flex", alignItems: "center", gap: 5, padding: "7px 8px", minWidth: 0 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: "#fff", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", letterSpacing: "0.02em" }}>
          {abbr(team)}
        </span>
        <div style={{ display: "flex", gap: 2, flexShrink: 0 }}>
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} style={{ width: 5, height: 5, borderRadius: "50%", background: i < wins ? s.pipFill : "rgba(255,255,255,0.15)" }} />
          ))}
        </div>
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

export default function BracketOverview({ cols, onZoom }) {
  if (cols.length < 7) return null;

  return (
    <div style={{ display: "flex", gap: 6, paddingBottom: 16 }}>
      {cols.map(([matchups, conf], colIdx) => (
        <div key={colIdx} style={{
          flex: 1, minWidth: 80, maxWidth: 220,
          height: TOTAL_H,
          display: "flex", flexDirection: "column",
          justifyContent: matchups.length === 1 ? "center" : "space-around",
        }}>
          {matchups.map(m => (
            <MiniCard key={m.id} matchup={m} conf={conf} onClick={() => onZoom(COL_TO_ROUND[colIdx])} />
          ))}
        </div>
      ))}
    </div>
  );
}
