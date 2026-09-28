import { Fragment, useState } from "react";
import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { TeamLink } from "../../components/fantasy/links";
import { BASE, PLAYOFF_TEAMS, REGULAR_SEASON_WEEKS, SEASON, record, standingsThrough, useFantasyApi } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";

const cell = { padding: "6px 8px", textAlign: "right" };
const tab = active => ({ fontSize: 13, padding: "6px 12px", fontWeight: active ? 700 : 400, borderColor: active ? "var(--text)" : "var(--border)" });

export default function Standings() {
  const user = useCurrentUser();
  const [view, setView] = useState("regular");
  const [week, setWeek] = useState(REGULAR_SEASON_WEEKS);
  const teams = useFantasyApi("teams");
  const rows = teams ? standingsThrough(teams, week) : [];

  return (
    <FantasyShell title="Standings" season={SEASON}>
      <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
        <button onClick={() => setView("regular")} style={tab(view === "regular")}>Regular Season</button>
        <button onClick={() => setView("playoffs")} style={tab(view === "playoffs")}>Playoffs Bracket</button>
      </div>

      {view === "regular" ? (
        <>
          <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 12, fontSize: 13 }}>
            <span>Standings through</span>
            <select value={week} onChange={e => setWeek(Number(e.target.value))} style={{ fontSize: 13 }}>
              {Array.from({ length: REGULAR_SEASON_WEEKS }, (_, i) => REGULAR_SEASON_WEEKS - i).map(w => <option key={w} value={w}>Week {w}</option>)}
            </select>
            <Link to={`${BASE}/recap?week=${week}`} style={{ fontSize: 13, fontWeight: 600 }}>Week {week} Recap &rarr;</Link>
            <Link to={`${BASE}/matchup?week=${week}`} style={{ fontSize: 13, fontWeight: 600 }}>Week {week} Matchups &rarr;</Link>
          </div>

          <p style={{ fontSize: 13, marginBottom: 10 }}>
            Weekly scores are projected from per-game averages until real box scores are hooked up.
          </p>

          {teams === undefined ? <p style={{ fontSize: 13 }}>Loading…</p> : (
            <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse", marginBottom: 16 }}>
              <thead>
                <tr style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.04em", borderBottom: "1px solid var(--border)" }}>
                  <th style={{ ...cell, textAlign: "left" }} title="Rank">#</th>
                  <th style={{ ...cell, textAlign: "left" }}>Team</th>
                  <th style={cell} title="Roster spots filled out of 11">Roster</th>
                  <th style={cell} title="Wins–losses(–ties)">Record</th>
                  <th style={cell} title="Total fantasy points scored">Pts For</th>
                  <th style={cell} title="Total fantasy points scored by opponents">Pts Against</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <Fragment key={r.team.id}>
                    <tr style={{ borderTop: "1px solid var(--border-subtle)", fontWeight: user && r.team.owner_user_id === user.discordId ? 700 : 400 }}>
                      <td style={{ ...cell, textAlign: "left" }}>{i + 1}</td>
                      <td style={{ ...cell, textAlign: "left", fontWeight: 600 }}><TeamLink ownerId={r.team.owner_user_id} name={r.team.name} /></td>
                      <td style={cell}>{r.team.roster.length}/11</td>
                      <td style={cell}>{record(r)}</td>
                      <td style={cell}>{r.pf}</td>
                      <td style={cell}>{r.pa}</td>
                    </tr>
                    {i === PLAYOFF_TEAMS - 1 && i < rows.length - 1 && (
                      <tr><td colSpan={6} style={{ borderTop: "2px dashed var(--border)", fontSize: 11, fontWeight: 700, textAlign: "center", padding: 4 }}>PLAYOFF LINE</td></tr>
                    )}
                  </Fragment>
                ))}
                {rows.length === 0 && <tr><td colSpan={6} style={{ padding: "12px 8px" }}>No teams yet.</td></tr>}
              </tbody>
            </table>
          )}
        </>
      ) : (
        <div style={{ border: "1px solid var(--border)", padding: 14, fontSize: 13 }}>
          The top {PLAYOFF_TEAMS} make the playoffs. Full bracket:{" "}
          <Link to={`${BASE}/playoffs`}>Playoffs</Link>.
        </div>
      )}
    </FantasyShell>
  );
}
