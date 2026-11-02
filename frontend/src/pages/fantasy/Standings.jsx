import { useState } from "react";
import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { TeamLink } from "../../components/fantasy/links";
import TeamIcon from "../../components/fantasy/TeamIcon";
import LastFive from "../../components/fantasy/LastFive";
import { base, useFantasyApi } from "../../components/fantasy/data";
import { accent, countedWeeks, finalWeeks, hasTie, recordText, standingsFrom } from "../../components/fantasy/standings";
import "./Standings.css";

// Standings (design: canvas "Standings v2") from real results — only final weeks count. Every team is
// listed from day one (0-0). Rows look like the Home standings card (team-color edge + wash, loud names). Playoff seeding/byes live on the Playoffs page.
export default function Standings() {
  const teams = useFantasyApi("teams");
  const res = useFantasyApi("results");
  const done = [0, ...countedWeeks(res)]; // 0 = Start (before any matchup counts)
  const full = new Set(finalWeeks(res));   // a week not over yet reads "Week N (so far)"
  const [pick, setPick] = useState(null);
  const through = pick ?? done[done.length - 1];
  const rows = standingsFrom(res, teams, through);
  const tie = hasTie(standingsFrom(res, teams));  // W-T-L once anyone in the league has a tie
  const i = done.indexOf(through);
  const cut = res?.settings?.playoff_teams; // last playoff seed gets a line under it
  // sortable (2026-11-01): click a header — biggest first (Rk / GB: best first, Team: A→Z), again to flip. Rk stays
  // the standings rank; the playoff line only shows in standings order.
  const [sort, setSort] = useState({ k: "rk", dir: 1 });
  const ranked = rows.map((r, k) => ({ ...r, rk: k + 1, diff: r.pfw == null ? 0 : Math.round((r.pfw - r.paw) * 10) / 10 }));
  const key = { rk: r => r.rk, team: r => r.team.name.toLowerCase(), pct: r => r.pct, gb: r => r.gb ?? 0, pf: r => r.pfw ?? 0, pa: r => r.paw ?? 0, diff: r => r.diff };
  const low = { rk: 1, team: 1, gb: 1 };  // first click: lowest first for these
  const shown = [...ranked].sort((a, b) => {
    const x = key[sort.k](a), y = key[sort.k](b);
    return sort.dir * (typeof x === "string" ? x.localeCompare(y) : x - y) || a.rk - b.rk;
  });
  const th = (k, label, cls, title) => (
    <th className={`${cls} st-sort${sort.k === k ? " on" : ""}`} title={title} aria-sort={sort.k === k ? (sort.dir < 0 ? "descending" : "ascending") : "none"}>
      <button type="button" onClick={() => setSort(s => ({ k, dir: s.k === k ? -s.dir : low[k] ? 1 : -1 }))}>{label}</button>
    </th>
  );

  return (
    <FantasyShell title="Standings">
      <div className="st-bar">
        <button className="st-btn page-btn" disabled={i <= 0} onClick={() => setPick(done[i - 1])} aria-label="Earlier week">‹</button>
        <span className="st-through">{through ? `Week ${through}${full.has(through) ? "" : " (so far)"}` : "Start"}</span>
        <button className="st-btn page-btn" disabled={i < 0 || i >= done.length - 1} onClick={() => setPick(done[i + 1])} aria-label="Later week">›</button>
        {through > 0 && <Link className="st-link" to={`${base()}/matchup?week=${through}`}>Week {through} matchups →</Link>}
      </div>

      {teams === undefined || res === undefined ? <p style={{ fontSize: 14 }}>Loading…</p> : (
        <section className="st-card">
          <table className="st-table">
            <thead>
              <tr>
                <th className="w-edge" />{th("rk", "Rk", "l w-rk")}{th("team", "Team", "l")}{th("pct", "W-L", "c w-wl", "Wins-losses(-ties)")}
                {th("pct", "Pct", "w-pct", "Win percentage (ties count as half)")}{th("gb", "GB", "w-gb", "Games behind the leader")}
                {th("pf", "PF/wk", "w-pts", "Points scored, average per week")}{th("pa", "PA/wk", "w-pts", "Points scored against, average per week")}
                {th("diff", "Diff/wk", "w-diff", "Points for minus points against, average per week")}<th className="l w-l5" title="Last 5 weeks, oldest to newest">Last 5</th>
              </tr>
            </thead>
            <tbody>
              {shown.map(r => {
                const diff = r.diff;
                return (
                  <tr key={r.team.id} className={sort.k === "rk" && sort.dir > 0 && r.rk === cut && r.rk < rows.length ? "cut" : ""} style={{ "--tc": accent(r.team.color) }}>
                    <td className="edge" />
                    <td className="l rk">{r.rk}</td>
                    <td className="l"><span className="st-team"><TeamIcon team={r.team} size={26} /><TeamLink ownerId={r.team.owner_user_id} name={r.team.name} /></span></td>
                    <td className="c rec">{recordText(r, tie)}</td>
                    <td>{r.pct}</td>
                    <td>{r.gb == null ? "—" : r.gb}</td>
                    <td>{r.pfw == null ? "—" : pts(r.pfw)}</td>
                    <td>{r.paw == null ? "—" : pts(r.paw)}</td>
                    <td className={diff < 0 ? "neg" : ""}>{diff > 0 ? "+" : diff < 0 ? "−" : ""}{pts(Math.abs(diff))}</td>
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

const pts = v => v.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
