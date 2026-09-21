import { useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";

const players = [
  [1, "Jalen Williams", "SF", "OKC", "41.2", "36.8", "62%", "Add"],
  [2, "Alperen Sengun", "C", "HOU", "38.9", "35.1", "58%", "Add"],
  [3, "Coby White", "PG", "CHI", "34.0", "29.4", "44%", "Add"],
  [4, "Devin Booker", "SG", "PHX", "42.0", "40.5", "100%", "Trade"],
  [5, "Domantas Sabonis", "C", "SAC", "41.5", "39.9", "100%", "—"],
  [6, "Jaylen Brown", "SF", "BOS", "38.9", "37.2", "100%", "Trade"],
  [7, "Herbert Jones", "SF", "NOP", "22.1", "20.8", "31%", "Add"],
  [8, "Jordan Poole", "SG", "WAS", "28.4", "25.0", "19%", "Add"],
];

const FILTERS = ["My Team", "Drafted", "Free Agents", "By NBA Team"];

export default function Players() {
  const [filter, setFilter] = useState("Free Agents");

  return (
    <FantasyShell title="Players" season="2026-27">
      <div style={{ fontSize: 10, color: "#999", marginBottom: 6 }}>Doubles as stats research + free agency/waivers</div>
      <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
        {FILTERS.map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{ fontSize: 12, padding: "4px 10px", fontWeight: filter === f ? 700 : 400, border: filter === f ? "2px solid #111" : "1px solid #ccc" }}>
            {f}
          </button>
        ))}
        <input placeholder="search" style={{ fontSize: 12, marginLeft: "auto", border: "1px solid #ccc", padding: "4px 8px" }} />
      </div>

      <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ fontSize: 10, color: "#999", textAlign: "left" }}>
            <th>#</th><th>Name</th><th>Pos</th><th>NBA</th><th style={{ textAlign: "right" }}>Wk</th>
            <th style={{ textAlign: "right" }}>Avg</th><th style={{ textAlign: "right" }}>Rost%</th><th></th>
          </tr>
        </thead>
        <tbody>
          {players.map(([rank, name, pos, team, wk, avg, rost, action]) => (
            <tr key={name} style={{ borderTop: "1px solid #eee" }}>
              <td style={{ padding: "5px 0" }}>{rank}</td>
              <td>{name}</td><td>{pos}</td><td>{team}</td>
              <td style={{ textAlign: "right" }}>{wk}</td>
              <td style={{ textAlign: "right" }}>{avg}</td>
              <td style={{ textAlign: "right", color: "#999" }}>{rost}</td>
              <td>{action !== "—" && <span style={{ border: "1px solid #333", padding: "2px 8px", fontSize: 11 }}>{action}</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ fontSize: 10, color: "#999", marginTop: 8 }}>Rost% is low-value in a closed 10-team league — kept for now, may drop later.</div>
    </FantasyShell>
  );
}
