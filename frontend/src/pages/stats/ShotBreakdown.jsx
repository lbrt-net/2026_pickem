import { useEffect, useMemo, useState } from "react";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import StatsNav, { ShootingTabs } from "./StatsNav";
import { TableFilter, TeamChip } from "./StatsControls";
import { teamEdge } from "./teamEdge";
import { makeShade } from "./shade";
import { matches } from "./statsMatch";
import "./Rebounding.css";
import "./ShotBreakdown.css";

// Shooting → By zone, type and situation: a top 10 per category — points over what the league scores from the same
// shot (zone × type × situation × shot clock). "Model pieces": who gains and loses when each piece is added to the
// model. Data: GET /nba/stats/shot-breakdown (nba-pipeline/models/export_breakdown.py), keyed on player ids.
const TOP = 10;
const signed = (v, d = 1) => (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(d);

function Seg({ label, value, options, onChange }) {
  return (
    <>
      {label && <label>{label}</label>}
      <div className="rb-seg" role="radiogroup" aria-label={label || "view"}>
        {options.map(o => <button key={o.v} role="radio" aria-checked={o.v === value} onClick={() => onChange(o.v)}>{o.l}</button>)}
      </div>
    </>
  );
}

function CatCard({ title, league, rows, players, shade }) {
  return (
    <section className="sb-card">
      <header><h2>{title}</h2>{league && <span>{(100 * league.fg).toFixed(1)}% · {league.pps.toFixed(2)} pts/shot</span>}</header>
      <table>
        <colgroup><col className="c-rk" /><col /><col className="c-sh" /><col className="c-fg" /><col className="c-ad" /></colgroup>
        <thead><tr><th /><th className="l">Player</th><th>Shots</th><th>FG% <i>exp</i> · act</th><th>Added</th></tr></thead>
        <tbody>
          {rows.length === 0 && <tr><td className="sb-none">No one</td></tr>}
          {rows.map((r, i) => (
            <tr key={r.pid} style={teamEdge(players[r.pid]?.team)}>
              <td className="sb-rk">{i + 1}</td>
              <td className="sb-name"><TeamChip team={players[r.pid]?.team} bare /> {players[r.pid]?.name}</td>
              <td className="sb-num">{r.shots}</td>
              <td className="sb-num"><i>{(100 * r.xfg).toFixed(0)}%</i> {(100 * r.fg).toFixed(0)}%</td>
              <td className={`sb-big ${shade(r.added) ? "shaded" : ""}`} style={shade(r.added)}>{signed(r.added, 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function CompCard({ title, desc, rows, players, shade }) {
  return (
    <section className="sb-card">
      <header><h2>{title}</h2><span>{desc}</span></header>
      <table>
        <colgroup><col className="c-rk" /><col /><col className="c-ba" /><col className="c-ch" /></colgroup>
        <thead><tr><th /><th className="l">Player</th><th><i>before</i> → after</th><th>Change</th></tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.pid} style={teamEdge(players[r.pid]?.team)}>
              <td className="sb-rk">{i + 1}</td>
              <td className="sb-name"><TeamChip team={players[r.pid]?.team} bare /> {players[r.pid]?.name}</td>
              <td className="sb-num"><i>{signed(r.before, 0)}</i> → {signed(r.after, 0)}</td>
              <td className={`sb-big ${shade(r.change) ? "shaded" : ""}`} style={shade(r.change)}>{signed(r.change, 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export default function ShotBreakdown() {
  const [data, setData] = useState(null);
  const [dim, setDim] = useState("zone");
  const [end, setEnd] = useState("best");
  const [query, setQuery] = useState("");
  const [team, setTeam] = useState("");

  useEffect(() => {
    fetch(`${API}/nba/stats/shot-breakdown`, { credentials: "include" }).then(r => r.json()).then(setData).catch(() => setData({}));
  }, []);

  const players = useMemo(() => data?.players || {}, [data]);
  const teams = useMemo(() => [...new Set(Object.values(players).map(p => p.team).filter(Boolean))].sort(), [players]);
  const keep = r => matches(players[r.pid]?.name, query) && (!team || players[r.pid]?.team === team);
  const worst = end === "worst";

  const splits = data?.by_category ? [...Object.entries(data.by_category).map(([k, d]) => ({ v: k, l: d.label })), { v: "pieces", l: "Model pieces" }] : [];
  let cards = null;
  if (data?.by_category && dim !== "pieces") {
    const d = data.by_category[dim];
    cards = d.order.map(c => {
      const list = (d.categories[c]?.players || []).filter(keep);
      const rows = (worst ? [...list].reverse() : list).slice(0, TOP);
      const shade = makeShade((d.categories[c]?.players || []).map(r => r.added));
      return <CatCard key={c} title={c} league={d.categories[c]?.league} rows={rows} players={players} shade={shade} />;
    });
  } else if (data?.by_component) {
    cards = Object.entries(data.by_component).map(([k, c]) => {
      const list = c.players.filter(keep);
      const rows = (worst ? [...list].reverse() : list).slice(0, TOP);
      const shade = makeShade(c.players.map(r => r.change));
      return <CompCard key={k} title={c.label} desc={c.desc} rows={rows} players={players} shade={shade} />;
    });
  }

  return (
    <div className="site-ui stats-ui" style={{ minHeight: "100vh" }}>
      <MainNav />
      <div className="sb-page">
        <StatsNav />
        <div className="rb-head">
          <h1 className="rb-title">Shooting</h1>
          <span className="rb-meta">{data?.meta?.season || ""} · top {data?.meta?.top || 300} shot-takers</span>
        </div>
        <ShootingTabs />
        <div className="rb-bar">
          <Seg value={dim} options={splits} onChange={setDim} />
          <Seg value={end} options={[{ v: "best", l: "Best" }, { v: "worst", l: "Worst" }]} onChange={setEnd} />
          <TableFilter query={query} setQuery={setQuery} team={team} setTeam={setTeam} teams={teams} />
        </div>
        {data === null ? <p>Loading…</p> : <div className="sb-grid">{cards}</div>}
      </div>
    </div>
  );
}
