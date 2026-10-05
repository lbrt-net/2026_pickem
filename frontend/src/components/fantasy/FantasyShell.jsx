import { Link, useLocation, useNavigate } from "react-router-dom";
import FantasySidebar from "./FantasySidebar";
import MainNav from "../shared/MainNav";
import PlayerCardHost from "./PlayerCard";
import { findTabGroup } from "./nav";
import { seasonOf } from "./data";
import "../shared/nav.css";

// 2025-26 = the test league: the same pages as 2026-27 under /fantasy/2025_26/ (data.js seasonOf).
const SEASON_OPTIONS = [
  { value: "2026_27", label: "2026-27" },
  { value: "2025_26", label: "2025-26 (test league)" },
  { value: "2027_28", label: "2027-28" },
];
const SAME_PAGES = ["2026_27", "2025_26"];

// Skeleton-only shell: real navigation, no visual design pass yet.
// Every fantasy page renders through this — don't add per-page chrome.
// Top bar (site-wide: home/season/user) is separate from the sidebar
// (fantasy-specific nav only), which MainNav shows in its menu drawer —
// see Sidebar.jsx's pickem equivalent split.
//
// A page that's one tab of a main page (nav.js `tabs`, e.g. My Team's
// Lineup/History/Settings) gets the main page's name as its title plus the
// tab row, instead of its own `title`.
// `skeleton`: pages still built on projected/placeholder numbers (not real results) show a label.
export default function FantasyShell({ title, children, skeleton = false }) {
  const navigate = useNavigate();
  const location = useLocation();
  const season = seasonOf(location.pathname);
  const base = `/fantasy/${season}`;
  const group = findTabGroup(base, location.pathname);

  // Between 2026-27 and the 2025-26 test league, stay on the same page.
  function changeSeason(s) {
    const rest = location.pathname.slice(base.length);
    navigate(`/fantasy/${s}${SAME_PAGES.includes(s) ? rest : ""}`);
  }

  return (
    <div className="site-ui" style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)" }}>
      <MainNav
        seasonOptions={SEASON_OPTIONS}
        currentSeason={season}
        onSeasonChange={changeSeason}
        sidebar={<FantasySidebar />}
      />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1100, boxSizing: "border-box", minWidth: 0 }}>
        {skeleton && (
          <div style={{ fontSize: 11, color: "var(--accent-gold)", border: "1px solid var(--accent-gold)", display: "inline-block", padding: "2px 8px", marginBottom: 12 }}>
            SKELETON — numbers are projected placeholders, not real results yet
          </div>
        )}
        <h1 className="page-title">{group ? group.label : title}</h1>
        {group && (
          <nav className="page-tabs" aria-label={group.label}>
            {group.tabs.map(tab => {
              const active = location.pathname === base + tab.path;
              return (
                <Link key={tab.path} to={base + tab.path}
                  className={`page-tab${active ? " active" : ""}`}
                  aria-current={active ? "page" : undefined}>
                  {tab.label}
                </Link>
              );
            })}
          </nav>
        )}
        {children}
      </div>
      <PlayerCardHost />
    </div>
  );
}
