import { useEffect, useMemo, useState } from "react";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import { useLeague, leagueQ, seasonLabel } from "./statsLeague";
import StatsNav from "./StatsNav";
import { TableFilter, Pager, TeamChip } from "./StatsControls";
import { teamEdge } from "./teamEdge";
import { makeShade } from "./shade";
import { matches } from "./statsMatch";
import "./Rebounding.css";
import "./Playmaking.css";

// Playmaking: Box Creation (Ben Taylor, Thinking Basketball / Backpicks, public 2017 form) — a box-score estimate of
// the open shots a player creates for teammates per 100 possessions. Every player with 500+ minutes, 25 a page,
// sortable. Click a row: the formula's pieces for him on the right. Data: GET /nba/stats/playmaking (static file from
// nba-pipeline/models/box_creation.py). Stats never link into fantasy.
const PAGE = 25;
const COLS = [
  { key: "name", label: "Player", left: true, str: true },
  { key: "team", label: "Team", left: true, str: true },
  { key: "minutes", label: "Min", int: true },
  { key: "poss", label: "Poss", int: true },
  { key: "pts100", label: "Pts /100", grp: true },
  { key: "ast100", label: "Ast /100" },
  { key: "tov100", label: "TOV /100" },
  { key: "fg3a100", label: "3PA /100" },
  { key: "fg3_pct", label: "3P%", pct: true },
  { key: "prof", label: "3-pt proficiency", d3: true },
  { key: "creation", label: "Creation /100", grp: true, big: true },
  { key: "creations", label: "Season", int: true },
];

function Seg({ label, value, options, onChange }) {
  return (
    <>
      <label>{label}</label>
      <div className="rb-seg" role="radiogroup" aria-label={label}>
        {options.map(o => <button key={o.v} role="radio" aria-checked={o.v === value} onClick={() => onChange(o.v)}>{o.l}</button>)}
      </div>
    </>
  );
}

