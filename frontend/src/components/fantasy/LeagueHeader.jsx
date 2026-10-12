import useFantasyScenario from "../../hooks/useFantasyScenario";
import { useFantasyApi } from "./data";
import "./LeagueHeader.css";

// The 2026-27 league's header (commissioner's pick, 2026-10-11): Steven Adams as Ned Stark, with the league name
// ("GTA is Coming") as text with it — the picture makes no sense without it. A short, wide banner: the photo was
// widened (sky and hill extended) so half the height keeps the same head-to-hands framing. Home's page title already
// is the league name, so Home passes showName={false}. Not on the 2025-26 test league.
export default function LeagueHeader({ showName = true }) {
  const [scenario] = useFantasyScenario();
  const info = useFantasyApi("league/members");
  if (scenario === "replay") return null;
  return (
    <div className="league-header">
      {showName && info?.league_name && <div className="league-header-name">{info.league_name}</div>}
      <img src="/fantasy/league-header-2026-27.jpg" alt="Steven Adams as Ned Stark" />
    </div>
  );
}
