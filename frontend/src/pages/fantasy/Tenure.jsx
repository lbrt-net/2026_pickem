import { useNavigate, useSearchParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { base, SEASON, useFantasyApi } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";

const cell = { padding: "6px 8px", textAlign: "left" };

// ?team=<ownerId>, defaults to your own team. Only the draft is recorded so far, so
// every row is "drafted, current" until adds/drops/trades exist.
export default function Tenure() {
  const user = useCurrentUser();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const draft = useFantasyApi("draft");

  const order = draft?.order || [];
  const owner = params.get("team") || user?.discordId || order[0]?.owner_user_id;
  const team = order.find(t => t.owner_user_id === owner);
  const picks = (draft?.picks || []).filter(p => p.owner_user_id === owner);

  return (
    <FantasyShell title="Team History" season={SEASON}>
      <p style={{ fontSize: 13, marginBottom: 10 }}>
        Every player who has ever been on a team's roster, and when. Grows across future seasons.
      </p>
      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 14, fontSize: 13 }}>
        <span>Team</span>
        <select value={owner ?? ""} onChange={e => navigate(`${base()}/tenure?team=${e.target.value}`)} style={{ fontSize: 13 }}>
          {order.map(t => <option key={t.id} value={t.owner_user_id}>{t.name}</option>)}
        </select>
        {team && <TeamLink ownerId={team.owner_user_id} name="Current roster →" />}
      </div>

      {draft === undefined ? <p style={{ fontSize: 13 }}>Loading…</p> : (
        <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.04em", borderBottom: "1px solid var(--border)" }}>
              <th style={cell}>Player</th><th style={cell} title="Position">Pos</th><th style={cell}>Joined</th><th style={cell}>Status</th>
            </tr>
          </thead>
          <tbody>
            {picks.map(p => (
              <tr key={p.pick} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                <td style={cell}><EntityLink id={p.id} name={p.name} /></td>
                <td style={cell}>{p.position}</td>
                <td style={cell}>2026-27 draft, round {p.round} (pick {p.pick})</td>
                <td style={cell}>Current ({p.slot})</td>
              </tr>
            ))}
            {picks.length === 0 && <tr><td colSpan={4} style={cell}>Nobody has been on this roster yet.</td></tr>}
          </tbody>
        </table>
      )}
    </FantasyShell>
  );
}
