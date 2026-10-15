import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import "./Shooting.css";

// Shooting: the 300 biggest shot-takers this season, scored against what the league makes from the same shots
// (nba-pipeline shot value v7: nine distance zones x five shot families). Per 75 possessions on the floor
// (team possessions from the play-by-play x his share of his team's minutes that game). Data: GET /nba/stats/shot-value,
// a static file rebuilt by hand when the model is re-run.
const COLS = [
  { key: "name", label: "Player", left: true },
  { key: "team", label: "Team", left: true },
  { key: "minutes", label: "Min" },
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

function Cell({ col, r }) {
  if (col.key === "name") return <td className="name l"><Link to={`/fantasy/2026_27/players/${r.pid}`}>{r.name}</Link></td>;
  if (col.key === "team") return <td className="team l">{r.team}</td>;
  if (col.key === "minutes") return <td>{r.minutes == null ? "—" : r.minutes.toLocaleString()}</td>;
  if (col.key === "fga75") return <td>{r.fga75.toFixed(1)}</td>;
  if (col.key === "diet") {
    const title = DIET.map((n, i) => `${n} ${Math.round(100 * r.diet[i])}%`).join(" · ");
    return <td className="l"><span className="sh-diet" title={title}>{r.diet.map((w, i) => <i key={i} className={`d${i}`} style={{ width: `${100 * w}%` }} />)}</span></td>;
  }
  const v = r[col.key]; const neg = v < 0;
  const text = col.key === "added" ? signed(v, 0) : col.key === "added75" ? signed(v, 2) : v.toFixed(2);
  return (
    <td className={`${col.big ? "big " : ""}${neg ? "neg" : ""}`}>
      {col.pct ? <span className="sh-v">{text}<small>{ordinal(r[col.pct])}</small></span> : text}
    </td>
  );
}

function ordinal(n) {
  const s = ["th", "st", "nd", "rd"], v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]) + " pct";
}

export default function Shooting() {
  const [data, setData] = useState(null);
  const [sort, setSort] = useState({ key: "added75", dir: -1 });
  const [end, setEnd] = useState("best");

  useEffect(() => {
    fetch(`${API}/nba/stats/shot-value`, { credentials: "include" }).then(r => r.json()).then(setData).catch(() => setData({ players: [] }));
  }, []);

  const rows = useMemo(() => {
    const list = [...(data?.players || [])];
    const k = sort.key, d = sort.dir * (end === "best" ? 1 : -1);
    list.sort((a, b) => (typeof a[k] === "string" ? a[k].localeCompare(b[k]) : (a[k] ?? -1e9) - (b[k] ?? -1e9)) * d);
    return list;
  }, [data, sort, end]);

  function clickHeader(col) {
    if (col.nosort) return;
    setSort(s => s.key === col.key ? { key: col.key, dir: -s.dir } : { key: col.key, dir: typeof (data?.players?.[0]?.[col.key]) === "string" ? 1 : -1 });
  }

  return (
    <div className="site-ui" style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1240, boxSizing: "border-box", minWidth: 0 }}>
        <div className="sh-head">
          <h1 className="sh-title">Shooting</h1>
          <span className="sh-meta">{data?.meta?.season || ""} · top 300 by attempts · points over what the league makes from the same shots, per 75 possessions</span>
        </div>
        <div className="sh-bar">
          <Seg label="Show" value={end} options={[{ v: "best", l: "Best first" }, { v: "worst", l: "Worst first" }]} onChange={setEnd} />
          <span className="sh-key"><i className="d0" style={{ background: "var(--accent)" }} />rim<i className="d1" style={{ background: "color-mix(in srgb, var(--text) 75%, transparent)" }} />3–8 ft<i className="d2" style={{ background: "color-mix(in srgb, var(--text) 50%, transparent)" }} />8–16<i className="d3" style={{ background: "color-mix(in srgb, var(--text) 28%, transparent)" }} />long two<i className="d4" style={{ background: "var(--accent-blue)" }} />three</span>
        </div>
        {data === null ? <p style={{ fontSize: 14 }}>Loading…</p> : (
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
                  {rows.map((r, i) => (
                    <tr key={r.pid} className={i < 3 ? (end === "best" ? "top" : "bottom") : ""}>
                      <td className="rk l">{i + 1}</td>
                      {COLS.map(c => <Cell key={c.key} col={c} r={r} />)}
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
