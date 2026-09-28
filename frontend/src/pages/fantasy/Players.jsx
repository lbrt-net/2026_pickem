import { useEffect, useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { API } from "../../utils/helpers";

const FILTERS = ["My Team", "Drafted", "Free Agents", "By NBA Team"];
const MY_TEAM = "Baseline Bandits"; // no real user<->team link yet; hardcoded like the rest of the fantasy skeleton

export default function Players() {
  const [filter, setFilter] = useState("Free Agents");
  const [nbaTeamFilter, setNbaTeamFilter] = useState("");
  const [search, setSearch] = useState("");
  const [players, setPlayers] = useState(null); // null = loading

  useEffect(() => {
    fetch(`${API}/fantasy/2026_27/players`)
      .then(r => r.json())
      .then(setPlayers)
      .catch(() => setPlayers([]));
  }, []);

  const nbaTeams = players ? [...new Set(players.map(p => p.nba_team))].sort() : [];

  const visible = (players || []).filter(p => {
    if (search && !p.name.toLowerCase().includes(search.toLowerCase())) return false;
    if (filter === "My Team") return p.team_name === MY_TEAM;
    if (filter === "Drafted") return !!p.team_name;
    if (filter === "Free Agents") return !p.team_name;
    if (filter === "By NBA Team") return !nbaTeamFilter || p.nba_team === nbaTeamFilter;
    return true;
  }).sort((a, b) => b.fantasy_points - a.fantasy_points);

  function actionFor(p) {
    if (p.team_name === MY_TEAM) return "—";
    if (!p.team_name) return "Add";
    return "Trade";
  }

  return (
    <FantasyShell title="Players" season="2026_27">
      <div style={{ fontSize: 10, color: "#999", marginBottom: 6 }}>
        Doubles as stats research + free agency/waivers. Real dummy data from <code>/fantasy/2026_27/players</code> — stats are per-game averages, fantasy points are a placeholder formula pending real league scoring settings.
      </div>
      <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap", alignItems: "center" }}>
        {FILTERS.map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{ fontSize: 12, padding: "4px 10px", fontWeight: filter === f ? 700 : 400, border: filter === f ? "2px solid #111" : "1px solid #ccc" }}>
            {f}
          </button>
        ))}
        {filter === "By NBA Team" && (
          <select value={nbaTeamFilter} onChange={e => setNbaTeamFilter(e.target.value)} style={{ fontSize: 12 }}>
            <option value="">All teams</option>
            {nbaTeams.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        )}
        <input placeholder="search" value={search} onChange={e => setSearch(e.target.value)} style={{ fontSize: 12, marginLeft: "auto", border: "1px solid #ccc", padding: "4px 8px" }} />
      </div>

      {players === null ? (
        <div style={{ fontSize: 12, color: "#999" }}>Loading…</div>
      ) : (
        <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ fontSize: 10, color: "#999", textAlign: "left" }}>
              <th>Name</th><th>Pos</th><th>NBA</th>
              <th style={{ textAlign: "right" }}>GP</th>
              <th style={{ textAlign: "right" }}>MIN</th>
              <th style={{ textAlign: "right" }}>PTS</th>
              <th style={{ textAlign: "right" }}>OREB</th>
              <th style={{ textAlign: "right" }}>DREB</th>
              <th style={{ textAlign: "right" }}>AST</th>
              <th style={{ textAlign: "right" }}>STL</th>
              <th style={{ textAlign: "right" }}>BLK</th>
              <th style={{ textAlign: "right" }}>FPTS</th>
              <th>Team</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {visible.map(p => (
              <tr key={p.id} style={{ borderTop: "1px solid #eee" }}>
                <td style={{ padding: "5px 0" }}>{p.name}</td>
                <td>{p.position}</td>
                <td>{p.nba_team}</td>
                <td style={{ textAlign: "right" }}>{p.games_played}</td>
                <td style={{ textAlign: "right" }}>{p.minutes}</td>
                <td style={{ textAlign: "right" }}>{p.pts}</td>
                <td style={{ textAlign: "right" }}>{p.off_reb}</td>
                <td style={{ textAlign: "right" }}>{p.def_reb}</td>
                <td style={{ textAlign: "right" }}>{p.ast}</td>
                <td style={{ textAlign: "right" }}>{p.stl}</td>
                <td style={{ textAlign: "right" }}>{p.blk}</td>
                <td style={{ textAlign: "right", fontWeight: 600 }}>{p.fantasy_points}</td>
                <td style={{ color: p.team_name ? "#111" : "#999" }}>{p.team_name || "Free agent"}</td>
                <td>{actionFor(p) !== "—" && <span style={{ border: "1px solid #333", padding: "2px 8px", fontSize: 11 }}>{actionFor(p)}</span>}</td>
              </tr>
            ))}
            {visible.length === 0 && (
              <tr><td colSpan={13} style={{ padding: "12px 0", color: "#999" }}>No players match this filter.</td></tr>
            )}
          </tbody>
        </table>
      )}
    </FantasyShell>
  );
}
