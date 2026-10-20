import { NavLink, useLocation } from "react-router-dom";
import { useLeague, statsRoot } from "./statsLeague";
import "./StatsNav.css";

// The stats pages, one row of links above the title (Shooting covers its sub-tabs), within the area you're in: NBA
// (/stats) or WNBA (/wnba/stats), two separate areas on separate data (2026-10-19). Stats never link into fantasy.
export default function StatsNav() {
  const league = useLeague(), root = statsRoot(league);
  return (
    <nav className="stats-nav" aria-label="Stats pages">
      <NavLink to={`${root}/shooting`}>Shooting</NavLink>
      <NavLink to={`${root}/rebounding`} end>Rebounding</NavLink>
      <NavLink to={`${root}/playmaking`} end>Playmaking</NavLink>
      <NavLink to={`${root}/gravity`} end>Gravity</NavLink>
      <NavLink to={`${root}/lineups`} end>Lineups</NavLink>
      {league === "nba" && <NavLink to="/stats/standings" end>Standings</NavLink>}
    </nav>
  );
}

// Tabs inside Shooting: the scoreboard and the breakdown are one page with two views.
export function ShootingTabs() {
  const { pathname } = useLocation(), root = statsRoot(useLeague());
  return (
    <div className="stats-tabs" role="tablist">
      <NavLink to={`${root}/shooting`} end className={pathname === `${root}/shooting` ? "active" : ""}>Scoreboard</NavLink>
      <NavLink to={`${root}/shooting/breakdown`} end>By zone, type and situation</NavLink>
    </div>
  );
}
