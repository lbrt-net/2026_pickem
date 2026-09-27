import { Link, useLocation } from "react-router-dom";

// Product-specific navigation only — home link, season selector, and the
// user dropdown live in the top bar (FantasyShell -> MainNav), not here.
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

export default function FantasySidebar({ season }) {
  const location = useLocation();
  const base = `/fantasy/${season}`;

  return (
    <div style={{ width: 180, flexShrink: 0, borderRight: "1px solid #ccc", padding: "16px 12px", display: "flex", flexDirection: "column", gap: 4 }}>
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
              color: active ? "#111" : "#555",
              fontWeight: active ? 700 : 400,
              border: active ? "1px solid #111" : "1px solid transparent",
            }}
          >
            {label}
          </Link>
        );
      })}
    </div>
  );
}
