import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import useCurrentUser from "../../hooks/useCurrentUser";
import StatsNav from "./StatsNav";
import { TeamChip } from "./StatsControls";
import { teamEdge } from "./teamEdge";
import { makeShade } from "./shade";
import "./Rebounding.css";
import "./Defense.css";

// /stats/defense (2026-10-17): every team's defenders, pairs and trios from the lineup possessions — facts only, no
// credit split between teammates. Built for the commissioner's notes pass: he writes his eye-test read of each player
// and pair in the notes boxes (admin only, saved on the server), and the next attribution method is checked against
// them. Data: GET /nba/stats/defense (nba-pipeline/models/defense_page.py). Stats never link into fantasy.
const PAGE = "defense";
const pct = v => (v == null ? "–" : `${Math.round(100 * v)}%`);
const f1 = v => (v == null ? "–" : v.toFixed(1));
const signed = v => (v == null ? "—" : (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(1));
const last = n => {
  const parts = (n || "").split(" ");
  const tail = parts[parts.length - 1];
  return /^(Jr\.?|Sr\.?|II|III|IV)$/.test(tail) && parts.length > 2 ? parts[parts.length - 2] : tail;
};

const COLS = [
  { key: "name", label: "Player", left: true, str: true },
  { key: "min", label: "Min", int: true },
  { key: "poss", label: "Def poss", int: true },
  { key: "drtg", label: "DRtg", grp: true },
  { key: "adj", label: "Adj DRtg", big: true, shade: "rtg" },
  { key: "off_adj", label: "Team adj, him off" },
  { key: "onoff", label: "On − off", shade: "onoff" },
  { key: "top30", label: "Vs top 30", grp: true, pct: true },
  { key: "top90", label: "Vs top 90", pct: true },
  { key: "third", label: "Vs 3rd string", pct: true },
  { key: "opp_off", label: "Opp offense", signed: true },
  { key: "lift", label: "Lift", grp: true, signed: true, shade: "lift" },
  { key: "spread", label: "Spread" },
  { key: "stability", label: "Stability", pct: true },
  { key: "better", label: "Mates better", frac: true },
];
const TIPS = {
  adj: "Points allowed per 100 with him on the floor, minus the strength of the offenses on the floor against him",
  off_adj: "The team's adjusted DRtg when he is off the floor",
  onoff: "Adj DRtg on minus off; negative = the defense was better with him",
  top30: "Share of his defensive possessions against a lineup with a top-30 scorer (points per game, 40+ games)",
  top90: "Share against a lineup with a top-90 scorer",
  third: "Share against third-string units: 3+ of the five ranked 11th or lower in possessions on their own team",
  opp_off: "How much better than league the offenses he faced were, per 100 (graded)",
  lift: "Average over teammates of: teammate's adj DRtg without him minus with him (150+ possessions each way)",
  spread: "How much that lift varies from teammate to teammate",
  stability: "|lift| ÷ (|lift| + spread)",
  better: "Teammates whose defense was better with him",
};

function useNotes(isAdmin, season) {
  const [notes, setNotes] = useState({});
  const [status, setStatus] = useState({});
  const timers = useRef({});
  useEffect(() => {
    if (!isAdmin || !season) return;
    fetch(`${API}/nba/admin/stats-notes?page=${PAGE}&season=${season}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : [])).then(rows => {
        const m = {};
        rows.forEach(r => { m[`${r.team}|${r.key}`] = r.body; });
        setNotes(m);
      }).catch(() => {});
  }, [isAdmin, season]);
  const save = useCallback((team, key, body) => {
    const id = `${team}|${key}`;
    setStatus(s => ({ ...s, [id]: "Saving…" }));
    fetch(`${API}/nba/admin/stats-notes`, {
      method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page: PAGE, season, team, key, body }),
    }).then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(() => setStatus(s => ({ ...s, [id]: `Saved ${new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}` })))
      .catch(() => setStatus(s => ({ ...s, [id]: "Not saved — type again to retry" })));
  }, [season]);
  const edit = useCallback((team, key, body) => {
    const id = `${team}|${key}`;
    setNotes(n => ({ ...n, [id]: body }));
    setStatus(s => ({ ...s, [id]: "Editing…" }));
    clearTimeout(timers.current[id]);
    timers.current[id] = setTimeout(() => save(team, key, body), 900);
  }, [save]);
  return { notes, status, edit };
}

function NoteBox({ label, team, k, notes }) {
  const id = `${team}|${k}`;
  return (
    <div className="df-note">
      <div className="df-note-head"><b>{label}</b><span>{notes.status[id] || ""}</span></div>
      <textarea value={notes.notes[id] || ""} onChange={e => notes.edit(team, k, e.target.value)} rows={7}
        placeholder="Your read: what he is, who carries whom, what the numbers miss" />
    </div>
  );
}

function PlayerPanel({ p, names, team, notes, isAdmin }) {
  if (!p) return null;
  return (
    <>
      <div className="rb-panel-head">
        <div className="rb-panel-name"><b>{names[p.pid]}</b><span>{team} · {Math.round(p.min).toLocaleString()} min · {p.poss.toLocaleString()} def poss</span></div>
        <div className="rb-panel-nums">
          <div><b>{f1(p.adj)}</b><span>adj DRtg</span></div>
          <div><b>{signed(p.onoff)}</b><span>on − off</span></div>
          <div><b>{p.stability == null ? "–" : pct(p.stability)}</b><span>stability</span></div>
        </div>
      </div>
      {isAdmin && <NoteBox label="Notes on him" team={team} k={String(p.pid)} notes={notes} />}
    </>
  );
}

function PairPanel({ a, b, pair, trios, names, team, notes, isAdmin }) {
  if (!pair) return null;
  const key = `${Math.min(a, b)}-${Math.max(a, b)}`;
  const [lo, hi] = a < b ? [a, b] : [b, a];
  return (
    <>
      <div className="rb-panel-head">
        <div className="rb-panel-name"><b>{last(names[lo])} + {last(names[hi])}</b><span>{team} · {Math.round(pair.min).toLocaleString()} min · {pair.poss.toLocaleString()} def poss</span></div>
        <div className="rb-panel-nums">
          <div><b>{f1(pair.adj)}</b><span>adj together</span></div>
          <div><b>{f1(pair.a_without[1])}</b><span>{last(names[lo])} without</span></div>
          <div><b>{f1(pair.b_without[1])}</b><span>{last(names[hi])} without</span></div>
        </div>
        <div className="df-sub">Raw {f1(pair.drtg)} together · {pair.a_without[0].toLocaleString()} and {pair.b_without[0].toLocaleString()} poss apart</div>
      </div>
      {isAdmin && <NoteBox label="Notes on the pair" team={team} k={key} notes={notes} />}
      <div className="df-trios">
        <h3>With a third man</h3>
        {!trios?.length ? <div className="rb-panel-empty">No third man with 25+ possessions.</div> : (
          <table className="df-trio-table">
            <thead><tr><th className="l">Third</th><th>Poss</th><th>Adj with</th><th>Pair without</th><th>Diff</th></tr></thead>
            <tbody>
              {trios.map(([c, n, adjw, , nwo, adjwo]) => (
                <tr key={c}>
                  <td className="l">{names[c]}</td>
                  <td>{n.toLocaleString()}</td>
                  <td>{f1(adjw)}</td>
                  <td>{f1(adjwo)} <i>{nwo.toLocaleString()}</i></td>
                  <td>{adjwo == null ? "–" : signed(adjw - adjwo)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

function Matrix({ title, roster, names, cell, shade, onPick, sel }) {
  return (
    <section className="rb-card df-matrix">
      <h2 className="df-h2">{title}</h2>
      <table>
        <thead>
          <tr><th />{roster.map(p => <th key={p.pid} title={names[p.pid]}>{last(names[p.pid])}</th>)}</tr>
        </thead>
        <tbody>
          {roster.map(r => (
            <tr key={r.pid}>
              <th className="l" title={names[r.pid]}>{names[r.pid]}</th>
              {roster.map(c => {
                const { text, value, pick } = cell(r, c);
                const st = shade ? shade(value) : undefined;
                const on = sel && ((sel[0] === r.pid && sel[1] === c.pid) || (sel[0] === c.pid && sel[1] === r.pid));
                return (
                  <td key={c.pid} className={`${r.pid === c.pid ? "diag" : ""}${pick ? " pick" : ""}${on ? " sel" : ""}${st ? " shaded" : ""}`}
                    style={st} onClick={pick ? () => onPick(r.pid, c.pid) : undefined}>{text}</td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export default function Defense() {
  const [data, setData] = useState(null);
  const [params, setParams] = useSearchParams();
  const [sort, setSort] = useState({ key: "adj", dir: 1 });
  const [sel, setSel] = useState(null);         // {kind: "player", pid} | {kind: "pair", a, b}
  const [mode, setMode] = useState("adj");
  const user = useCurrentUser();
  const isAdmin = !!user?.isAdmin;

  useEffect(() => {
    fetch(`${API}/nba/stats/defense`, { credentials: "include" }).then(r => r.json()).then(setData).catch(() => setData({ teams: {} }));
  }, []);

  const season = data?.meta?.season;
  const notes = useNotes(isAdmin, season);
  const teams = useMemo(() => Object.keys(data?.teams || {}).sort(), [data]);
  const team = params.get("team") && data?.teams?.[params.get("team")] ? params.get("team") : teams[0];
  const T = data?.teams?.[team];
  const names = data?.players || {};

  const roster = useMemo(() => (T?.players || []).map(p => ({ ...p, name: names[p.pid], onoff: p.off_adj == null ? null : p.adj - p.off_adj })), [T, names]);
  const rows = useMemo(() => {
    const k = sort.key;
    const val = r => (k === "better" ? (r.mates ? r.better / r.mates : null) : r[k]);
    return [...roster].sort((a, b) => {
      const x = val(a), y = val(b);
      if (typeof x === "string") return x.localeCompare(y) * sort.dir;
      return ((x ?? 1e9 * sort.dir) - (y ?? 1e9 * sort.dir)) * sort.dir;
    });
  }, [roster, sort]);

  // shading against every qualified player in the league (objective scale, not this team's min/max); lower DRtg = good
  const shades = useMemo(() => {
    const all = Object.values(data?.teams || {}).flatMap(t => t.players);
    const lg = data?.meta?.league ?? 0;
    const allPairs = Object.values(data?.teams || {}).flatMap(t => Object.values(t.pairs).filter(p => p.poss >= 150).map(p => lg - p[mode]));
    const rtg = makeShade(all.map(p => lg - p.adj));
    const onoff = makeShade(all.filter(p => p.off_adj != null).map(p => p.off_adj - p.adj));
    const lift = makeShade(all.filter(p => p.lift != null).map(p => p.lift));
    const pair = makeShade(allPairs);
    return { rtg: v => rtg(lg - v), onoff: v => onoff(-v), lift, pair: v => (v == null ? undefined : pair(lg - v)) };
  }, [data, mode]);

  const pickTeam = t => { setParams({ team: t }, { replace: true }); setSel(null); };
  const clickHeader = c => setSort(s => (s.key === c.key ? { key: c.key, dir: -s.dir } : { key: c.key, dir: c.str ? 1 : (["adj", "drtg", "off_adj", "onoff", "spread"].includes(c.key) ? 1 : -1) }));
  const pairOf = (a, b) => T?.pairs?.[`${Math.min(a, b)}-${Math.max(a, b)}`];
  const hasNote = k => !!(notes.notes[`${team}|${k}`] || "").trim();

  const drtgCell = (r, c) => {
    if (r.pid === c.pid) return { text: f1(r[mode]), value: r[mode] };
    const p = pairOf(r.pid, c.pid);
    if (!p || p.poss < 25) return { text: "·" };
    return { text: f1(p[mode]), value: p.poss >= 150 ? p[mode] : null, pick: true };
  };
  const minCell = (r, c) => {
    if (r.pid === c.pid) return { text: Math.round(r.min).toLocaleString() };
    const p = pairOf(r.pid, c.pid);
    if (!p) return { text: "·" };
    return { text: Math.round(p.min).toLocaleString(), pick: p.poss >= 25 };
  };
  const pickPair = (a, b) => setSel({ kind: "pair", a, b });
  const selPlayer = sel?.kind === "player" ? roster.find(p => p.pid === sel.pid) : null;

  return (
    <div className="site-ui stats-ui" style={{ minHeight: "100vh" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1640, boxSizing: "border-box", minWidth: 0 }}>
        <StatsNav />
        <div className="rb-head">
          <h1 className="rb-title">Defense</h1>
          <span className="rb-meta">{season || ""} · points allowed per 100 possessions · garbage time out</span>
        </div>
        <div className="df-teams" role="tablist" aria-label="Team">
          {teams.map(t => (
            <button key={t} role="tab" aria-selected={t === team} className={t === team ? "on" : ""} onClick={() => pickTeam(t)}>
              <TeamChip team={t} />
            </button>
          ))}
        </div>
        {data === null ? <p style={{ fontSize: 14 }}>Loading…</p> : !T ? <div className="rb-empty">No data.</div> : (
          <div className="rb-layout df-layout">
            <div className="df-main">
              <div className="df-teamline">
                <b>{team}</b> allowed <b>{f1(T.drtg)}</b> per 100 · adjusted for opponents <b>{f1(T.adj)}</b> · league {f1(data.meta.league)}
              </div>
              <section className="rb-card">
                <table className="rb-table df-table">
                  <thead>
                    <tr>
                      {COLS.map(c => (
                        <th key={c.key} title={TIPS[c.key]} className={`${c.left ? "l" : ""}${c.grp ? " g" : ""}${sort.key === c.key ? " on" : ""}`} onClick={() => clickHeader(c)}>{c.label}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map(r => (
                      <tr key={r.pid} className={sel?.kind === "player" && sel.pid === r.pid ? "sel" : ""} style={teamEdge(team)} onClick={() => setSel({ kind: "player", pid: r.pid })}>
                        {COLS.map(c => {
                          if (c.key === "name") return <td key="n" className="name l">{r.name}{isAdmin && hasNote(r.pid) && <span className="df-has-note" title="Has notes">✎</span>}</td>;
                          const v = c.key === "better" ? null : r[c.key];
                          const text = c.key === "better" ? (r.mates ? `${r.better} of ${r.mates}` : "–")
                            : c.int ? Math.round(v).toLocaleString() : c.pct ? pct(v) : c.signed || c.key === "onoff" ? signed(v) : f1(v);
                          const st = c.shade && v != null ? shades[c.shade](v) : undefined;
                          return <td key={c.key} className={`${c.grp ? "g " : ""}${c.big ? "big " : ""}${st ? "shaded" : ""}`} style={st}>{text}</td>;
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>

              <div className="rb-bar df-matrix-bar">
                <label>Pairs</label>
                <div className="rb-seg" role="radiogroup" aria-label="Pair DRtg">
                  {[{ v: "adj", l: "Adj DRtg" }, { v: "drtg", l: "Raw DRtg" }].map(o => (
                    <button key={o.v} role="radio" aria-checked={mode === o.v} onClick={() => setMode(o.v)}>{o.l}</button>
                  ))}
                </div>
              </div>
              <Matrix title={mode === "adj" ? "DRtg together, adjusted" : "DRtg together, raw"} roster={roster} names={names} cell={drtgCell}
                shade={shades.pair} onPick={pickPair} sel={sel?.kind === "pair" ? [sel.a, sel.b] : null} />
              <Matrix title="Minutes together" roster={roster} names={names} cell={minCell} onPick={pickPair} sel={sel?.kind === "pair" ? [sel.a, sel.b] : null} />
            </div>
            <aside className="rb-panel df-panel">
              {!sel ? <div className="rb-panel-empty">Click a player, or a pair in the matrices.</div>
                : sel.kind === "player" ? <PlayerPanel p={selPlayer} names={names} team={team} notes={notes} isAdmin={isAdmin} />
                  : <PairPanel a={sel.a} b={sel.b} pair={pairOf(sel.a, sel.b)} trios={T.trios[`${Math.min(sel.a, sel.b)}-${Math.max(sel.a, sel.b)}`]}
                    names={names} team={team} notes={notes} isAdmin={isAdmin} />}
            </aside>
          </div>
        )}
      </div>
    </div>
  );
}
