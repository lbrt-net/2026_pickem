import FantasyShell from "../../components/fantasy/FantasyShell";

const tenure = [
  ["Nikola Jokic", "C", "2026-27 Rd 1", "current"],
  ["Tyrese Haliburton", "PG", "2026-27 Rd 2", "current"],
  ["Bam Adebayo", "C", "2026-27 Waivers, Wk 3", "current"],
  ["Herbert Jones", "SF", "2026-27 Rd 9", "dropped Wk 11"],
  ["Deandre Ayton", "C", "2026-27 Rd 4", "traded Wk 8"],
];

export default function Tenure() {
  return (
    <FantasyShell title="Team History (Tenure)" season="2026_27">
      <div style={{ fontSize: 10, color: "#999", marginBottom: 10 }}>
        Every player who has ever been on this team's roster, and when — an alumni record. Only spans one season right now; grows across future seasons as they're added.
      </div>
      <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ fontSize: 10, color: "#999", textAlign: "left" }}>
            <th>Player</th><th>Pos</th><th>Joined</th><th>Status</th>
          </tr>
        </thead>
        <tbody>
          {tenure.map(([name, pos, joined, status]) => (
            <tr key={name} style={{ borderTop: "1px solid #eee" }}>
              <td style={{ padding: "6px 0" }}>{name}</td>
              <td>{pos}</td>
              <td>{joined}</td>
              <td style={{ color: status === "current" ? "#111" : "#999" }}>{status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </FantasyShell>
  );
}
