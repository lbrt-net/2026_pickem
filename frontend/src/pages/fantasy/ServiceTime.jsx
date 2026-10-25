import { useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { Headshot, NbaTeamSquare } from "../../components/fantasy/RosterBits";
import { EntityLink } from "../../components/fantasy/links";
import { SEASON, useFantasyApi } from "../../components/fantasy/data";
import "./ServiceTime.css";

// Service Time (public, 2026-10-25): every player's locked weeks, read from the roster lock record — the permanent line
// written when each spot locks. One row per player, one column per week: the fantasy team he was locked in for and the
// spot. Most weeks first.

const SPOT = { G: "G", F: "F", C: "C", TEAM: "TM", FLEX: "FLX", BENCH: "Bench", IR: "IR" };
const sub = e => (e.kind === "nba_team" ? "TM" : [e.position || "—", e.nba_team].filter(Boolean).join(" · "));
const when = iso => new Date(iso).toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

export default function ServiceTime() {
  const data = useFantasyApi("service-time");
  const teams = useFantasyApi("teams");
  const [q, setQ] = useState("");
  const teamById = Object.fromEntries((teams || []).map(t => [t.id, t]));
  const rows = (data?.players || []).filter(e => !q || (e.name || "").toLowerCase().includes(q.toLowerCase()));
  return (
    <FantasyShell title="Service Time" season={SEASON}>
      <div className="st-bar">
        <input className="st-search" type="search" placeholder="Find a player" value={q} onChange={e => setQ(e.target.value)} aria-label="Find a player" />
      </div>
      {data === undefined ? <p className="st-note">Loading…</p> : !data?.players?.length ? <p className="st-note">No locked weeks yet.</p> : (
        <section className="st-card">
          <table className="st-table">
            <thead>
              <tr>
                <th className="l">Player</th><th>Weeks</th>
                {data.weeks.map(w => <th key={w}>Wk {w}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map(e => {
                const by = Object.fromEntries(e.weeks.map(w => [w.week, w]));
                return (
                  <tr key={e.id}>
                    <td className="l">
                      <span className="st-who">
                        {e.kind === "player" ? <Headshot playerId={e.id} tricode={e.nba_team} width={30} height={22} /> : <NbaTeamSquare tricode={e.id} size={22} />}
                        <span><EntityLink id={e.id} name={e.name} style={{ color: "inherit", textDecoration: "none" }} /><small>{sub(e)}</small></span>
                      </span>
                    </td>
                    <td>{e.weeks.length}</td>
                    {data.weeks.map(wk => {
                      const w = by[wk];
                      const t = w && teamById[w.team_id];
                      return (
                        <td key={wk} title={w ? `${w.team_name} · ${SPOT[w.slot] || w.slot} · locked ${when(w.locked_at)}` : undefined}>
                          {w && <span className="st-cell">{t ? <TeamIcon team={t} size={18} /> : null}<span>{SPOT[w.slot] || w.slot}</span></span>}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}
    </FantasyShell>
  );
}
