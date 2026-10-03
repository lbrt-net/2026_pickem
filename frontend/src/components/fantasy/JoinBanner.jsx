import { Link, useLocation } from "react-router-dom";
import { BASE, useFantasyApi } from "./data";
import useCurrentUser from "../../hooks/useCurrentUser";
import { API } from "../../utils/helpers";

// The big, obvious way in: shown at the top of fantasy Home whenever the viewer isn't in the
// league and joining is open (or they need to log in first). Opens the join form on the League page.
export default function JoinBanner() {
  const user = useCurrentUser();
  const location = useLocation();
  const info = useFantasyApi("league/members");
  if (!info || info.my_team_id || info.draft_status !== "not_started" || info.teams.length >= info.team_limit) return null;

  const wrap = { border: "2px solid var(--accent-blue)", background: "var(--surface)", padding: 18, marginBottom: 18, display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" };
  const button = { fontSize: 16, fontWeight: 700, padding: "10px 22px", background: "var(--accent-blue)", color: "var(--text)", textDecoration: "none", border: 0 };
  const spots = info.team_limit - info.teams.length;

  return (
    <div style={wrap}>
      <div style={{ flex: 1, minWidth: 220 }}>
        <div style={{ fontSize: 18, fontWeight: 700 }}>You're not in this league yet</div>
        <div style={{ fontSize: 14, marginTop: 4 }}>
          {info.teams.length} team{info.teams.length === 1 ? "" : "s"} in, {spots} spot{spots === 1 ? "" : "s"} left. Joining closes when the draft starts.
        </div>
      </div>
      {user === null ? (
        <a href={`${API}/auth/discord?next=${encodeURIComponent(location.pathname)}`} style={button}>Log in to join</a>
      ) : (
        <Link to={`${BASE}/league?join=1`} style={button}>Join this league &rarr;</Link>
      )}
    </div>
  );
}
