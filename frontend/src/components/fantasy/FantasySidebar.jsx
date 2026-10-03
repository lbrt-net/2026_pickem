import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";
import { SECTIONS, isLinkActive } from "./nav";
import { seasonOf } from "./data";
import "../shared/nav.css";

// Product-specific navigation only — home link, season selector, and the
// user dropdown live in the top bar (FantasyShell -> MainNav), not here.
// Rendered inside MainNav's menu drawer, which owns positioning/open state.
// Sections and links are defined in nav.js (shared with FantasyShell's tabs).

const SCENARIOS = [
  { value: "live", label: "Live" },
  { value: "test_pre", label: "Test: pre-draft" },
  { value: "test_post", label: "Test: post-draft" },
];

// Admin-only. 2026-27: pick which sandbox the pages show, and reset test ones.
// 2025-26 test league: its replay controls.
function ScenarioControl({ season }) {
  const [scenario, setScenario] = useFantasyScenario();
  const base = `/fantasy/${season}`;
  const [busy, setBusy] = useState(false);

  async function reset() {
    setBusy(true);
    await fetch(`${API}/fantasy/2026_27/admin/scenario/${scenario}/reset`, { method: "POST", credentials: "include" });
    window.location.reload();
  }

  return (
    <div className="side-nav-footer">
      <div className="side-nav-section" style={{ padding: "0 10px" }}>Admin · Sandbox</div>
      {scenario === "replay" ? <Link to={`${base}/replay`} style={{ fontSize: 12 }}>Replay controls &rarr;</Link> : (
        <select value={scenario} onChange={e => setScenario(e.target.value)} style={{ fontSize: 12 }}>
          {SCENARIOS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      )}
      {scenario !== "live" && scenario !== "replay" && (
        <button onClick={reset} disabled={busy} style={{ fontSize: 12, padding: "4px 8px" }}>
          {busy ? "Resetting…" : "Reset this sandbox"}
        </button>
      )}
      <Link to={`${base}/league-settings`} style={{ fontSize: 12 }}>League settings &rarr;</Link>
    </div>
  );
}

export default function FantasySidebar() {
  const location = useLocation();
  const user = useCurrentUser();
  const season = seasonOf(location.pathname);
  const base = `/fantasy/${season}`;

  return (
    <nav className="side-nav" aria-label="Fantasy">
      {SECTIONS.map(section => (
        <div key={section.label} style={{ display: "contents" }}>
          <div className="side-nav-section">{section.label}</div>
          {section.links.map(link => {
            const active = isLinkActive(link, base, location.pathname);
            return (
              <Link key={link.path} to={`${base}${link.path}`}
                className={`side-nav-link${active ? " active" : ""}`}
                aria-current={active ? "page" : undefined}>
                {link.label}
              </Link>
            );
          })}
        </div>
      ))}
      {user?.isAdmin && <ScenarioControl season={season} />}
    </nav>
  );
}
