import { Link, useLocation } from "react-router-dom";
import useCurrentUser from "../../hooks/useCurrentUser";
import UserChip from "../UserChip";

// The site-wide top bar: home link + season selector (when applicable) on
// the left, user dropdown on the right. Renders its own full-width bar so it
// looks identical on landing, pickem, fantasy, and account.
export default function MainNav({ seasonOptions, currentSeason, onSeasonChange, showHome = true }) {
  const user = useCurrentUser();
  const location = useLocation();
  const next = location.pathname + location.search;

  return (
    <div className="site-ui" style={{
      position: "sticky", top: 0, zIndex: 50,
      height: "var(--topbar-h)", boxSizing: "border-box",
      display: "flex", alignItems: "center", gap: 12,
      padding: "0 16px",
      background: "var(--surface)", borderBottom: "1px solid var(--border)",
    }}>
      {showHome && <Link to="/" style={{ fontSize: 13, fontWeight: 600, textDecoration: "none" }}>&larr; lbrt.net</Link>}

      {seasonOptions && seasonOptions.length > 1 && (
        <select value={currentSeason} onChange={e => onSeasonChange(e.target.value)} style={{ fontSize: 13 }}>
          {seasonOptions.map(({ value, label }) => <option key={value} value={value}>{label}</option>)}
        </select>
      )}
      {seasonOptions && seasonOptions.length === 1 && (
        <span style={{ fontSize: 13 }}>{seasonOptions[0].label}</span>
      )}

      <div style={{ marginLeft: "auto" }}>
        <UserChip user={user} next={next} extraLinks={[{ label: "Account", to: "/account" }, ...(user?.isAdmin ? [{ label: "Site Map", to: "/admin/sitemap" }] : [])]} />
      </div>
    </div>
  );
}
