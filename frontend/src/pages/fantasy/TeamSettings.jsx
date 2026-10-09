import { useState } from "react";
import { useNavigate } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { API } from "../../utils/helpers";
import { API_BASE, base, SEASON, useFantasyApi } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import "./Join.css";

// Team Settings: notifications (not built yet) and Leave the league. Name / abbreviation / picture / color are
// edited where the team name lives — the Roster page's team header (TeamEditor).
// Leaving before the draft removes the team; once the draft has started it becomes a bot.
export default function TeamSettings() {
  const user = useCurrentUser();
  const navigate = useNavigate();
  const [scenario] = useFantasyScenario();
  const info = useFantasyApi("league/members");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const team = info && info.my_team_id ? info.teams.find(t => t.id === info.my_team_id) : null;

  async function leave() {
    const before = info.draft_status === "not_started";
    if (!window.confirm(before ? "Leave the league? Your team is removed." : "Leave the league? Your team becomes a bot the commissioner controls.")) return;
    setBusy(true); setError(null);
    const r = await fetch(`${API}${API_BASE}/league/leave?scenario=${scenario}`, { method: "POST", credentials: "include" });
    const out = await r.json().catch(() => ({}));
    setBusy(false);
    if (!r.ok) { setError(out.detail || "Couldn't leave"); return; }
    navigate(base());
  }

  let body;
  if (user === undefined || info === undefined) body = <p style={{ fontSize: 13 }}>Loading…</p>;
  else if (!user) body = <p style={{ fontSize: 13 }}>Log in to edit your team.</p>;
  else if (!team) body = <p style={{ fontSize: 13 }}>You don't have a team in this league.</p>;
  else body = (
    <div className="lj">
      <section className="lj-panel" aria-label="Notifications">
        <span className="lj-label"><span className="lj-tick" aria-hidden="true" />Notifications</span>
        <span className="lj-uc">Under construction</span>
      </section>
      {error && <div className="lj-error" role="alert">{error}</div>}
      {info.can_leave && (
        <section className="lj-panel lj-leave" aria-label="Leave the league">
          <span className="lj-label"><span className="lj-tick" aria-hidden="true" />Leave the league</span>
          <span className="lj-leave-row">
            <span>{info.draft_status === "not_started" ? "Your team is removed from the league." : "Your team stays in the league as a bot the commissioner controls."}</span>
            <button type="button" className="lj-leave-btn" disabled={busy} onClick={leave}>Leave the league</button>
          </span>
        </section>
      )}
    </div>
  );

  return <FantasyShell title="Team Settings" season={SEASON}>{body}</FantasyShell>;
}
