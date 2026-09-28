import { useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { SEASON, useFantasyApi } from "../../components/fantasy/data";

const FILTERS = ["All", "Adds & Drops", "Trades", "Draft"];

// Only draft picks are recorded so far; adds, drops, and trades will join this feed once they exist.
export default function Transactions() {
  const [filter, setFilter] = useState("All");
  const draft = useFantasyApi("draft");
  const picks = draft?.picks || [];
  const items = filter === "All" || filter === "Draft" ? [...picks].reverse() : [];

  return (
    <FantasyShell title="League Activity" season={SEASON}>
      <div style={{ border: "1px solid var(--border)", padding: 12, marginBottom: 14 }}>
        <div style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 6 }}>Summary</div>
        <div style={{ fontSize: 13 }}>{picks.length} draft picks · 0 adds · 0 drops · 0 trades</div>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        {FILTERS.map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{ fontSize: 13, padding: "4px 10px", fontWeight: filter === f ? 700 : 400, borderColor: filter === f ? "var(--text)" : "var(--border)" }}>
            {f}
          </button>
        ))}
      </div>

      {draft === undefined && <p style={{ fontSize: 13 }}>Loading…</p>}
      {draft !== undefined && items.length === 0 && <p style={{ fontSize: 13 }}>Nothing here yet.</p>}
      {items.map(p => (
        <div key={p.pick} style={{ display: "flex", gap: 12, fontSize: 13, padding: "6px 0", borderBottom: "1px solid var(--border-subtle)", alignItems: "center" }}>
          <div style={{ width: 60, border: "1px solid var(--border)", textAlign: "center", fontSize: 11 }}>DRAFT</div>
          <div>
            <TeamLink ownerId={p.owner_user_id} name={p.team_name} /> drafted <EntityLink id={p.id} name={p.name} /> ({p.position}) — round {p.round}, pick {p.pick}
          </div>
        </div>
      ))}
    </FantasyShell>
  );
}
