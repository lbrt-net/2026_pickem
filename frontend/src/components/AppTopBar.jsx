import { useNavigate, useLocation } from "react-router-dom";
import MainNav from "./shared/MainNav";

// Site-wide top bar for pickem pages (home/year/user). Pickem has no shared
// page shell like fantasy's FantasyShell, so each pickem page renders this
// directly instead of one wrapper covering all of them.
const YEAR_OPTIONS = [
  { value: "2026", label: "2026" },
  { value: "2027", label: "2027" },
];

export default function AppTopBar() {
  const navigate = useNavigate();
  const location = useLocation();
  const year = location.pathname.startsWith("/pickem/2027") ? "2027" : "2026";

  return (
    <MainNav
      seasonOptions={YEAR_OPTIONS}
      currentSeason={year}
      onSeasonChange={y => navigate(`/pickem/${y}`)}
    />
  );
}
