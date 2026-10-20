import { useEffect, useMemo, useState } from "react";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import { NBA_TEAMS } from "../../components/fantasy/nbaTeams";
import StatsNav from "./StatsNav";
import { TeamChip } from "./StatsControls";
import { teamEdge } from "./teamEdge";
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
  const W = 520, top = 30, bot = 22, xD = 90, y = gb => top + (gb / maxGb) * (H - top - bot);
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

// odds cell: shaded by the probability (accent over the panel), the number always in the one text color
const Odds = ({ v }) => <td className="sd-odds" style={{ background: v < 0.005 ? undefined : `color-mix(in srgb, var(--accent) ${Math.round(8 + 62 * v)}%, transparent)` }}>{pct(v)}</td>;

function StandTable({ title, rows, league }) {
  const sorted = [...rows].sort((a, b) => (b.w - b.l) - (a.w - a.l) || b.proj_w - a.proj_w);
  return (
    <div className="sd-tcard">
      {title && <div className="sd-ttitle">{title}</div>}
      <table className="sd-t">
        <thead><tr>
          <th className="n">#</th><th className="l">Team</th><th>W-L</th><th>GB</th><th title="Model net rating per 100 possessions">Net</th>
          <th className="g">Proj</th>{league && <th title="Best record in the league">Best</th>}
          <th title="1 seed in the conference">1st</th><th>Top 4</th><th>Top 6</th><th>Play-in</th><th>Miss</th>
        </tr></thead>
        <tbody>{sorted.map((r, k) => (
          <tr key={r.team} style={teamEdge(r.team)}>
            <td className="n">{k + 1}</td>
            <td className="l team"><TeamChip team={r.team} />{league && <span className="sd-conf-tag">{r.conf[0]}</span>}</td>
            <td>{r.w}-{r.l}</td><td>{gbText(league ? r.lgb : r.gb)}</td>
            <td>{r.net > 0 ? "+" : r.net < 0 ? "−" : ""}{Math.abs(r.net).toFixed(1)}</td>
            <td className="g b">{Math.round(r.proj_w)}-{Math.round(r.proj_l)}</td>
            {league && <Odds v={r.best} />}
            <Odds v={r.seed1} /><Odds v={r.top4} /><Odds v={r.top6} /><Odds v={r.playin} /><Odds v={r.miss} />
          </tr>))}</tbody>
      </table>
    </div>
  );
}

export default function Standings() {
  const [data, setData] = useState(null);
  const [i, setI] = useState(null);
  const [scope, setScope] = useState("conf");
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
  return (
    <div className="site-ui stats-ui" style={{ minHeight: "100vh" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1240, boxSizing: "border-box", minWidth: 0 }}>
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
          <div className="sd-scope rb-seg" role="radiogroup" aria-label="Standings view">
            {[["conf", "Conference"], ["league", "League"]].map(([v, l]) => <button key={v} type="button" role="radio" aria-checked={scope === v} onClick={() => setScope(v)}>{l}</button>)}
          </div>
          {scope === "conf"
            ? <div className="sd-tables">{["East", "West"].map(c => <StandTable key={c} title={c} rows={day.teams.filter(t => t.conf === c)} />)}</div>
            : <StandTable rows={day.teams} league />}
          <div className="sd-charts">
            {["East", "West"].map(c => <ConfChart key={c} conf={c} teams={day.teams.filter(t => t.conf === c)} maxGb={maxGb} H={H} />)}
          </div>
        </>}
      </div>
    </div>
  );
}
