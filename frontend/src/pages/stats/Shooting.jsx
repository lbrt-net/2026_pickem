import { useEffect, useMemo, useState } from "react";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import { useLeague, leagueQ, seasonLabel } from "./statsLeague";
import StatsNav, { ShootingTabs } from "./StatsNav";
import { TableFilter, Pager, TeamChip } from "./StatsControls";
import { teamEdge } from "./teamEdge";
import { makeShade } from "./shade";
import { matches } from "./statsMatch";
import "./Shooting.css";

// Shooting: the 300 biggest shot-takers this season, scored against what the league makes from the same shots
// (nba-pipeline shot value v9: nine distance zones x five shot families x the play's context — transition, semi-transition,
// half-court, putback). Per 75 possessions on the floor
// (team possessions from the play-by-play x his share of his team's minutes that game). Data: GET /nba/stats/shot-value,
// a static file rebuilt by hand when the model is re-run.
const COLS = [
  { key: "name", label: "Player", left: true },
  { key: "team", label: "Team", left: true },
  { key: "minutes", label: "Min" },
  { key: "shots", label: "FGA" },
  { key: "fga75", label: "FGA /75" },
  { key: "diet", label: "Shot diet", left: true, nosort: true },
  { key: "exp_pps", label: "Exp pts/shot", pct: "pct_exp" },
  { key: "pps", label: "Pts/shot", pct: "pct_pps" },
  { key: "added75", label: "Added /75", pct: "pct_added75", big: true },
  { key: "added", label: "Added" },
];
const DIET = ["rim", "short 3–8", "mid 8–16", "long two", "three"];

function Seg({ label, value, options, onChange }) {
  return (
    <>
      <label>{label}</label>
      <div className="sh-seg" role="radiogroup" aria-label={label}>
        {options.map(o => <button key={o.v} role="radio" aria-checked={o.v === value} onClick={() => onChange(o.v)}>{o.l}</button>)}
      </div>
    </>
  );
}

