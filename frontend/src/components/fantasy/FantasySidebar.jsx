import { Link, useLocation } from "react-router-dom";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { SECTIONS, isLinkActive } from "./nav";
import { seasonOf } from "./data";
import "../shared/nav.css";

// Product-specific navigation only — home link, season selector, and the
// user dropdown live in the top bar (FantasyShell -> MainNav), not here.
// Rendered inside MainNav's menu drawer, which owns positioning/open state.
// Sections and links are defined in nav.js (shared with FantasyShell's tabs).

// Admin-only, 2025-26 test league: a link to its replay controls. (The 2026-27 sandbox switcher was removed 2026-11-08.)
function ReplayLink({ season }) {
  const [scenario] = useFantasyScenario();
  if (scenario !== "replay") return null;
  return (
    <div className="side-nav-footer">
      <Link to={`/fantasy/${season}/replay`} style={{ fontSize: 12 }}>Replay controls &rarr;</Link>
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
            if (link.admin && !user?.isAdmin) return null;  // commissioner-only pages (Projection Check)
            if (link.disabled) return <span key={link.path} className="side-nav-link disabled" aria-disabled="true">{link.label}</span>;
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
      {user?.isAdmin && <ReplayLink season={season} />}
    </nav>
  );
}
