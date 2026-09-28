import { useNavigate } from "react-router-dom";
import FantasySidebar from "./FantasySidebar";
import MainNav from "../shared/MainNav";

const SEASON_OPTIONS = [
  { value: "2026_27", label: "2026-27" },
  { value: "2027_28", label: "2027-28" },
];

// Skeleton-only shell: real navigation, no visual design pass yet.
// Every fantasy page renders through this — don't add per-page chrome.
// Top bar (site-wide: home/season/user) is separate from the sidebar
// (fantasy-specific nav only) — see Sidebar.jsx's pickem equivalent split.
export default function FantasyShell({ title, season, children }) {
  const navigate = useNavigate();

  return (
    <div className="site-ui" style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)" }}>
      <MainNav
        seasonOptions={SEASON_OPTIONS}
        currentSeason={season}
        onSeasonChange={s => navigate(`/fantasy/${s}`)}
      />
      <div style={{ display: "flex" }}>
        <FantasySidebar season={season} />
        <div style={{ flexGrow: 1, padding: 24, maxWidth: 1100 }}>
          <div style={{ fontSize: 11, color: "var(--accent-gold)", border: "1px solid var(--accent-gold)", display: "inline-block", padding: "2px 8px", marginBottom: 12 }}>
            SKELETON — layout only, design not final
          </div>
          <h1 style={{ fontSize: 20, marginBottom: 16 }}>{title}</h1>
          {children}
        </div>
      </div>
    </div>
  );
}
