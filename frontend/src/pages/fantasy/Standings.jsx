import { Fragment, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { API } from "../../utils/helpers";

// Record/PA are still mock — no weekly-matchup schedule modeled yet. PF now
// comes from real roster data (see realTotals below) to prove the
// stats -> roster -> team-score mechanic actually flows end to end.
const mockRecords = [
  ["Baseline Bandits", "10-2", 1198],
  ["Rim Reapers", "9-3", 1210],
  ["Baseline Bandits Jr", "8-4", 1244],
  ["Screen Time", "8-4", 1251],
  ["Full Court Press", "7-5", 1233],
  ["Buzzer Beaters", "6-6", 1201],
  ["Airball Assassins", "5-7", 1220],
  ["Triple Double Trouble", "4-8", 1266],
  ["Bench Mob", "3-9", 1301],
  ["Zero Dark Thirty", "2-10", 1344],
];

const results = [
  ["Baseline Bandits", "412.5", "388.2", "Dunk or Be Dunked"],
  ["Rim Reapers", "395.1", "401.4", "Screen Time"],
  ["Full Court Press", "378.6", "362.0", "Buzzer Beaters"],
];

export default function Standings() {
  const season = "2026_27";
  const [tab, setTab] = useState("regular");
  const [week, setWeek] = useState("12");
  const [realTotals, setRealTotals] = useState(null); // name -> total_fantasy_points

  useEffect(() => {
    fetch(`${API}/fantasy/2026_27/teams`)
      .then(r => r.json())
      .then(data => setRealTotals(Object.fromEntries(data.map(t => [t.name, t.total_fantasy_points]))))
      .catch(() => setRealTotals({}));
  }, []);

  const teams = mockRecords
    .map(([name, rec, pa]) => [name, rec, realTotals?.[name] ?? "…", pa])
    .sort((a, b) => (typeof b[2] === "number" && typeof a[2] === "number" ? b[2] - a[2] : 0));

  return (
    <FantasyShell title="Standings" season={season}>
      <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
        <button onClick={() => setTab("regular")} style={{ fontSize: 12, padding: "6px 12px", fontWeight: tab === "regular" ? 700 : 400, border: tab === "regular" ? "2px solid #111" : "1px solid #ccc" }}>
          Regular Season
        </button>
        <button onClick={() => setTab("playoffs")} style={{ fontSize: 12, padding: "6px 12px", fontWeight: tab === "playoffs" ? 700 : 400, border: tab === "playoffs" ? "2px solid #111" : "1px solid #ccc" }}>
          Playoffs Bracket
        </button>
      </div>

      {tab === "regular" ? (
        <>
          <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 10 }}>
            <span style={{ fontSize: 11, color: "#999" }}>Standings as of</span>
            <select value={week} onChange={e => setWeek(e.target.value)} style={{ fontSize: 12 }}>
              {Array.from({ length: 12 }, (_, i) => 12 - i).map(w => <option key={w} value={w}>Week {w}</option>)}
            </select>
            <Link to={`/fantasy/${season}/recap?week=${week}`} style={{ fontSize: 11, border: "1px solid #333", padding: "3px 10px", textDecoration: "none" }}>
              Recap &rarr;
            </Link>
          </div>

          <div style={{ fontSize: 10, color: "#999", marginBottom: 6 }}>
            PF is real (sum of each team's rostered dummy players' fantasy points) — Record/PA are still mock, no weekly schedule modeled yet.
          </div>
          <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse", marginBottom: 16 }}>
            <thead>
              <tr style={{ fontSize: 10, color: "#999", textAlign: "left" }}>
                <th>#</th><th>Team</th><th>Record</th><th style={{ textAlign: "right" }}>PF</th><th style={{ textAlign: "right" }}>PA</th>
              </tr>
            </thead>
            <tbody>
              {teams.map(([name, rec, pf, pa], i) => (
                <Fragment key={name}>
                  <tr style={{ fontWeight: i < 6 ? 700 : 400, borderTop: "1px solid #eee" }}>
                    <td style={{ padding: "5px 0" }}>{i + 1}</td>
                    <td>{name}</td>
                    <td>{rec}</td>
                    <td style={{ textAlign: "right" }}>{pf}</td>
                    <td style={{ textAlign: "right" }}>{pa}</td>
                  </tr>
                  {i === 5 && <tr><td colSpan={5} style={{ borderTop: "2px dashed #333", fontSize: 9, color: "#999", textAlign: "center" }}>PLAYOFF LINE</td></tr>}
                </Fragment>
              ))}
            </tbody>
          </table>

          <div style={{ fontSize: 10, color: "#999", marginBottom: 6 }}>THIS WEEK'S RESULTS (score-only — full detail lives on Matchup)</div>
          {results.map(([a, sa, sb, b]) => (
            <div key={a} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, border: "1px solid #eee", padding: "6px 10px", marginBottom: 4 }}>
              <span>{a}</span><span>{sa} – {sb}</span><span>{b}</span>
            </div>
          ))}

          <div style={{ fontSize: 10, color: "#999", marginTop: 16 }}>
            [PLANNED] standings-over-time graph, earnings-over-time graph (blocked on prize pool structure)
          </div>
        </>
      ) : (
        <div style={{ border: "1px solid #999", padding: 14, fontSize: 12 }}>
          Compact bracket preview goes here — same content as the full{" "}
          <Link to={`/fantasy/${season}/playoffs`} style={{ textDecoration: "underline" }}>Playoffs</Link> page.
        </div>
      )}
    </FantasyShell>
  );
}
