import FantasyShell from "../../components/fantasy/FantasyShell";
import { TeamLink } from "../../components/fantasy/links";
import { SEASON, useFantasyApi } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";

const box = { border: "1px solid var(--border)", padding: 14, marginBottom: 14 };
const label = { fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em" };

export default function TeamSettings() {
  const user = useCurrentUser();
  const teams = useFantasyApi("teams");
  const team = user && teams ? teams.find(t => t.owner_user_id === user.discordId) : null;

  let body;
  if (user === undefined || teams === undefined) body = <p style={{ fontSize: 13 }}>Loading…</p>;
  else if (!user) body = <p style={{ fontSize: 13 }}>Log in to edit your team.</p>;
  else if (!team) body = <p style={{ fontSize: 13 }}>You don't have a team in this league.</p>;
  else body = (
    <>
      <p style={{ fontSize: 13, marginBottom: 10 }}>
        Editing <TeamLink ownerId={team.owner_user_id} name={team.name} />. Saving isn't built yet.
      </p>
      <div style={box}>
        <div style={{ display: "flex", gap: 20, alignItems: "center" }}>
          <div style={{ width: 64, height: 64, border: "1px dashed var(--border)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12 }}>logo</div>
          <div style={{ flexGrow: 1 }}>
            <div style={label}>Team name</div>
            <input key={team.id} defaultValue={team.name} style={{ fontSize: 13, width: "100%", boxSizing: "border-box", marginTop: 2 }} />
          </div>
        </div>
        <div style={{ marginTop: 10 }}>
          <div style={label}>Team abbreviation</div>
          <input key={team.id} defaultValue={team.name.slice(0, 3).toUpperCase()} maxLength={3} style={{ fontSize: 13, width: 80, marginTop: 2 }} />
          <div style={{ fontSize: 12, color: "var(--accent-gold)", marginTop: 4 }}>
            Auto-generation + collision handling (two teams wanting the same letters) isn't decided yet.
          </div>
        </div>
        <button disabled style={{ marginTop: 12, padding: "6px 14px", fontSize: 13 }}>Change Logo</button>
      </div>

      <div style={box}>
        <div style={{ ...label, marginBottom: 8 }}>Notifications (no email — in-app/Discord only)</div>
        {["Trade offers", "Waiver results"].map(l => (
          <div key={l} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--border-subtle)", fontSize: 13 }}>
            <span>{l}</span>
            <input type="checkbox" defaultChecked />
          </div>
        ))}
      </div>

      <button disabled style={{ padding: "8px 20px", fontSize: 13 }}>Save Changes</button>
    </>
  );

  return <FantasyShell title="Team Settings" season={SEASON}>{body}</FantasyShell>;
}
