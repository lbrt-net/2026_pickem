import { useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { SEASON, useFantasyApi } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";

const FILTERS = ["My Team", "Drafted", "Free Agents", "By NBA Team", "NBA Teams"];

// [header, tooltip, value]
const PLAYER_COLUMNS = [
  ["GP", "Games played", p => p.games_played],
  ["MIN", "Minutes per game", p => p.minutes],
  ["PTS", "Points per game", p => p.pts],
  ["Off Reb", "Offensive rebounds per game", p => p.off_reb],
  ["Def Reb", "Defensive rebounds per game", p => p.def_reb],
  ["AST", "Assists per game", p => p.ast],
  ["STL", "Steals per game", p => p.stl],
  ["BLK", "Blocks per game", p => p.blk],
  ["Fantasy Pts", "Fantasy points per game: PTS +1, missed FG −0.5, 3PM +0.5, missed FT −0.5, Off Reb +1.5, Def Reb +0.5, AST +1, STL +2, BLK +1.5, TO −2", p => p.fantasy_points],
];

const TEAM_COLUMNS = [
  ["GP", "Games played", t => t.games_played],
  ["Wins", "Wins", t => t.wins],
  ["Pts For", "Points scored per game", t => t.pts],
  ["Pts Against", "Points allowed per game", t => t.opp_pts],
  ["Fantasy Pts", "Fantasy points per game (placeholder formula until league scoring is decided)", t => t.fantasy_points],
];

const cell = { padding: "6px 8px", textAlign: "right" };

export default function Players() {
  const user = useCurrentUser();
  const [scenario] = useFantasyScenario();
  const [filter, setFilter] = useState("Free Agents");
  const [nbaTeamFilter, setNbaTeamFilter] = useState("");
  const [search, setSearch] = useState("");
  const players = useFantasyApi("players");
  const nbaTeams = useFantasyApi("nba-teams");

  const showTeams = filter === "NBA Teams";
  const rows = (showTeams ? nbaTeams : players) || [];
  const columns = showTeams ? TEAM_COLUMNS : PLAYER_COLUMNS;
  const mine = e => user && e.owner_user_id === user.discordId;

  const visible = rows.filter(e => {
    if (search && !e.name.toLowerCase().includes(search.toLowerCase())) return false;
    if (filter === "My Team") return mine(e);
    if (filter === "Drafted") return !!e.team_id;
    if (filter === "Free Agents") return !e.team_id;
    if (filter === "By NBA Team") return !nbaTeamFilter || e.nba_team === nbaTeamFilter;
    return true;
  }).sort((a, b) => b.fantasy_points - a.fantasy_points);

  const nbaTeamOptions = players ? [...new Set(players.map(p => p.nba_team))].sort() : [];
  const loading = players === undefined || nbaTeams === undefined;
  const nbaIds = new Set((nbaTeams || []).map(t => t.id));

  return (
    <FantasyShell title="Players" season={SEASON}>
      <p style={{ fontSize: 13, marginBottom: 12 }}>
        Stats research and free agency in one place. Stats are per-game averages{players?.[0]?.stats_season ? ` from the ${players[0].stats_season} regular season` : " (dummy data until box scores are loaded)"}.
        {scenario !== "live" && <strong> Viewing test sandbox: {scenario === "test_pre" ? "pre-draft" : "post-draft"}.</strong>}
      </p>

      <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap", alignItems: "center" }}>
        {FILTERS.map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{
            fontSize: 13, padding: "5px 12px", fontWeight: filter === f ? 700 : 400,
            borderColor: filter === f ? "var(--text)" : "var(--border)",
          }}>
            {f}
          </button>
        ))}
        {filter === "By NBA Team" && (
          <select value={nbaTeamFilter} onChange={e => setNbaTeamFilter(e.target.value)} style={{ fontSize: 13 }}>
            <option value="">All teams</option>
            {nbaTeamOptions.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        )}
        <input placeholder="Search" value={search} onChange={e => setSearch(e.target.value)} style={{ fontSize: 13, marginLeft: "auto" }} />
      </div>

      {loading ? (
        <p style={{ fontSize: 13 }}>Loading…</p>
      ) : (
        <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.04em", borderBottom: "1px solid var(--border)" }}>
              <th style={{ ...cell, textAlign: "left" }}>Name</th>
              {!showTeams && <th style={{ ...cell, textAlign: "left" }} title="Position">Pos</th>}
              {!showTeams && <th style={{ ...cell, textAlign: "left" }} title="NBA team">NBA</th>}
              {columns.map(([h, tip]) => <th key={h} style={cell} title={tip}>{h}</th>)}
              <th style={{ ...cell, textAlign: "left" }} title="Fantasy team that owns them, and the roster slot they fill">Fantasy Team</th>
            </tr>
          </thead>
          <tbody>
            {visible.map(e => (
              <tr key={e.id} style={{ borderTop: "1px solid var(--border-subtle)", fontWeight: mine(e) ? 700 : 400 }}>
                <td style={{ ...cell, textAlign: "left" }}><EntityLink id={e.id} name={e.name} /></td>
                {!showTeams && <td style={{ ...cell, textAlign: "left" }}>{e.position}</td>}
                {!showTeams && <td style={{ ...cell, textAlign: "left" }}>{nbaIds.has(e.nba_team) ? <EntityLink id={e.nba_team} name={e.nba_team} /> : e.nba_team}</td>}
                {columns.map(([h, , get]) => <td key={h} style={cell}>{get(e)}</td>)}
                <td style={{ ...cell, textAlign: "left" }}>{e.team_name ? <><TeamLink ownerId={e.owner_user_id} name={e.team_name} /> ({e.slot})</> : "Free agent"}</td>
              </tr>
            ))}
            {visible.length === 0 && (
              <tr><td colSpan={columns.length + 4} style={{ padding: "12px 8px" }}>Nothing matches this filter.</td></tr>
            )}
          </tbody>
        </table>
      )}
    </FantasyShell>
  );
}
