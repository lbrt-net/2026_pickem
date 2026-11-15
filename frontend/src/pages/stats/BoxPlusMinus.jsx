import { useEffect, useMemo, useState } from "react";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import StatsNav from "./StatsNav";
import { TeamChip } from "./StatsControls";
import { teamEdge } from "./teamEdge";
import { makeShade } from "./shade";
import "./Rebounding.css";
import "./BoxPlusMinus.css";
import { signed } from "../../utils/numbers";

// Box +/- (2026-11-14): what a player's own game stats say his plus-minus should be, per game, for the season in progress.
// Model: nba-pipeline/models/game_rtg_split.py --export — two GBMs from one player-game's box line plus every other game-level
// stat we pull (hustle, tracking, shot defense, shot types): Off = points his team scored with him on vs a league-average
// offense, Def = points allowed vs league average, per game, with context known before tip-off (opponent, his own team,
// home) taken out. Box +/- = Off + Def exactly; each stat's part = its offense part + its defense part. Trained on 2022-23
// → 2025-26 only, so this season's numbers are out of sample; re-predicted every night.
// Two views: the top 25 (5+ games, 15+ minutes a game) and any team's 10 biggest-minute players. Click a row: each stat's
// part of his number. Data: GET /nba/stats/box-pm. NBA only. Stats never link into fantasy.
const MIN_GP = 5, MIN_MPG = 15;
const GROUPS = ["Shooting", "Playmaking", "Rebounding", "Defense", "Hustle", "Minutes"];
const COLS = [
  { key: "name", label: "Player", left: true, str: true },
  { key: "team", label: "Team", left: true, str: true },
  { key: "gp", label: "GP", int: true },
  { key: "mpg", label: "Min" },
  { key: "box", label: "Box +/-", grp: true, big: true, sign: true },
  { key: "off", label: "Off", sign: true },
  { key: "deff", label: "Def", sign: true },
  { key: "actual", label: "Actual +/-", sign: true },
  { key: "context", label: "Context", sign: true, grp: true },
  ...GROUPS.map((g, i) => ({ key: `g:${g}`, label: g, sign: true, grp: i === 0 })),
];
const val = (r, k) => (k.startsWith("g:") ? r.groups[k.slice(2)] : r[k]);

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

function Cell({ col, r, shade }) {
  if (col.key === "name") return <td className="name l">{r.name}</td>;
  if (col.key === "team") return <td className="team l"><TeamChip team={r.team} /></td>;
  const v = val(r, col.key);
  if (v == null) return <td className={col.grp ? "g" : ""}>–</td>;
  const text = col.int ? v.toLocaleString() : col.sign ? signed(v, 1) : v.toFixed(1);
  const sh = col.key === "box" ? shade?.(v) : undefined;
  return <td className={`${col.grp ? "g " : ""}${col.big ? "big " : ""}${sh ? "shaded" : ""}`} style={sh}>{text}</td>;
}

