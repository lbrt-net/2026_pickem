import { useEffect, useState } from "react";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import StatsNav from "./StatsNav";
import { TeamChip } from "./StatsControls";
import { ramp, rampInk } from "./statsRamp";
import "./Rebounding.css";
import "./Standings.css";
import "./Games.css";

// /stats/nba/games (2026-10-21): each day's games, predicted the night before from what was known then — the same
// player ratings x projected minutes as the standings (nba-pipeline/models/standings.py, "next" on each date): expected
// margin = strength gap x pace + home court, win chance from that margin and one game's spread. Earlier days show the
// final scores next to the call. Stats never link into fantasy.
const niceDate = d => new Date(`${d}T12:00:00`).toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
const tipTime = iso => (iso ? new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: "America/Chicago" }) : "TBD");
const pct = v => `${Math.round(100 * v)}%`;
const Win = ({ v }) => <td className="sd-odds" style={{ background: ramp(v), color: rampInk(v) }}>{pct(v)}</td>;

export default function Games() {
  const [data, setData] = useState(null);
  const [k, setK] = useState(null);
  useEffect(() => {
    fetch(`${API}/nba/stats/standings`, { credentials: "include" }).then(r => r.json())
      .then(d => {
        const days = (d.dates || []).map(x => x.next).filter(x => x && x.games?.length);
        setData(days); setK(Math.max(0, days.length - 1));
      })
      .catch(() => setData([]));
  }, []);
  const day = data?.[k];
  // every finished game so far: did the favored team win
  const done = (data || []).flatMap(x => x.games).filter(g => g.final && g.home_score != null);
  const called = done.filter(g => (g.p_home >= 0.5) === (g.home_score > g.away_score)).length;
  return (
    <div className="site-ui stats-ui" style={{ minHeight: "100vh" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1000, boxSizing: "border-box", minWidth: 0 }}>
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
          <div className="sd-tcard">
            <table className="sd-t gm-t">
              <thead><tr>
                <th className="l">Tip (CT)</th><th className="l">Away</th><th>Win</th><th className="l">Home</th><th>Win</th>
                <th className="g">Line</th><th>Final</th>
              </tr></thead>
              <tbody>{day.games.map(g => {
                const fav = g.margin >= 0 ? g.home : g.away;
                const homeWon = g.final && g.home_score > g.away_score;
                return (
                  <tr key={g.game_id}>
                    <td className="l">{tipTime(g.tip)}</td>
                    <td className="l team"><TeamChip team={g.away} /></td><Win v={1 - g.p_home} />
                    <td className="l team"><TeamChip team={g.home} /></td><Win v={g.p_home} />
                    <td className="g">{Math.abs(g.margin) < 0.05 ? "even" : `${fav} −${Math.abs(g.margin).toFixed(1)}`}</td>
                    <td>{g.final ? <><span className={homeWon ? "" : "b"}>{g.away_score}</span>–<span className={homeWon ? "b" : ""}>{g.home_score}</span></> : ""}</td>
                  </tr>);
              })}</tbody>
            </table>
          </div>
        </>}
      </div>
    </div>
  );
}
