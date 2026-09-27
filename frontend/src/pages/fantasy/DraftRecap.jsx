import FantasyShell from "../../components/fantasy/FantasyShell";

const steals = [["Alperen Sengun", 6, 68], ["Jalen Williams", 5, 58], ["Herbert Jones", 9, 95]];
const reaches = [["Deandre Ayton", 4, 58], ["Jordan Poole", 5, 61], ["Cam Johnson", 4, 61]];
const grades = [
  ["Baseline Bandits", "A-", "Best value, PF/C depth"],
  ["Rim Reapers", "B+", "Solid across the board"],
  ["Baseline Bandits Jr", "B", "Guard heavy"],
  ["Screen Time", "B-", "Reached early, recovered"],
  ["Full Court Press", "B+", "Best overall roster"],
  ["Buzzer Beaters", "C+", "Thin at center"],
  ["Airball Assassins", "C", "Overpaid for name value"],
  ["Triple Double Trouble", "C-", "No clear plan"],
  ["Bench Mob", "D+", "Reached constantly"],
  ["Zero Dark Thirty", "D", "Missed the run on centers"],
];

export default function DraftRecap() {
  return (
    <FantasyShell title="Draft Recap" season="2026_27">
      <div style={{ fontSize: 10, color: "#b45309", marginBottom: 10 }}>Content flagged as "not quite right" — kept as a placeholder, revisit later.</div>
      <div style={{ display: "flex", gap: 14, marginBottom: 14 }}>
        <div style={{ flex: 1, border: "1px solid #999", padding: 12 }}>
          <div style={{ fontSize: 10, color: "#999", marginBottom: 6 }}>BIGGEST STEALS</div>
          {steals.map(([name, round, adp]) => <div key={name} style={{ fontSize: 12, padding: "2px 0" }}>{name} — Rd {round} (ADP {adp})</div>)}
        </div>
        <div style={{ flex: 1, border: "1px solid #999", padding: 12 }}>
          <div style={{ fontSize: 10, color: "#999", marginBottom: 6 }}>BIGGEST REACHES</div>
          {reaches.map(([name, round, adp]) => <div key={name} style={{ fontSize: 12, padding: "2px 0" }}>{name} — Rd {round} (ADP {adp})</div>)}
        </div>
      </div>
      <div style={{ fontSize: 10, color: "#999", marginBottom: 6 }}>TEAM GRADES</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        {grades.map(([name, grade, note]) => (
          <div key={name} style={{ border: "1px solid #999", padding: 10, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div><div style={{ fontSize: 13, fontWeight: 600 }}>{name}</div><div style={{ fontSize: 11, color: "#666" }}>{note}</div></div>
            <div style={{ fontSize: 18, fontWeight: 700, border: "1px solid #333", padding: "2px 10px" }}>{grade}</div>
          </div>
        ))}
      </div>
    </FantasyShell>
  );
}
