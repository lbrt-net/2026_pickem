import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { Headshot } from "../../components/fantasy/RosterBits";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { ctDateTime, ctMonthDay } from "../../components/fantasy/format";

// the viewer's calendar day of a timestamp, "2026-10-30" (what a date input holds; same clock as the When column)
const ctDay = v => new Date(v).toLocaleDateString("en-CA");
import "../../components/fantasy/injuries.css";

// Injury Updates (Transactions tab, 2026-10-30): every change to the injury report for pool players (newly listed,
// status changed, return date moved, cleared), newest first by fantasy week, with the fantasy team that has him now.
// The dot on the headshot is his status NOW; the Change cell is shaded by where he ended up (green = healthy, red =
// Out / out for season / suspended, yellow = Day-To-Day). Only the ones that matter by default: 20+ AVG, players at 15+ MPG this
// season (in 20%+ of his team's games) OR over the 2 seasons before (a rookie who plays now is in; so is a regular
// who's missing now; a one-game call-up isn't). MPG / AVG show this season, or his projection (italic) when he hasn't
// played this season. Missed so far = team games he's sat since the report (a running count, grows as games go final); Total
// out = the whole stint: games he sat in a row before the report + missed so far + games still to come before his
// return date while he's Out (italic when it includes that estimate).

const PAGE_ROWS = 25;
const RED = new Set(["Out", "Out For Season", "Suspension"]);
const dotOf = st => (!st ? null : RED.has(st) ? "out" : "dtd");
const sevOf = e => new Set([e.status, e.prev_status].filter(Boolean).map(x => (RED.has(x) ? "red" : "yellow")));
const regular = e => e.gp_now > 0 && e.gp_now >= 0.2 * e.team_games;
// a floor passes on this season's number (once he's played 20%+ of his team's games) or the 2 seasons before's
const passes = (e, k, min) => !(Number(min) > 0) || [regular(e) ? e[`${k}_now`] : null, e[`${k}2`]].some(v => v != null && v >= Number(min));
const SEV = [["all", "All"], ["red", <span key="r" className="hf-dots" title="Out"><i className="out" /></span>],
  ["yellow", <span key="y" className="hf-dots" title="Day-to-day"><i className="dtd" /></span>]];

function Seg({ options, value, onChange, label }) {
  return (
    <span className="dr-seg" role="radiogroup" aria-label={label}>
      {options.map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={value === k} onClick={() => onChange(k)}>{l}</button>)}
    </span>
  );
}

// The Change cell's background is where he ended up: green = healthy again, red = Out (or out for season /
// suspended), yellow = Day-To-Day. Same status, return date moved (Out → Out): red when it moved later, green when
// sooner, plain when a date was added or dropped. The dot on the headshot is his status now.
const changeTone = e => (e.kind === "cleared" ? "ok"
  : e.kind === "return" ? (e.prev_return && e.return_date ? (e.return_date > e.prev_return ? "out" : "ok") : "")
    : dotOf(e.status) || "");
function Change({ e }) {
  if (e.kind === "cleared") return <>{e.prev_status} → Healthy</>;
  if (e.kind === "status") return <>{e.prev_status} → {e.status}</>;
  if (e.kind === "return") return <>{e.status} → {e.status}</>;
  return <>Healthy → {e.status}</>;  // newly listed
}

const num = (v, italic) => (v == null ? "—" : italic ? <i>{v.toFixed(1)}</i> : v.toFixed(1));