const signed = (v, d) => (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(d);

function Cell({ col, r, shade }) {
  if (col.key === "name") return <td className="name l">{r.name}</td>;
  if (col.key === "team") return <td className="team l"><TeamChip team={r.team} /></td>;
  const v = r[col.key];
  const text = col.int ? v.toLocaleString() : col.pct ? `${(100 * v).toFixed(1)}%` : col.d3 ? v.toFixed(3) : v.toFixed(1);
  const sh = col.key === "creation" ? shade?.(v) : undefined;
  return <td className={`${col.grp ? "g " : ""}${col.big ? "big " : ""}${sh ? "shaded" : ""}`} style={sh}>{text}</td>;
}

// the formula's pieces, as a waterfall from the constant to his number
function Pieces({ r }) {
  const steps = [
    ["constant", r.t_const], ["assists", r.t_ast], ["points + turnovers", r.t_score], ["shooting (3-pt proficiency)", r.t_shoot], ["assists × scoring × shooting", r.t_inter],
  ];
  const W = 392, L = 170, R = 56, rh = 24, H = steps.length * rh + 34;
  const lo = Math.min(0, ...steps.reduce((acc, [, v]) => { acc.push(acc[acc.length - 1] + v); return acc; }, [0])) - 0.5;
  const hi = Math.max(r.creation, ...steps.reduce((acc, [, v]) => { acc.push(acc[acc.length - 1] + v); return acc; }, [0])) + 0.5;
  const sx = v => L + ((v - lo) / (hi - lo)) * (W - L - R);
  let level = 0;
  const bars = steps.map(([lab, v], i) => {
    const x0 = sx(level), x1 = sx(level + v); level += v;
    return (
      <g key={lab} transform={`translate(0 ${i * rh})`}>
        <text x={L - 8} y={14} textAnchor="end">{lab}</text>
        <rect x={Math.min(x0, x1)} y={3} width={Math.max(1, Math.abs(x1 - x0))} height={16} fill={v >= 0 ? "var(--accent)" : "var(--accent-red)"} rx="2" />
        <text x={Math.max(x0, x1) + 5} y={14}>{signed(v, 2)}</text>
      </g>
    );
  });
  return (
    <div className="rb-fig">
      <h3>Where his number comes from</h3>
      <svg viewBox={`0 0 ${W} ${H}`}>
        <line x1={sx(0)} y1={0} x2={sx(0)} y2={steps.length * rh + 4} stroke="var(--text)" strokeOpacity="0.4" />
        {bars}
        <g transform={`translate(0 ${steps.length * rh + 4})`}>
          <line x1={sx(0)} y1={6} x2={sx(r.creation)} y2={6} stroke="var(--text)" strokeWidth="2" />
          <text x={sx(r.creation) + 5} y={11} className="b">{r.creation.toFixed(2)} created per 100</text>
        </g>
      </svg>
    </div>
  );
}

function Panel({ r }) {
  if (!r) return <aside className="rb-panel"><div className="rb-panel-empty">Click a player.</div></aside>;
  return (
    <aside className="rb-panel">
      <div className="rb-panel-head">
        <div className="rb-panel-name"><b>{r.name}</b><span>{r.team} · {r.games} g · {r.minutes.toLocaleString()} min · {r.poss.toLocaleString()} poss</span></div>
        <div className="rb-panel-nums">
          <div><b className={r.creation < 0 ? "neg" : ""}>{r.creation.toFixed(1)}</b><span>created /100</span></div>
          <div><b>{r.creations.toLocaleString()}</b><span>created, season</span></div>
          <div><b>{r.pct}</b><span>percentile</span></div>
        </div>
      </div>
      <Pieces r={r} />
      <div className="pm-inputs">
        <div><b>{r.ast100.toFixed(1)}</b><span>ast /100</span></div>
        <div><b>{r.pts100.toFixed(1)}</b><span>pts /100</span></div>
        <div><b>{r.tov100.toFixed(1)}</b><span>tov /100</span></div>
        <div><b>{r.fg3a100.toFixed(1)}</b><span>3PA /100</span></div>
        <div><b>{(100 * r.fg3_pct).toFixed(1)}%</b><span>3P%</span></div>
        <div><b>{r.prof.toFixed(3)}</b><span>proficiency</span></div>
      </div>
    </aside>
  );
}

export default function Playmaking() {
  const [data, setData] = useState(null);
  const [sort, setSort] = useState({ key: "creation", dir: -1 });
  const [end, setEnd] = useState("best");
  const [page, setPage] = useState(0);
  const [query, setQuery] = useState("");
  const [team, setTeam] = useState("");
  const [sel, setSel] = useState(null);

  const league = useLeague();
  useEffect(() => {
    fetch(`${API}/nba/stats/playmaking${leagueQ(league)}`, { credentials: "include" }).then(r => r.json()).then(setData).catch(() => setData({ players: [] }));
  }, [league]);

  const rows = useMemo(() => {
    const list = (data?.players || []).filter(p => matches(p.name, query) && (!team || (p.team || "").split("/").includes(team)));
    const k = sort.key, d = sort.dir * (end === "best" ? 1 : -1);
    list.sort((a, b) => (typeof a[k] === "string" ? a[k].localeCompare(b[k]) : (a[k] ?? -1e9) - (b[k] ?? -1e9)) * d);
    return list;
  }, [data, sort, end, query, team]);

  const shade = useMemo(() => makeShade((data?.players || []).map(p => p.creation), { center: "median" }), [data]);
  const teams = useMemo(() => [...new Set((data?.players || []).flatMap(p => (p.team || "").split("/")))].filter(Boolean).sort(), [data]);
  const pages = Math.max(1, Math.ceil(rows.length / PAGE));
  const pg = Math.min(page, pages - 1);
  const slice = rows.slice(pg * PAGE, pg * PAGE + PAGE);
  const current = useMemo(() => rows.find(r => r.pid === sel) || slice[0] || null, [rows, slice, sel]);

  function clickHeader(col) {
    setPage(0);
    setSort(s => s.key === col.key ? { key: col.key, dir: -s.dir } : { key: col.key, dir: col.str ? 1 : -1 });
  }

  return (
    <div className="site-ui stats-ui" style={{ minHeight: "100vh" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1560, boxSizing: "border-box", minWidth: 0 }}>
        <StatsNav />
        <div className="rb-head">
          <h1 className="rb-title">Playmaking</h1>
          <span className="rb-meta">{seasonLabel(data?.meta, league)} · Box Creation per 100 possessions · {data?.meta?.min_minutes || 500}+ minutes</span>
        </div>
        <div className="rb-bar">
          <Seg label="Show" value={end} options={[{ v: "best", l: "Best first" }, { v: "worst", l: "Worst first" }]} onChange={v => { setEnd(v); setPage(0); }} />
          <TableFilter query={query} setQuery={q => { setQuery(q); setPage(0); }} team={team} setTeam={t => { setTeam(t); setPage(0); }} teams={teams} />
        </div>
        {data === null ? <p style={{ fontSize: 14 }}>Loading…</p> : (
          <div className="rb-layout">
            <section className="rb-card">
              {rows.length === 0 ? <div className="rb-empty">No data.</div> : (
                <table className="rb-table pm-table">
                  <thead>
                    <tr>
                      <th className="grp" colSpan={5}></th>
                      <th className="grp g" colSpan={6}>Inputs, per 100 possessions</th>
                      <th className="grp g" colSpan={2}>Box Creation</th>
                    </tr>
                    <tr>
                      <th className="l">#</th>
                      {COLS.map(c => <th key={c.key} className={`${c.left ? "l" : ""}${c.grp ? " g" : ""}${sort.key === c.key ? " on" : ""}`} onClick={() => clickHeader(c)}>{c.label}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {slice.map((r, i) => (
                      <tr key={r.pid} className={`${pg === 0 && i < 3 ? (end === "best" ? "top" : "bottom") : ""}${current?.pid === r.pid ? " sel" : ""}`} style={teamEdge(r.team)} onClick={() => setSel(r.pid)}>
                        <td className="rk l">{pg * PAGE + i + 1}</td>
                        {COLS.map(c => <Cell key={c.key} col={c} r={r} shade={shade} />)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              <Pager page={pg} pages={pages} total={rows.length} size={PAGE} setPage={setPage} />
            </section>
            <Panel r={current} />
          </div>
        )}
      </div>
    </div>
  );
}
