import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { SEASON, useFantasyApi } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";

const box = { border: "1px solid var(--border)", padding: 14, marginBottom: 14 };
const heading = { fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 8 };

function RosterPicker({ team, chosen, onToggle }) {
  if (!team) return <div style={{ fontSize: 13 }}>Choose a team.</div>;
  if (team.roster.length === 0) return <div style={{ fontSize: 13 }}>Empty roster.</div>;
  return team.roster.map(e => (
    <label key={e.id} style={{ display: "flex", gap: 8, fontSize: 13, padding: "3px 0", alignItems: "center" }}>
      <input type="checkbox" checked={chosen.includes(e.id)} onChange={() => onToggle(e.id)} />
      <EntityLink id={e.id} name={e.name} /> ({e.position}, {e.fantasy_points})
    </label>
  ));
}

// ?with=<ownerId> preselects the trade partner (linked from team pages).
export default function Trades() {
  const user = useCurrentUser();
  const teams = useFantasyApi("teams");
  const [params] = useSearchParams();
  const [partner, setPartner] = useState(params.get("with") || "");
  const [send, setSend] = useState([]);
  const [receive, setReceive] = useState([]);

  const all = teams || [];
  const mine = user ? all.find(t => t.owner_user_id === user.discordId) : null;
  const other = all.find(t => t.owner_user_id === partner && t !== mine);
  const toggle = setter => id => setter(list => (list.includes(id) ? list.filter(x => x !== id) : [...list, id]));

  return (
    <FantasyShell title="Trade Center" season={SEASON}>
      <p style={{ fontSize: 13, marginBottom: 10 }}>Player-for-player only — no draft picks. All trades, including pending ones, are visible to the whole league.</p>

      <div style={box}>
        <div style={heading}>Propose trade</div>
        {!user && <div style={{ fontSize: 13 }}>Log in to propose a trade.</div>}
        {user && !mine && teams !== undefined && <div style={{ fontSize: 13 }}>You don't have a team in this league.</div>}
        {mine && (
          <>
            <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: 260 }}>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>You send (<TeamLink ownerId={mine.owner_user_id} name={mine.name} />)</div>
                <RosterPicker team={mine} chosen={send} onToggle={toggle(setSend)} />
              </div>
              <div style={{ flex: 1, minWidth: 260 }}>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4, display: "flex", gap: 8, alignItems: "center" }}>
                  You receive from
                  <select value={other?.owner_user_id ?? ""} onChange={e => { setPartner(e.target.value); setReceive([]); }} style={{ fontSize: 13 }}>
                    <option value="">choose team</option>
                    {all.filter(t => t !== mine).map(t => <option key={t.id} value={t.owner_user_id}>{t.name}</option>)}
                  </select>
                </div>
                <RosterPicker team={other} chosen={receive} onToggle={toggle(setReceive)} />
              </div>
            </div>
            <button disabled style={{ marginTop: 10, padding: "8px 16px", fontSize: 13 }}>Propose Trade</button>
            <span style={{ fontSize: 13, marginLeft: 10 }}>Sending trades isn't built yet.</span>
          </>
        )}
      </div>

      <div style={box}>
        <div style={heading}>Pending trades (league-wide)</div>
        <div style={{ fontSize: 13 }}>No pending trades.</div>
      </div>

      <div style={box}>
        <div style={heading}>Trade history (league-wide)</div>
        <div style={{ fontSize: 13 }}>No trades yet.</div>
      </div>
    </FantasyShell>
  );
}
