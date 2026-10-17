import { useEffect, useMemo, useState } from "react";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import StatsNav from "./StatsNav";
import { TableFilter, Pager, TeamChip } from "./StatsControls";
import { teamEdge } from "./teamEdge";
import { makeShade } from "./shade";
import { matches } from "./statsMatch";
import "./Rebounding.css";

// Rebounding: actual vs expected on every live rebound chance a player was on the floor for (2024-25, lineups).
// Expected comes two ways — from the shot alone (league rate for that miss distance) and from the other nine on the
// floor with an average player in his spot. Actual is what happened. His effect = actual − other nine, in points of
// rate and in boards. Data: GET /nba/stats/rebounding (nba-pipeline/models/rebounding_tables.py), a static file.
const PAGE = 25;
const DIST = ["FT", "rim 0-3", "short 3-8", "mid 8-16", "long two", "three"];
const COLS = [
  { key: "name", label: "Player", left: true, str: true },
  { key: "team", label: "Team", left: true, str: true },
  { key: "size", label: "Size", left: true, nosort: true },
  { key: "chances", label: "Chances" },
  { key: "own_exp_shot", label: "shot", grp: true, exp: true, pct: true, tip: "League rate for that kind of miss" },
  { key: "own_exp_others", label: "lineup", exp: true, pct: true, tip: "The other nine who were there, and a man of his size in his spot" },
  { key: "own_act", label: "actual", act: true, pct: true },
  { key: "team_exp_shot", label: "shot", grp: true, exp: true, pct: true, tip: "League rate for that kind of miss" },
  { key: "team_exp_others", label: "lineup", exp: true, pct: true, tip: "The other nine who were there, and a man of his size in his spot" },
  { key: "team_act", label: "actual", act: true, pct: true },
  { key: "own_effect", label: "player", grp: true, signed: true, pts: true },
  { key: "team_effect", label: "team", signed: true, pts: true, big: true },
];

