import useFantasyScenario from "../../hooks/useFantasyScenario";
import "./LeagueHeader.css";

// The 2026-27 league's header image (commissioner's pick, 2026-10-11: Steven Adams as Ned Stark — "GTA VI is coming").
// Shown at the top of Home, Rules and Join for the 2026-27 league; not on the 2025-26 test league.
export default function LeagueHeader() {
  const [scenario] = useFantasyScenario();
  if (scenario === "replay") return null;
  return <img className="league-header" src="/fantasy/league-header-2026-27.jpg" alt="Steven Adams as Ned Stark: GTA VI is coming" />;
}
