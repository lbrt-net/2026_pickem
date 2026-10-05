import { useState } from "react";
import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { TeamLink } from "../../components/fantasy/links";
import TeamIcon from "../../components/fantasy/TeamIcon";
import LastFive from "../../components/fantasy/LastFive";
import { base, useFantasyApi } from "../../components/fantasy/data";
import { finalWeeks, recordText, standingsFrom } from "../../components/fantasy/standings";
import "./Standings.css";

// Standings (design: canvas "Standings v2") from real results — only final weeks count. Every team is
// listed from day one (0-0). Best Pts For lit. Playoff seeding/byes live on the Playoffs page.
export default function Standings() {
  const teams = useFantasyApi("teams");
  const res = useFantasyApi("results");
  const done = [0, ...finalWeeks(res)]; // 0 = Initial (before any week is final)
  const [pick, setPick] = useState(null);
  const through = pick ?? done[done.length - 1];
  const rows = standingsFrom(res, teams, through);
  const bestPf = Math.max(...rows.map(r => r.pf));
  const i = done.indexOf(through);

  return (
    <FantasyShell title="Standings">
      <div className="st-bar">
        <button className="st-btn" disabled={i <= 0} onClick={() => setPick(done[i - 1])} aria-label="Earlier week">‹</button>
        <span className="st-through">{through ? `Week ${through}` : "Initial"}</span>
        <button className="st-btn" disabled={i < 0 || i >= done.length - 1} onClick={() => setPick(done[i + 1])} aria-label="Later week">›</button>
        {through && <Link className="st-link" to={`${base()}/matchup?week=${through}`}>Week {through} matchups →</Link>}
      </div>

      {teams === undefined || res === undefined ? <p style={{ fontSize: 14 }}>Loading…</p> : (
        <section className="st-card">
          <table className="st-table">
            <thead>
              <tr>
                <th className="l w-rk">Rk</th><th className="l">Team</th><th className="w-wl" title="Wins-losses(-ties)">W-L</th>
                <th className="w-pct" title="Win percentage (ties count as half)">Pct</th><th className="w-gb" title="Games behind the leader">GB</th>
                <th className="w-pts" title="Total fantasy points scored">Pts For</th><th className="w-pts" title="Total fantasy points scored by opponents">Pts Against</th>
                <th className="w-diff" title="Points for minus points against">Diff</th><th className="l w-l5" title="Last 5 weeks, oldest to newest">Last 5</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, k) => {
                const diff = Math.round((r.pf - r.pa) * 10) / 10;
                return (
                  <tr key={r.team.id}>
                    <td className="l">{k + 1}</td>
                    <td className="l"><span className="st-team"><TeamIcon team={r.team} size={24} /><TeamLink ownerId={r.team.owner_user_id} name={r.team.name} /></span></td>
                    <td>{recordText(r)}</td>
                    <td>{r.pct}</td>
                    <td>{r.gb == null ? "—" : r.gb}</td>
                    <td className={r.pf > 0 && r.pf === bestPf ? "lit" : ""}>{r.pf.toFixed(1)}</td>
                    <td>{r.pa.toFixed(1)}</td>
                    <td className={diff < 0 ? "neg" : ""}>{diff > 0 ? "+" : diff < 0 ? "−" : ""}{Math.abs(diff).toFixed(1)}</td>
                    <td className="l"><LastFive results={r.results} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}
    </FantasyShell>
  );
}
