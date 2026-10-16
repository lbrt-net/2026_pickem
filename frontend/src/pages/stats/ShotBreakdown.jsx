import { useEffect, useMemo, useState } from "react";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import StatsNav from "./StatsNav";
import "./Rebounding.css";
import "./Lineups.css";

// Shot breakdown: who gains or loses in each piece of the shot model. "By category": inside one distance zone, shot
// type, situation or shot-clock range, each player's points over what the league scores from the same shots.
// "By model piece": what adding shot type, situation and shot clock to the model did to each player's points added.
// Data: GET /nba/stats/shot-breakdown (nba-pipeline/models/export_breakdown.py). Keyed on player ids.
const PAGE = 25;
const signed = (v, d = 1) => (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(d);

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

const CAT_COLS = [
  { key: "name", label: "Player", left: true, str: true },
  { key: "team", label: "Team", left: true, str: true },
  { key: "shots", label: "Shots" },
  { key: "share", label: "Share of his shots", pct: true },
  { key: "xfg", label: "Expected FG%", pct: true, exp: true },
  { key: "fg", label: "FG%", pct: true },
  { key: "added", label: "Points added", signed: true, big: true },
  { key: "per100", label: "Per 100 shots", signed: true },
];
const COMP_COLS = [
  { key: "name", label: "Player", left: true, str: true },
  { key: "team", label: "Team", left: true, str: true },
  { key: "shots", label: "Shots" },
  { key: "before", label: "Points added before", signed: true, exp: true },
  { key: "after", label: "After", signed: true },
  { key: "change", label: "Change", signed: true, big: true },
  { key: "per100", label: "Change per 100 shots", signed: true, d: 2 },
];

export default function ShotBreakdown() {
  const [data, setData] = useState(null);
  const [view, setView] = useState("category");
  const [dim, setDim] = useState("zone");
  const [cat, setCat] = useState(null);
  const [comp, setComp] = useState("clock");
  const [sort, setSort] = useState({ key: "added", dir: -1 });
  const [page, setPage] = useState(0);

  useEffect(() => {
    fetch(`${API}/nba/stats/shot-breakdown`, { credentials: "include" }).then(r => r.json()).then(setData).catch(() => setData({}));
  }, []);

  const dimObj = data?.by_category?.[dim];
  const curCat = cat && dimObj?.order?.includes(cat) ? cat : dimObj?.order?.[0];
  const cols = view === "category" ? CAT_COLS : COMP_COLS;
  const players = useMemo(() => data?.players || {}, [data]);

  const rows = useMemo(() => {
    const src = view === "category" ? (dimObj?.categories?.[curCat]?.players || []) : (data?.by_component?.[comp]?.players || []);
    const list = src.map(r => ({ ...r, name: players[r.pid]?.name || String(r.pid), team: players[r.pid]?.team || "" }));
    const k = cols.some(c => c.key === sort.key) ? sort.key : (view === "category" ? "added" : "change");
    return list.sort((a, b) => (typeof a[k] === "string" ? a[k].localeCompare(b[k]) : a[k] - b[k]) * sort.dir);
  }, [data, view, dimObj, curCat, comp, sort, cols, players]);

  const pages = Math.max(1, Math.ceil(rows.length / PAGE));
  const pg = Math.min(page, pages - 1);
  const slice = rows.slice(pg * PAGE, pg * PAGE + PAGE);
  const league = view === "category" ? dimObj?.categories?.[curCat]?.league : null;

  function clickHeader(c) {
    setPage(0);
    setSort(s => s.key === c.key ? { key: c.key, dir: -s.dir } : { key: c.key, dir: c.str ? 1 : -1 });
  }
  const fmt = (c, v) => c.pct ? `${(100 * v).toFixed(1)}%` : c.signed ? signed(v, c.d || 1) : typeof v === "number" ? v.toLocaleString() : v;

  return (
    <div className="site-ui" style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1200, boxSizing: "border-box", minWidth: 0 }}>
        <StatsNav />
        <div className="rb-head">
          <h1 className="rb-title">Shot breakdown</h1>
          <span className="rb-meta">{data?.meta?.season || ""} · top {data?.meta?.top || 300} shot-takers · points over what the league scores from the same shot (distance × type × situation × shot clock) · <i className="rb-model">blue</i> = the model's number</span>
        </div>
        <div className="rb-bar">
          <Seg label="View" value={view} options={[{ v: "category", l: "By category" }, { v: "component", l: "By model piece" }]}
               onChange={v => { setView(v); setPage(0); setSort({ key: v === "category" ? "added" : "change", dir: -1 }); }} />
          {view === "category" && dimObj && <Seg label="Split" value={dim} options={Object.entries(data.by_category).map(([k, d]) => ({ v: k, l: d.label }))} onChange={v => { setDim(v); setCat(null); setPage(0); }} />}
          {view === "component" && data?.by_component && <Seg label="Piece" value={comp} options={Object.entries(data.by_component).map(([k, d]) => ({ v: k, l: d.label }))} onChange={v => { setComp(v); setPage(0); }} />}
        </div>
        {view === "category" && dimObj && (
          <div className="rb-bar">
            <Seg label={dimObj.label} value={curCat} options={dimObj.order.map(c => ({ v: c, l: c }))} onChange={v => { setCat(v); setPage(0); }} />
            {league && <span className="rb-meta">league: {league.shots.toLocaleString()} shots · {(100 * league.fg).toFixed(1)}% · {league.pps.toFixed(2)} pts/shot · players with {data.meta.min_cat}+ shots here</span>}
          </div>
        )}
        {view === "component" && data?.by_component?.[comp] && (
          <div className="rb-bar"><span className="rb-meta">{data.by_component[comp].desc} · positive = his shots were harder than the model without this piece said, so he gets credit back</span></div>
        )}
        <div className="rb-bar">
          <div className="rb-pages" style={{ marginLeft: 0 }}>
            <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={pg === 0}>‹</button>
            <span>{rows.length ? `${pg * PAGE + 1}–${Math.min(rows.length, (pg + 1) * PAGE)} of ${rows.length}` : "0"}</span>
            <button onClick={() => setPage(p => Math.min(pages - 1, p + 1))} disabled={pg >= pages - 1}>›</button>
          </div>
        </div>
        {data === null ? <p style={{ fontSize: 14 }}>Loading…</p> : (
          <section className="rb-card">
            {rows.length === 0 ? <div className="rb-empty">No data.</div> : (
              <table className="rb-table ln-table">
                <thead>
                  <tr>
                    <th className="l">#</th>
                    {cols.map(c => <th key={c.key} className={`${c.left ? "l" : ""}${sort.key === c.key ? " on" : ""}`} onClick={() => clickHeader(c)}>{c.label}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {slice.map((r, i) => (
                    <tr key={r.pid} style={{ cursor: "default" }}>
                      <td className="rk l">{pg * PAGE + i + 1}</td>
                      {cols.map(c => (
                        <td key={c.key} className={`${c.left ? "l " : ""}${c.key === "name" ? "name " : ""}${c.key === "team" ? "team " : ""}${c.exp ? "exp " : ""}${c.big ? "big " : ""}${c.signed && r[c.key] < 0 ? "neg" : ""}`}>{fmt(c, r[c.key])}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
