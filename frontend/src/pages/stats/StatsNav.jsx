import { NavLink } from "react-router-dom";
import "./StatsNav.css";

// The stats pages, one row of links above the title. Stats never link into fantasy.
export default function StatsNav() {
  return (
    <nav className="stats-nav" aria-label="Stats pages">
      <NavLink to="/stats/shooting" end>Shooting</NavLink>
      <NavLink to="/stats/shooting/breakdown" end>Shot breakdown</NavLink>
      <NavLink to="/stats/rebounding" end>Rebounding</NavLink>
      <NavLink to="/stats/playmaking" end>Playmaking</NavLink>
      <NavLink to="/stats/lineups" end>Lineups</NavLink>
    </nav>
  );
}
