import { useEffect, useMemo, useState } from "react";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import { NBA_TEAMS } from "../../components/fantasy/nbaTeams";
import StatsNav from "./StatsNav";
import { TeamChip } from "./StatsControls";
import { logoUrl } from "../../components/fantasy/media";
import { teamEdge } from "./teamEdge";
import { ramp, rampInk } from "./statsRamp";
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

// games back over the season (2026-10-22: was one day's dots): one line per team from opening night to the latest
// date, a marker at the slider's date, labels at the right end in standings order. Live results only, no projection
function ConfChart({ conf, dates, i, maxGb, H }) {
  const W = 560, top = 30, bot = 26, x0 = 34, x1 = W - 170, lab = x1 + 26, LG = 16;
  const n = dates.length, x = k => (n < 2 ? x1 : x0 + (k / (n - 1)) * (x1 - x0));
  const y = gb => top + (gb / maxGb) * (H - top - bot);
  const teams = dates[n - 1].teams.filter(t => t.conf === conf).sort((a, b) => a.rank - b.rank);
  // tied teams spread a little (2026-10-25, commissioner: "jitter the lines a bit when teams have the same record"):
  // at each date, teams on the same games-back are fanned out JIT px apart, in standings order, so every line shows
  const JIT = 3, SPREAD = 8;          // at most ±8 px, so a 15-way tie on opening night stays near its line
  const gbAt = dates.map(d => Object.fromEntries(d.teams.filter(t => t.conf === conf).map(t => [t.team, t.gb ?? 0])));
  const off = dates.map((d, k) => {
    const g = {}; teams.forEach(t => { const v = gbAt[k][t.team] ?? 0; (g[v] = g[v] || []).push(t.team); });
    const o = {}; Object.values(g).forEach(arr => arr.forEach((t, j) => { o[t] = (j - (arr.length - 1) / 2) * Math.min(JIT, (2 * SPREAD) / Math.max(arr.length - 1, 1)); })); return o;
  });
  const series = teams.map(t => ({ team: t.team, pts: dates.map((d, k) => [x(k), y(gbAt[k][t.team] ?? 0) + off[k][t.team]]) }));
  // the label column follows the date selector: each team's logo, name and record where it stood that day
  const at = dates[i].teams.filter(t => t.conf === conf);
  const rec = Object.fromEntries(at.map(t => [t.team, t]));
  const ly = dodge(series.map(s => s.pts[i][1]), 19);
  const ticks = []; for (let g = 0; g <= maxGb; g += maxGb > 30 ? 10 : maxGb > 12 ? 5 : 2) ticks.push(g);
  const xt = dates.map((d, k) => [k, d.date]).filter(([k]) => n <= 8 || k % Math.ceil(n / 6) === 0 || k === n - 1);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="sd-chart" role="img" aria-label={`${conf} games back over the season`}>
      <text x={W / 2} y={16} className="sd-conf" textAnchor="middle">{conf}</text>
      {ticks.map(g => <g key={g}><line x1={x0} x2={x1} y1={y(g)} y2={y(g)} className="sd-grid" /><text x={x0 - 6} y={y(g) + 4} className="sd-ax" textAnchor="end">{g === 0 ? "lead" : g}</text></g>)}
      {xt.map(([k, d]) => <text key={d} x={x(k)} y={H - 8} className="sd-ax" textAnchor="middle">{new Date(`${d}T12:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</text>)}
      <line x1={x(i)} x2={x(i)} y1={top - 6} y2={H - bot} className="sd-now" />
      {series.map((s, k) => (
        <g key={s.team}>
          <polyline points={s.pts.map(p => p.join(",")).join(" ")} fill="none" stroke={color(s.team)} strokeWidth="2" strokeLinejoin="round" />
          <circle cx={s.pts[i][0]} cy={s.pts[i][1]} r="3.5" fill={color(s.team)} />
          <line x1={s.pts[i][0] + 3} y1={s.pts[i][1]} x2={lab - LG / 2 - 4} y2={ly[k]} stroke={color(s.team)} strokeWidth="1" />
          <image href={logoUrl(s.team)} x={lab - LG / 2} y={ly[k] - LG / 2} width={LG} height={LG} />
          <text x={lab + LG / 2 + 4} y={ly[k] + 4} className="sd-lab">{s.team} <tspan className="sd-sub">{rec[s.team] ? `${rec[s.team].w}-${rec[s.team].l}` : ""}</tspan></text>
        </g>))}
    </svg>
  );
}

// odds cell: shaded on the stats ramp (same as Lineups); dark text on the bright end so it stays readable
const Odds = ({ v }) => <td className="sd-odds" style={v < 0.005 ? undefined : { background: ramp(v), color: rampInk(v) }}>{pct(v)}</td>;

// sortable columns (2026-10-21): click a header to sort by it, click again to flip; "#" puts the standings order back
const COLS = [
  { key: "team", label: "Team", cls: "l", val: r => r.team, asc: true },
  { key: "wl", label: "W-L", val: r => r.w - r.l },
  { key: "gb", label: "GB", val: (r, lg) => (lg ? r.lgb : r.gb), asc: true },
  { key: "net", label: "Net", title: "Net rating: points scored minus allowed per 100 possessions", val: r => r.net },
  { key: "proj", label: "Proj", cls: "g", val: r => r.proj_w },
  { key: "best", label: "Best", title: "Best record in the league", val: r => r.best, league: true },
  { key: "seed1", label: "1st", title: "1 seed in the conference", val: r => r.seed1 },
  { key: "top4", label: "Top 4", val: r => r.top4 }, { key: "top6", label: "Top 6", val: r => r.top6 },
  { key: "playin", label: "Play-in", val: r => r.playin }, { key: "miss", label: "Miss", val: r => r.miss },
];
// the standings order is the NBA's (win %, then the league's tiebreakers — models/standings.py nba_order); # never moves with the sort
const standOrder = lg => (a, b) => (lg ? a.lrank - b.lrank : a.rank - b.rank);

function StandTable({ title, rows, league, sort, onSort }) {
  const col = COLS.find(c => c.key === sort.key), so = standOrder(league);
  const sorted = [...rows].sort((a, b) => {
    if (!col) return so(a, b);
    const x = col.val(a, league), y = col.val(b, league);
    if (x == null && y == null) return so(a, b);
    if (x == null) return 1; if (y == null) return -1;              // blanks (no games yet) always last
    const d = typeof x === "string" ? x.localeCompare(y) : x - y;
    return d * sort.dir || so(a, b);
  });
  const cols = COLS.filter(c => !c.league || league);
  return (
    <div className="sd-tcard">
      {title && <div className="sd-ttitle">{title}</div>}
      <table className="sd-t">
        <thead><tr>
          <th className={`n${!col ? " on" : ""}`} onClick={() => onSort(null)} title="Standings order">#</th>
          {cols.map(c => (
            <th key={c.key} className={`${c.cls || ""}${sort.key === c.key ? " on" : ""}`} title={c.title} onClick={() => onSort(c)}
              aria-sort={sort.key === c.key ? (sort.dir > 0 ? "ascending" : "descending") : undefined}>{c.label}</th>))}
        </tr></thead>
        <tbody>{sorted.map(r => (
          <tr key={r.team} style={teamEdge(r.team)}>
            <td className="n">{league ? r.lrank : r.rank}</td>
            <td className="l team"><TeamChip team={r.team} />{league && <span className="sd-conf-tag">{r.conf[0]}</span>}</td>
            <td>{r.w}-{r.l}</td><td>{gbText(league ? r.lgb : r.gb)}</td>
            <td>{r.net == null ? "" : `${r.net > 0 ? "+" : r.net < 0 ? "−" : ""}${Math.abs(r.net).toFixed(1)}`}</td>
            <td className="g b">{Math.round(r.proj_w)}-{82 - Math.round(r.proj_w)}</td>
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
  const [sort, setSort] = useState({ key: null, dir: -1 });
  const onSort = c => setSort(s => (!c ? { key: null, dir: -1 } : s.key === c.key ? { key: c.key, dir: -s.dir } : { key: c.key, dir: c.asc ? 1 : -1 }));
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
  const H = 15 * 24 + 80 + maxGb * 10;  // tall enough for 15 logo labels (taller, 2026-10-25); grows as the gaps open up
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
            ? <div className="sd-tables">{["East", "West"].map(c => <StandTable key={c} title={c} rows={day.teams.filter(t => t.conf === c)} sort={sort} onSort={onSort} />)}</div>
            : <StandTable rows={day.teams} league sort={sort} onSort={onSort} />}
          <div className="sd-charts">
            {["East", "West"].map(c => <ConfChart key={c} conf={c} dates={data.dates} i={i} maxGb={maxGb} H={H} />)}
          </div>
        </>}
      </div>
    </div>
  );
}
