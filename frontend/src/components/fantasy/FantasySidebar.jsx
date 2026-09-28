import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";

// Product-specific navigation only — home link, season selector, and the
// user dropdown live in the top bar (FantasyShell -> MainNav), not here.
// Rendered inside MainNav's menu drawer, which owns positioning/open state.
const LINKS = [
  { label: "Home", path: "" },
  { label: "Standings", path: "/standings" },
  { label: "Matchup", path: "/matchup" },
  { label: "Players", path: "/players" },
  { label: "Draft", path: "/draft" },
  { label: "Trades", path: "/trades" },
  { label: "Transactions", path: "/transactions" },
  { label: "Team", path: "/team" },
  { label: "Team History", path: "/tenure" },
  { label: "Playoffs", path: "/playoffs" },
  { label: "Recap", path: "/recap" },
];

const SCENARIOS = [
  { value: "live", label: "Live" },
  { value: "test_pre", label: "Test: pre-draft" },
  { value: "test_post", label: "Test: post-draft" },
];

// Admin-only: pick which sandbox the fantasy pages show, and reset test ones.
function ScenarioControl() {
  const [scenario, setScenario] = useFantasyScenario();
  const [busy, setBusy] = useState(false);

  async function reset() {
    setBusy(true);
    await fetch(`${API}/fantasy/2026_27/admin/scenario/${scenario}/reset`, { method: "POST", credentials: "include" });
    window.location.reload();
  }

  return (
    <div style={{ marginTop: "auto", paddingTop: 12, borderTop: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>Admin: data sandbox</div>
      <select value={scenario} onChange={e => setScenario(e.target.value)} style={{ fontSize: 12 }}>
        {SCENARIOS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
      </select>
      {scenario !== "live" && (
        <button onClick={reset} disabled={busy} style={{ fontSize: 12, padding: "4px 8px" }}>
          {busy ? "Resetting…" : "Reset this sandbox"}
        </button>
      )}
    </div>
  );
}

export default function FantasySidebar({ season }) {
  const location = useLocation();
  const user = useCurrentUser();
  const base = `/fantasy/${season}`;

  return (
    <div style={{ flexGrow: 1, display: "flex", flexDirection: "column", gap: 4 }}>
      {LINKS.map(({ label, path }) => {
        const href = `${base}${path}`;
        const active = location.pathname === href || (path === "" && location.pathname === base);
        return (
          <Link
            key={path}
            to={href}
            style={{
              fontSize: 13,
              padding: "6px 8px",
              textDecoration: "none",
              color: "var(--text)",
              fontWeight: active ? 700 : 400,
              border: active ? "1px solid var(--border)" : "1px solid transparent",
              background: active ? "var(--surface-2)" : "transparent",
            }}
          >
            {label}
          </Link>
        );
      })}
      {user?.isAdmin && <ScenarioControl />}
    </div>
  );
}
