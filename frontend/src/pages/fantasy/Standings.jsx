import { useState } from "react";
import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { TeamLink } from "../../components/fantasy/links";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { BASE, REGULAR_SEASON_WEEKS, SEASON, record, standingsThrough, useFantasyApi } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import { isOn } from "../../components/fantasy/features";
import "./Standings.css";

function Chevron() {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
      <path d="M2 3.5 L5 6.5 L8 3.5" stroke="currentColor" strokeWidth="1.6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const RESULT_WORD = { W: "win", L: "loss", T: "tie" };

function LastFive({ results, className = "" }) {
  const last = results.slice(-5);
  return (
    <span className={`st-last5 ${className}`} aria-label={`Last ${last.length}: ${last.map(r => RESULT_WORD[r]).join(", ")}`}>
      {last.map((r, i) => <span key={i} className={`st-pip ${r}`} aria-hidden="true" />)}
    </span>
  );
}

function Diff({ value }) {
  const up = value > 0, down = value < 0;
  return (
    <span className="st-diff">
      {(up || down) && (
        <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
          <path d={up ? "M5 1 L9 8 L1 8 Z" : "M5 9 L9 2 L1 2 Z"} fill={up ? "var(--accent-green)" : "var(--accent-red)"} />
        </svg>
      )}
      {up ? "+" : down ? "−" : ""}{Math.abs(value).toFixed(1)}
    </span>
  );
}

// Playoff seeding/byes live on the Playoffs page, not here.
export default function Standings() {
  const user = useCurrentUser();
  const [week, setWeek] = useState(REGULAR_SEASON_WEEKS);
  const teams = useFantasyApi("teams");
  const rows = teams ? standingsThrough(teams, week) : [];

  return (
    <FantasyShell title="Standings" season={SEASON}>
      <div className="st-controls">
        <label className="st-week">
          <span className="st-week-face" aria-hidden="true">Through week {week}<Chevron /></span>
          <select aria-label="Standings through week" value={week} onChange={e => setWeek(Number(e.target.value))}>
            {Array.from({ length: REGULAR_SEASON_WEEKS }, (_, i) => REGULAR_SEASON_WEEKS - i).map(w => <option key={w} value={w}>Week {w}</option>)}
          </select>
        </label>
        <div className="st-links">
          {isOn("/recap") && <Link to={`${BASE}/recap?week=${week}`}>Week {week} recap &rarr;</Link>}
          <Link to={`${BASE}/matchup?week=${week}`}>Week {week} matchups &rarr;</Link>
        </div>
      </div>

      {teams === undefined ? <p style={{ fontSize: 14 }}>Loading…</p> : (
        <table className="st-table">
          <thead>
            <tr>
              <th className="left" style={{ paddingLeft: 14 }} title="Rank">Rk</th>
              <th className="left">Team</th>
              <th title="Wins-losses(-ties)">W-L</th>
              <th className="st-wide" title="Win percentage (ties count as half)">Pct</th>
              <th className="st-wide" title="Total fantasy points scored">Pts For</th>
              <th className="st-wide" title="Total fantasy points scored by opponents">Pts Agst</th>
              <th title="Points for minus points against">Diff</th>
              <th className="left st-wide" title="Last 5 weeks, oldest to newest">Last 5</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              const you = user && r.team.owner_user_id === user.discordId;
              const games = r.w + r.l + r.t;
              const pct = games ? ((r.w + r.t / 2) / games).toFixed(3).replace(/^0/, "") : "—";
              return (
                <tr key={r.team.id} className={you ? "you" : undefined}>
                  <td className="st-rank">{i + 1}</td>
                  <td className="left">
                    <div className="st-team">
                      <span className="st-icon"><TeamIcon team={r.team} size={28} /></span>
                      <TeamLink ownerId={r.team.owner_user_id} name={r.team.name} />
                      {you && <span className="st-you">YOU</span>}
                      <LastFive results={r.results} className="st-last5-inline" />
                    </div>
                  </td>
                  <td className="st-wl">{record(r)}</td>
                  <td className="st-wide">{pct}</td>
                  <td className="st-wide">{r.pf.toFixed(1)}</td>
                  <td className="st-wide">{r.pa.toFixed(1)}</td>
                  <td><Diff value={Math.round((r.pf - r.pa) * 10) / 10} /></td>
                  <td className="left st-wide"><LastFive results={r.results} /></td>
                </tr>
              );
            })}
            {rows.length === 0 && <tr><td colSpan={8} className="left">No teams yet.</td></tr>}
          </tbody>
        </table>
      )}

      <div className="st-legend">
        <span><span className="st-pip W" aria-hidden="true" />Win</span>
        <span><span className="st-pip" aria-hidden="true" />Loss</span>
        <span>Weekly scores are projected from per-game averages until real box scores are hooked up.</span>
      </div>
    </FantasyShell>
  );
}
