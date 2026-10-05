import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import LockClock, { LockIcon, UnlockIcon } from "../../components/fantasy/LockClock";
import { Headshot, NbaTeamSquare } from "../../components/fantasy/RosterBits";
import { nameLines } from "../../components/fantasy/nbaTeams";
import { EntityLink } from "../../components/fantasy/links";
import { API_BASE, base, teamPath, useFantasyApi } from "../../components/fantasy/data";
import { isOn } from "../../components/fantasy/features";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";
import "./TeamManagement.css";

// Roster (design: canvas "Roster v2"). /team = yours, /team/:ownerId = anyone's — the team header is
// the switcher. No score here: scores live on Matchup.
// Forward-looking: once all your starters have locked it opens on next week; future weeks default to
// Schedule (day columns, each future game's projection in italics). Points = each player's best game
// broken down by scoring category. Past weeks are read-only. LED lock clock, headshots on every row.
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

// When his week's first game tips: "10/19 @ 5 PM" / "@ 2:30 PM" (local time). He locks 5 min before.
function tipText(g) {
  if (!g) return "";
  const md = MD(g.date);
  if (!g.tipoff) return md;
  const t = new Date(g.tipoff);
  const time = t.toLocaleTimeString(undefined, { hour: "numeric", ...(t.getMinutes() ? { minute: "2-digit" } : {}) });
  return `${md} @ ${time}`;
}

// Player cell, three lines, top-aligned: last name / "G · LAL" / lock line (locked, or open + first tip-off).
function WhoCells({ e, past }) {
  if (!e) return <><td className="hs" /><td className="who"><span className="tm-open">Open</span></td></>;
  const [, last] = nameLines(e);
  const sub = e.kind === "nba_team" ? "TM" : `${e.position || "—"} · ${e.nba_team || ""}`;
  const locked = past || e.locked;
  return (
    <>
      <td className="hs">{e.kind === "player" ? <Headshot playerId={e.id} tricode={e.nba_team} width={48} height={35} /> : <NbaTeamSquare tricode={e.id} size={26} />}</td>
      <td className="who">
        <EntityLink id={e.id} name={last} style={{ color: "inherit", textDecoration: "none" }} />
        <span className="tm-sub">{sub}</span>
        <span className="tm-lockline">
          {locked ? <LockIcon /> : e.games.length ? <><UnlockIcon /><span>{tipText(e.games[0])}</span></> : null}
        </span>
      </td>
    </>
  );
}

function Counts({ e }) {
  if (!e) return null;
  const done = e.games_done ?? e.games.filter(g => g.played).length;
  const today = e.games_today || 0;
  return (
    <span className="tm-counts">
      <span><i className="k done" />{done}</span><span><i className="k today" />{today}</span><span><i className="k later" />{Math.max(0, (e.games_left || 0) - today)}</span>
    </span>
  );
}

