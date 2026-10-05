import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import LedClock from "../../components/fantasy/LedClock";
import { Headshot, NbaTeamSquare } from "../../components/fantasy/RosterBits";
import { nameLines } from "../../components/fantasy/nbaTeams";
import { EntityLink } from "../../components/fantasy/links";
import { API_BASE, base, teamPath, useFantasyApi } from "../../components/fantasy/data";
import { isOn } from "../../components/fantasy/features";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";
import { textOnColor } from "../../components/fantasy/teamColors";
import "./TeamManagement.css";

// My Team (design: canvas "Facelift v2"). /team = yours, /team/:ownerId = anyone's.
// Forward-looking: once all your starters have locked it opens on next week; future weeks show each
// player's projected best game (expected best single game over his games that week) and default to
// Schedule. Past weeks are read-only: actual best game with its box line, for reviewing decisions.
// Scorebug header (your color | score | opponent's color), LED lock clock, headshots on every row.
// Move: tap the move button, then "Move here" / "Swap". Each player locks 5 min before his NBA
// team's first game of the week; a move involving a locked player counts from next week.

const SPOT = { G: "G", F: "F", C: "C", TEAM: "TM", FLEX: "FLX", BENCH: "Bench" };
const WEEKDAY = d => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { weekday: "short" });
const MD = d => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { month: "numeric", day: "numeric" });
const RANGE = (a, b) => `${new Date(`${a}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })} – ${new Date(`${b}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;
const fmt = (v, kind) => (v == null ? "—" : `${kind === "nba_team" && v > 0 ? "+" : ""}${Number(v).toFixed(1)}`);
const oppText = g => `${g.home ? "vs" : "@"} ${g.opp}`;

function canPlay(e, slot) {
  if (slot === "FLEX" || slot === "BENCH") return true;
  if (e.kind === "nba_team") return slot === "TEAM";
  return slot === e.position;
}

const MOVE_ICON = (
  <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
    <path d="M5 2.5v11M5 2.5 2.6 4.9M5 2.5l2.4 2.4M11 13.5v-11M11 13.5l-2.4-2.4M11 13.5l2.4-2.4" stroke="currentColor" strokeWidth="1.7" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
const LOCK_ICON = (
  <svg width="12" height="12" viewBox="0 0 12 12" aria-label="Locked this week">
    <rect x="2.2" y="5.2" width="7.6" height="5.6" rx="1" stroke="currentColor" strokeWidth="1.4" fill="none" />
    <path d="M4 5.2V3.8a2 2 0 0 1 4 0v1.4" stroke="currentColor" strokeWidth="1.4" fill="none" />
  </svg>
);

// The spot is a plain row label (G / F / C / TM / FLX / Bench).
// Row menu (⋯): Drop and Trade — shown, not built yet (disabled).
function RowMenu({ name }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="tm-menu" onBlur={e => { if (!e.currentTarget.contains(e.relatedTarget)) setOpen(false); }}>
      <button type="button" className="tm-ghost" aria-label={`More for ${name}`} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(o => !o)}>⋯</button>
      {open && (
        <span className="tm-menu-list" role="menu">
          <button type="button" role="menuitem" disabled title="Coming later">Drop</button>
          <button type="button" role="menuitem" disabled title="Coming later">Trade</button>
        </span>
      )}
    </span>
  );
}

function SpotChip({ slot }) {
  return <span className="tm-slotlabel" title={slot === "FLEX" ? "Flex" : undefined}>{SPOT[slot]}</span>;
}

function Who({ e }) {
  const [first, last] = nameLines(e);
  // The player's own position sits at the end of the small line: "Cade · DET · G".
  const pos = e.kind === "nba_team" ? "TM" : e.position || "—";
  const sub = e.kind === "nba_team" ? `${first} · ${pos}` : `${first} · ${e.nba_team || ""} · ${pos}`;
  return (
    <span className="tm-who">
      {e.kind === "player"
        ? <Headshot playerId={e.id} tricode={e.nba_team} width={72} height={53} />
        : <span className="tm-logo"><NbaTeamSquare tricode={e.id} size={40} /></span>}
      <EntityLink id={e.id} name={<span className="tm-name2"><span>{sub}</span><b>{last}</b></span>} />
    </span>
  );
}

// Lock clock: one unit, counting down — 3 D → 14 H → 22 M → 41 S. The replay (whole days) counts days.
function LockClock({ lock, asOf, now }) {
  if (!lock) return null;
  const ms = lock.at ? Date.parse(lock.at) - now : Date.parse(`${lock.date}T00:00:00`) - Date.parse(`${asOf}T00:00:00`);
  if (ms <= 0) return <span className="tm-lockclock"><span className="lbl">Locked</span>{LOCK_ICON}</span>;
  const s = Math.floor(ms / 1000);
  const [v, u] = s >= 86400 ? [Math.floor(s / 86400), "D"] : s >= 3600 ? [Math.floor(s / 3600), "H"] : s >= 60 ? [Math.floor(s / 60), "M"] : [s, "S"];
  return (
    <span className="tm-lockclock" title={lock.at ? `Locks ${new Date(lock.at).toLocaleString()}` : `First game ${lock.date}`}>
      <span className="lbl">Locks in</span><LedClock text={String(v)} step={2.6} r={1.05} label={`${v} ${u}`} /><b>{u}</b>
    </span>
  );
}

function Scorebug({ team, record, opp, oppRecord, mine, theirs, label, sub }) {
  const abbr = t => t.abbreviation || t.name.slice(0, 4).toUpperCase();
  return (
    <section className="tm-bug">
      <svg className="court" viewBox="0 0 600 160" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <g fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="300" y1="0" x2="300" y2="160" /><circle cx="300" cy="80" r="46" /><circle cx="300" cy="80" r="14" />
          <rect x="-10" y="40" width="120" height="80" /><path d="M110 40a40 40 0 0 1 0 80" /><path d="M-10 4 Q 230 80 -10 156" />
          <rect x="490" y="40" width="120" height="80" /><path d="M490 40a40 40 0 0 0 0 80" /><path d="M610 4 Q 370 80 610 156" />
        </g>
      </svg>
      <div className="side left" style={{ "--team": team.color, color: textOnColor(team.color) }}>
        <TeamIcon team={team} size={60} />
        <div><b className="abbr">{abbr(team)}</b><span>{team.name}{record ? ` · ${record}` : ""}</span></div>
      </div>
      <div className="mid">
        <span className="lbl">{label}</span>
        <span className="score">{mine ?? "—"}<span className="dash">–</span>{theirs ?? "—"}</span>
        {sub && <span className="sub">{sub}</span>}
      </div>
      {opp ? (
        <div className="side right" style={{ "--team": opp.color, color: textOnColor(opp.color) }}>
          <div><b className="abbr">{abbr(opp)}</b><span>{opp.name}{oppRecord ? ` · ${oppRecord}` : ""}</span></div>
          <TeamIcon team={opp} size={60} />
        </div>
      ) : <div className="side right"><div><b className="abbr">BYE</b><span>No matchup this week</span></div></div>}
    </section>
  );
}

export default function TeamManagement() {
  const { ownerId } = useParams();
  const navigate = useNavigate();
  const user = useCurrentUser();
  const [scenario] = useFantasyScenario();
  const teams = useFantasyApi("teams");
  const results = useFantasyApi("results");
  const [viewPick, setView] = useState(null); // null = Schedule for future weeks, Points otherwise
  const [weekNo, setWeekNo] = useState(null);
  const [data, setData] = useState(undefined);
  const [oppData, setOppData] = useState(null);
  const [moving, setMoving] = useState(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState(null);
  const [now, setNow] = useState(() => Date.now());

  const targetOwner = ownerId || user?.discordId;
  const team = teams?.find(t => t.owner_user_id === targetOwner);
  const mine = !!user && team?.owner_user_id === user.discordId;
  const canEdit = mine || !!user?.isAdmin;

  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t); }, []);

  const load = useCallback(() => {
    if (!team) return;
    const q = new URLSearchParams({ scenario, ...(weekNo ? { week: weekNo } : {}) });
    fetch(`${API}${API_BASE}/team/${encodeURIComponent(team.id)}/week?${q}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null).then(setData);
  }, [team, scenario, weekNo]);
  useEffect(() => { load(); }, [load]);
  // The opponent's same week, for the scorebug's other number.
  useEffect(() => {
    if (!data?.opponent) return undefined;
    let live = true;
    const q = new URLSearchParams({ scenario, week: data.week.week });
    fetch(`${API}${API_BASE}/team/${encodeURIComponent(data.opponent.id)}/week?${q}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null).then(d => { if (live) setOppData(d); });
    return () => { live = false; };
  }, [data, scenario]);

  async function moveTo(slot, swapWith) {
    setBusy(true); setNote(null);
    try {
      const r = await fetch(`${API}${API_BASE}/team/${encodeURIComponent(team.id)}/move?scenario=${scenario}`, {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entity_id: moving.id, to_slot: slot, swap_with: swapWith || null }),
      });
      const out = await r.json().catch(() => ({}));
      if (!r.ok) { setNote({ error: true, text: out.detail || "Couldn't move him" }); return; }
      setNote({ text: out.applies === "now" ? "Moved — counts this week." : "Moved — someone involved already locked this week, so it counts from next week." });
      setMoving(null);
      load();
    } finally {
      setBusy(false);
    }
  }

  const spots = useMemo(() => {
    if (!data) return [];
    const left = [...data.entries];
    return data.slot_list.map(slot => {
      const i = left.findIndex(e => e.slot === slot);
      return { slot, entry: i === -1 ? null : left.splice(i, 1)[0] };
    });
  }, [data]);
  const days = useMemo(() => {
    if (!data) return [];
    const out = [];
    for (let d = new Date(`${data.week.start}T12:00:00`); d <= new Date(`${data.week.end}T12:00:00`); d.setDate(d.getDate() + 1)) out.push(d.toISOString().slice(0, 10));
    return out;
  }, [data]);

  const recOf = id => {
    const r = results?.standings?.find(x => x.team.id === id);
    return r ? `${r.w}-${r.l}${r.t ? `-${r.t}` : ""}` : null;
  };

  let body;
  if (teams === undefined || (!ownerId && user === undefined)) body = <p style={{ fontSize: 13 }}>Loading…</p>;
  else if (!ownerId && !user) body = <p style={{ fontSize: 13 }}>Log in to see your team.</p>;
  else if (!team) body = <p style={{ fontSize: 13 }}>{ownerId ? "No team found for this owner." : "You don't have a team in this league."}</p>;
  else if (data === undefined) body = <p style={{ fontSize: 13 }}>Loading…</p>;
  else if (data === null) body = <p style={{ fontSize: 13 }}>Couldn't load this week.</p>;
  else {
    const past = data.current_week != null && data.week.week < data.current_week;
    const future = data.current_week == null || data.week.week > data.current_week;
    const view = viewPick || (future ? "schedule" : "points");
    const opp = oppData && data.opponent && oppData.team_id === data.opponent.id && oppData.week.week === data.week.week ? oppData : null;
    const dayNo = data.is_current ? Math.max(1, days.indexOf(data.as_of) + 1) : null;
    const bugLabel = past ? `${data.week.label} · Final` : future ? `${data.week.label} · Projected` : `${data.week.label} · Day ${dayNo} / ${days.length}`;
    const mineScore = future ? data.starters_projected : data.starters_score;
    const theirScore = opp ? (future ? opp.starters_projected : opp.starters_score) : null;
    const bugSub = future ? "projected best games" : data.is_current ? `projected ${data.starters_projected} – ${opp?.starters_projected ?? "—"}` : null;

    const action = (slot, entry) => {
      if (!canEdit || past) return null;
      if (moving) {
        if (entry && entry.id === moving.id) return <button type="button" className="tm-btn small" onClick={() => setMoving(null)}>Cancel</button>;
        if (!canPlay(moving, slot)) return null;
        if (!entry) return <button type="button" className="tm-btn primary small" disabled={busy} onClick={() => moveTo(slot)}>Move here</button>;
        if (!canPlay(entry, moving.slot)) return null;
        return <button type="button" className="tm-btn primary small" disabled={busy} onClick={() => moveTo(slot, entry.id)}>Swap</button>;
      }
      if (!entry) return null;
      return <button type="button" className="tm-ghost" title={`Move ${entry.name}`} aria-label={`Move ${entry.name}`} onClick={() => { setMoving(entry); setNote(null); }}>{MOVE_ICON}</button>;
    };

    // Best game: projection for future weeks; actual (with its box line) once games are played.
    const bestCell = e => {
      if (!e) return null;
      if (future) {
        return <><span className="tm-big">{fmt(e.projected, e.kind)}</span><span className="tm-boxline">projected · {e.games.length} game{e.games.length === 1 ? "" : "s"}</span></>;
      }
      const playedN = e.games.filter(g => g.played).length;
      return (
        <>
          <span className="tm-big">{fmt(e.week_score, e.kind)}</span>
          {e.box_line && <span className="tm-boxline">{e.box_line}</span>}
          {e.kind === "nba_team" && e.week_score != null && <span className="tm-boxline">point margin · {playedN} game{playedN === 1 ? "" : "s"}</span>}
          {data.is_current && e.games_left > 0 && <span className="tm-boxline">proj {fmt(e.projected, e.kind)} · {e.games_left} left</span>}
        </>
      );
    };

    const firstBench = spots.findIndex(s => s.slot === "BENCH");
    const row = ({ slot, entry }, i) => {
      const played = entry ? entry.games.filter(g => g.played).length : 0;
      const next = entry?.games.find(g => !g.played);
      return (
        <tr key={i} className={[moving && entry?.id === moving.id ? "moving" : "", slot === "BENCH" && i === firstBench ? "bench-start" : ""].join(" ").trim()}>
          <td className="spot"><SpotChip slot={slot} /></td>
          <td className="who">{entry ? <Who e={entry} /> : <span className="tm-open">Open</span>}</td>
          {view === "points" ? (
            <>
              <td className="hide-sm divl">{next ? `${WEEKDAY(next.date)} ${oppText(next)}` : entry ? "—" : ""}</td>
              <td className="num hide-sm">{entry ? `${played} / ${entry.games.length}` : ""}</td>
              <td className="num best divl">{bestCell(entry)}</td>
              <td className="num hide-sm">{entry ? fmt(entry.season_ppg, entry.kind) : ""}</td>
            </>
          ) : (
            <>
              {days.map((d, k) => {
                const g = entry?.games.find(x => x.date === d);
                const cls = `day${d === data.as_of ? " today" : ""}${k === 0 ? " divl" : ""}`;
                if (!g) return <td key={d} className={cls} />;
                if (g.played) {
                  const isBest = entry.kind === "player" && g.points != null && g.points === entry.week_score;
                  return <td key={d} className={cls}><span className={`tm-cell played${isBest ? " best" : ""}`}><b>{g.points == null ? "DNP" : fmt(g.points, entry.kind)}</b><span>{oppText(g)}</span></span></td>;
                }
                return <td key={d} className={cls}><span className="tm-cell">{oppText(g)}</span></td>;
              })}
              <td className="num prob divl">{entry ? "—" : ""}</td>
            </>
          )}
          <td className="act"><span className="tm-act">{entry?.locked && <span className="tm-lock" title="Locked this week">{LOCK_ICON}</span>}{action(slot, entry)}{entry && canEdit && !moving && <RowMenu name={entry.name} />}</span></td>
        </tr>
      );
    };

    const starters = spots.filter(s => s.slot !== "BENCH");
    const bench = spots.filter(s => s.slot === "BENCH");

    body = (
      <div className="tm">
        <div className="tm-top">
          <label className="tm-switch">Team
            <select value={team.owner_user_id || ""} onChange={e => navigate(teamPath(e.target.value))}>
              {teams.filter(t => t.owner_user_id).map(t => <option key={t.id} value={t.owner_user_id}>{t.name}{user && t.owner_user_id === user.discordId ? " (you)" : ""}</option>)}
            </select>
          </label>
          {mine && isOn("/team/settings") && <Link className="tm-btn" to={`${base()}/team/settings`}>Team settings</Link>}
        </div>

        <Scorebug team={team} record={recOf(team.id)} opp={data.opponent} oppRecord={data.opponent && recOf(data.opponent.id)}
          mine={mineScore} theirs={theirScore} label={bugLabel} sub={bugSub} />

        <div className="tm-weekbar">
          <button type="button" className="tm-btn" disabled={data.week.week <= 1} onClick={() => { setMoving(null); setWeekNo(data.week.week - 1); }}>‹</button>
          <b className="tm-week">{data.week.label} · {RANGE(data.week.start, data.week.end)}</b>
          <button type="button" className="tm-btn" disabled={data.week.week >= data.weeks.length} onClick={() => { setMoving(null); setWeekNo(data.week.week + 1); }}>›</button>
          {past ? <span className="tm-pastnote">Past week · read-only — your lineup then</span> : <LockClock lock={data.lock} asOf={data.as_of} now={now} />}
          <span className="tm-seg" role="radiogroup" aria-label="View">
            {[["points", "Points"], ["schedule", "Schedule"]].map(([k, l]) => (
              <button key={k} type="button" role="radio" aria-checked={view === k} onClick={() => setView(k)}>{l}</button>
            ))}
          </span>
        </div>

        {moving && (
          <div className="tm-moving"><span>Moving <b>{moving.name}</b> — pick a spot he can play.</span><button type="button" className="tm-btn small" onClick={() => setMoving(null)}>Cancel</button></div>
        )}
        {note && <div className={`tm-result${note.error ? " error" : ""}`} role="status">{note.text}</div>}

        <section className="tm-card">
          <div className="tm-scroll">
            <table className={`tm-table${view === "schedule" ? " sched" : ""}`}>
              <thead>
                <tr>
                  <th className="spot" aria-label="Spot" /><th className="who">Player</th>
                  {view === "points" ? (
                    <><th className="hide-sm divl">Next</th><th className="num hide-sm">Games</th><th className="num divl">{future ? "Proj. best game" : "Best game"}</th><th className="num hide-sm">Season avg</th></>
                  ) : (
                    <>{days.map((d, k) => <th key={d} className={`day${d === data.as_of ? " today" : ""}${k === 0 ? " divl" : ""}`}>{WEEKDAY(d)}<br /><span>{MD(d)}</span></th>)}<th className="num prob divl" title="Chance he plays at least one game this week">1+ Game %</th></>
                  )}
                  <th className="act" />
                </tr>
              </thead>
              <tbody>
                {starters.map(row)}
                {bench.map((s, i) => row(s, starters.length + i))}
              </tbody>
            </table>
          </div>
        </section>
        <p className="tm-footnote">
          Scoring: each player's best single game of the week; NBA team = its point margins added up. Projected best game = the expected best single game over his games that week, from his game scores this season (plus last season's while he has few).
        </p>
      </div>
    );
  }

  return <FantasyShell title="My Team">{body}</FantasyShell>;
}
