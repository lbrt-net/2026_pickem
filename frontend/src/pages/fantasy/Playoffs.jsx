import FantasyShell from "../../components/fantasy/FantasyShell";

const box = { border: "1px solid var(--border)", padding: 8, fontSize: 12 };

export default function Playoffs() {
  return (
    <FantasyShell title="Fantasy Playoffs" season="2026_27">
      <div style={{ fontSize: 11, color: "var(--text)", marginBottom: 14 }}>Top 6 seeds — weeks 20-22 — seeds 1 &amp; 2 get a first-round bye</div>
      <div style={{ display: "flex", gap: 40, alignItems: "center" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 30, flex: 1 }}>
          <div style={{ fontSize: 10, color: "var(--text)" }}>ROUND 1</div>
          <div style={box}>1. Baseline Bandits<br /><span style={{ color: "var(--text)" }}>(bye)</span></div>
          <div style={box}>3. Baseline Bandits Jr vs 6. Buzzer Beaters</div>
          <div style={box}>4. Screen Time vs 5. Full Court Press</div>
          <div style={box}>2. Rim Reapers<br /><span style={{ color: "var(--text)" }}>(bye)</span></div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 90, flex: 1 }}>
          <div style={{ fontSize: 10, color: "var(--text)" }}>SEMIFINALS</div>
          <div style={{ ...box, color: "var(--text)" }}>1. Baseline Bandits vs [winner 3/6]</div>
          <div style={{ ...box, color: "var(--text)" }}>2. Rim Reapers vs [winner 4/5]</div>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 10, color: "var(--text)" }}>CHAMPIONSHIP</div>
          <div style={{ border: "2px solid var(--text)", padding: 14, fontSize: 13, fontWeight: 700, textAlign: "center", color: "var(--text)" }}>[TBD] vs [TBD]</div>
        </div>
      </div>
    </FantasyShell>
  );
}
