import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import "./Shooting.css";

// Shooting scoreboard: who adds the most and the fewest points over what the league scores from the same
// shots (nba-pipeline shot value v7: nine distance zones x five shot families). Data: GET /nba/stats/shot-value,
// a static file rebuilt by hand when the model is re-run.
const SEASONS = ["2025-26", "2024-25"];
const MINS = [100, 300, 600];
const N = 25;

function Seg({ label, value, options, onChange, fmt = v => v }) {
  return (
    <>
      <label>{label}</label>
      <div className="sh-seg" role="radiogroup" aria-label={label}>
        {options.map(o => (
          <button key={o} role="radio" aria-checked={o === value} onClick={() => onChange(o)}>{fmt(o)}</button>
        ))}
      </div>
    </>
  );
}

function Board({ title, rows, kind }) {
  return (
    <section className="sh-card">
      <h2>{title}</h2>
      {rows.length === 0 ? <div className="sh-empty">No players at this minimum.</div> : (
        <table className="sh-table">
          <thead>
            <tr>
              <th className="l">#</th><th className="l">Player</th><th className="l">Team</th>
              <th title="Field-goal attempts">FGA</th><th title="Share of attempts that were threes">3PA%</th>
              <th title="Points the league scores per shot from his shot profile">Exp/shot</th><th title="His points per shot">Pts/shot</th>
              <th title="Points above or below what the league scores from the same shots">Added</th><th title="Per 100 attempts">/100</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.pid} className={i < 3 ? kind : ""}>
                <td className="rk l">{i + 1}</td>
                <td className="name l"><Link to={`/fantasy/2026_27/players/${r.pid}`}>{r.name}</Link></td>
                <td className="team">{r.team}</td>
                <td>{r.shots.toLocaleString()}</td>
                <td>{Math.round(100 * r.shots3 / r.shots)}%</td>
                <td>{r.exp_per_shot.toFixed(2)}</td>
                <td>{r.pps.toFixed(2)}</td>
                <td className={`added${r.added < 0 ? " neg" : ""}`}>{r.added > 0 ? "+" : r.added < 0 ? "−" : ""}{Math.abs(r.added).toFixed(0)}</td>
                <td className={r.per100 < 0 ? "neg" : ""}>{r.per100 > 0 ? "+" : r.per100 < 0 ? "−" : ""}{Math.abs(r.per100).toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

export default function Shooting() {
  const [data, setData] = useState(null);
  const [season, setSeason] = useState(SEASONS[0]);
  const [min, setMin] = useState(MINS[1]);

  useEffect(() => {
    fetch(`${API}/nba/stats/shot-value`, { credentials: "include" }).then(r => r.json()).then(setData).catch(() => setData({ seasons: {} }));
  }, []);

  const rows = useMemo(() => (data?.seasons?.[season] || []).filter(r => r.shots >= min), [data, season, min]);
  const best = useMemo(() => [...rows].sort((a, b) => b.added - a.added).slice(0, N), [rows]);
  const worst = useMemo(() => [...rows].sort((a, b) => a.added - b.added).slice(0, N), [rows]);

  return (
    <div className="site-ui" style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1240, boxSizing: "border-box", minWidth: 0 }}>
        <div className="sh-head">
          <h1 className="sh-title">Shooting</h1>
          <span className="sh-meta">{season} · points added over the league from the same shots</span>
        </div>
        <div className="sh-bar">
          <Seg label="Season" value={season} options={SEASONS} onChange={setSeason} />
          <Seg label="Min attempts" value={min} options={MINS} onChange={setMin} />
        </div>
        {data === null ? <p style={{ fontSize: 14 }}>Loading…</p> : (
          <div className="sh-boards">
            <Board title="Best shot-makers" rows={best} kind="top" />
            <Board title="Worst shot-makers" rows={worst} kind="bottom" />
          </div>
        )}
      </div>
    </div>
  );
}