// his 14 biggest parts, biggest first, with how many a game he had, then everything else in one bar
function Pieces({ r, labels }) {
  const steps = Object.entries(r.c).map(([s, v]) => [labels[s] || s, v, r.per_game[s], r.c_off[s], r.c_def[s]]).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  if (Math.abs(r.other) >= 0.005) steps.push(["Everything else", r.other, null, null, null]);
  const W = 520, L = 210, R = 136, rh = 22, H = steps.length * rh + 40;
  const lo = Math.min(0, ...steps.map(s => s[1]), r.box) - 0.3, hi = Math.max(0, ...steps.map(s => s[1]), r.box) + 0.3;
  const sx = v => L + ((v - lo) / (hi - lo)) * (W - L - R);
  return (
    <div className="rb-fig">
      <h3>Where his number comes from, per game</h3>
      <svg viewBox={`0 0 ${W} ${H}`}>
        <line x1={sx(0)} y1={0} x2={sx(0)} y2={steps.length * rh + 4} stroke="var(--text)" strokeOpacity="0.4" />
        {steps.map(([s, v, n, o, d], i) => (
          <g key={s} transform={`translate(0 ${i * rh})`}>
            <text x={L - 8} y={14} textAnchor="end">{s}{n == null ? "" : ` · ${n.toFixed(n >= 10 ? 0 : 1)}`}</text>
            <rect x={Math.min(sx(0), sx(v))} y={3} width={Math.max(1, Math.abs(sx(v) - sx(0)))} height={15} fill={v >= 0 ? "var(--accent)" : "var(--accent-red)"} rx="2" />
            <text x={Math.max(sx(0), sx(v)) + 5} y={14}>{signed(v, 2)}{o == null ? "" : ` (O ${signed(o, 2)} · D ${signed(d, 2)})`}</text>
          </g>
        ))}
        <g transform={`translate(0 ${steps.length * rh + 4})`}>
          <line x1={sx(0)} y1={6} x2={sx(r.box)} y2={6} stroke="var(--text)" strokeWidth="2" />
          <text x={W - 2} y={24} textAnchor="end" className="b">{signed(r.box, 2)} box +/- a game = O {signed(r.off, 2)} + D {signed(r.deff, 2)}</text>
        </g>
      </svg>
    </div>
  );
}

function Panel({ r, meta }) {
  if (!r) return <aside className="rb-panel"><div className="rb-panel-empty">Click a player.</div></aside>;
  return (
    <aside className="rb-panel">
      <div className="rb-panel-head">
        <div className="rb-panel-name"><b>{r.name}</b><span>{r.team} · {r.gp} g · {Math.round(r.min).toLocaleString()} min</span></div>
        <div className="rb-panel-nums">
          <div><b className={r.box < 0 ? "neg" : ""}>{signed(r.box, 1)}</b><span>box +/- a game</span></div>
          <div><b className={r.off < 0 ? "neg" : ""}>{signed(r.off, 1)}</b><span>offense ({signed(r.off100, 1)} /100)</span></div>
          <div><b className={r.deff < 0 ? "neg" : ""}>{signed(r.deff, 1)}</b><span>defense ({signed(r.def100, 1)} /100)</span></div>
          <div><b className={r.actual < 0 ? "neg" : ""}>{signed(r.actual, 1)}</b><span>actual a game</span></div>
        </div>
      </div>
      <Pieces r={r} labels={meta.labels} />
      <p className="bp-ctx">Actual with him on, vs league, a game: offense {signed(r.act_off, 1)} · defense {signed(r.act_def, 1)}</p>
      <p className="bp-ctx">Context, left out of his number ({signed(r.context, 1)} a game): opponent {signed(r.ctx.opp, 1)} · his team {signed(r.ctx.own, 1)} · home court {signed(r.ctx.home, 1)}</p>
      <div className="bp-worth">
        <h3>One more of each, in game +/- (the {meta.values.length} that move it most)</h3>
        <div className="bp-worth-grid">
          {meta.values.map(v => <div key={v.stat}><span>{meta.labels[v.stat] || v.stat}</span><b>{signed(v.per_one, 2)}</b></div>)}
        </div>
      </div>
    </aside>
  );
}

