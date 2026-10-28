import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useLeague, statsRoot } from "./statsLeague";
import "./StatsNav.css";

// The stats pages, one row of links above the title (Shooting covers its sub-tabs), within the area you're in, and the
// NBA / WNBA switch: /stats/nba/… and /stats/wnba/…, two separate areas on separate data (2026-10-21). The switch keeps
// the page you're on when the other league has it. Stats never link into fantasy.
const NBA_ONLY = ["standings", "games"];
export default function StatsNav() {
  const league = useLeague(), root = statsRoot(league);
  const { pathname } = useLocation(), navigate = useNavigate();
  const go = to => {
    if (to === league) return;
    const rest = pathname.replace(/^\/stats\/(nba|wnba)/, "");
    const page = rest.split("/")[1] || "";
    navigate(`${statsRoot(to)}${to === "wnba" && NBA_ONLY.includes(page) ? "" : rest}`);
  };
  return (
    <div className="stats-navrow">
      <div className="stats-league" role="radiogroup" aria-label="League">
        {[["nba", "NBA"], ["wnba", "WNBA"]].map(([v, l]) => <button key={v} role="radio" aria-checked={league === v} onClick={() => go(v)}>{l}</button>)}
      </div>
      <nav className="stats-nav" aria-label="Stats pages">
        {league === "nba" && <NavLink to={`${root}/games`}>Games</NavLink>}
        {league === "nba" && <NavLink to={`${root}/standings`} end>Standings</NavLink>}
        <NavLink to={`${root}/shooting`}>Shooting</NavLink>
        <NavLink to={`${root}/rebounding`} end>Rebounding</NavLink>
        <NavLink to={`${root}/playmaking`} end>Playmaking</NavLink>
        <NavLink to={`${root}/gravity`} end>Gravity</NavLink>
        <NavLink to={`${root}/lineups`} end>Lineups</NavLink>
      </nav>
    </div>
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

// Tabs inside Games (2026-10-28): each day's games, and how the predictions have done against the results.
export function GamesTabs() {
  const root = statsRoot(useLeague());
  return (
    <div className="stats-tabs" role="tablist">
      <NavLink to={`${root}/games`} end>By day</NavLink>
      <NavLink to={`${root}/games/accuracy`} end>Predicted vs actual</NavLink>
    </div>
  );
}