const signed = (v, d) => (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(d);

function Cell({ col, r, shades }) {
  if (col.key === "name") return <td className="name l">{r.name}</td>;
  if (col.key === "team") return <td className="team l"><TeamChip team={r.team} /></td>;
  if (col.key === "minutes") return <td>{r.minutes == null ? "—" : r.minutes.toLocaleString()}</td>;
  if (col.key === "fga75") return <td>{r.fga75.toFixed(1)}</td>;
  if (col.key === "shots") return <td>{r.shots.toLocaleString()}</td>;
  if (col.key === "diet") {
    const title = DIET.map((n, i) => `${n} ${Math.round(100 * r.diet[i])}%`).join(" · ");
    return <td className="l"><span className="sh-diet" title={title}>{r.diet.map((w, i) => <i key={i} className={`d${i}`} style={{ width: `${100 * w}%` }} />)}</span></td>;
  }
  const v = r[col.key];
  const text = col.key === "added" ? signed(v, 0) : col.key === "added75" ? signed(v, 2) : v.toFixed(2);
  const sh = shades?.[col.key]?.(v);
  return (
    <td className={`${col.big ? "big " : ""}${col.key === "exp_pps" ? "exp " : ""}${sh ? "shaded" : ""}`} style={sh}>
      {col.pct ? <span className="sh-v">{text}<i>{ordinal(r[col.pct])}</i></span> : text}
    </td>
  );
}

function ordinal(n) {
  const s = ["th", "st", "nd", "rd"], v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

function ChartImg({ src, alt }) {
  const [missing, setMissing] = useState(false);
  return missing ? <div className="sh-panel-empty">No chart yet.</div> : <img src={src} alt={alt} onError={() => setMissing(true)} />;
}

// the shot line (2026-10-24): points per shot by distance — his actual and what the league expects from those same
// shots, each smoothed over 2 ft (twos and threes apart, never across the line), his shots per foot underneath
function ShotLine({ dist }) {
  const [hover, setHover] = useState(null);
  if (!dist) return null;
  const W = 360, H = 176, L = 30, R = 10, T = 14, VB = 26, B = H - 22, top = T, bot = B - VB - 6;
  const x = f => L + (f / 30) * (W - L - R), y = v => bot - (Math.min(v, 1.8) / 1.8) * (bot - top);
  const all = [...(dist.two || []), ...(dist.three || [])];
  const maxN = Math.max(1, ...all.map(d => d[1]));
  const line = (seg, k) => {
    const pts = seg.filter(d => d[k] != null).map(d => `${x(d[0]).toFixed(1)},${y(d[k]).toFixed(1)}`);
    return pts.length > 1 ? pts.join(" ") : null;
  };
  const near = hover == null ? null : all.reduce((b, d) => (Math.abs(d[0] - hover) < Math.abs(b[0] - hover) ? d : b), all[0]);
  return (
    <div className="sh-line">
      <div className="sh-line-key"><span className="act">actual</span><span className="exp">expected for his shots</span><span className="vol">his shots</span></div>
      <svg viewBox={`0 0 ${W} ${H}`} onMouseMove={e => { const b = e.currentTarget.getBoundingClientRect(); setHover(((e.clientX - b.left) / b.width * W - L) / (W - L - R) * 30); }} onMouseLeave={() => setHover(null)}>
        {[0.5, 1.0, 1.5].map(v => <g key={v}><line x1={L} x2={W - R} y1={y(v)} y2={y(v)} className="g" /><text x={L - 5} y={y(v) + 4} className="ax" textAnchor="end">{v.toFixed(1)}</text></g>)}
        {[0, 5, 10, 15, 20, 25, 30].map(f => <text key={f} x={x(f)} y={H - 6} className="ax" textAnchor="middle">{f === 30 ? "30 ft" : f}</text>)}
        <line x1={x(23.75)} x2={x(23.75)} y1={top} y2={B} className="three" />
        {all.map((d, i) => d[1] > 0 && <rect key={i} x={x(d[0]) - 3} width="6" y={B - (d[1] / maxN) * VB} height={(d[1] / maxN) * VB} className="vol" />)}
        {["two", "three"].map(s => dist[s] && <g key={s}>
          {line(dist[s], 3) && <polyline points={line(dist[s], 3)} className="exp" />}
          {line(dist[s], 2) && <polyline points={line(dist[s], 2)} className="act" />}
        </g>)}
        {near && <g><line x1={x(near[0])} x2={x(near[0])} y1={top} y2={B} className="cur" />
          <text x={Math.min(x(near[0]) + 6, W - 150)} y={top + 10} className="tip">{near[0]} ft · {near[1]} shot{near[1] === 1 ? "" : "s"}{near[2] != null ? ` · ${near[2].toFixed(2)} vs ${near[3].toFixed(2)}` : ""}</text></g>}
      </svg>
    </div>
  );
}

function ChartPanel({ r, season }) {
  if (!r) return <aside className="sh-panel"><div className="sh-panel-empty">Click a player.</div></aside>;
  const src = `${API}/nba/stats/shot-chart/${season}/${r.pid}`;
  return (
    <aside className="sh-panel">
      <div className="sh-panel-head">
        <div className="sh-panel-name"><b>{r.name}</b><span className="sh-panel-team">{r.team}</span></div>
        <div className="sh-panel-nums">
          <div><b className={r.added75 < 0 ? "neg" : ""}>{signed(r.added75, 2)}</b><span>added /75</span></div>
          <div><b className={r.added < 0 ? "neg" : ""}>{signed(r.added, 0)}</b><span>added</span></div>
          <div><b>{r.pps.toFixed(2)}</b><span>pts/shot <i>{ordinal(r.pct_pps)}</i></span></div>
          <div><b>{r.exp_pps.toFixed(2)}</b><span>expected <i>{ordinal(r.pct_exp)}</i></span></div>
          <div><b>{r.fga75.toFixed(1)}</b><span>FGA /75</span></div>
        </div>
      </div>
      <div className="sh-chart"><ChartImg key={r.pid} src={src} alt={`${r.name} shot chart`} /></div>
      <ShotLine dist={r.dist} />
    </aside>
  );
}

export default function Shooting() {
  const [data, setData] = useState(null);
  const [sort, setSort] = useState({ key: "shots", dir: -1 });   // most attempts first (2026-10-24)
  const [end, setEnd] = useState("best");
  const [sel, setSel] = useState(null);
  const [query, setQuery] = useState("");
  const [team, setTeam] = useState("");
  const [page, setPage] = useState(0);
  const [minShots, setMinShots] = useState(0);
  const PAGE = 25;
  const season = data?.meta?.season || "2025-26";

  const league = useLeague();
  useEffect(() => {
    fetch(`${API}/nba/stats/shot-value${leagueQ(league)}`, { credentials: "include" }).then(r => r.json()).then(setData).catch(() => setData({ players: [] }));
  }, [league]);

  const rows = useMemo(() => {
    const list = (data?.players || []).filter(p => matches(p.name, query) && (!team || (p.team || "").split("/").includes(team)) && p.shots >= minShots);
    const k = sort.key, d = sort.dir * (end === "best" ? 1 : -1);
    list.sort((a, b) => (typeof a[k] === "string" ? a[k].localeCompare(b[k]) : (a[k] ?? -1e9) - (b[k] ?? -1e9)) * d);
    return list;
  }, [data, sort, end, query, team, minShots]);
  const shades = useMemo(() => ({ added75: makeShade((data?.players || []).map(p => p.added75)), added: makeShade((data?.players || []).map(p => p.added)) }), [data]);
  const teams = useMemo(() => [...new Set((data?.players || []).flatMap(p => (p.team || "").split("/")))].filter(Boolean).sort(), [data]);
  const pages = Math.max(1, Math.ceil(rows.length / PAGE));
  const pg = Math.min(page, pages - 1);
  const slice = rows.slice(pg * PAGE, pg * PAGE + PAGE);

  const current = useMemo(() => rows.find(r => r.pid === sel) || slice[0] || null, [rows, slice, sel]);

  function clickHeader(col) {
    if (col.nosort) return;
    setPage(0);
    setSort(s => s.key === col.key ? { key: col.key, dir: -s.dir } : { key: col.key, dir: typeof (data?.players?.[0]?.[col.key]) === "string" ? 1 : -1 });
  }

  return (
    <div className="site-ui stats-ui" style={{ minHeight: "100vh" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1480, boxSizing: "border-box", minWidth: 0 }}>
        <StatsNav />
        <div className="sh-head">
          <h1 className="sh-title">Shooting</h1>
          <span className="sh-meta">{seasonLabel(data?.meta, league)} · top 300 shot-takers · per 75 possessions</span>
        </div>
        <ShootingTabs />
        <div className="sh-bar">
          <Seg label="Show" value={end} options={[{ v: "best", l: "Best first" }, { v: "worst", l: "Worst first" }]} onChange={v => { setEnd(v); setPage(0); }} />
          <TableFilter query={query} setQuery={q => { setQuery(q); setPage(0); }} team={team} setTeam={t => { setTeam(t); setPage(0); }} teams={teams} />
          <select className="sh-min" value={minShots} onChange={e => { setMinShots(+e.target.value); setPage(0); }} aria-label="Minimum shots">
            {[[0, "Any number of shots"], [10, "10+ shots"], [25, "25+ shots"], [50, "50+ shots"], [100, "100+ shots"], [250, "250+ shots"]].map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <span className="sh-key"><i className="d0" style={{ background: "var(--accent)" }} />rim<i className="d1" style={{ background: "color-mix(in srgb, var(--text) 75%, transparent)" }} />3–8 ft<i className="d2" style={{ background: "color-mix(in srgb, var(--text) 50%, transparent)" }} />8–16<i className="d3" style={{ background: "color-mix(in srgb, var(--text) 28%, transparent)" }} />long two<i className="d4" style={{ background: "var(--diet-three)" }} />three</span>
        </div>
        {data === null ? <p style={{ fontSize: 14 }}>Loading…</p> : (
          <div className="sh-layout">
          <section className="sh-card">
            {rows.length === 0 ? <div className="sh-empty">No data.</div> : (
              <table className="sh-table">
                <thead>
                  <tr>
                    <th className="l">#</th>
                    {COLS.map(c => <th key={c.key} className={`${c.left ? "l" : ""}${sort.key === c.key ? " on" : ""}`} onClick={() => clickHeader(c)}>{c.label}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {slice.map((r, i) => (
                    <tr key={r.pid} className={`${pg === 0 && i < 3 && !query && !team ? (end === "best" ? "top" : "bottom") : ""}${current?.pid === r.pid ? " sel" : ""}`} style={teamEdge(r.team)} onClick={() => setSel(r.pid)}>
                      <td className="rk l">{pg * PAGE + i + 1}</td>
                      {COLS.map(c => <Cell key={c.key} col={c} r={r} shades={shades} />)}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <Pager page={pg} pages={pages} total={rows.length} size={PAGE} setPage={setPage} />
          </section>
          <ChartPanel r={current} season={league === "wnba" ? `wnba-${season}` : season} />
          </div>
        )}
      </div>
    </div>
  );
}
