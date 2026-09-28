import { Link, useLocation } from "react-router-dom";
import useCurrentUser from "../hooks/useCurrentUser";
import "./shared/nav.css";

// Product-specific navigation only — home link, year selector, and the user
// dropdown live in the top bar (AppTopBar -> MainNav), not here. Rendered
// inside MainNav's menu drawer, which owns the positioning and open state.
export default function Sidebar() {
  const location = useLocation();
  const user = useCurrentUser();

  const year = location.pathname.startsWith("/pickem/2027") ? "2027" : "2026";

  const links2026 = [
    { label: "Bracket", path: `/pickem/${year}` },
    { label: "My Picks", path: `/pickem/${year}/picks/me` },
    { label: "Leaderboard", path: `/pickem/${year}/leaderboard` },
    { label: "Rules", path: `/pickem/${year}/rules` },
  ];

  const linksAdmin = user?.isAdmin ? [
    { label: "Edit Bracket", path: `/pickem/${year}/admin` },
    { label: "User Admin", path: `/pickem/${year}/users` },
  ] : [];

  function isActive(path) {
    if (path === `/pickem/${year}`) return location.pathname === path;
    if (path === `/pickem/${year}/picks/me`) return location.pathname.startsWith(`/pickem/${year}/picks`);
    return location.pathname === path;
  }

  function renderLink({ label, path }) {
    const active = isActive(path);
    return (
      <Link key={path} to={path} className={`side-nav-link${active ? " active" : ""}`}
        aria-current={active ? "page" : undefined}>
        {label}
      </Link>
    );
  }

  return (
    <nav className="side-nav" aria-label="Pickem">
      <div className="side-nav-section">Playoff Pick'em</div>
      {links2026.map(renderLink)}

      {linksAdmin.length > 0 && (
        <div className="side-nav-footer">
          <div className="side-nav-section" style={{ padding: "0 10px 4px" }}>Admin</div>
          {linksAdmin.map(renderLink)}
        </div>
      )}
    </nav>
  );
}