// Team header = team switcher: every team's roster is one pick away. No score.
function TeamHeader({ team, teams, standings, user, onPick }) {
  const [open, setOpen] = useState(false);
  const rank = id => { const i = standings?.findIndex(r => r.team.id === id) ?? -1; return i === -1 ? null : i + 1; };
  const rec = id => { const r = standings?.find(x => x.team.id === id); return r ? `${r.w}-${r.l}${r.t ? `-${r.t}` : ""}` : null; };
  const ord = n => `${n}${["th", "st", "nd", "rd"][n % 100 >= 11 && n % 100 <= 13 ? 0 : Math.min(n % 10, 4) % 4] || "th"}`;
  const line = t => [t.abbreviation, rec(t.id), rank(t.id) && ord(rank(t.id)), t.owner_name].filter(Boolean).join(" · ");
  const list = teams.filter(t => t.owner_user_id).sort((a, b) => (rank(a.id) ?? 99) - (rank(b.id) ?? 99));
  return (
    <section className="tm-head" style={{ "--team": team.color || "var(--surface-2)" }}
      onBlur={e => { if (!e.currentTarget.contains(e.relatedTarget)) setOpen(false); }}>
      <button type="button" className="tm-head-btn" aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen(o => !o)}>
        <TeamIcon team={team} size={40} />
        <span className="tm-head-txt"><span className="n">{team.name} <span aria-hidden="true">▾</span></span><span className="s">{line(team)}</span></span>
      </button>
      {open && (
        <div className="tm-head-menu" role="listbox">
          {list.map(t => (
            <button key={t.id} type="button" role="option" aria-selected={t.id === team.id} className={t.id === team.id ? "on" : ""}
              onClick={() => { setOpen(false); onPick(t.owner_user_id); }}>
              <TeamIcon team={t} size={24} /><span className="n">{t.name}</span>
              <span className="s">{[rec(t.id), rank(t.id) && ord(rank(t.id))].filter(Boolean).join(" · ")}</span>
            </button>
          ))}
        </div>
      )}
      {user && team.owner_user_id === user.discordId && isOn("/team/settings") && <Link className="tm-btn small tm-head-set" to={`${base()}/team/settings`}>Team settings</Link>}
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
  const scoring = useFantasyApi("scoring");
  const [viewPick, setView] = useState(null); // null = Schedule for future weeks, Points otherwise
  const [weekNo, setWeekNo] = useState(null);
  const [data, setData] = useState(undefined);
  const [moving, setMoving] = useState(null);
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
        body: JSON.stringify({ entity_id: moving.id, to_slot: slot, swap_with: swapWith || null, week: data.week.week }),
      });
      const out = await r.json().catch(() => ({}));
      if (!r.ok) { setNote({ error: true, text: out.detail || "Couldn't move him" }); return; }
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
    const action = (slot, entry) => {
      if (!canEdit || past) return null;
      if (moving) {
        if (entry && entry.id === moving.id) return <button type="button" className="tm-btn small" onClick={() => setMoving(null)}>Cancel</button>;
        if (!canPlay(moving, slot)) return null;
        if (!entry) return <button type="button" className="tm-btn primary small" disabled={busy} onClick={() => moveTo(slot)}>Move here</button>;
        if (!canPlay(entry, moving.slot) || (data.is_current && entry.locked)) return null;
        return <button type="button" className="tm-btn primary small" disabled={busy} onClick={() => moveTo(slot, entry.id)}>Swap</button>;
      }
      if (!entry || (data.is_current && entry.locked)) return null;
      return <button type="button" className="tm-ghost" title={`Move ${entry.name}`} aria-label={`Move ${entry.name}`} onClick={() => { setMoving(entry); setNote(null); }}>{MOVE_ICON}</button>;
    };

    // Points view: the best game by scoring category (rules order from /scoring; BLKD not loaded yet).
    const cats = (scoring?.rules || []).filter(r => r.key !== "blkd");
    const signed = v => (v > 0 ? `+${v}` : v < 0 ? `−${Math.abs(v)}` : "0");
    const firstBench = spots.findIndex(s => s.slot === "BENCH");
    const row = ({ slot, entry }, i) => (
      <tr key={i} className={[moving && entry?.id === moving.id ? "moving" : "", slot === "BENCH" && i === firstBench ? "bench-start" : ""].join(" ").trim()}>
        <td className="spot"><SpotChip slot={slot} /></td>
        <WhoCells e={entry} past={past} />
        {view === "points" ? (
          <>
            {entry?.kind === "nba_team"
              ? <td className="cat divl c" colSpan={cats.length}>{entry.week_score != null ? `Δ ${fmt(entry.week_score, "nba_team")}` : ""}</td>
              : cats.map((c, k) => {
                const v = entry?.breakdown?.[c.key];
                return <td key={c.key} className={`cat${k === 0 ? " divl" : ""}${v < 0 ? " neg" : ""}`}>{v == null ? "" : signed(v)}</td>;
              })}
            <td className="fpts divl">
              {entry && <><span className="a">{fmt(entry.week_score ?? 0, entry.kind)}</span>{entry.games_left > 0 && <span className="tm-proj p">{fmt(entry.projected, entry.kind)}</span>}</>}
            </td>
          </>
        ) : (
          <>
            {days.map((d, k) => {
              const g = entry?.games.find(x => x.date === d);
              const cls = `day${d === data.as_of ? " today" : ""}${k === 0 ? " divl" : ""}`;
              if (!g) return <td key={d} className={cls} />;
              if (g.played) {
                const isBest = entry.kind === "player" && g.points != null && g.points === entry.week_score;
                return <td key={d} className={cls}><span className={`tm-cell played${isBest ? " best" : ""}`}>{g.points == null ? "DNP" : fmt(g.points, entry.kind)}</span></td>;
              }
              return <td key={d} className={cls}><span className="tm-cell">{oppText(g)}{entry.game_proj != null && <i className="tm-proj">{fmt(entry.game_proj, entry.kind)}</i>}</span></td>;
            })}
            <td className="games divl"><Counts e={entry} /></td>
            <td className="num prob">{entry ? "—" : ""}</td>
          </>
        )}
        <td className="act"><span className="tm-act">{action(slot, entry)}{entry && canEdit && !moving && <RowMenu name={entry.name} />}</span></td>
      </tr>
    );

    const starters = spots.filter(s => s.slot !== "BENCH");
    const bench = spots.filter(s => s.slot === "BENCH");

    body = (
      <div className="tm">
        <TeamHeader team={team} teams={teams} standings={results?.standings} user={user} onPick={o => { setMoving(null); navigate(teamPath(o)); }} />

        <div className="tm-weekbar">
          <button type="button" className="tm-btn" disabled={data.week.week <= 1} onClick={() => { setMoving(null); setWeekNo(data.week.week - 1); }}>‹</button>
          <b className="tm-week">{data.week.label} · {RANGE(data.week.start, data.week.end)}</b>
          <button type="button" className="tm-btn" disabled={data.week.week >= data.weeks.length} onClick={() => { setMoving(null); setWeekNo(data.week.week + 1); }}>›</button>
          {!past && <LockClock lock={data.week_lock} next={data.next_lock} asOf={data.as_of} />}
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
            <table className={`tm-table ${view === "schedule" ? "sched" : "pts"}`}>
              <thead>
                <tr>
                  <th className="spot" aria-label="Spot" /><th className="hs l">Player</th><th className="who" />
                  {view === "points" ? (
                    <>{cats.map((c, k) => <th key={c.key} className={`cat${k === 0 ? " divl" : ""}`} title={c.name}>{c.label}</th>)}<th className="fpts divl">FPTS</th></>
                  ) : (
                    <>{days.map((d, k) => <th key={d} className={`day${d === data.as_of ? " today" : ""}${k === 0 ? " divl" : ""}`}>{WEEKDAY(d)}<br /><span>{MD(d)}</span></th>)}
                      <th className="games divl">Games</th><th className="num prob" title="Chance he plays at least one game this week">1+ Game %</th></>
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
      </div>
    );
  }

  return <FantasyShell title="Roster">{body}</FantasyShell>;
}