export default function BoxPlusMinus() {
  const [data, setData] = useState(null);
  const [view, setView] = useState("top");
  const [team, setTeam] = useState("");
  const [sort, setSort] = useState({ key: "box", dir: -1 });
  const [sel, setSel] = useState(null);

  useEffect(() => {
    fetch(`${API}/nba/stats/box-pm`, { credentials: "include" }).then(r => r.json()).then(setData).catch(() => setData({ players: [], meta: {} }));
  }, []);

  const players = useMemo(() => data?.players || [], [data]);
  const teams = useMemo(() => [...new Set(players.flatMap(p => Object.keys(p.teams || {})))].sort(), [players]);
  const curTeam = team || teams[0] || "";

  const rows = useMemo(() => {
    let list;
    if (view === "top") {
      list = players.filter(p => p.gp >= MIN_GP && p.mpg >= MIN_MPG).sort((a, b) => b.box - a.box).slice(0, 25);
    } else {
      list = players.filter(p => p.teams?.[curTeam]).sort((a, b) => b.teams[curTeam] - a.teams[curTeam]).slice(0, 10);
    }
    const k = sort.key, d = sort.dir;
    return [...list].sort((a, b) => (typeof val(a, k) === "string" ? val(a, k).localeCompare(val(b, k)) : val(a, k) - val(b, k)) * d);
  }, [players, view, curTeam, sort]);

  const shade = useMemo(() => makeShade(players.filter(p => p.gp >= MIN_GP && p.mpg >= MIN_MPG).map(p => p.box), { center: 0 }), [players]);
  const current = useMemo(() => rows.find(r => r.pid === sel) || rows[0] || null, [rows, sel]);
  const meta = data?.meta || {};

  function clickHeader(col) {
    setSort(s => s.key === col.key ? { key: col.key, dir: -s.dir } : { key: col.key, dir: col.str ? 1 : -1 });
  }

  return (
    <div className="site-ui stats-ui" style={{ minHeight: "100vh" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1560, boxSizing: "border-box", minWidth: 0 }}>
        <StatsNav />
        <div className="rb-head">
          <h1 className="rb-title">Box +/-</h1>
          <span className="rb-meta">{meta.season || ""} · plus-minus from a player's own game stats ({meta.stats || 0} of them), offense + defense, opponent and his team taken out · trained on {meta.train ? meta.train.join(" to ") : "earlier seasons"} · {meta.games || 0} games{meta.built ? ` · built ${meta.built}` : ""}</span>
        </div>
        <div className="rb-bar">
          <Seg label="Show" value={view} options={[{ v: "top", l: "Top 25" }, { v: "team", l: "By team" }]} onChange={v => { setView(v); setSel(null); }} />
          {view === "team" && (
            <div className="bp-teams" role="radiogroup" aria-label="Team">
              {teams.map(t => <button key={t} role="radio" aria-checked={t === curTeam} onClick={() => { setTeam(t); setSel(null); }}>{t}</button>)}
            </div>
          )}
        </div>
        <p className="bp-sub">{view === "top" ? `The 25 best box +/- a game, ${MIN_GP}+ games and ${MIN_MPG}+ minutes a game.` : `${curTeam}'s 10 players with the most minutes for them.`}</p>
        {data === null ? <p style={{ fontSize: 14 }}>Loading…</p> : (
          <div className="rb-layout">
            <section className="rb-card">
              {rows.length === 0 ? <div className="rb-empty">No data.</div> : (
                <table className="rb-table bp-table">
                  <thead>
                    <tr>
                      <th className="grp" colSpan={5}></th>
                      <th className="grp g" colSpan={4}>Per game · Box = Off + Def</th>
                      <th className="grp g" colSpan={1}></th>
                      <th className="grp g" colSpan={6}>Box +/- by part, per game</th>
                    </tr>
                    <tr>
                      <th className="l">#</th>
                      {COLS.map(c => <th key={c.key} className={`${c.left ? "l" : ""}${c.grp ? " g" : ""}${sort.key === c.key ? " on" : ""}`} onClick={() => clickHeader(c)}
                        aria-sort={sort.key === c.key ? (sort.dir > 0 ? "ascending" : "descending") : undefined}>{c.label}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r, i) => (
                      <tr key={r.pid} className={current?.pid === r.pid ? "sel" : ""} style={teamEdge(r.team)} onClick={() => setSel(r.pid)}>
                        <td className="rk l">{i + 1}</td>
                        {COLS.map(c => <Cell key={c.key} col={c} r={r} shade={shade} />)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
            {meta.groups && <Panel r={current} meta={meta} />}
          </div>
        )}
      </div>
    </div>
  );
}
