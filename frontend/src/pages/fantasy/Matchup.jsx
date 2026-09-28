import { useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";

const lineup = [
  ["PG", "Tyrese Haliburton", "51.0", "38.2", "Jalen Brunson"],
  ["SG", "Anthony Edwards", "39.8", "44.1", "Devin Booker"],
  ["SF", "Jayson Tatum", "48.2", "35.0", "Paul George"],
  ["PF", "Giannis Antetokounmpo", "58.9", "40.6", "Julius Randle"],
  ["C", "Nikola Jokic", "54.0", "52.1", "Joel Embiid"],
];

const weeklyLeaderboard = [
  ["Giannis Antetokounmpo", "Baseline Bandits", "58.9"],
  ["Nikola Jokic", "Baseline Bandits", "54.0"],
  ["Joel Embiid", "Dunk or Be Dunked", "52.1"],
  ["Tyrese Haliburton", "Baseline Bandits", "51.0"],
  ["Devin Booker", "Dunk or Be Dunked", "44.1"],
];

export default function Matchup() {
  const season = "2026_27";
  const [week, setWeek] = useState("12");
  const [matchup, setMatchup] = useState("Baseline Bandits vs Dunk or Be Dunked");
  const [view, setView] = useState("matchup");

  return (
    <FantasyShell title="Matchup" season={season}>
      <div style={{ display: "flex", gap: 10, marginBottom: 10 }}>
        <select value={week} onChange={e => setWeek(e.target.value)} style={{ fontSize: 12 }}>
          {Array.from({ length: 12 }, (_, i) => 12 - i).map(w => <option key={w} value={w}>Week {w}</option>)}
        </select>
        <select value={matchup} onChange={e => setMatchup(e.target.value)} style={{ fontSize: 12 }}>
          <option>Baseline Bandits vs Dunk or Be Dunked</option>
          <option>Rim Reapers vs Screen Time</option>
          <option>Full Court Press vs Buzzer Beaters</option>
        </select>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
        <button onClick={() => setView("matchup")} style={{ fontSize: 12, padding: "6px 12px", fontWeight: view === "matchup" ? 700 : 400, border: view === "matchup" ? "2px solid var(--text)" : "1px solid var(--border)" }}>
          Matchup View
        </button>
        <button onClick={() => setView("leaderboard")} style={{ fontSize: 12, padding: "6px 12px", fontWeight: view === "leaderboard" ? 700 : 400, border: view === "leaderboard" ? "2px solid var(--text)" : "1px solid var(--border)" }}>
          Weekly Leaderboard (top scorer wins a prize)
        </button>
      </div>

      <div style={{ border: "1px solid var(--border)", padding: 14, marginBottom: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700, fontSize: 15 }}>
          <span>Baseline Bandits</span><span>Week {week}</span><span>Dunk or Be Dunked</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 28, fontWeight: 700 }}>
          <span>412.5</span><span style={{ fontSize: 11, color: "var(--text)", alignSelf: "center" }}>updated ~3:00 AM daily, not live</span><span>388.2</span>
        </div>
      </div>

      {view === "matchup" ? (
        <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ fontSize: 10, color: "var(--text)" }}>
              <th style={{ textAlign: "left" }}>My Player</th><th style={{ textAlign: "right" }}>Pts</th><th>Slot</th><th style={{ textAlign: "left" }}>Pts</th><th style={{ textAlign: "left" }}>Opp Player</th>
            </tr>
          </thead>
          <tbody>
            {lineup.map(([slot, my, myPts, oppPts, opp]) => (
              <tr key={slot} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                <td style={{ padding: "5px 0" }}>{my}</td>
                <td style={{ textAlign: "right" }}>{myPts}</td>
                <td style={{ textAlign: "center", color: "var(--text)" }}>{slot}</td>
                <td>{oppPts}</td>
                <td>{opp}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ fontSize: 10, color: "var(--text)" }}>
              <th style={{ textAlign: "left" }}>#</th><th style={{ textAlign: "left" }}>Player</th><th style={{ textAlign: "left" }}>Team</th><th style={{ textAlign: "right" }}>Pts</th>
            </tr>
          </thead>
          <tbody>
            {weeklyLeaderboard.map(([name, team, pts], i) => (
              <tr key={name} style={{ borderTop: "1px solid var(--border-subtle)", fontWeight: i === 0 ? 700 : 400 }}>
                <td style={{ padding: "5px 0" }}>{i + 1}{i === 0 ? " (prize)" : ""}</td>
                <td>{name}</td>
                <td>{team}</td>
                <td style={{ textAlign: "right" }}>{pts}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </FantasyShell>
  );
}
