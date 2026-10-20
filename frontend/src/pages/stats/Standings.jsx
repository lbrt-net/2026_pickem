import { useEffect, useMemo, useState } from "react";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import { NBA_TEAMS } from "../../components/fantasy/nbaTeams";
import StatsNav from "./StatsNav";
import { TeamChip } from "./StatsControls";
import "./Rebounding.css";
import "./Standings.css";

// /stats/standings (2026-10-20): the season in progress — one date slider (default yesterday), one table (W-L, games
// back, projected record and odds), then one tall chart of live games back per conference (no projection in it). Data: GET
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

// live games back only (projections live in the table): each team at its games back on the slider's date
function ConfChart({ conf, teams, maxGb, H }) {
  const W = 300, top = 30, bot = 22, xD = 70, y = gb => top + (gb / maxGb) * (H - top - bot);
  const rows = [...teams].sort((a, b) => a.gb - b.gb || (b.w - b.l) - (a.w - a.l) || a.team.localeCompare(b.team));
  const ly = dodge(rows.map(r => y(r.gb)), 17);
  const ticks = []; for (let g = 0; g <= maxGb; g += maxGb > 30 ? 10 : maxGb > 12 ? 5 : 2) ticks.push(g);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="sd-chart" role="img" aria-label={`${conf} games back`}>
      <text x={W / 2} y={16} className="sd-conf" textAnchor="middle">{conf}</text>
      {ticks.map(g => <g key={g}><line x1={xD - 8} x2={W - 12} y1={y(g)} y2={y(g)} className="sd-grid" /><text x={xD - 14} y={y(g) + 4} className="sd-ax" textAnchor="end">{g === 0 ? "lead" : g}</text></g>)}
      {rows.map((r, i) => (
        <g key={r.team}>
          <circle cx={xD} cy={y(r.gb)} r="5" fill={color(r.team)} />
          <line x1={xD + 6} y1={y(r.gb)} x2={xD + 22} y2={ly[i]} stroke={color(r.team)} strokeWidth="1" />
          <text x={xD + 26} y={ly[i] + 4} className="sd-lab">{r.team} <tspan className="sd-sub">{r.w}-{r.l}{r.gb > 0 ? ` · ${gbText(r.gb)} GB` : ""}</tspan></text>
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
    const m = Math.max(...data.dates.flatMap(d => d.teams.map(t => t.gb)));
    return Math.max(4, Math.ceil(m / 2) * 2);
  }, [data]);
  const H = 15 * 19 + 60 + maxGb * 6;   // tall enough for 15 labels; grows as the gaps open up
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
          <div className="sd-charts">
            {["East", "West"].map(c => <ConfChart key={c} conf={c} teams={day.teams.filter(t => t.conf === c)} maxGb={maxGb} H={H} />)}
          </div>
        </>}
      </div>
    </div>
  );
}
