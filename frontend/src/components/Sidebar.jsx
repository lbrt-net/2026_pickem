import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { API } from "../utils/helpers";

// Product-specific navigation only — home link, year selector, and the user
// dropdown live in the top bar (AppTopBar -> MainNav), not here.
export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [isAdmin, setIsAdmin] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    fetch(`${API}/me`, { credentials: "include" })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.is_admin) setIsAdmin(true); })
      .catch(() => {});
  }, []);

  const year = location.pathname.startsWith("/pickem/2027") ? "2027" : "2026";

  const links2026 = [
    { label: "Bracket", path: `/pickem/${year}` },
    { label: "My Picks", path: `/pickem/${year}/picks/me` },
    { label: "Leaderboard", path: `/pickem/${year}/leaderboard` },
    { label: "Rules", path: `/pickem/${year}/rules` },
  ];

  const linksAdmin = isAdmin ? [
    { label: "Edit Bracket", path: `/pickem/${year}/admin` },
    { label: "User Admin", path: `/pickem/${year}/users` },
  ] : [];

  function isActive(path) {
    if (path === `/pickem/${year}`) return location.pathname === path;
    if (path === `/pickem/${year}/picks/me`) return location.pathname.startsWith(`/pickem/${year}/picks`);
    return location.pathname === path;
  }

  function go(path) {
    navigate(path);
    setOpen(false);
  }

  return (
    <>
      <button className="sidebar-hamburger" onClick={() => setOpen(o => !o)}>☰</button>
      {open && <div className="sidebar-overlay" onClick={() => setOpen(false)} />}
      <div className={`sidebar${open ? " sidebar-open" : ""}`}>
        <div className="sidebar-title">Playoff Pick'em</div>

        {links2026.map(({ label, path }) => (
          <button key={path} className={`sidebar-link${isActive(path) ? " active" : ""}`}
            onClick={() => go(path)}>
            {label}
          </button>
        ))}

        {linksAdmin.length > 0 && (
          <div style={{ marginTop: "auto", paddingTop: 12, borderTop: "1px solid var(--border)" }}>
            {linksAdmin.map(({ label, path }) => (
              <button key={path} className={`sidebar-link${isActive(path) ? " active" : ""}`}
                onClick={() => go(path)}>
                {label}
              </button>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
