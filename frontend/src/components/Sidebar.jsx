import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { API } from "../utils/helpers";

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

  // Only 2026 exists today. When a future year ships, add it here and the
  // selector below picks it up — no other wiring needed.
  const YEARS = ["2026"];
  const year = YEARS.find(y => location.pathname.startsWith(`/pickem/${y}`)) || YEARS[YEARS.length - 1];

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

        {YEARS.length > 1 ? (
          <select
            className="sidebar-year-select"
            value={year}
            onChange={e => go(`/pickem/${e.target.value}`)}
            style={{ margin: "10px 10px 4px", fontSize: 11, fontWeight: 600 }}
          >
            {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        ) : (
          <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)", padding: "10px 10px 4px" }}>
            {year}
          </div>
        )}
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
