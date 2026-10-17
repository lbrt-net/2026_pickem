import { useEffect, useMemo, useState } from "react";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import StatsNav from "./StatsNav";
import { TableFilter, Pager, TeamChip } from "./StatsControls";
import { makeShade } from "./shade";
import { matches } from "./statsMatch";
import "./Rebounding.css";
import "./Lineups.css";

// Lineups: net rating of every 1-, 2-, 3- and 5-man group with enough possessions together (raw, unadjusted: who
// shared the floor and what happened). 25 a page, sortable, team filter. Data: GET /nba/stats/lineups, from
// nba-pipeline/models/lineups.py. Rows are keyed on player ids. Stats never link into fantasy.
const PAGE = 25;
const SIZES = [{ v: "1", l: "1-man" }, { v: "2", l: "2-man" }, { v: "3", l: "3-man" }, { v: "5", l: "5-man" }];

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

const signed = v => (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(1);

export default function Lineups() {
  const [data, setData] = useState(null);
  const [size, setSize] = useState("2");

  const [sort, setSort] = useState({ key: "net", dir: -1 });
  const [page, setPage] = useState(0);
  const [query, setQuery] = useState("");
  const [team, setTeam] = useState("");

  useEffect(() => {
    fetch(`${API}/nba/stats/lineups`, { credentials: "include" }).then(r => r.json()).then(setData).catch(() => setData({ groups: {} }));
  }, []);

  const cols = useMemo(() => [
    { key: "names", label: size === "1" ? "Player" : "Players", left: true, str: true },
    { key: "team", label: "Team", left: true, str: true },
    { key: "poss", label: "Poss" },
    { key: "ortg", label: "Off /100" },
    { key: "drtg", label: "Def /100" },
    { key: "net", label: "Net /100", big: true },
    ...(size === "1" ? [{ key: "on_off", label: "On − off" }] : []),
  ], [size]);

  const rows = useMemo(() => {
    const list = (data?.groups?.[size] || []).filter(r => (!team || r.team === team) && matches(r.names, query));
    const k = sort.key;
    const val = r => (k === "names" ? r.names.join(" ") : r[k]);
    return [...list].sort((a, b) => (typeof val(a) === "string" ? val(a).localeCompare(val(b)) : (val(a) ?? -1e9) - (val(b) ?? -1e9)) * sort.dir);
  }, [data, size, team, sort, query]);

  const teams = useMemo(() => [...new Set((data?.groups?.["1"] || []).map(r => r.team))].filter(Boolean).sort(), [data]);
  const shadeNet = useMemo(() => makeShade((data?.groups?.[size] || []).map(r => r.net)), [data, size]);
  const shadeOn = useMemo(() => makeShade((data?.groups?.["1"] || []).map(r => r.on_off)), [data]);
  const pages = Math.max(1, Math.ceil(rows.length / PAGE));
  const pg = Math.min(page, pages - 1);
  const slice = rows.slice(pg * PAGE, pg * PAGE + PAGE);
  const minPoss = data?.meta?.min_poss?.[size];

  function clickHeader(c) {
    setPage(0);
    setSort(s => s.key === c.key ? { key: c.key, dir: -s.dir } : { key: c.key, dir: c.str ? 1 : -1 });
  }

  return (
    <div className="site-ui stats-ui" style={{ minHeight: "100vh" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1200, boxSizing: "border-box", minWidth: 0 }}>
        <StatsNav />
        <div className="rb-head">
          <h1 className="rb-title">Lineups</h1>
          <span className="rb-meta">{data?.meta?.season || ""} · net per 100 possessions together{minPoss ? ` · ${minPoss.toLocaleString()}+ possessions` : ""}</span>
        </div>
        <div className="rb-bar">
          <Seg label="Group" value={size} options={SIZES} onChange={v => { setSize(v); setPage(0); }} />
          <TableFilter query={query} setQuery={q => { setQuery(q); setPage(0); }} team={team} setTeam={t => { setTeam(t); setPage(0); }} teams={teams} />
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
                  {slice.map((r, i) => {
                    const rank = pg * PAGE + i;
                    const top = sort.key === "net" && pg === 0 && i < 3;
                    return (
                      <tr key={r.ids.join("-")} className={top ? (sort.dir < 0 ? "top" : "bottom") : ""} style={{ cursor: "default" }}>
                        <td className="rk l">{rank + 1}</td>
                        <td className="name l ln-names">{r.names.join(" · ")}</td>
                        <td className="team l"><TeamChip team={r.team} /></td>
                        <td>{r.poss.toLocaleString()}</td>
                        <td>{r.ortg.toFixed(1)}</td>
                        <td>{r.drtg.toFixed(1)}</td>
                        <td className={`big ${shadeNet(r.net) ? "shaded" : ""}`} style={shadeNet(r.net)}>{signed(r.net)}</td>
                        {size === "1" && <td className={shadeOn(r.on_off) ? "shaded" : ""} style={shadeOn(r.on_off)}>{signed(r.on_off)}</td>}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
            <Pager page={pg} pages={pages} total={rows.length} size={PAGE} setPage={setPage} />
          </section>
        )}
      </div>
    </div>
  );
}
