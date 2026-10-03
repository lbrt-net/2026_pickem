import { Link, useLocation } from "react-router-dom";
import { BASE, useFantasyApi } from "./data";
import { TEAM_COLOR_GROUPS } from "./teamColors";
import useCurrentUser from "../../hooks/useCurrentUser";
import { API } from "../../utils/helpers";

// The big, obvious way in: a multicolored Join button (stripes of the team palette) at the top
// of fantasy Home, shown only while the viewer isn't in the league and joining is open.
const STRIPE = TEAM_COLOR_GROUPS[0].colors.slice(0, 6).map(([, c], i) => `${c} ${i * 26}px ${(i + 1) * 26}px`).join(", ");

export default function JoinBanner() {
  const user = useCurrentUser();
  const location = useLocation();
  const info = useFantasyApi("league/members");
  if (!info || info.my_team_id || info.draft_status !== "not_started" || info.teams.length >= info.team_limit) return null;

  const style = { background: `repeating-linear-gradient(115deg, ${STRIPE})` };
  const arrow = (
    <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
      <path d="M4 11h13M12 5l6 6-6 6" stroke="currentColor" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
  if (user === null) {
    return (
      <a className="hm-join" style={style} href={`${API}/auth/discord?next=${encodeURIComponent(location.pathname)}`}>
        <span className="hm-join-label">Log in to join{arrow}</span>
      </a>
    );
  }
  return (
    <Link className="hm-join" style={style} to={`${BASE}/league?join=1`}>
      <span className="hm-join-label">Join this league{arrow}</span>
    </Link>
  );
}