const signed = (v, d) => (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(d);

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

function Cell({ col, r, s, shades }) {
  if (col.key === "name") return <td className="name l">{r.name}</td>;
  if (col.key === "team") return <td className="team l"><TeamChip team={r.team} /></td>;
  if (col.key === "size") return <td className="size l">{r.ht}{r.wt ? ` · ${r.wt}` : ""}</td>;
  if (col.key === "chances") return <td>{s.chances.toLocaleString()}</td>;
  const v = s[col.key];
  const text = col.int ? signed(v, 0) : col.signed ? `${signed(v, 1)} pts` : `${v.toFixed(1)}%`;
  const sh = shades?.[col.key]?.(v);
  const cls = `${col.grp ? "g " : ""}${col.exp ? "exp " : ""}${col.act ? "act " : ""}${col.big ? "big " : ""}${sh ? "shaded" : ""}`;
  return <td className={cls} style={sh}>{text}</td>;
}

// three bars: expected from the shot, expected from the other nine, actual
function ThreeBars({ title, shot, others, act, max }) {
  const W = 392, L = 108, R = 46, H = 78, bh = 16;
  const sx = v => L + (v / max) * (W - L - R);
  const rows = [["model · shot", shot, "i", 0.35], ["model · lineup", others, "i", 0.55], ["actual", act, "b", 1]];
  return (
    <div className="rb-fig">
      <h3>{title}</h3>
      <svg viewBox={`0 0 ${W} ${H}`}>
        {rows.map(([lab, v, cls, op], i) => (
          <g key={lab} transform={`translate(0 ${i * 26})`}>
            <text x={L - 8} y={13} textAnchor="end" className={cls}>{lab}</text>
            <rect x={L} y={2} width={Math.max(0, sx(v) - L)} height={bh} fill="var(--accent)" opacity={op} rx="2" />
            <text x={sx(v) + 6} y={13} className={cls}>{v.toFixed(1)}%</text>
          </g>
        ))}
      </svg>
    </div>
  );
}

// where the boards go: him / teammates / opponents (or team rebound), expected vs actual
function Stacked({ side, s }) {
  const W = 392, L = 76, H = 70, bh = 20;
  const rows = [
    ["expected", s.own_exp_others, s.team_exp_others - s.own_exp_others, 100 - s.team_exp_others, "i"],
    ["actual", s.own_act, s.team_act - s.own_act, 100 - s.team_act, "b"],
  ];
  const sx = v => L + (v / 100) * (W - L - 8);
  return (
    <div className="rb-fig">
      <h3>Who comes down with it</h3>
      <svg viewBox={`0 0 ${W} ${H}`}>
        {rows.map(([lab, him, mates, opp, cls], i) => {
          const y = i * 30 + 2;
          return (
            <g key={lab}>
              <text x={L - 8} y={y + 14} textAnchor="end" className={cls}>{lab}</text>
              <rect x={sx(0)} y={y} width={sx(him) - sx(0)} height={bh} fill="var(--accent)" />
              <rect x={sx(him) + 1} y={y} width={Math.max(0, sx(him + mates) - sx(him) - 1)} height={bh} fill="var(--text)" opacity="0.8" />
              <rect x={sx(him + mates) + 1} y={y} width={Math.max(0, sx(100) - sx(him + mates) - 1)} height={bh} fill="var(--text)" opacity="0.22" />
              <text x={sx(0) + 4} y={y + 14} className={cls} fill="var(--accent-ink)" style={{ fill: "var(--accent-ink)" }}>{him.toFixed(1)}</text>
              <text x={sx(him) + 6} y={y + 14} className={cls} style={{ fill: "var(--bg)" }}>{mates.toFixed(1)}</text>
              <text x={sx(100) - 4} y={y + 14} textAnchor="end" className={cls}>{opp.toFixed(1)}</text>
            </g>
          );
        })}
      </svg>
      <div className="rb-key"><span><i style={{ background: "var(--accent)" }} />him</span><span><i style={{ background: "var(--text)", opacity: 0.8 }} />teammates</span><span><i style={{ background: "var(--text)", opacity: 0.22 }} />{side === "D" ? "offense" : "defense"}</span></div>
    </div>
  );
}

// by miss distance: team expected (other nine) vs actual, with the chance count
function ByDist({ s }) {
  const keys = DIST.filter(k => s.by_dist[k]);
  const W = 392, L = 76, R = 40, rh = 22, H = keys.length * rh + 6;
  const vals = keys.flatMap(k => [s.by_dist[k][1], s.by_dist[k][2]]);
  const lo = Math.max(0, Math.min(...vals) - 8), hi = Math.min(100, Math.max(...vals) + 8);
  const sx = v => L + ((v - lo) / (hi - lo)) * (W - L - R);
  return (
    <div className="rb-fig">
      <h3>Team rate by where the miss came from</h3>
      <svg viewBox={`0 0 ${W} ${H}`}>
        {keys.map((k, i) => {
          const [n, exp, act] = s.by_dist[k]; const y = i * rh + 4;
          return (
            <g key={k}>
              <text x={L - 8} y={y + 12} textAnchor="end">{k}</text>
              <line x1={sx(exp)} y1={y + 8} x2={sx(act)} y2={y + 8} stroke={act >= exp ? "var(--accent)" : "var(--accent-red)"} strokeWidth="3" />
              <circle cx={sx(exp)} cy={y + 8} r="4" fill="var(--surface)" stroke="var(--text)" strokeWidth="1.5" />
              <circle cx={sx(act)} cy={y + 8} r="4.5" fill={act >= exp ? "var(--accent)" : "var(--accent-red)"} />
              <text x={W - R + 6} y={y + 12} className="i">{n}</text>
            </g>
          );
        })}
      </svg>
      <div className="rb-key"><span><i style={{ background: "var(--surface)", border: "1.5px solid var(--text)", boxSizing: "border-box" }} />model</span><span><i style={{ background: "var(--accent)" }} />actual</span></div>
    </div>
  );
}

function Panel({ r, side }) {
  if (!r) return <aside className="rb-panel"><div className="rb-panel-empty">Click a player.</div></aside>;
  const s = r[side];
  if (!s) return <aside className="rb-panel"><div className="rb-panel-empty">Under 400 {side === "D" ? "defensive" : "offensive"} chances.</div></aside>;
  const max = Math.max(s.team_act, s.team_exp_others, s.team_exp_shot) * 1.15;
  return (
    <aside className="rb-panel">
      <div className="rb-panel-head">
        <div className="rb-panel-name"><b>{r.name}</b><span>{r.team} · {r.ht}{r.wt ? ` · ${r.wt}` : ""} · {s.chances.toLocaleString()} chances</span></div>
        <div className="rb-panel-nums">
          <div><b className={s.team_effect < 0 ? "neg" : ""}>{signed(s.team_effect, 1)}</b><span>team {side}REB%, pts</span></div>
          <div><b className={s.own_effect < 0 ? "neg" : ""}>{signed(s.own_effect, 1)}</b><span>player {side}REB%, pts</span></div>
          <div><b className={s.for_teammates < 0 ? "neg" : ""}>{signed(s.for_teammates, 1)}</b><span>for teammates, pts</span></div>
          <div><b className={s.team_boards_added < 0 ? "neg" : ""}>{signed(s.team_boards_added, 0)}</b><span>team boards</span></div>
          <div><b className={s.own_boards_added < 0 ? "neg" : ""}>{signed(s.own_boards_added, 0)}</b><span>his boards</span></div>
          <div><b className={s.teammate_boards < 0 ? "neg" : ""}>{signed(s.teammate_boards, 0)}</b><span>teammates' boards</span></div>
        </div>
      </div>
      <ThreeBars title={`Team ${side === "D" ? "defensive" : "offensive"} rebound %`} shot={s.team_exp_shot} others={s.team_exp_others} act={s.team_act} max={max} />
      <ThreeBars title={`Player ${side}REB%`} shot={s.own_exp_shot} others={s.own_exp_others} act={s.own_act} max={max} />
      <Stacked side={side} s={s} />
      <ByDist s={s} />
    </aside>
  );
}

export default function Rebounding() {
  const [data, setData] = useState(null);
  const [side, setSide] = useState("D");
  const [sort, setSort] = useState({ key: "team_effect", dir: -1 });
  const [end, setEnd] = useState("best");
  const [page, setPage] = useState(0);
  const [query, setQuery] = useState("");
  const [team, setTeam] = useState("");
  const [sel, setSel] = useState(null);

  useEffect(() => {
    fetch(`${API}/nba/stats/rebounding`, { credentials: "include" }).then(r => r.json()).then(setData).catch(() => setData({ players: [] }));
  }, []);

  const rows = useMemo(() => {
    const list = (data?.players || []).filter(p => p[side] && matches(p.name, query) && (!team || p.team === team));
    const k = sort.key, d = sort.dir * (end === "best" ? 1 : -1);
    const col = COLS.find(c => c.key === k);
    const val = p => (col?.str || k === "size" ? p[k] : p[side][k]);
    list.sort((a, b) => (typeof val(a) === "string" ? val(a).localeCompare(val(b)) : (val(a) ?? -1e9) - (val(b) ?? -1e9)) * d);
    return list;
  }, [data, side, sort, end, query, team]);

  const shades = useMemo(() => {
    const all = (data?.players || []).filter(p => p[side]).map(p => p[side]);
    return { own_effect: makeShade(all.map(x => x.own_effect)), team_effect: makeShade(all.map(x => x.team_effect)) };
  }, [data, side]);
  const teams = useMemo(() => [...new Set((data?.players || []).map(p => p.team))].filter(Boolean).sort(), [data]);
  const pages = Math.max(1, Math.ceil(rows.length / PAGE));
  const pg = Math.min(page, pages - 1);
  const slice = rows.slice(pg * PAGE, pg * PAGE + PAGE);
  const current = useMemo(() => rows.find(r => r.pid === sel) || slice[0] || null, [rows, slice, sel]);

  function clickHeader(col) {
    if (col.nosort) return;
    setPage(0);
    setSort(s => s.key === col.key ? { key: col.key, dir: -s.dir } : { key: col.key, dir: col.str ? 1 : -1 });
  }
  function pick(v, setter) { setter(v); setPage(0); }

  return (
    <div className="site-ui stats-ui" style={{ minHeight: "100vh" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1560, boxSizing: "border-box", minWidth: 0 }}>
        <StatsNav />
        <div className="rb-head">
          <h1 className="rb-title">Rebounding</h1>
          <span className="rb-meta">{data?.meta?.season || ""} · every live miss on the floor</span>
        </div>
        <div className="rb-bar">
          <Seg label="Side" value={side} options={[{ v: "D", l: "Defense" }, { v: "O", l: "Offense" }]} onChange={v => pick(v, setSide)} />
          <Seg label="Show" value={end} options={[{ v: "best", l: "Best first" }, { v: "worst", l: "Worst first" }]} onChange={v => pick(v, setEnd)} />
          <TableFilter query={query} setQuery={q => { setQuery(q); setPage(0); }} team={team} setTeam={t => { setTeam(t); setPage(0); }} teams={teams} />
        </div>
        {data === null ? <p style={{ fontSize: 14 }}>Loading…</p> : (
          <div className="rb-layout">
            <section className="rb-card">
              {rows.length === 0 ? <div className="rb-empty">No data.</div> : (
                <table className="rb-table">
                  <thead>
                    <tr>
                      <th className="grp" colSpan={5}></th>
                      <th className="grp g" colSpan={3}><span className="rb-group-tick" />Player {side}REB%</th>
                      <th className="grp g" colSpan={3}><span className="rb-group-tick" />Team {side}REB%</th>
                      <th className="grp g" colSpan={2}><span className="rb-group-tick" />Effect</th>
                    </tr>
                    {/* "Model" heads the two modeled columns of each group, once (2026-10-16) */}
                    <tr className="rb-sub">
                      <th colSpan={5} />
                      <th className="g exp" colSpan={2}>Model</th><th />
                      <th className="g exp" colSpan={2}>Model</th><th />
                      <th className="g" colSpan={2} />
                    </tr>
                    <tr>
                      <th className="l">#</th>
                      {COLS.map(c => <th key={c.key} title={c.tip || ""} className={`${c.left ? "l" : ""}${c.grp ? " g" : ""}${sort.key === c.key ? " on" : ""}`} onClick={() => clickHeader(c)}>{c.label}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {slice.map((r, i) => (
                      <tr key={r.pid} className={`${pg === 0 && i < 3 ? (end === "best" ? "top" : "bottom") : ""}${current?.pid === r.pid ? " sel" : ""}`} style={teamEdge(r.team)} onClick={() => setSel(r.pid)}>
                        <td className="rk l">{pg * PAGE + i + 1}</td>
                        {COLS.map(c => <Cell key={c.key} col={c} r={r} s={r[side]} shades={shades} />)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              <Pager page={pg} pages={pages} total={rows.length} size={PAGE} setPage={setPage} />
            </section>
            <Panel r={current} side={side} />
          </div>
        )}
      </div>
    </div>
  );
}
