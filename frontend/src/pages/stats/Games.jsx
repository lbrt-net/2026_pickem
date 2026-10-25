import { useEffect, useState } from "react";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import StatsNav from "./StatsNav";
import { TeamChip } from "./StatsControls";
import { winRamp, winInk } from "./statsRamp";
import "./Rebounding.css";
import "./Standings.css";
import "./Games.css";

// /stats/nba/games (2026-10-21): each day's games, predicted the night before from what was known then — the same
// player ratings x projected minutes as the standings (nba-pipeline/models/standings.py, "next" on each date): expected
// margin = strength gap x pace + home court, win chance from that margin and one game's spread. Predicted points = the
// league's average team score ± half the margin (italic: a projection). Finished games add the final and the shot-based
// score (models/analytic_score.py: what each team's shots and free throws were worth). Stats never link into fantasy.
const niceDate = d => new Date(`${d}T12:00:00`).toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
const tipTime = iso => (iso ? new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: "America/Chicago" }) : "TBD");
const pct = v => `${Math.round(100 * v)}%`;
const one = v => (v == null ? "" : v.toFixed(1));
const Win = ({ v }) => <td className="gm-win" style={{ background: winRamp(v), color: winInk(v) }}>{pct(v)}</td>;

export default function Games() {
  const [data, setData] = useState(null);
  const [k, setK] = useState(null);
  useEffect(() => {
    fetch(`${API}/nba/stats/standings`, { credentials: "include" }).then(r => r.json())
      .then(d => {
        const days = (d.dates || []).map(x => x.next).filter(x => x && x.games?.length);
        // open on today's games (Central), else the latest day predicted
        const today = new Date().toLocaleDateString("en-CA", { timeZone: "America/Chicago" });
        const ti = days.findIndex(x => x.date === today);
        setData(days); setK(ti >= 0 ? ti : Math.max(0, days.length - 1));
      })
      .catch(() => setData([]));
  }, []);
  const day = data?.[k];
  // every finished game so far: did the favored team win
  const done = (data || []).flatMap(x => x.games).filter(g => g.final && g.home_score != null);
  const called = done.filter(g => (g.p_home >= 0.5) === (g.home_score > g.away_score)).length;
  const anyFinal = day?.games.some(g => g.final);
  return (
    <div className="site-ui stats-ui" style={{ minHeight: "100vh" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1100, boxSizing: "border-box", minWidth: 0 }}>
        <StatsNav />
        <div className="rb-head">
          <h1 className="rb-title">Games</h1>
          <span className="rb-meta">{done.length ? `favorites ${called}-${done.length - called} so far` : "predicted the night before"}</span>
        </div>
        {data && !data.length && <p className="rb-empty">No games predicted yet.</p>}
        {day && <>
          <div className="gm-day">
            <button onClick={() => setK(k - 1)} disabled={k === 0} aria-label="Previous day">‹</button>
            <span>{niceDate(day.date)}</span>
            <button onClick={() => setK(k + 1)} disabled={k === data.length - 1} aria-label="Next day">›</button>
          </div>
          <div className="sd-tcard gm-card">
            <table className="sd-t gm-t">
              <colgroup>
                <col className="c-tip" /><col className="c-team" /><col className="c-win" /><col className="c-pts" />
                <col className="c-team" /><col className="c-win" /><col className="c-pts" /><col className="c-line" />
                {anyFinal && <><col className="c-score" /><col className="c-shots" /></>}
              </colgroup>
              <thead><tr>
                <th className="l">Tip (CT)</th>
                <th className="l">Away</th><th>Win</th><th>Pts</th>
                <th className="l g">Home</th><th>Win</th><th>Pts</th>
                <th className="g">Line</th>
                {anyFinal && <><th className="g">Final</th><th>By shots</th></>}
              </tr></thead>
              <tbody>{day.games.map(g => {
                const fav = g.margin >= 0 ? g.home : g.away;
                const homeWon = g.final && g.home_score > g.away_score;
                const xHome = g.home_xp != null && g.away_xp != null && g.home_xp > g.away_xp;
                return (
                  <tr key={g.game_id}>
                    <td className="l">{tipTime(g.tip)}</td>
                    <td className="l team"><TeamChip team={g.away} /></td><Win v={1 - g.p_home} /><td className="gm-proj">{one(g.away_pred)}</td>
                    <td className="l team g"><TeamChip team={g.home} /></td><Win v={g.p_home} /><td className="gm-proj">{one(g.home_pred)}</td>
                    <td className="g">{Math.abs(g.margin) < 0.05 ? "even" : `${fav} −${Math.abs(g.margin).toFixed(1)}`}</td>
                    {anyFinal && <>
                      <td className="g">{g.final ? <><span className={homeWon ? "" : "b"}>{g.away_score}</span>–<span className={homeWon ? "b" : ""}>{g.home_score}</span></> : ""}</td>
                      <td>{g.final && g.home_xp != null ? <><span className={xHome ? "" : "b"}>{one(g.away_xp)}</span>–<span className={xHome ? "b" : ""}>{one(g.home_xp)}</span></> : ""}</td>
                    </>}
                  </tr>);
              })}</tbody>
            </table>
          </div>
        </>}
      </div>
    </div>
  );
}
