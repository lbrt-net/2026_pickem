import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import LockClock, { LockIcon } from "../../components/fantasy/LockClock";
import { Headshot, NbaTeamSquare } from "../../components/fantasy/RosterBits";
import { NBA_TEAMS, nameLines } from "../../components/fantasy/nbaTeams";
import { textOnColor } from "../../components/fantasy/teamColors";
import { EntityLink } from "../../components/fantasy/links";
import { API_BASE, base, teamPath, useFantasyApi } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";
import GlossaryButton from "../../components/fantasy/GlossaryButton";
import { InjuryDot } from "../../components/fantasy/InjuryDot";
import { backText, injuryKind, injuryWord, useInjuries } from "../../components/fantasy/injuries";
import { winText } from "../../components/fantasy/teamWeeks";
import "./TeamManagement.css";

// Roster (design: canvas "Roster v2"). /team = yours, /team/:ownerId = anyone's — the team header is
// the switcher. No score here: scores live on Matchup.
// Forward-looking: once all your starters have locked it opens on next week. Opens on Fantasy Points; Schedule =
// day columns, each future game's projection in italics. Points = each player's best game
// broken down by scoring category. Past weeks are read-only. LED lock clock, headshots on every row.
// Move: drag a row onto another spot (see below). Each player locks 5 min before his NBA team's first game of the
// week; a move involving a locked player counts from next week.

