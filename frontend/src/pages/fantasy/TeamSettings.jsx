import FantasyShell from "../../components/fantasy/FantasyShell";

export default function TeamSettings() {
  return (
    <FantasyShell title="Team Settings" season="2026_27">
      <div style={{ border: "1px solid #999", padding: 14, marginBottom: 14 }}>
        <div style={{ display: "flex", gap: 20, alignItems: "center" }}>
          <div style={{ width: 64, height: 64, border: "1px dashed #999", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, color: "#999" }}>logo</div>
          <div style={{ flexGrow: 1 }}>
            <div style={{ fontSize: 10, color: "#999" }}>TEAM NAME</div>
            <input defaultValue="Baseline Bandits" style={{ fontSize: 13, border: "1px solid #ccc", padding: "6px 10px", width: "100%", boxSizing: "border-box", marginTop: 2 }} />
          </div>
        </div>
        <div style={{ marginTop: 10 }}>
          <div style={{ fontSize: 10, color: "#999" }}>TEAM ABBREVIATION</div>
          <input defaultValue="BB" maxLength={3} style={{ fontSize: 13, border: "1px solid #ccc", padding: "6px 10px", width: 80, marginTop: 2 }} />
          <div style={{ fontSize: 10, color: "#b45309", marginTop: 4 }}>
            Auto-generation + collision handling (e.g. two "BB" teams) not spec'd yet — placeholder only.
          </div>
        </div>
        <button style={{ marginTop: 12, border: "1px solid #333", padding: "6px 14px", fontSize: 12, background: "#fff" }}>Change Logo</button>
      </div>

      <div style={{ border: "1px solid #999", padding: 14, marginBottom: 14 }}>
        <div style={{ fontSize: 10, color: "#999", marginBottom: 8 }}>NOTIFICATIONS (no email — in-app/Discord only)</div>
        {["Trade offers", "Waiver results"].map(label => (
          <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid #eee", fontSize: 12 }}>
            <span>{label}</span>
            <input type="checkbox" defaultChecked />
          </div>
        ))}
      </div>

      <button style={{ border: "1px solid #333", padding: "8px 20px", fontSize: 12, background: "#fff" }}>Save Changes</button>
    </FantasyShell>
  );
}
