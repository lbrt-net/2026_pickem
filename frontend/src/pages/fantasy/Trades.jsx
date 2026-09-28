import FantasyShell from "../../components/fantasy/FantasyShell";

const pending = [
  "Screen Time offers Domantas Sabonis for your Jaylen Brown",
  "Full Court Press offers Jordan Poole for your Bam Adebayo",
  "Rim Reapers offers Franz Wagner for Bench Mob's Cam Johnson", // shown because trades are public
];

const history = [
  ["Buzzer Beaters traded Deandre Ayton to Airball Assassins for Cam Johnson", "3 days ago"],
  ["Rim Reapers traded Jalen Suggs to Bench Mob for Herbert Jones", "1 week ago"],
];

export default function Trades() {
  const send = [];
  const receive = [];

  return (
    <FantasyShell title="Trade Center" season="2026_27">
      <div style={{ fontSize: 10, color: "var(--text)", marginBottom: 10 }}>Player-for-player only — no draft picks. All trades, including pending ones, are visible to the whole league.</div>

      <div style={{ border: "1px solid var(--border)", padding: 14, marginBottom: 14 }}>
        <div style={{ fontSize: 10, color: "var(--text)", marginBottom: 8 }}>PROPOSE TRADE (starts empty)</div>
        <div style={{ display: "flex", gap: 20 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 4 }}>You send</div>
            {send.length === 0 && <div style={{ border: "1px dashed var(--border)", padding: 8, fontSize: 12, color: "var(--text)" }}>+ add player</div>}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 4 }}>You receive (from: choose team ▾)</div>
            {receive.length === 0 && <div style={{ border: "1px dashed var(--border)", padding: 8, fontSize: 12, color: "var(--text)" }}>+ add player</div>}
          </div>
        </div>
        <button style={{ marginTop: 10, border: "1px solid var(--border)", padding: "8px 16px", fontSize: 12, background: "var(--surface-2)" }}>Propose Trade</button>
      </div>

      <div style={{ border: "1px solid var(--border)", padding: 14, marginBottom: 14 }}>
        <div style={{ fontSize: 10, color: "var(--text)", marginBottom: 6 }}>PENDING TRADES (all teams, since trades are public)</div>
        {pending.map(p => (
          <div key={p} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, padding: "6px 0", borderBottom: "1px solid var(--border-subtle)" }}>
            <span>{p}</span>
            <span style={{ display: "flex", gap: 6 }}>
              <span style={{ border: "1px solid var(--border)", padding: "2px 8px", fontSize: 11 }}>Accept</span>
              <span style={{ border: "1px solid var(--border)", padding: "2px 8px", fontSize: 11 }}>Reject</span>
            </span>
          </div>
        ))}
      </div>

      <div style={{ border: "1px solid var(--border)", padding: 14 }}>
        <div style={{ fontSize: 10, color: "var(--text)", marginBottom: 6 }}>TRADE HISTORY (public, league-wide)</div>
        {history.map(([desc, when]) => <div key={desc} style={{ fontSize: 12, padding: "3px 0", color: "var(--text)" }}>{desc} — {when}</div>)}
      </div>
    </FantasyShell>
  );
}
