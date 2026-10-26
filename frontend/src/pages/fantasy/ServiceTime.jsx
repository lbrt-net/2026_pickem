import { useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { Headshot, NbaTeamSquare } from "../../components/fantasy/RosterBits";
import { EntityLink } from "../../components/fantasy/links";
import { SEASON, useFantasyApi } from "../../components/fantasy/data";
import "./ServiceTime.css";

// Service Time (public, 2026-10-25): from the roster lock record — the permanent line
// written when each spot locks. A section per fantasy team; players are rows, weeks are columns, each cell his spot.
//

const SPOT = { G: "G", F: "F", C: "C", TEAM: "TM", FLEX: "FLX", BENCH: "Bench", IR: "IR" };
const sub = e => (e.kind === "nba_team" ? "TM" : [e.position || "—", e.nba_team].filter(Boolean).join(" · "));
const when = iso => new Date(iso).toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

const ORDER = { G: 0, F: 1, C: 2, FLEX: 3, TEAM: 4, BENCH: 5, IR: 6 };

// Grouped by fantasy team (2026-10-25): every player ever locked into that team's lineup, and his spot each week he was
// (a player who moved teams shows under each). Players in lineup order of their usual spot, then most weeks.
export default function ServiceTime() {
  const data = useFantasyApi("service-time");
  const teams = useFantasyApi("teams");
  const [q, setQ] = useState("");
  const weeks = data?.weeks || [];
  const groups = {};
  for (const e of data?.players || []) {
    if (q && !(e.name || "").toLowerCase().includes(q.toLowerCase())) continue;
    for (const w of e.weeks) {
      const g = (groups[w.team_id] ||= { id: w.team_id, name: w.team_name, rows: {} });
      (g.rows[e.id] ||= { e, by: {} }).by[w.week] = w;
    }
  }
  const teamOf = Object.fromEntries((teams || []).map(t => [t.id, t]));
  const usual = r => Math.min(...Object.values(r.by).map(w => ORDER[w.slot] ?? 9));
  const list = Object.values(groups).sort((x, y) => (x.name || "").localeCompare(y.name || ""));
  return (
    <FantasyShell title="Service Time" season={SEASON}>
      <div className="st-bar">
        <input className="st-search" type="search" placeholder="Find a player" value={q} onChange={e => setQ(e.target.value)} aria-label="Find a player" />
      </div>
      {data === undefined ? <p className="st-note">Loading…</p> : !list.length ? <p className="st-note">No locked weeks yet.</p> : list.map(g => {
        const t = teamOf[g.id];
        const rows = Object.values(g.rows).sort((x, y) => usual(x) - usual(y) || Object.keys(y.by).length - Object.keys(x.by).length || (x.e.name || "").localeCompare(y.e.name || ""));
        return (
          <section className="st-card" key={g.id} style={{ "--tc": t?.color || "var(--surface-3)" }}>
            <div className="st-team">{t && <TeamIcon team={t} size={28} />}<b>{g.name}</b><span>{rows.length} {rows.length === 1 ? "player" : "players"}</span></div>
            <table className="st-table">
              <thead><tr><th className="l st-p">Player</th><th className="st-n">Wks</th>{weeks.map(w => <th key={w} className="st-w">{w}</th>)}</tr></thead>
              <tbody>
                {rows.map(({ e, by }) => (
                  <tr key={e.id}>
                    <td className="l st-p"><span className="st-who">
                      {e.kind === "player" ? <Headshot playerId={e.id} tricode={e.nba_team} width={30} height={22} /> : <NbaTeamSquare tricode={e.id} size={22} />}
                      <span><EntityLink id={e.id} name={e.name} style={{ color: "inherit", textDecoration: "none" }} /><small>{sub(e)}</small></span>
                    </span></td>
                    <td className="st-n">{Object.keys(by).length}</td>
                    {weeks.map(wk => <td key={wk} className={`st-w${by[wk] ? ` s-${by[wk].slot}` : ""}`} title={by[wk] ? `Week ${wk} · locked ${when(by[wk].locked_at)}` : undefined}>{by[wk] ? (SPOT[by[wk].slot] || by[wk].slot) : ""}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        );
      })}
    </FantasyShell>
  );
}
