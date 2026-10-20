import { useEffect, useMemo, useState } from "react";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import { NBA_TEAMS } from "../../components/fantasy/nbaTeams";
import StatsNav from "./StatsNav";
import { TeamChip } from "./StatsControls";
import "./Rebounding.css";
import "./Standings.css";

// /stats/standings (2026-10-20): the season in progress — one date slider (default yesterday), one tall chart of games
// back per conference (where each team stands on that date → where it's projected to finish), one table. Data: GET
// /nba/stats/standings (nba-pipeline/models/standings.py: player ratings x projected minutes, 10,000 simulations; each
// date's projection uses only what was known that day). Stats never link into fantasy.
const pct = v => (v >= 0.995 ? ">99%" : v > 0 && v < 0.005 ? "<1%" : `${Math.round(100 * v)}%`);
const gbText = v => (v === 0 ? "—" : v.toFixed(1).replace(/\.0$/, ""));
const lum = hex => { const h = (hex || "").replace("#", ""); if (h.length !== 6) return 0; const [r, g, b] = [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16)); return 0.299 * r + 0.587 * g + 0.114 * b; };
const color = t => { const c = NBA_TEAMS[t]; if (!c) return "var(--text)"; return lum(c.primary) >= 45 ? c.primary : lum(c.secondary) >= 45 ? c.secondary : `color-mix(in srgb, ${c.primary} 60%, white)`; };
const niceDate = d => new Date(`${d}T12:00:00`).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });

// labels on one side, nudged apart so none overlap (min gap px), kept in order
function dodge(ys, gap) {
  const order = ys.map((y, i) => [y, i]).sort((a, b) => a[0] - b[0]); const out = Array(ys.length);
  let last = -Infinity;
  for (const [y, i] of order) { const v = Math.max(y, last + gap); out[i] = v; last = v; }
  return out;
}

function ConfChart({ conf, teams, maxGb, H }) {
  const W = 360, top = 34, bot = 18, xL = 70, xR = 250, y = gb => top + (gb / maxGb) * (H - top - bot);
  const rows = [...teams].sort((a, b) => a.proj_gb - b.proj_gb);
  const ly = dodge(rows.map(r => y(r.proj_gb)), 17), lyL = dodge(rows.map(r => y(r.gb)), 17);
  const ticks = []; for (let g = 0; g <= maxGb; g += maxGb > 30 ? 10 : 5) ticks.push(g);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="sd-chart" role="img" aria-label={`${conf} games back, now and projected`}>
      <text x={xL} y={14} className="sd-ax" textAnchor="middle">Now</text>
      <text x={xR} y={14} className="sd-ax" textAnchor="middle">Projected finish</text>
      <text x={W / 2} y={H - 2} className="sd-conf" textAnchor="middle">{conf}</text>
      {ticks.map(g => <g key={g}><line x1={xL - 30} x2={xR} y1={y(g)} y2={y(g)} className="sd-grid" /><text x={xL - 34} y={y(g) + 4} className="sd-ax" textAnchor="end">{g === 0 ? "lead" : g}</text></g>)}
      {rows.map((r, i) => (
        <g key={r.team}>
          <line x1={xL} y1={y(r.gb)} x2={xR} y2={y(r.proj_gb)} stroke={color(r.team)} strokeWidth="2" opacity="0.9" />
          <circle cx={xL} cy={y(r.gb)} r="4" fill={color(r.team)} />
          <circle cx={xR} cy={y(r.proj_gb)} r="4.5" fill="var(--bg)" stroke={color(r.team)} strokeWidth="2" />
          <line x1={xR + 5} y1={y(r.proj_gb)} x2={xR + 14} y2={ly[i]} stroke={color(r.team)} strokeWidth="1" />
          <text x={xR + 17} y={ly[i] + 4} className="sd-lab">{r.team} <tspan className="sd-sub">{Math.round(r.proj_w)}</tspan></text>
          {r.gb > 0 && <text x={xL - 8} y={lyL[i] + 4} className="sd-lab sd-l" textAnchor="end">{r.team}</text>}
        </g>))}
    </svg>
  );
}

export default function Standings() {
  const [data, setData] = useState(null);
  const [i, setI] = useState(null);
  useEffect(() => {
    fetch(`${API}/nba/stats/standings`, { credentials: "include" }).then(r => r.json())
      .then(d => { setData(d); const k = (d.dates || []).findIndex(x => x.date === d.meta?.default_date); setI(k >= 0 ? k : Math.max(0, (d.dates || []).length - 1)); })
      .catch(() => setData({ dates: [] }));
  }, []);
  const day = data?.dates?.[i];
  const maxGb = useMemo(() => {
    if (!data?.dates?.length) return 10;
    const m = Math.max(...data.dates.flatMap(d => d.teams.flatMap(t => [t.gb, t.proj_gb])));
    return Math.max(10, Math.ceil(m / 5) * 5);
  }, [data]);
  const H = Math.max(720, maxGb * 18);
  const table = useMemo(() => day ? ["East", "West"].map(c => [c, day.teams.filter(t => t.conf === c).sort((a, b) => b.proj_w - a.proj_w || a.gb - b.gb)]) : [], [day]);
  return (
    <div className="site-ui stats-ui" style={{ minHeight: "100vh" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1100, boxSizing: "border-box", minWidth: 0 }}>
        <StatsNav />
        <div className="rb-head">
          <h1 className="rb-title">Standings</h1>
          <span className="rb-meta">{data?.meta?.season || ""}{day ? ` · through ${niceDate(day.date)} · ${day.games} games played` : ""}</span>
        </div>
        {data && !data.dates?.length && <p className="rb-empty">Not built yet.</p>}
        {day && <>
          <div className="sd-slider">
            <input type="range" min={0} max={data.dates.length - 1} value={i} onChange={e => setI(+e.target.value)} aria-label="Date" disabled={data.dates.length < 2} />
            <span>{niceDate(day.date)}</span>
          </div>
          <div className="sd-charts">
            {["East", "West"].map(c => <ConfChart key={c} conf={c} teams={day.teams.filter(t => t.conf === c)} maxGb={maxGb} H={H} />)}
          </div>
          <div className="rb-card">
            <table className="rb-table sd-table">
              <thead><tr><th className="l">Team</th><th>W-L</th><th>GB</th><th className="g">Projected</th><th>Top 6</th><th>Play-in</th></tr></thead>
              <tbody>
                {table.map(([c, rows]) => [
                  <tr key={c} className="sd-conf-row"><td className="l" colSpan={6}>{c}</td></tr>,
                  ...rows.map(r => (
                    <tr key={r.team} style={{ cursor: "default" }}>
                      <td className="team l"><TeamChip team={r.team} /></td>
                      <td>{r.w}-{r.l}</td><td>{gbText(r.gb)}</td>
                      <td className="g big">{Math.round(r.proj_w)}-{Math.round(r.proj_l)}</td>
                      <td>{pct(r.top6)}</td><td>{pct(r.playin)}</td>
                    </tr>))])}
              </tbody>
            </table>
          </div>
        </>}
      </div>
    </div>
  );
}
