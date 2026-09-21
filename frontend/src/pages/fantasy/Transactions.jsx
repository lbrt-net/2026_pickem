import { useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";

const FILTERS = ["All", "Adds & Drops", "Trades", "Draft"];

const items = [
  ["2h ago", "ADD", "Baseline Bandits added Jalen Williams"],
  ["2h ago", "DROP", "Baseline Bandits dropped Herbert Jones"],
  ["5h ago", "TRADE", "Buzzer Beaters <> Airball Assassins: Ayton for Johnson"],
  ["1d ago", "ADD", "Screen Time added Alperen Sengun off waivers"],
  ["1d ago", "DROP", "Screen Time dropped Deandre Ayton"],
  ["1d ago", "ADD", "Rim Reapers added Coby White"],
  ["2d ago", "TRADE", "Rim Reapers <> Bench Mob: Herbert Jones for Jalen Suggs"],
  ["3d ago", "ADD", "Full Court Press added Jordan Poole"],
];

export default function Transactions() {
  const [filter, setFilter] = useState("All");

  return (
    <FantasyShell title="League Activity" season="2026-27">
      <div style={{ border: "1px solid #999", padding: 12, marginBottom: 14 }}>
        <div style={{ fontSize: 10, color: "#999", marginBottom: 6 }}>PAST WEEK SUMMARY</div>
        <div style={{ fontSize: 12 }}>6 adds &middot; 5 drops &middot; 2 trades league-wide. Most active: Screen Time (3 moves).</div>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        {FILTERS.map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{ fontSize: 12, padding: "4px 10px", fontWeight: filter === f ? 700 : 400, border: filter === f ? "2px solid #111" : "1px solid #ccc" }}>
            {f}
          </button>
        ))}
      </div>

      {items.map(([when, tag, desc]) => (
        <div key={desc} style={{ display: "flex", gap: 12, fontSize: 12, padding: "6px 0", borderBottom: "1px solid #eee" }}>
          <div style={{ width: 60, color: "#999", fontSize: 10 }}>{when}</div>
          <div style={{ width: 50, border: "1px solid #999", textAlign: "center", fontSize: 10 }}>{tag}</div>
          <div>{desc}</div>
        </div>
      ))}
    </FantasyShell>
  );
}
