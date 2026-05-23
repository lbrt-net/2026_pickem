import { getTeamStyle } from "../utils/helpers";

const COL_TO_ROUND = [0, 1, 2, 3, 2, 1, 0];
const TOTAL_H = 520;

function MiniCard({ matchup, conf, onClick }) {
  const sA = getTeamStyle(matchup.team_a || "", conf);
  const sB = getTeamStyle(matchup.team_b || "", conf);
  const aWon = !!matchup.winner_result && matchup.winner_result === matchup.team_a;
  const bWon = !!matchup.winner_result && matchup.winner_result === matchup.team_b;

  // If series result is final, winner gets 4 dots; loser gets games_result-4
  const winsA = aWon ? 4 : (bWon && matchup.games_result ? matchup.games_result - 4 : matchup.wins_a || 0);
  const winsB = bWon ? 4 : (aWon && matchup.games_result ? matchup.games_result - 4 : matchup.wins_b || 0);

  const row = (team, seed, wins, s, elim) => (
    <div style={{
      display: "flex", alignItems: "center", gap: 5, padding: "5px 6px 5px 8px",
      opacity: elim ? 0.32 : 1,
      borderLeft: `3px solid ${s.pipFill}`,
    }}>
      <span style={{ fontSize: 9, color: "var(--text-muted)", width: 10, flexShrink: 0 }}>{seed}</span>
      <span style={{ fontSize: 11, fontWeight: 500, color: elim ? "var(--text-muted)" : "var(--text)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {team || "TBD"}
      </span>
      <div style={{ display: "flex", gap: 2, flexShrink: 0 }}>
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} style={{ width: 5, height: 5, borderRadius: "50%", background: i < wins ? s.pipFill : "rgba(255,255,255,0.1)" }} />
        ))}
      </div>
    </div>
  );

  return (
    <div onClick={onClick} className="mini-card">
      {row(matchup.team_a, matchup.seed_a, winsA, sA, bWon)}
      <div style={{ height: 1, background: "var(--border)" }} />
      {row(matchup.team_b, matchup.seed_b, winsB, sB, aWon)}
    </div>
  );
}

export default function BracketOverview({ cols, onZoom }) {
  return (
    <div style={{ display: "flex", gap: 4, overflowX: "auto", paddingBottom: 16 }}>
      {cols.map(([matchups, conf], colIdx) => (
        <div key={colIdx} style={{
          flex: 1, minWidth: 100, maxWidth: 200,
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
