import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { NbaTeamSquare, PositionBadge } from "../../components/fantasy/RosterBits";
import { nameLines } from "../../components/fantasy/nbaTeams";
import { EntityLink } from "../../components/fantasy/links";
import { API_BASE, base, teamPath, useFantasyApi } from "../../components/fantasy/data";
import { isOn } from "../../components/fantasy/features";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";
import "./TeamManagement.css";

// My Team (design: canvas row M — Points / Schedule views). /team = yours, /team/:ownerId = anyone's.
// Spots G / F / C / TM / FLX, then Bench (doesn't score). Tap the move button on a player, then
// "Move here" / "Swap" on a spot he can play. Each player locks at his NBA team's first game of the
// week; a move involving a locked player applies from next week (the server decides and says so).

const SPOT = { G: "G", F: "F", C: "C", TEAM: "TM", FLEX: "FLX", BENCH: "Bench" };
const WEEKDAY = d => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { weekday: "short" });
const MD = d => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { month: "numeric", day: "numeric" });
const RANGE = (a, b) => `${new Date(`${a}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })} – ${new Date(`${b}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;
const fmt = (v, kind) => (v == null ? "—" : `${kind === "nba_team" && v > 0 ? "+" : ""}${Number(v).toFixed(1)}`);
const oppText = g => `${g.home ? "vs" : "@"} ${g.opp}`;

// Same spot rule as the server (lineup.eligible).
function canPlay(e, slot) {
  if (slot === "FLEX" || slot === "BENCH") return true;
  if (e.kind === "nba_team") return slot === "TEAM";
  return slot === e.position;
}

const MOVE_ICON = (
  <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
    <path d="M4 2v10M4 2 1.8 4.2M4 2l2.2 2.2M10 12V2M10 12l-2.2-2.2M10 12l2.2-2.2" stroke="currentColor" strokeWidth="1.6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
const LOCK_ICON = (
  <svg width="12" height="12" viewBox="0 0 12 12" aria-label="Locked this week">
    <rect x="2.2" y="5.2" width="7.6" height="5.6" rx="1" stroke="currentColor" strokeWidth="1.4" fill="none" />
    <path d="M4 5.2V3.8a2 2 0 0 1 4 0v1.4" stroke="currentColor" strokeWidth="1.4" fill="none" />
  </svg>
);

function Panel({ title, aside, children }) {
  return (
    <section className="tm-panel" aria-label={title}>
      <div className="tm-panel-head"><span className="tm-h2">{title}</span>{aside && <span className="tm-aside">{aside}</span>}</div>
      {children}
    </section>
  );
}

function Player({ e, small }) {
  const [first, last] = nameLines(e);
  return (
    <span className="tm-player">
      <PositionBadge entry={e} size={small ? 22 : 26} />
      <NbaTeamSquare tricode={e.kind === "nba_team" ? e.id : e.nba_team} size={small ? 22 : 26} />
      <EntityLink id={e.id} name={<span className="tm-name2"><span>{first}</span><b>{last}</b></span>} />
    </span>
  );
}

export default function TeamManagement() {
  const { ownerId } = useParams();
  const navigate = useNavigate();
  const user = useCurrentUser();
  const [scenario] = useFantasyScenario();
  const teams = useFantasyApi("teams");
  const results = useFantasyApi("results");
  const [view, setView] = useState("points");
  const [weekNo, setWeekNo] = useState(null); // null = the current week
  const [data, setData] = useState(undefined);
  const [moving, setMoving] = useState(null); // the entry being moved
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState(null);

  const targetOwner = ownerId || user?.discordId;
  const team = teams?.find(t => t.owner_user_id === targetOwner);
  const mine = !!user && team?.owner_user_id === user.discordId;
  const canEdit = mine || !!user?.isAdmin;

  const load = useCallback(() => {
    if (!team) return;
    const q = new URLSearchParams({ scenario, ...(weekNo ? { week: weekNo } : {}) });
    fetch(`${API}${API_BASE}/team/${encodeURIComponent(team.id)}/week?${q}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null).then(setData);
  }, [team, scenario, weekNo]);
  useEffect(() => { load(); }, [load]);

  async function moveTo(slot, swapWith) {
    setBusy(true); setNote(null);
    try {
      const r = await fetch(`${API}${API_BASE}/team/${encodeURIComponent(team.id)}/move?scenario=${scenario}`, {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entity_id: moving.id, to_slot: slot, swap_with: swapWith || null }),
      });
      const out = await r.json().catch(() => ({}));
      if (!r.ok) { setNote({ error: true, text: out.detail || "Couldn't move him" }); return; }
      setNote({ text: out.applies === "now" ? "Moved — counts this week." : "Moved — someone involved already played this week, so it counts from next week." });
      setMoving(null);
      load();
    } finally {
      setBusy(false);
    }
  }

  // Spots in order, each filled with its player (or open).
  const spots = useMemo(() => {
    if (!data) return [];
    const left = [...data.entries];
    return data.slot_list.map(slot => {
      const i = left.findIndex(e => e.slot === slot);
      return { slot, entry: i === -1 ? null : left.splice(i, 1)[0] };
    });
  }, [data]);

  const standing = results?.standings?.find(r => r.team.id === team?.id);
  const rank = standing ? results.standings.indexOf(standing) + 1 : null;
  const weekResult = data && results?.weeks?.find(w => w.week === data.week.week);
  const matchup = weekResult?.matchups?.find(m => m.home.team.id === team?.id || m.away.team.id === team?.id);
  const days = useMemo(() => {
    if (!data) return [];
    const out = [];
    for (let d = new Date(`${data.week.start}T12:00:00`); d <= new Date(`${data.week.end}T12:00:00`); d.setDate(d.getDate() + 1)) out.push(d.toISOString().slice(0, 10));
    return out;
  }, [data]);
  const editableWeek = data && (data.current_week == null || data.week.week >= data.current_week);

  let body;
  if (teams === undefined || (!ownerId && user === undefined)) body = <p style={{ fontSize: 13 }}>Loading…</p>;
  else if (!ownerId && !user) body = <p style={{ fontSize: 13 }}>Log in to see your team.</p>;
  else if (!team) body = <p style={{ fontSize: 13 }}>{ownerId ? "No team found for this owner." : "You don't have a team in this league."}</p>;
  else {
    const action = (slot, entry) => {
      if (!canEdit || !editableWeek) return null;
      if (moving) {
        if (entry && entry.id === moving.id) return <button type="button" className="tm-btn small" onClick={() => setMoving(null)}>Cancel</button>;
        if (!canPlay(moving, slot)) return null;
        if (!entry) return <button type="button" className="tm-btn primary small" disabled={busy} onClick={() => moveTo(slot)}>Move here</button>;
        if (!canPlay(entry, moving.slot)) return null;
        return <button type="button" className="tm-btn primary small" disabled={busy} onClick={() => moveTo(slot, entry.id)}>Swap</button>;
      }
      if (!entry) return null;
      return <button type="button" className="tm-icon-btn" title={`Move ${entry.name}`} aria-label={`Move ${entry.name}`} onClick={() => { setMoving(entry); setNote(null); }}>{MOVE_ICON}</button>;
    };

    const pointsRows = list => list.map(({ slot, entry }, i) => {
      const played = entry ? entry.games.filter(g => g.played).length : 0;
      const next = entry?.games.find(g => !g.played);
      return (
        <tr key={i} className={moving && entry?.id === moving.id ? "moving" : ""}>
          <td className="spot"><span className="tm-spot">{SPOT[slot]}</span></td>
          <td>{entry ? <Player e={entry} /> : <span className="tm-open">Open</span>}</td>
          <td className="hide-sm">{next ? `${WEEKDAY(next.date)} ${oppText(next)}` : entry ? "—" : ""}</td>
          <td className="num hide-sm">{entry ? `${played} of ${entry.games.length}` : ""}</td>
          <td className="num best">{entry ? fmt(entry.week_score, entry.kind) : ""}{entry?.kind === "nba_team" && entry.week_score != null && <span className="tm-sub"> margin</span>}</td>
          <td className="num hide-sm">{entry ? fmt(entry.season_ppg, entry.kind) : ""}</td>
          <td className="act"><span className="tm-act">{entry?.locked && <span className="tm-lock" title="Locked this week — he's already played">{LOCK_ICON}</span>}{action(slot, entry)}</span></td>
        </tr>
      );
    });

    const schedRows = list => list.map(({ slot, entry }, i) => {
      const byDate = Object.fromEntries((entry?.games || []).map(g => [g.date, g]));
      const best = entry && entry.kind === "player" ? entry.week_score : null;
      return (
        <tr key={i} className={moving && entry?.id === moving.id ? "moving" : ""}>
          <td className="spot"><span className="tm-spot">{SPOT[slot]}</span></td>
          <td className="who">{entry ? <Player e={entry} small /> : <span className="tm-open">Open</span>}</td>
          {days.map(d => {
            const g = byDate[d];
            const today = d === data.as_of;
            if (!g) return <td key={d} className={`day${today ? " today" : ""}`} />;
            if (g.played) {
              return (
                <td key={d} className={`day${today ? " today" : ""}`}>
                  <span className={`tm-cell played${best != null && g.points === best ? " best" : ""}`}>
                    <b>{g.points == null ? "DNP" : fmt(g.points, entry.kind)}</b><span>{oppText(g)}</span>
                  </span>
                </td>
              );
            }
            return <td key={d} className={`day${today ? " today" : ""}`}><span className="tm-cell">{oppText(g)}</span></td>;
          })}
          <td className="num games">{entry ? `${entry.games.filter(g => g.played).length}/${entry.games.length}` : ""}</td>
          <td className="act"><span className="tm-act">{entry?.locked && <span className="tm-lock">{LOCK_ICON}</span>}{action(slot, entry)}</span></td>
        </tr>
      );
    });

    const starters = spots.filter(s => s.slot !== "BENCH");
    const bench = spots.filter(s => s.slot === "BENCH");
    const table = list => (view === "points" ? (
      <div className="tm-scroll">
        <table className="tm-table">
          <thead><tr><th className="spot">Spot</th><th>Player / team</th><th className="hide-sm">Next game</th><th className="num hide-sm">Games this week</th>
            <th className="num" title="Best single game this week (NBA team: point margins added up)">Best game this week</th><th className="num hide-sm">Season pts / game</th><th className="act" /></tr></thead>
          <tbody>{pointsRows(list)}</tbody>
        </table>
      </div>
    ) : (
      <div className="tm-scroll">
        <table className="tm-table sched">
          <thead><tr><th className="spot">Spot</th><th className="who">Player / team</th>
            {days.map(d => <th key={d} className={`day${d === data.as_of ? " today" : ""}`}>{WEEKDAY(d)}<br /><span>{MD(d)}</span></th>)}
            <th className="num games">Games</th><th className="act" /></tr></thead>
          <tbody>{schedRows(list)}</tbody>
        </table>
      </div>
    ));

    body = (
      <div className="tm">
        <div className="tm-head">
          <TeamIcon team={team} size={52} />
          <div className="tm-head-name">
            <span className="tm-team-name">{team.name}</span>
            <span>{standing ? `${standing.w}-${standing.l}${standing.t ? `-${standing.t}` : ""} · ${rank} of ${results.standings.length}` : ""}</span>
          </div>
          <label className="tm-switch">Team
            <select value={team.owner_user_id || ""} onChange={e => navigate(teamPath(e.target.value))}>
              {teams.filter(t => t.owner_user_id).map(t => <option key={t.id} value={t.owner_user_id}>{t.name}{user && t.owner_user_id === user.discordId ? " (you)" : ""}</option>)}
            </select>
          </label>
          {mine && isOn("/team/settings") && <Link className="tm-btn" to={`${base()}/team/settings`}>Team settings</Link>}
        </div>

        {data === undefined && <p style={{ fontSize: 13 }}>Loading…</p>}
        {data === null && <p style={{ fontSize: 13 }}>Couldn't load this week.</p>}
        {data && (
          <>
            <section className="tm-weekbar">
              <span className="tm-weeknav">
                <button type="button" className="tm-btn small" disabled={data.week.week <= 1} onClick={() => { setMoving(null); setWeekNo(data.week.week - 1); }}>‹</button>
                <b>{data.week.label} · {RANGE(data.week.start, data.week.end)}</b>
                <button type="button" className="tm-btn small" disabled={data.week.week >= data.weeks.length} onClick={() => { setMoving(null); setWeekNo(data.week.week + 1); }}>›</button>
              </span>
              {matchup && (() => {
                const me = matchup.home.team.id === team.id ? matchup.home : matchup.away;
                const them = me === matchup.home ? matchup.away : matchup.home;
                return <span className="tm-matchup">vs <b>{them.team.name}</b> · {me.score} – {them.score}{weekResult.status === "final" ? " final" : " so far"}</span>;
              })()}
              <span className="tm-seg" role="radiogroup" aria-label="View">
                {[["points", "Points"], ["schedule", "Schedule"]].map(([k, l]) => (
                  <button key={k} type="button" role="radio" aria-checked={view === k} onClick={() => setView(k)}>{l}</button>
                ))}
              </span>
            </section>

            {data.is_current && (
              <section className="tm-note"><b>Lineup locks per player</b><span>each player locks at his team's first game of the week. A move involving a locked player counts from next week.</span></section>
            )}
            {moving && (
              <section className="tm-moving">
                <span>Moving <b>{moving.name}</b> — pick a spot he can play.</span>
                <button type="button" className="tm-btn small" onClick={() => setMoving(null)}>Cancel</button>
              </section>
            )}
            {note && <section className={`tm-result${note.error ? " error" : ""}`} role="status">{note.text}</section>}

            <Panel title="Starters" aside={`${starters.filter(s => s.entry).length} of ${starters.length} · this week ${data.starters_score}`}>{table(starters)}</Panel>
            <Panel title="Bench" aside={`${bench.filter(s => s.entry).length} of ${bench.length}`}>
              {bench.length ? table(bench) : <div className="tm-empty">This league has no bench spots. The commissioner can add them in League settings → Roster.</div>}
            </Panel>
            <p className="tm-footnote">Scoring: each player's best single game of the week; NBA team = its point margins added up. Bench doesn't score.</p>
          </>
        )}
      </div>
    );
  }

  return <FantasyShell title="My Team">{body}</FantasyShell>;
}