export default function InjuryUpdates({ log, teams, teamById }) {
  const [team, setTeam] = useState("");
  const [page, setPage] = useState(0);
  const [sev, setSev] = useState("all");
  const [minMpg, setMinMpg] = useState("15");
  const [minAvg, setMinAvg] = useState("20");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [params, setParams] = useSearchParams();
  const player = params.get("player") || "";
  const set = f => v => { f(v); setPage(0); };

  const all = log?.injuries || [];
  const rows = all.filter(e => (!team || e.team_id === team) && (!from || ctDay(e.at) >= from) && (!to || ctDay(e.at) <= to) && (!player || e.player.id === player) && (player || (
    (sev === "all" || sevOf(e).has(sev))
    && passes(e, "mpg", minMpg) && passes(e, "avg", minAvg))));
  const weekInfo = Object.fromEntries((log?.weeks || []).map(w => [w.week, w]));
  const pages = Math.max(1, Math.ceil(rows.length / PAGE_ROWS));
  const at = Math.min(page, pages - 1);
  const pageRows = rows.slice(at * PAGE_ROWS, (at + 1) * PAGE_ROWS);
  const playerName = player ? (all.find(e => e.player.id === player)?.player.name || "this player") : null;

  return (
    <section className="dr-panel tx-panel" aria-label="Injury updates">
      <div className="tx-tools">
        <select className="tx-team" value={team} onChange={e => set(setTeam)(e.target.value)} aria-label="Team">
          <option value="">All teams</option>
          {(teams || []).map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <Seg label="Status" options={SEV} value={sev} onChange={set(setSev)} />
        <label className="tx-f">MPG ≥ <input type="number" min="0" step="1" value={minMpg} onChange={e => set(setMinMpg)(e.target.value)} /></label>
        <label className="tx-f">AVG ≥ <input type="number" min="0" step="1" value={minAvg} onChange={e => set(setMinAvg)(e.target.value)} /></label>
        <label className="tx-f">From <input className="tx-date" type="date" value={from} max={to || undefined} onChange={e => set(setFrom)(e.target.value)} /></label>
        <label className="tx-f">To <input className="tx-date" type="date" value={to} min={from || undefined} onChange={e => set(setTo)(e.target.value)} /></label>
        {player && (
          <button type="button" className="tx-player" onClick={() => { setParams({}); setPage(0); }} aria-label="Show all players">
            {playerName} <span aria-hidden="true">✕</span>
          </button>
        )}
      </div>

      {log === undefined && <p className="tx-msg">Loading…</p>}
      {log && rows.length === 0 && <p className="tx-msg">{all.length ? "No injury updates match these filters." : "No injury updates yet. They're logged from 10/30 on."}</p>}
      {rows.length > 0 && (
        <div className="dr-scroll">
          <table className="dr-table iu-table">
            <thead>
              <tr>
                <th>When</th><th>Team</th><th>Player</th><th>Change</th><th>Injury</th><th>Return</th>
                <th className="num">Missed so far</th><th className="num">Total out</th><th className="num">MPG</th><th className="num">AVG</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map((e, i) => {
                const t = teamById[e.team_id];
                const wk = e.week ?? "pre";
                const head = i === 0 || (pageRows[i - 1].week ?? "pre") !== wk;
                const proj = !(e.gp_now > 0);
                return [
                  head && (
                    <tr key={`w${wk}-${e.id}`} className="iu-week"><td colSpan={10}>
                      <b>{e.week ? (e.week_label || `Week ${e.week}`) : "Before the season"}</b>
                      {e.week && weekInfo[e.week] && <span>{ctMonthDay(weekInfo[e.week].start)} – {ctMonthDay(weekInfo[e.week].end)}</span>}
                    </td></tr>
                  ),
                  <tr key={e.id}>
                    <td className="iu-when">{ctDateTime(e.at)}</td>
                    <td className="iu-team" style={t?.color ? { "--tc": t.color } : undefined}>
                      <span className="iu-tm">{t ? <><TeamIcon team={t} size={28} /><TeamLink ownerId={t.owner_user_id} name={t.abbreviation || e.team_name} style={{ color: "inherit", textDecoration: "none", fontWeight: 600 }} /></> : "FA"}</span>
                    </td>
                    <td className="iu-player"><span className="iu-pl">
                      <span className="iu-hs"><Headshot playerId={e.player.id} tricode={e.player.nba_team} width={48} height={52} />
                        {dotOf(e.current) && <span className={`inj-dot ${dotOf(e.current)}`} title={e.current} aria-label={`Now: ${e.current}`} />}</span>
                      <span className="iu-name"><EntityLink id={e.player.id} name={e.player.name} style={{ color: "inherit", textDecoration: "none" }} />
                        <small>{[e.player.position, e.player.nba_team].filter(Boolean).join(" · ")}</small></span>
                    </span></td>
                    <td className={`iu-change ${changeTone(e)}`}><Change e={e} /></td>
                    <td className="iu-injury" title={e.comment || undefined}>{e.injury || "—"}</td>
                    <td className="iu-ret">{e.return_date ? ctMonthDay(e.return_date) : e.kind === "cleared" ? "" : "—"}
                      {e.prev_return && e.prev_return !== e.return_date && e.kind !== "cleared" && <small> (was {ctMonthDay(e.prev_return)})</small>}</td>
                    <td className="num">{e.kind === "cleared" ? "—" : e.sat_since || "—"}</td>
                    <td className="num">{(() => {
                      const n = (e.missed || 0) + (e.sat_since || 0) + (e.will_miss || 0);
                      return !n ? "—" : e.will_miss ? <i>{n}</i> : n;
                    })()}</td>
                    <td className="num">{num(proj ? e.proj_mpg : e.mpg_now, proj)}</td>
                    <td className="num">{num(proj ? e.proj_avg : e.avg_now, proj)}</td>
                  </tr>,
                ];
              })}
            </tbody>
          </table>
        </div>
      )}

      {rows.length > PAGE_ROWS && (
        <div className="dr-pager">
          <span>{at * PAGE_ROWS + 1}–{Math.min(rows.length, (at + 1) * PAGE_ROWS)} of {rows.length}</span>
          <span className="dr-pager-btns">
            <button type="button" className="dr-btn small" disabled={at === 0} onClick={() => setPage(0)} aria-label="First page">«</button>
            <button type="button" className="dr-btn small" disabled={at === 0} onClick={() => setPage(at - 1)}>‹ Prev</button>
            <span className="dr-pager-at">Page {at + 1} of {pages}</span>
            <button type="button" className="dr-btn small" disabled={at >= pages - 1} onClick={() => setPage(at + 1)}>Next ›</button>
            <button type="button" className="dr-btn small" disabled={at >= pages - 1} onClick={() => setPage(pages - 1)} aria-label="Last page">»</button>
          </span>
        </div>
      )}
    </section>
  );
}
