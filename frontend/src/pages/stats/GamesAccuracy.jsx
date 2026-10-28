import { useEffect, useState } from "react";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import StatsNav, { GamesTabs } from "./StatsNav";
import "./Rebounding.css";
import "./Games.css";

// /stats/nba/games/accuracy (2026-10-28): predicted vs actual. Every finished game's win chances, as the Games page
// shows them (predicted the night before), grouped by that chance: how often teams given
// that chance won. Both teams of a game count, so a 70% favorite is also a 30% underdog and the bands mirror.
// symmetric bins on the exact (unrounded) chance (commissioner, 2026-10-28): below 50 a bin is lo ≤ p < hi, above 50 it
// is lo < p ≤ hi, a bin across 50 takes both ends — so 40–50 and 50–60 mirror each other and both teams of a game land
// in mirrored bins
const steps = w => Array.from({ length: 100 / w }, (_, i) => [w * i, w * (i + 1)]);
const GROUPINGS = [["20", "Bands", [[0, 20], [20, 40], [40, 60], [60, 80], [80, 100]]], ["10", "10%", steps(10)], ["5", "5%", steps(5)], ["1", "1%", steps(1)]];
const inBin = (p, [lo, hi]) => (hi <= 50 ? p >= lo && p < hi : lo >= 50 ? p > lo && p <= hi : p >= lo && p <= hi);
const range = ([lo, hi]) => `${lo}–${hi}%`;

// predicted vs actual (2026-10-28): one dot per bin at (average predicted chance, how often those teams won); the
// diagonal is a perfect call — dots above it won more than predicted. Hover a dot for its bin and record.
const CW = 420, CH = 420, M = { l: 48, r: 16, t: 12, b: 40 };
function Calibration({ rows }) {
  const x = v => M.l + (v / 100) * (CW - M.l - M.r), y = v => CH - M.b - (v / 100) * (CH - M.t - M.b);
  const ticks = [0, 25, 50, 75, 100];
  return (
    <svg width={CW} height={CH} className="ga-chart" role="img" aria-label="Predicted win chance against actual win rate">
      {ticks.map(t => <g key={t}>
        <line x1={x(0)} x2={x(100)} y1={y(t)} y2={y(t)} className="grid" />
        <line x1={x(t)} x2={x(t)} y1={y(0)} y2={y(100)} className="grid" />
        <text x={x(0) - 8} y={y(t) + 4} textAnchor="end">{t}%</text>
        <text x={x(t)} y={y(0) + 18} textAnchor="middle">{t}%</text>
      </g>)}
      <line x1={x(0)} y1={y(0)} x2={x(100)} y2={y(100)} className="diag" />
      <text x={x(50)} y={CH - 4} textAnchor="middle" className="ax">Predicted</text>
      <text transform={`translate(12 ${y(50)}) rotate(-90)`} textAnchor="middle" className="ax">Won</text>
      {rows.map(r => {
        const cx = x(r.avg), cy = y(100 * r.won / r.n);
        return <g key={r.b[0]}>
          <circle cx={cx} cy={cy} r={6} className="dot" />
          <circle cx={cx} cy={cy} r={14} className="hit"><title>{`${range(r.b)}: won ${r.won} of ${r.n} (${Math.round(100 * r.won / r.n)}%), predicted ${r.avg.toFixed(1)}% on average`}</title></circle>
        </g>;
      })}
    </svg>
  );
}

export default function GamesAccuracy() {
  const [sides, setSides] = useState(null);
  const [by, setBy] = useState("20");
  useEffect(() => {
    fetch(`${API}/nba/stats/standings`, { credentials: "include" }).then(r => r.json())
      .then(d => {
        const games = (d.dates || []).flatMap(x => x.next?.games || []).filter(g => g.final && g.home_score != null);
        setSides(games.flatMap(g => {
          const p = 100 * g.p_home, home = g.home_score > g.away_score;
          return [{ p, won: home }, { p: 100 - p, won: !home }];
        }));
      })
      .catch(() => setSides([]));
  }, []);
  const bins = GROUPINGS.find(x => x[0] === by)[2];
  const rows = (sides || []).length ? bins.map(b => {
    const s = sides.filter(x => inBin(x.p, b));
    return { b, n: s.length, won: s.filter(x => x.won).length, avg: s.reduce((a, x) => a + x.p, 0) / (s.length || 1) };
  }).filter(r => r.n) : [];
  return (
    <div className="site-ui stats-ui" style={{ minHeight: "100vh" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1100, boxSizing: "border-box", minWidth: 0 }}>
        <StatsNav />
        <div className="rb-head">
          <h1 className="rb-title">Games</h1>
          {sides?.length > 0 && <span className="rb-meta">{sides.length / 2} games, both teams counted</span>}
        </div>
        <GamesTabs />
        {sides && !sides.length && <p className="rb-empty">No finished games yet.</p>}
        {rows.length > 0 && <>
          <div className="stats-league ga-by" role="radiogroup" aria-label="Group by">
            {GROUPINGS.map(([v, l]) => <button key={v} role="radio" aria-checked={by === v} onClick={() => setBy(v)}>{l}</button>)}
          </div>
          <div className="ga-row">
          <div className="gm-card ga-card"><Calibration rows={rows} /></div>
          <div className="gm-card">
            <table className="ga-t">
              <thead><tr><th className="l">Predicted</th><th>Teams</th><th>Won</th><th>Win rate</th><th>Avg predicted</th></tr></thead>
              <tbody>{rows.map(r => (
                <tr key={r.b[0]}>
                  <td className="l">{range(r.b)}</td>
                  <td>{r.n}</td>
                  <td>{r.won}</td>
                  <td className="b">{Math.round(100 * r.won / r.n)}%</td>
                  <td>{r.avg.toFixed(1)}%</td>
                </tr>))}
              </tbody>
            </table>
          </div>
          </div>
        </>}
      </div>
    </div>
  );
}
