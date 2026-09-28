import { Link, useNavigate, useParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { EntityLink } from "../../components/fantasy/links";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { BASE, SEASON, rosterBySlot, teamPath, useFantasyApi } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";

const cell = { padding: "6px 8px" };

// /team = your own team; /team/:ownerId = any team (read-only unless it's yours).
export default function TeamManagement() {
  const { ownerId } = useParams();
  const navigate = useNavigate();
  const user = useCurrentUser();
  const teams = useFantasyApi("teams");

  const targetOwner = ownerId || user?.discordId;
  const team = teams?.find(t => t.owner_user_id === targetOwner);
  const mine = !!user && team?.owner_user_id === user.discordId;
  const rank = teams && team ? teams.indexOf(team) + 1 : null;

  let body;
  if (teams === undefined || (!ownerId && user === undefined)) {
    body = <p style={{ fontSize: 13 }}>Loading…</p>;
  } else if (!ownerId && !user) {
    body = <p style={{ fontSize: 13 }}>Log in to see your team, or pick any team above.</p>;
  } else if (!team) {
    body = <p style={{ fontSize: 13 }}>{ownerId ? "No team found for this owner." : "You don't have a team in this league."}</p>;
  } else {
    body = (
      <>
        <div style={{ fontSize: 14, marginBottom: 14, display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
          <TeamIcon team={team} size={40} />
          <span>{team.total_fantasy_points} Fantasy Pts per game</span>
          <span>#{rank} of {teams.length} in <Link to={`${BASE}/standings`}>Standings</Link></span>
          <Link to={`${BASE}/tenure?team=${team.owner_user_id}`}>Team History</Link>
          {mine && <Link to={`${BASE}/team/settings`}>Team Settings</Link>}
          {!mine && user && <Link to={`${BASE}/trades?with=${team.owner_user_id}`}>Propose a trade</Link>}
        </div>

        <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse", marginBottom: 14 }}>
          <thead>
            <tr style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.04em", borderBottom: "1px solid var(--border)", textAlign: "left" }}>
              <th style={cell} title="Roster slot">Slot</th>
              <th style={cell}>Name</th>
              <th style={cell} title="Position">Pos</th>
              <th style={cell} title="NBA team">NBA</th>
              <th style={{ ...cell, textAlign: "right" }} title="Fantasy points per game">Fantasy Pts</th>
            </tr>
          </thead>
          <tbody>
            {rosterBySlot(team.roster).map(({ slot, entry }, i) => (
              <tr key={i} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                <td style={{ ...cell, fontWeight: 700 }}>{slot}</td>
                <td style={cell}>{entry ? <EntityLink id={entry.id} name={entry.name} /> : <Link to={`${BASE}/players`}>Empty — find a player</Link>}</td>
                <td style={cell}>{entry?.position ?? ""}</td>
                <td style={cell}>{entry?.kind === "player" ? <EntityLink id={entry.nba_team} name={entry.nba_team} /> : ""}</td>
                <td style={{ ...cell, textAlign: "right" }}>{entry?.fantasy_points ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <p style={{ fontSize: 13 }}>
          All 11 slots count every week (no bench). Adding, dropping, and swapping players aren't built yet.
        </p>
      </>
    );
  }

  return (
    <FantasyShell title={team ? team.name : "Team"} season={SEASON}>
      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 14, fontSize: 13 }}>
        <span>View team</span>
        <select value={team?.owner_user_id ?? ""} onChange={e => navigate(teamPath(e.target.value))} style={{ fontSize: 13 }}>
          {!team && <option value="">Choose…</option>}
          {(teams || []).map(t => <option key={t.id} value={t.owner_user_id}>{t.name}{user && t.owner_user_id === user.discordId ? " (you)" : ""}</option>)}
        </select>
      </div>
      {body}
    </FantasyShell>
  );
}
