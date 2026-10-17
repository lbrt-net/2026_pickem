import { NavLink, useLocation } from "react-router-dom";
import "./StatsNav.css";

// The stats pages, one row of links above the title (Shooting covers its sub-tabs). Stats never link into fantasy.
export default function StatsNav() {
  return (
    <nav className="stats-nav" aria-label="Stats pages">
      <NavLink to="/stats/shooting">Shooting</NavLink>
      <NavLink to="/stats/rebounding" end>Rebounding</NavLink>
      <NavLink to="/stats/playmaking" end>Playmaking</NavLink>
      <NavLink to="/stats/lineups" end>Lineups</NavLink>
    </nav>
  );
}

// Tabs inside Shooting: the scoreboard and the breakdown are one page with two views.
export function ShootingTabs() {
  const { pathname } = useLocation();
  return (
    <div className="stats-tabs" role="tablist">
      <NavLink to="/stats/shooting" end className={pathname === "/stats/shooting" ? "active" : ""}>Scoreboard</NavLink>
      <NavLink to="/stats/shooting/breakdown" end>By zone, type and situation</NavLink>
    </div>
  );
}
