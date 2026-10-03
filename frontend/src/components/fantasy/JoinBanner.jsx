import { Link, useLocation } from "react-router-dom";
import { base, useFantasyApi } from "./data";
import useCurrentUser from "../../hooks/useCurrentUser";
import { API } from "../../utils/helpers";

// The obvious way in: a full-width gradient Join button at the top of fantasy Home, shown only
// while the viewer isn't in the league and joining is open (Home.css .hm-join).
export default function JoinBanner() {
  const user = useCurrentUser();
  const location = useLocation();
  const info = useFantasyApi("league/members");
  if (!info || info.my_team_id || info.draft_status !== "not_started" || info.teams.length >= info.team_limit) return null;

  const arrow = (
    <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
      <path d="M4 11h13M12 5l6 6-6 6" stroke="currentColor" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
  if (user === null) {
    return <a className="hm-join" href={`${API}/auth/discord?next=${encodeURIComponent(location.pathname)}`}>Log in to join{arrow}</a>;
  }
  return <Link className="hm-join" to={`${base()}/join`}>Join this league{arrow}</Link>;
}
