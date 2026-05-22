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

  const links2026 = [
    { label: "Bracket", path: "/" },
    { label: "My Picks", path: "/picks/me" },
    { label: "Leaderboard", path: "/leaderboard" },
    { label: "Rules", path: "/rules" },
    ...(isAdmin ? [{ label: "Admin", path: "/admin" }] : []),
  ];

  function isActive(path) {
    if (path === "/") return location.pathname === "/";
    if (path === "/picks/me") return location.pathname.startsWith("/picks");
    return location.pathname.startsWith(path);
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

        <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)", padding: "10px 10px 4px" }}>
          2026
        </div>
        {links2026.map(({ label, path }) => (
          <button key={path} className={`sidebar-link${isActive(path) ? " active" : ""}`}
            onClick={() => go(path)}>
            {label}
          </button>
        ))}
      </div>
    </>
  );
}
