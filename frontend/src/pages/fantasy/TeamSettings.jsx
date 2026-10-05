import { useState } from "react";
import { useNavigate } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { API } from "../../utils/helpers";
import { API_BASE, base, SEASON, useFantasyApi } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { TEAM_COLOR_GROUPS } from "../../components/fantasy/teamColors";
import "./Join.css";

// Team settings. Editing name / abbreviation / picture / notifications isn't wired yet (the API
// exists in backend settings.py); for now this holds Leave the league, tucked at the bottom.
// Leaving before the draft removes the team; once the draft has started it becomes a bot.
export default function TeamSettings() {
  const user = useCurrentUser();
  const navigate = useNavigate();
  const [scenario] = useFantasyScenario();
  const info = useFantasyApi("league/members");
  const [busy, setBusy] = useState(false);
  const [color, setColor] = useState(null);
  const [savingColor, setSavingColor] = useState(false);
  const [colorNote, setColorNote] = useState(null);
  const [error, setError] = useState(null);
  const team = info && info.my_team_id ? info.teams.find(t => t.id === info.my_team_id) : null;

  async function saveColor() {
    setSavingColor(true); setColorNote(null);
    const r = await fetch(`${API}${API_BASE}/teams/${encodeURIComponent(team.id)}/settings`, {
      method: "PUT", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ color }),
    });
    const out = await r.json().catch(() => ({}));
    setSavingColor(false);
    setColorNote(r.ok ? "Saved." : out.detail || "Couldn't save");
    if (r.ok) team.color = color;
  }

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
      <section className="lj-panel" aria-label="Your team" style={{ flexDirection: "row", alignItems: "center", gap: 16 }}>
        <TeamIcon team={team} size={52} />
        <span className="lj-preview-name">{team.name}</span>
        <span className="lj-abbr">{team.abbreviation}</span>
      </section>
      <section className="lj-panel" aria-label="Team color">
        <span className="lj-label"><span className="lj-tick" aria-hidden="true" />Team color</span>
        <span style={{ fontSize: 14 }}>Your accent across the site — scorebug, team headers, draft board — even when you have a picture.</span>
        <div className="lj-swatches" role="radiogroup" aria-label="Team color">
          {TEAM_COLOR_GROUPS.flatMap(g => g.colors).map(([label, hex]) => (
            <button key={hex} type="button" role="radio" aria-checked={(color ?? team.color) === hex} aria-label={label} title={label}
              className="lj-swatch" style={{ background: hex }} onClick={() => setColor(hex)} />
          ))}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ width: 120, height: 36, borderRadius: 8, background: `linear-gradient(90deg, ${color || team.color} 0%, transparent 100%)` }} aria-hidden="true" />
          <button type="button" disabled={savingColor || !color || color === team.color} onClick={saveColor}>Save color</button>
          {colorNote && <span style={{ fontSize: 14 }}>{colorNote}</span>}
        </div>
      </section>
      <section className="lj-panel" aria-label="Edit team">
        <span className="lj-label"><span className="lj-tick" aria-hidden="true" />Name, picture &amp; notifications</span>
        <span style={{ fontSize: 14 }}>Under construction.</span>
      </section>
      {error && <div className="lj-error" role="alert">{error}</div>}
      {info.can_leave && (
        <section className="lj-panel" aria-label="Leave the league">
          <span className="lj-label"><span className="lj-tick" aria-hidden="true" />Leave the league</span>
          <span style={{ fontSize: 14 }}>
            {info.draft_status === "not_started" ? "Your team is removed from the league." : "Your team stays in the league as a bot the commissioner controls."}
          </span>
          <button type="button" disabled={busy} onClick={leave} style={{ alignSelf: "flex-start" }}>Leave the league</button>
        </section>
      )}
    </div>
  );

  return <FantasyShell title="Team Settings" season={SEASON}>{body}</FantasyShell>;
}
