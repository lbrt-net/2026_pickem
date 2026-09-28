import { Fragment, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";

const PLAYOFF_SPOTS = 4; // of 6 teams — placeholder until league rules are set

const cell = { padding: "6px 8px", textAlign: "right" };
const tab = active => ({ fontSize: 13, padding: "6px 12px", fontWeight: active ? 700 : 400, borderColor: active ? "var(--text)" : "var(--border)" });

export default function Standings() {
  const season = "2026_27";
  const [scenario] = useFantasyScenario();
  const [view, setView] = useState("regular");
  const [week, setWeek] = useState("12");
  const [teams, setTeams] = useState(null);

  useEffect(() => {
    fetch(`${API}/fantasy/2026_27/teams?scenario=${scenario}`, { credentials: "include" })
      .then(r => r.json()).then(setTeams).catch(() => setTeams([]));
  }, [scenario]);

  return (
    <FantasyShell title="Standings" season={season}>
      <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
        <button onClick={() => setView("regular")} style={tab(view === "regular")}>Regular Season</button>
        <button onClick={() => setView("playoffs")} style={tab(view === "playoffs")}>Playoffs Bracket</button>
      </div>

      {view === "regular" ? (
        <>
          <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 12, fontSize: 13 }}>
            <span>Standings as of</span>
            <select value={week} onChange={e => setWeek(e.target.value)} style={{ fontSize: 13 }}>
              {Array.from({ length: 12 }, (_, i) => 12 - i).map(w => <option key={w} value={w}>Week {w}</option>)}
            </select>
            <Link to={`/fantasy/${season}/recap?week=${week}`} style={{ fontSize: 13, fontWeight: 600 }}>Recap &rarr;</Link>
          </div>

          <p style={{ fontSize: 13, marginBottom: 10 }}>
            One team per visible pickem user. Pts For is each roster's total fantasy points per game.
            Record and Pts Against need a weekly matchup schedule, which doesn't exist yet.
          </p>

          {teams === null ? <p style={{ fontSize: 13 }}>Loading…</p> : (
            <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse", marginBottom: 16 }}>
              <thead>
                <tr style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.04em", borderBottom: "1px solid var(--border)" }}>
                  <th style={{ ...cell, textAlign: "left" }} title="Rank">#</th>
                  <th style={{ ...cell, textAlign: "left" }}>Team</th>
                  <th style={cell} title="Roster spots filled out of 11">Roster</th>
                  <th style={cell} title="Wins–losses (needs a schedule)">Record</th>
                  <th style={cell} title="Total fantasy points per game across the roster">Pts For</th>
                  <th style={cell} title="Opponents' fantasy points (needs a schedule)">Pts Against</th>
                </tr>
              </thead>
              <tbody>
                {teams.map((t, i) => (
                  <Fragment key={t.id}>
                    <tr style={{ borderTop: "1px solid var(--border-subtle)" }}>
                      <td style={{ ...cell, textAlign: "left" }}>{i + 1}</td>
                      <td style={{ ...cell, textAlign: "left", fontWeight: 600 }}>{t.name}</td>
                      <td style={cell}>{t.roster.length}/11</td>
                      <td style={cell}>—</td>
                      <td style={cell}>{t.total_fantasy_points}</td>
                      <td style={cell}>—</td>
                    </tr>
                    {i === PLAYOFF_SPOTS - 1 && i < teams.length - 1 && (
                      <tr><td colSpan={6} style={{ borderTop: "2px dashed var(--border)", fontSize: 11, fontWeight: 700, textAlign: "center", padding: 4 }}>PLAYOFF LINE</td></tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          )}

          <p style={{ fontSize: 13 }}>This week's results will show here once there's a matchup schedule.</p>
        </>
      ) : (
        <div style={{ border: "1px solid var(--border)", padding: 14, fontSize: 13 }}>
          Compact bracket preview goes here — same content as the full{" "}
          <Link to={`/fantasy/${season}/playoffs`}>Playoffs</Link> page.
        </div>
      )}
    </FantasyShell>
  );
}
