import { Link, useLocation, useNavigate } from "react-router-dom";

// Only one fantasy season exists today. When a second one ships, add it here —
// same pattern as the pickem Sidebar's YEARS array.
const SEASONS = ["2026-27"];

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

export default function FantasySidebar({ season = SEASONS[SEASONS.length - 1] }) {
  const location = useLocation();
  const navigate = useNavigate();
  const base = `/fantasy/${season}`;

  return (
    <div style={{ width: 180, flexShrink: 0, borderRight: "1px solid #ccc", padding: "16px 12px", display: "flex", flexDirection: "column", gap: 4 }}>
      <Link to="/" style={{ fontSize: 11, color: "#666", marginBottom: 12, textDecoration: "none" }}>&larr; lbrt.net</Link>

      {SEASONS.length > 1 ? (
        <select
          value={season}
          onChange={e => navigate(`/fantasy/${e.target.value}`)}
          style={{ marginBottom: 8, fontSize: 12, padding: 4 }}
        >
          {SEASONS.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      ) : (
        <div style={{ fontSize: 11, color: "#999", marginBottom: 8 }}>Season {season}</div>
      )}

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
