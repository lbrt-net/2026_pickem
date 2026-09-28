import { Link, useParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { BASE, SEASON, useFantasyApi } from "../../components/fantasy/data";
import GameLog from "../../components/fantasy/GameLog";

const PLAYER_STATS = [
  ["Games played", "games_played"], ["Minutes", "minutes"], ["Points", "pts"],
  ["Off Reb", "off_reb"], ["Def Reb", "def_reb"], ["Assists", "ast"], ["Steals", "stl"], ["Blocks", "blk"],
  ["Fantasy Pts", "fantasy_points"],
];
const TEAM_STATS = [
  ["Games played", "games_played"], ["Wins", "wins"], ["Pts For", "pts"], ["Pts Against", "opp_pts"], ["Fantasy Pts", "fantasy_points"],
];

const box = { border: "1px solid var(--border)", padding: 14, marginBottom: 14 };
const heading = { fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 8 };

// One page for both draftable kinds: players (p1, p2, …) and NBA team units (ATL, BOS, …).
export default function PlayerDetail() {
  const { id } = useParams();
  const players = useFantasyApi("players");
  const nbaTeams = useFantasyApi("nba-teams");
  const draft = useFantasyApi("draft");

  if (players === undefined || nbaTeams === undefined) {
    return <FantasyShell title="Player" season={SEASON}><p style={{ fontSize: 13 }}>Loading…</p></FantasyShell>;
  }

  const player = (players || []).find(p => p.id === id);
  const nbaTeam = (nbaTeams || []).find(t => t.id === id);
  const entity = player || nbaTeam;
  if (!entity) {
    return (
      <FantasyShell title="Not found" season={SEASON}>
        <p style={{ fontSize: 13 }}>No player or NBA team with id "{id}". <Link to={`${BASE}/players`}>Back to Players</Link></p>
      </FantasyShell>
    );
  }

  const pick = draft?.picks?.find(p => p.id === id);
  const stats = player ? PLAYER_STATS : TEAM_STATS;
  // For a player: teammates on the same NBA team. For an NBA team unit: its players.
  const related = (players || [])
    .filter(p => p.id !== id && p.nba_team === (player ? player.nba_team : nbaTeam.id))
    .sort((a, b) => b.fantasy_points - a.fantasy_points);
  const unit = player && (nbaTeams || []).find(t => t.id === player.nba_team);

  return (
    <FantasyShell title={entity.name} season={SEASON}>
      <div style={{ fontSize: 14, marginBottom: 14, display: "flex", gap: 16, flexWrap: "wrap" }}>
        <span>{player ? player.position : "NBA team unit"}</span>
        {player && <span>NBA: {unit ? <EntityLink id={unit.id} name={unit.name} /> : player.nba_team}</span>}
        <span>
          Fantasy team: {entity.team_name
            ? <><TeamLink ownerId={entity.owner_user_id} name={entity.team_name} /> ({entity.slot})</>
            : "Free agent"}
        </span>
        {pick && <span>Drafted: round {pick.round}, pick {pick.pick}</span>}
      </div>

      <div style={box}>
        <div style={heading}>Per-game averages{entity.stats_season ? ` (${entity.stats_season} regular season)` : ""}</div>
        <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
          {stats.map(([label, key]) => (
            <div key={key}>
              <div style={{ fontSize: 12 }}>{label}</div>
              <div style={{ fontSize: 20, fontWeight: 700 }}>{entity[key]}</div>
            </div>
          ))}
        </div>
      </div>

      <GameLog entityId={entity.id} />

      {related.length > 0 && (
        <div style={box}>
          <div style={heading}>{player ? `Other ${player.nba_team} players` : "Players on this team"}</div>
          <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
            <tbody>
              {related.map(p => (
                <tr key={p.id} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "5px 8px" }}><EntityLink id={p.id} name={p.name} /></td>
                  <td style={{ padding: "5px 8px" }}>{p.position}</td>
                  <td style={{ padding: "5px 8px" }}>{p.team_name ? <TeamLink ownerId={p.owner_user_id} name={p.team_name} /> : "Free agent"}</td>
                  <td style={{ padding: "5px 8px", textAlign: "right" }}>{p.fantasy_points} Fantasy Pts</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Link to={`${BASE}/players`} style={{ fontSize: 13 }}>&larr; All players</Link>
    </FantasyShell>
  );
}
