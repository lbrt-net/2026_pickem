import { getTeamStyle } from "../utils/helpers";

const COL_TO_ROUND = [0, 1, 2, 3, 2, 1, 0];

function MiniCard({ matchup, conf, onClick }) {
  const sA = getTeamStyle(matchup.team_a || "", conf);
  const sB = getTeamStyle(matchup.team_b || "", conf);
  const aWon = !!matchup.winner_result && matchup.winner_result === matchup.team_a;
  const bWon = !!matchup.winner_result && matchup.winner_result === matchup.team_b;

  const row = (team, seed, wins, s, elim) => (
    <div style={{ display: "flex", alignItems: "center", gap: 4, padding: "4px 6px", opacity: elim ? 0.35 : 1 }}>
      <span style={{ fontSize: 9, color: "var(--text-muted)", width: 10, flexShrink: 0 }}>{seed}</span>
      <span style={{ fontSize: 10, fontWeight: 500, color: elim ? "var(--text-muted)" : "var(--text)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
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
      {row(matchup.team_a, matchup.seed_a, matchup.wins_a || 0, sA, bWon)}
      <div style={{ height: 1, background: "var(--border)" }} />
      {row(matchup.team_b, matchup.seed_b, matchup.wins_b || 0, sB, aWon)}
    </div>
  );
}

export default function BracketOverview({ cols, onZoom }) {
  const CARD_H = 41;
  const CARD_GAP = 8;
  const TOTAL_H = 4 * CARD_H + 3 * CARD_GAP;

  return (
    <div style={{ display: "flex", gap: 4, overflowX: "auto", paddingBottom: 16 }}>
      {cols.map(([matchups, conf], colIdx) => (
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
      ))}
    </div>
  );
}
