import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";

const starters = [
  ["PG", "Tyrese Haliburton", "IND"],
  ["SG", "Anthony Edwards", "MIN"],
  ["SF", "Jayson Tatum", "BOS"],
  ["PF", "Giannis Antetokounmpo", "MIL"],
  ["C", "Nikola Jokic", "DEN"],
];

const bench = [
  ["BN", "Devin Booker", "PHX"],
  ["BN", "Domantas Sabonis", "SAC"],
  ["BN", "Jaylen Brown", "BOS"],
  ["IL", "Bam Adebayo", "MIA"],
];

export default function TeamManagement() {
  const season = "2026_27";
  return (
    <FantasyShell title="Team Management" season={season}>
      <div style={{ fontSize: 10, color: "#999", marginBottom: 10 }}>
        This is distinct from <Link to={`/fantasy/${season}/team/settings`} style={{ textDecoration: "underline" }}>Team Settings</Link> (branding) —
        this page is where you actually set your lineup and manage your roster.
      </div>

      <div style={{ border: "1px solid #999", padding: 14, marginBottom: 14 }}>
        <div style={{ fontSize: 10, color: "#999", marginBottom: 8 }}>STARTING LINEUP</div>
        {starters.map(([slot, name, team]) => (
          <div key={slot} style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 12, padding: "6px 0", borderBottom: "1px solid #eee" }}>
            <div style={{ width: 34, color: "#999" }}>{slot}</div>
            <div style={{ flexGrow: 1 }}>{name} ({team})</div>
            <div style={{ border: "1px solid #999", padding: "2px 8px", fontSize: 11 }}>Bench</div>
          </div>
        ))}
      </div>

      <div style={{ border: "1px solid #999", padding: 14, marginBottom: 14 }}>
        <div style={{ fontSize: 10, color: "#999", marginBottom: 8 }}>BENCH</div>
        {bench.map(([slot, name, team]) => (
          <div key={slot} style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 12, padding: "6px 0", borderBottom: "1px solid #eee", color: "#666" }}>
            <div style={{ width: 34, color: "#999" }}>{slot}</div>
            <div style={{ flexGrow: 1 }}>{name} ({team})</div>
            <div style={{ border: "1px solid #333", padding: "2px 8px", fontSize: 11, color: "#111" }}>Start</div>
          </div>
        ))}
      </div>

      <button style={{ border: "1px solid #333", padding: "8px 16px", fontSize: 12, background: "#fff" }}>Save Lineup</button>
    </FantasyShell>
  );
}
