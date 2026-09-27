import FantasyShell from "../../components/fantasy/FantasyShell";

const box = { border: "1px solid #999", padding: 8, fontSize: 12 };

export default function Playoffs() {
  return (
    <FantasyShell title="Fantasy Playoffs" season="2026_27">
      <div style={{ fontSize: 11, color: "#999", marginBottom: 14 }}>Top 6 seeds — weeks 20-22 — seeds 1 &amp; 2 get a first-round bye</div>
      <div style={{ display: "flex", gap: 40, alignItems: "center" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 30, flex: 1 }}>
          <div style={{ fontSize: 10, color: "#999" }}>ROUND 1</div>
          <div style={box}>1. Baseline Bandits<br /><span style={{ color: "#999" }}>(bye)</span></div>
          <div style={box}>3. Baseline Bandits Jr vs 6. Buzzer Beaters</div>
          <div style={box}>4. Screen Time vs 5. Full Court Press</div>
          <div style={box}>2. Rim Reapers<br /><span style={{ color: "#999" }}>(bye)</span></div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 90, flex: 1 }}>
          <div style={{ fontSize: 10, color: "#999" }}>SEMIFINALS</div>
          <div style={{ ...box, color: "#999" }}>1. Baseline Bandits vs [winner 3/6]</div>
          <div style={{ ...box, color: "#999" }}>2. Rim Reapers vs [winner 4/5]</div>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 10, color: "#999" }}>CHAMPIONSHIP</div>
          <div style={{ border: "2px solid #111", padding: 14, fontSize: 13, fontWeight: 700, textAlign: "center", color: "#999" }}>[TBD] vs [TBD]</div>
        </div>
      </div>
    </FantasyShell>
  );
}