const SPOT = { G: "G", F: "F", C: "C", TEAM: "TM", FLEX: "FLX", BENCH: "Bench", IR: "IR" };
const WEEKDAY = d => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { weekday: "short" });
const MD = d => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { month: "numeric", day: "numeric" });
const RANGE = (a, b) => `${new Date(`${a}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })} – ${new Date(`${b}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;
const fmt = (v, kind) => (v == null ? "—" : `${kind === "nba_team" && v > 0 ? "+" : ""}${Number(v).toFixed(1)}`);
const oppText = g => `${g.home ? "vs" : "@"} ${g.opp}`;

// IR: only players with a red / yellow dot (out or day-to-day on the injury report).
const irOk = (e, inj) => e.kind === "player" && (!!injuryKind(inj) || inj?.status === "Out For Season");

function canPlay(e, slot, inj) {
  if (slot === "IR") return irOk(e, inj);
  if (e.slot === "IR" && slot !== "IR" && !canPlay({ ...e, slot: null }, slot)) return false;
  if (slot === "FLEX" || slot === "BENCH") return true;
  if (e.kind === "nba_team") return slot === "TEAM";
  return slot === e.position;
}

// Moving players: press and drag a row onto another spot (mouse; a finger presses and holds first) — only spots he can legally play light up;
// dropping on a filled spot swaps when the other player fits his old spot. Locked players (and IR-locked) don't drag.
// The row's one action is Drop (asks first; he goes straight back to the free-agent pool).

// Fantasy Points view: one stat bar per row instead of a column per category (players and NBA teams score different
// things, and any spot from TM to Bench can hold an NBA team). Every category gets its own labelled block (at least
// MIN_PX wide so it reads), the rest in proportion; plus parts biggest first, then minus parts (red). Bar length:
// 60% of the cell plus up to 40% more by his weekly score against the page's best, so lengths stay consistent. The header toggle picks the numbers:
// Projected · Actual (Season through today / Last week / Last 4 weeks / Last 6 weeks — real Mon–Sun weeks, never the
// current one) · past seasons.
const HISTORY = ["2025-26", "2024-25", "2023-24", "2022-23"];
const VIEWS = [["proj", "Projected"], ["actual", "Actual"], ...HISTORY.map(h => [h, `'${h.slice(-2)}`])];
const WINDOWS = [["season", "Season"], ["w1", "Last week"], ["w4", "Last 4 weeks"], ["w6", "Last 6 weeks"]];
const MIN_PX = 34;
const shade = (c, parts) => {
  const same = parts.filter(x => (x.points < 0) === (c.points < 0));
  const i = same.indexOf(c), n = Math.max(1, same.length - 1);
  return c.points < 0 ? Math.round(78 - (i / n) * 34) : Math.round(46 - (i / n) * 26);
};
function StatBar({ parts, score, scale }) {
  if (!parts?.length) return null;
  // Bars stay close in length (60% of the cell at least, the rest by how big his week is), so they read as a set
  const w = 60 + 40 * Math.min(1, Math.max(0, score || 0) / scale);
  return (
    <div className="tm-bar" style={{ width: `${w}%`, minWidth: `${parts.length * (MIN_PX + 1)}px` }}>
      {parts.map(c => (
        <span key={c.label} className={`tm-bpart${c.points < 0 ? " neg" : ""}`} style={{ flex: `${Math.abs(c.points)} 1 0`, "--l": `${shade(c, parts)}%` }} title={`${c.label} ${c.points > 0 ? "+" : ""}${c.points}`}>
          <span className="seg">{Math.abs(c.points)}</span>
          <span className="call">{c.label}</span>
        </span>
      ))}
    </div>
  );
}

// Locked: a big outline lock drawn behind the spot name (the label itself doesn't change). Unlocked: nothing. Every
// spot of a past week is locked, empty ones and IR included.
const BIG_LOCK = ( // the outline of a solid padlock silhouette (thick shackle + body), like the recap's outlined WEEK N
  <svg className="tm-biglock" viewBox="0 0 40 48" aria-hidden="true">
    <path d="M8.5 22V15a11.5 11.5 0 0 1 23 0V22H32a4 4 0 0 1 4 4v16a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4V26a4 4 0 0 1 4-4Z M14 22V15a6 6 0 0 1 12 0V22Z"
      fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
  </svg>
);
function SpotChip({ slot, locked }) {
  return <span className="tm-slotlabel" title={locked ? "Locked" : slot === "FLEX" ? "Flex" : undefined}>{locked && BIG_LOCK}<span className="t">{SPOT[slot]}</span></span>;
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
// Current injury (present only): a red / yellow dot on the headshot and the status on the small line —
// "C · DEN · Out · back Nov 12" or "· Day-to-day".
function WhoCells({ e, past, inj }) {
  if (!e) return <><td className="hs" /><td className="who"><span className="tm-open">Open</span></td></>;
  const [, last] = nameLines(e);
  const sub = e.kind === "nba_team" ? "TM" : `${e.position || "—"} · ${e.nba_team || ""}`;
  const locked = past || e.locked;
  return (
    <>
      <td className="hs">{e.kind === "player" ? <Headshot playerId={e.id} tricode={e.nba_team} width={48} height={35} /> : <NbaTeamSquare tricode={e.id} size={26} />}<InjuryDot inj={inj} /></td>
      <td className="who">
        <EntityLink id={e.id} name={last} style={{ color: "inherit", textDecoration: "none" }} />
        <span className="tm-sub">{sub}{injuryKind(inj) && <> · <span className={`inj-word ${injuryKind(inj)}`}>{injuryWord(inj)}</span>{injuryKind(inj) === "out" && backText(inj) && ` · back ${backText(inj)}`}</>}</span>
        <span className="tm-lockline">{!locked && e.games.length ? tipText(e.games[0]) : null}</span>
      </td>
    </>
  );
}

function Counts({ e }) {
  if (!e) return null;
  const done = e.games_done ?? e.games.filter(g => g.played).length;
  const today = e.games_today || 0;
  const left = Math.max(0, (e.games_left || 0) - today);
  const g = n => `${n} ${n === 1 ? "game" : "games"}`;
  return (
    <span className="tm-counts">
      <span title={`${g(done)} complete`}><i className="k done" />{done}</span><span title={`${g(today)} in progress`}><i className="k today" />{today}</span><span title={`${g(left)} left`}><i className="k later" />{left}</span>
    </span>
  );
}

// Team header = team switcher, in the Matchup banner's housing: the team plate (click to switch teams) inset on the
// left, the lock countdown in a recessed window on the right. No score. Rank shows once a week is final.
function TeamHeader({ team, teams, standings, ranked, aside, onPick }) {
  const [open, setOpen] = useState(false);
  const rank = id => { if (!ranked) return null; const i = standings?.findIndex(r => r.team.id === id) ?? -1; return i === -1 ? null : i + 1; };
  const rec = id => { const r = standings?.find(x => x.team.id === id); return r ? `${r.w}-${r.l}${r.t ? `-${r.t}` : ""}` : null; };
  const ord = n => `${n}${["th", "st", "nd", "rd"][n % 100 >= 11 && n % 100 <= 13 ? 0 : Math.min(n % 10, 4) % 4] || "th"}`;
  const line = t => [t.abbreviation, rec(t.id), rank(t.id) && ord(rank(t.id)), t.owner_name].filter(Boolean).join(" · ");
  const list = teams.filter(t => t.owner_user_id).sort((a, b) => (rank(a.id) ?? 99) - (rank(b.id) ?? 99) || a.name.localeCompare(b.name));
  return (
    <section className="tm-head" onBlur={e => { if (!e.currentTarget.contains(e.relatedTarget)) setOpen(false); }}>
      <button type="button" className="tm-head-btn" style={{ "--team": team.color || "var(--surface-2)", "--on": textOnColor(team.color) }}
        aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen(o => !o)}>
        <TeamIcon team={team} size={44} />
        <span className="tm-head-txt"><span className="n">{team.name} <span aria-hidden="true">▾</span></span><span className="s">{line(team)}</span></span>
      </button>
      {aside && <span className="tm-head-led">{aside}</span>}
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
    </section>
  );
}

// The NBA team color for a row's wash (the player's team, or the NBA team itself).
const nbaColor = e => (e ? NBA_TEAMS[e.kind === "nba_team" ? e.id : e.nba_team]?.primary : null);

export default function TeamManagement() {
  const { ownerId } = useParams();
  const navigate = useNavigate();
  const user = useCurrentUser();
  const [scenario] = useFantasyScenario();
  const teams = useFantasyApi("teams");
  const results = useFantasyApi("results");
  const injuries = useInjuries();
  const [viewPick, setView] = useState(null); // null = Fantasy Points
  const [weekNo, setWeekNo] = useState(null);
  const [data, setData] = useState(undefined);
  const [moving, setMoving] = useState(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState(null);
  const [irAsk, setIrAsk] = useState(null); // {slot, swapWith}: the IR confirm pop-up
  const [drag, setDrag] = useState(null); // {entry, x, y, over}: a row being dragged
  const dragRef = useRef({ start: null, entry: null, drop: null, legal: null, moved: false });
  const [barView, setBarView] = useState(null); // null = Projected until Week 1 is final, then Actual
  const [barWin, setBarWin] = useState("season");
  const [barData, setBarData] = useState({ key: null, data: undefined });

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
  async function moveTo(slot, swapWith, confirm = false, mover = moving) {
    setBusy(true); setNote(null);
    try {
      const r = await fetch(`${API}${API_BASE}/team/${encodeURIComponent(team.id)}/move?scenario=${scenario}`, {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entity_id: mover.id, to_slot: slot, swap_with: swapWith || null, week: data.week.week, confirm }),
      });
      const out = await r.json().catch(() => ({}));
      if (!r.ok) { setNote({ error: true, text: out.detail || "Couldn't move him" }); return; }
      setMoving(null);
      load();
    } finally {
      setBusy(false);
    }
  }

  // Drop: like the Players page, a Drop goes into a Moves box at the bottom first. From there, Drop now (the same
  // checkout Players uses), or Add players → opens Players with these drops already in its Moves box.
  const [dropList, setDropList] = useState([]);
  const drop = entry => setDropList(l => (l.some(e => e.id === entry.id) ? l.filter(e => e.id !== entry.id) : [...l, entry]));
  async function confirmDrops() {
    setBusy(true); setNote(null);
    try {
      const r = await fetch(`${API}${API_BASE}/team/${encodeURIComponent(team.id)}/checkout?scenario=${scenario}`, {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ adds: [], drops: dropList.map(e => e.id), apply: true }),
      });
      const out = await r.json().catch(() => ({}));
      if (!r.ok) { setNote({ error: true, text: out.detail || "Couldn't drop them" }); return; }
      setNote({ text: `${dropList.map(e => e.name).join(", ")} dropped.` });
      setDropList([]);
      load();
    } finally {
      setBusy(false);
    }
  }
  const toPlayers = () => {
    try { sessionStorage.setItem("fantasyMoves", JSON.stringify({ scenario, drops: dropList.map(e => e.id) })); } catch { /* storage unavailable */ }
    navigate(`${base()}/players`);
  };
  useEffect(() => { setDropList([]); }, [team?.id]);

  const spots = useMemo(() => {
    if (!data) return [];
    const left = [...data.entries];
    return [...data.slot_list, ...(data.ir_list || [])].map(slot => {
      const i = left.findIndex(e => e.slot === slot);
      return { slot, entry: i === -1 ? null : left.splice(i, 1)[0] };
    });
  }, [data]);
  useEffect(() => {
    const st = dragRef.current;
    const rowAt = (x, y) => {
      const tr = document.elementFromPoint(x, y)?.closest("tr[data-idx]");
      return tr ? Number(tr.dataset.idx) : null;
    };
    const move = e => {
      if (!st.start) return;
      if (st.touch && !st.armed) {  // finger moved before the hold finished: it's a scroll, not a drag
        if (Math.hypot(e.clientX - st.start.x, e.clientY - st.start.y) > 8) { clearTimeout(st.hold); st.start = null; st.entry = null; }
        return;
      }
      if (!st.moved && Math.hypot(e.clientX - st.start.x, e.clientY - st.start.y) < 6) return;
      st.moved = true;
      e.preventDefault();
      setDrag({ entry: st.entry, x: e.clientX, y: e.clientY, over: rowAt(e.clientX, e.clientY) });
    };
    const up = e => {
      clearTimeout(st.hold);
      if (!st.start) return;
      st.armed = false;
      const was = st.moved, entry = st.entry, over = was ? rowAt(e.clientX, e.clientY) : null;
      st.start = null; st.entry = null;
      setDrag(null);
      if (was) {
        setTimeout(() => { st.moved = false; }, 0); // the click that follows a drag doesn't open the player card
        if (over != null && st.drop) st.drop(entry, over);
      }
    };
    const noScroll = e => { if (st.armed) e.preventDefault(); };  // while a held row is being dragged, the page stays put
    window.addEventListener("pointermove", move, { passive: false });
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
    window.addEventListener("touchmove", noScroll, { passive: false });
    return () => {
      window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); window.removeEventListener("pointercancel", up);
      window.removeEventListener("touchmove", noScroll);
    };
  }, []);

  const weekOneDone = (results?.weeks || []).some(w => w.status === "final");
  const bv = barView || (weekOneDone ? "actual" : "proj");
  const barIds = (data?.entries || []).map(e => e.id).join(",");
  const barKey = team && barIds ? `${team.id}|${barIds}|${bv}|${barWin}|${scenario}` : null;
  useEffect(() => {
    if (!barKey) return undefined;
    let live = true;
    const q = new URLSearchParams({ ids: barIds, view: bv, window: barWin, scenario });
    fetch(`${API}${API_BASE}/team/${encodeURIComponent(team.id)}/bars?${q}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null)
      .then(d => { if (live) setBarData({ key: barKey, data: d }); });
    return () => { live = false; };
  }, [barKey, barIds, bv, barWin, scenario, team]);
  const rawBars = barData.key === barKey ? barData.data?.entities || {} : {};
  // Projected = this week's weekly number (the week view's `projected`, same as Matchup), its category split in the
  // shares of his projection; an out player's week is 0 (2026-10-21)
  const bars = useMemo(() => {
    if (bv !== "proj" || !data) return rawBars;
    const out = { ...rawBars };
    for (const e of data.entries || []) {
      const b = rawBars[e.id];
      if (e.projected == null) continue;
      const k = b?.score ? e.projected / b.score : 0;
      out[e.id] = { ...(b || {}), score: e.projected, parts: (b?.parts || []).map(p => ({ ...p, points: Math.round(p.points * k * 10) / 10 })).filter(p => p.points) };
    }
    return out;
  }, [rawBars, bv, data]);

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
    const view = viewPick || "points"; // Fantasy Points first, every week
    // IR lock covers every lineup through Week ir_until; a later week (viewed during his last IR week) is free.
    const irLocked = e => e?.slot === "IR" && e.ir_until != null && data.week.week <= e.ir_until;
    const canDrag = e => canEdit && !past && e && e.on_roster !== false && !(data.is_current && e.locked) && !irLocked(e);
    const legal = (mover, slot, entry) => {
      if (!mover || (entry && entry.id === mover.id) || (!entry && slot === mover.slot)) return false;
      if (!canPlay(mover, slot, injuries[mover.id])) return false;
      if (!entry) return true;
      if (mover.slot === "IR" || irLocked(entry) || (data.is_current && entry.locked)) return false;
      return canPlay(entry, mover.slot, injuries[entry.id]);
    };
    dragRef.current.drop = (mover, idx) => {
      const { slot, entry } = spots[idx] || {};
      if (!slot || !legal(mover, slot, entry)) return;
      setNote(null);
      if (slot === "IR") { setMoving(mover); setIrAsk({ slot, swapWith: entry?.id }); return; }
      moveTo(slot, entry?.id, false, mover);
    };
    const startDrag = (e, entry) => {
      if (!canDrag(entry) || e.button > 0) return;
      const st = dragRef.current;
      st.start = { x: e.clientX, y: e.clientY };
      st.entry = entry;
      st.touch = e.pointerType === "touch";
      st.armed = false;
      clearTimeout(st.hold);
      // A finger has to press and hold first (a quick swipe scrolls the page); then the row lifts and drags.
      if (st.touch) {
        const { clientX: x, clientY: y } = e;
        st.hold = setTimeout(() => {
          if (!st.start) return;
          st.armed = true;
          st.moved = true;
          navigator.vibrate?.(10);
          setDrag({ entry, x, y, over: null });
        }, 300);
      }
    };
    const action = entry => {
      if (!canEdit || past || !entry) return null;
      if (irLocked(entry)) return <span className="tm-irlock" title="On IR: can't be moved or dropped until the lock ends"><LockIcon /> through Wk {entry.ir_until}</span>;
      if (entry.on_roster === false) return null;
      const on = dropList.some(x => x.id === entry.id);
      return <button type="button" className={`tm-drop${on ? " on" : ""}`} disabled={busy} onClick={() => drop(entry)}>{on ? "Dropping ✕" : "Drop"}</button>;
    };

    // Fantasy Points view: the stat bar (StatBar above; numbers from GET /team/:id/bars).
    // Stat bar scale = the biggest weekly score on the page; FPTS = the bar's weekly score.
    const barScale = Math.max(1, ...Object.values(bars).map(b => b.score || 0));
    const barTitle = bv === "proj" ? "Projected weekly best game" : bv === "actual" ? `Weekly best game · ${WINDOWS.find(w => w[0] === barWin)[1]}` : `Weekly best game · ${bv}`;
    const firstBench = spots.findIndex(s => s.slot === "BENCH");
    const firstIr = spots.findIndex(s => s.slot === "IR");
    const row = ({ slot, entry }, i) => (
      <tr key={i} data-idx={i} style={{ "--ca": nbaColor(entry) || "transparent" }} onPointerDown={e => startDrag(e, entry)}
        onClickCapture={e => { if (dragRef.current.moved) { e.preventDefault(); e.stopPropagation(); } }}
        className={[drag && entry?.id === drag.entry.id ? "moving" : "", drag && legal(drag.entry, slot, entry) ? (drag.over === i ? "drop-over" : "drop-ok") : "", canDrag(entry) ? "draggable" : "", slot === "BENCH" ? "bench" : slot === "IR" ? "ir" : "", (slot === "BENCH" && i === firstBench) || (slot === "IR" && i === firstIr) ? "bench-start" : ""].join(" ").trim()}>
        <td className="spot"><SpotChip slot={slot} locked={past || (!!entry && (entry.locked || irLocked(entry)))} /></td>
        <WhoCells e={entry} past={past} inj={entry && injuries[entry.id]} />
        {view === "points" ? (
          <>
            <td className="statbar divl">{entry && <StatBar parts={bars[entry.id]?.parts} score={bars[entry.id]?.score} scale={barScale} />}</td>
            <td className="fpts divl">
              {entry && bars[entry.id] && <span className={`a${bv === "proj" ? " tm-proj" : ""}`}>{fmt(bars[entry.id].score)}</span>}
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
                // played: opponent on top, score · minutes under it (a low score in few minutes reads differently)
                return <td key={d} className={cls}><span className={`tm-cell played${isBest ? " best" : ""}`}>{oppText(g)}
                  <b>{g.points == null ? "DNP" : fmt(g.points, entry.kind)}{g.min != null && <small className="tm-min"> · {g.min}m</small>}</b></span></td>;
              }
              // Out until his return date: the games before it read OUT instead of a projection.
              const inj = injuries[entry.id];
              const misses = injuryKind(inj) === "out" && (!inj.return_date || g.date < inj.return_date);
              return <td key={d} className={cls}><span className="tm-cell">{oppText(g)}{misses ? <b className="tm-miss">OUT</b> : (g?.proj ?? entry.game_proj) != null && <i className="tm-proj">{fmt(g?.proj ?? entry.game_proj, entry.kind)}</i>}</span></td>;
            })}
            <td className="games divl"><Counts e={entry} /></td>
            <td className={`num prob${entry?.play_prob != null && entry.play_prob < 0.5 ? " low" : ""}`}>{winText(entry?.play_prob)}</td>
          </>
        )}
        <td className="act"><span className="tm-act">{action(entry)}</span></td>
      </tr>
    );

    const starters = spots.filter(s => s.slot !== "BENCH" && s.slot !== "IR");
    const bench = spots.filter(s => s.slot === "BENCH");
    const ir = spots.filter(s => s.slot === "IR");
    const cols = 3 + (view === "points" ? 2 : days.length + 2) + 1;

    body = (
      <div className="tm">
        <TeamHeader team={team} teams={teams} standings={results?.standings} ranked={(results?.weeks || []).some(w => w.status === "final")}
          aside={!past && <LockClock lock={data.week_lock} next={data.next_lock} asOf={data.as_of} />}
          onPick={o => { setMoving(null); navigate(teamPath(o)); }} />

        <div className="tm-weekbar">
          <button type="button" className="tm-btn page-btn" disabled={data.week.week <= 1} onClick={() => { setMoving(null); setWeekNo(data.week.week - 1); }}>‹</button>
          <span className="tm-week"><b>{data.week.label}</b><span className="wk-range">{RANGE(data.week.start, data.week.end)}</span></span>
          <button type="button" className="tm-btn page-btn" disabled={data.week.week >= data.weeks.length} onClick={() => { setMoving(null); setWeekNo(data.week.week + 1); }}>›</button>
          <span className="tm-seg" role="radiogroup" aria-label="View">
            {[["points", "Fantasy Points"], ["schedule", "Schedule"]].map(([k, l]) => (
              <button key={k} type="button" role="radio" aria-checked={view === k} onClick={() => setView(k)}>{l}</button>
            ))}
          </span>
        </div>

        <div className="tm-barbar">
          {view === "points" && <>
            <span className="tm-seg" role="radiogroup" aria-label="Numbers">
              {VIEWS.map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={bv === k} onClick={() => setBarView(k)}>{l}</button>)}
            </span>
            {bv === "actual" && (
              <span className="tm-seg" role="radiogroup" aria-label="Weeks">
                {WINDOWS.map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={barWin === k} onClick={() => setBarWin(k)}>{l}</button>)}
              </span>
            )}
          </>}
          {/* that week's opponent (like Fantrax): the name links to their roster; Bye if none */}
          <span className="tm-opp">
            <span className="lbl">Opponent</span>
            {(() => {
              const o = teams.find(t => t.id === data.opponent?.id) || data.opponent;
              return o
                ? <a href={teamPath(o.owner_user_id)} onClick={ev => { ev.preventDefault(); setMoving(null); navigate(teamPath(o.owner_user_id)); }}><TeamIcon team={o} size={20} />{o.name}</a>
                : <b>Bye</b>;
            })()}
          </span>
        </div>
        {dropList.length > 0 && (
          <div className="tm-moves" aria-label="Moves">
            <b>Moves</b>
            {dropList.map(e => <span key={e.id} className="tm-mv"><i>−</i>{e.name}</span>)}
            <span className="tm-go">
              <button type="button" className="tm-btn small" onClick={() => setDropList([])}>Clear</button>
              {mine && <button type="button" className="tm-btn small" onClick={toPlayers}>Add players →</button>}
              <button type="button" className="tm-btn primary small" disabled={busy} onClick={confirmDrops}>Drop now</button>
            </span>
          </div>
        )}
        {drag && <div className="tm-ghostrow" style={{ left: drag.x + 12, top: drag.y - 14 }}>{drag.entry.name}</div>}
        {note && <div className={`tm-result${note.error ? " error" : ""}`} role="status">{note.text}</div>}
        {irAsk && moving && (
          <div className="tm-modal" role="dialog" aria-modal="true" aria-label="Move to IR" onClick={e => { if (e.target === e.currentTarget) setIrAsk(null); }}>
            <div className="tm-modal-box">
              <b className="tm-modal-h">Move {moving.name} to IR?</b>
              <p>He'll be locked on IR through <b>Week {data.ir_week_now + data.ir_lock_weeks}</b> — the next {data.ir_lock_weeks} weeks. Until then he can't be moved back or dropped.</p>
              <div className="tm-modal-f">
                <button type="button" className="tm-btn primary" disabled={busy} onClick={async () => { await moveTo(irAsk.slot, irAsk.swapWith, true); setIrAsk(null); setMoving(null); }}>Move to IR</button>
                <button type="button" className="tm-btn" onClick={() => { setIrAsk(null); setMoving(null); }}>Cancel</button>
              </div>
            </div>
          </div>
        )}

        <section className="tm-card">
          <div className="tm-scroll">
            <table className={`tm-table ${view === "schedule" ? "sched" : "pts"}`}>
              <thead>
                <tr>
                  <th className="spot" aria-label="Spot" /><th className="hs l">Player</th><th className="who" />
                  {view === "points" ? (
                    <><th className="statbar divl">{barTitle}<GlossaryButton terms={["FPTS", "FG-", "FT-", "3PTM", "BLKD", "Δ"]} /></th><th className="fpts divl">FPTS</th></>
                  ) : (
                    <>{days.map((d, k) => <th key={d} className={`day${d === data.as_of ? " today" : ""}${k === 0 ? " divl" : ""}`}>{WEEKDAY(d)}<br /><span>{MD(d)}</span></th>)}
                      <th className="games divl">Games</th><th className="num prob" title="Chance he plays at least one game this week">1+ Game %</th></>
                  )}
                  <th className="act" />
                </tr>
              </thead>
              <tbody>
                {starters.map(row)}
                {bench.length > 0 && <tr className="tm-sec"><td colSpan={cols}>Bench</td></tr>}
                {bench.map((s, i) => row(s, starters.length + i))}
                {ir.length > 0 && <tr className="tm-gap" aria-hidden="true"><td colSpan={cols} /></tr>}
                {ir.map((s, i) => row(s, starters.length + bench.length + i))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    );
  }

  return <FantasyShell title="Roster">{body}</FantasyShell>;
}
