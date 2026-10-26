import { Fragment, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import LedScore from "../../components/fantasy/LedScore";
import { Headshot, NbaTeamSquare } from "../../components/fantasy/RosterBits";
import { nameLines } from "../../components/fantasy/nbaTeams";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { API_BASE, rosterBySlot, teamPath, useFantasyApi } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import { load as loadCached, useCached } from "../../components/fantasy/cache";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";
import { useTeamWeeks, useWinProbs, winProb, winText, refreshTeamWeeks } from "../../components/fantasy/teamWeeks";
import { NBA_TEAMS } from "../../components/fantasy/nbaTeams";
import { accent, bigGameFirst, scheduleOf, standingsFrom } from "../../components/fantasy/standings";
import { textOnColor } from "../../components/fantasy/teamColors";
import FitText from "../../components/fantasy/FitText";
import GlossaryButton from "../../components/fantasy/GlossaryButton";
import { InjuryDot } from "../../components/fantasy/InjuryDot";
import "./Matchup.css";

// Matchup (design: canvas "Matchup v6"). ?week=N&team=<ownerId>&view=all — state in the URL so
// other pages can link straight in. Data: /results (every matchup's score, records) and
// /team/:id/week for both sides (spots, games, best game's top-5 contributions, projections).
// Row, each side mirrored: headshot · player · schedule · FPTS contribution · score | spot | ...
// Schedule counts: white dot = played, orange = today, outlined = still to play — the same dot marks a game's label
// (best game = played, next game = still to play; 2026-10-24).

const SPOT = { G: "G", F: "F", C: "C", TEAM: "TM", FLEX: "FLX", BENCH: "Bench", IR: "IR" };
const WEEKDAY = d => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { weekday: "short" });
const MD = d => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { month: "numeric", day: "numeric" });
const RANGE = (a, b) => `${new Date(`${a}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })} – ${new Date(`${b}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;
const fmt = (v, kind) => `${kind === "nba_team" && v > 0 ? "+" : ""}${Number(v ?? 0).toFixed(1)}`;
// Hover on the schedule cell: his whole week, one game per line, no abbreviations — played (with his score), live
// now, and still to come ("Thursday, Oct 15 vs Indiana Pacers") — ending with how many are left.
const teamName = t => (NBA_TEAMS[t] ? `${NBA_TEAMS[t].city} ${NBA_TEAMS[t].nickname}` : t);
const scheduleTip = e => {
  const gs = e.games || [];
  if (!gs.length) return "No games this week";
  const line = g => {
    const when = new Date(`${g.date}T12:00:00`).toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" });
    const tail = g.live ? ` — live now${g.points != null ? `, ${g.points} so far` : ""}` : g.played ? (g.points != null ? ` — ${g.points}` : " — didn't play") : g.out ? " — out" : "";
    return `${when} ${g.home ? "vs" : "at"} ${teamName(g.opp)}${tail}`;
  };
  // first line = the dots, spelled out
  const done = e.games_done || 0, now = e.games_today || 0, left = Math.max(0, (e.games_left || 0) - now);
  const n = (k, w) => `${k} ${k === 1 ? "game" : "games"} ${w}`;
  return [`${n(done, "complete")} · ${n(now, "in progress")} · ${n(left, "left")}`, ...gs.map(line)].join("\n");
};
const signed = v => `${v > 0 ? "+" : "−"}${Math.abs(v)}`;

function useWeek(teamId, week, scenario, tick = 0) {
  // through the visit's store (cache.js); `tick` = refresh it now — while a refresh loads, the last numbers stay up
  const url = teamId ? `${API}${API_BASE}/team/${encodeURIComponent(teamId)}/week?${new URLSearchParams({ scenario, ...(week ? { week } : {}) })}` : null;
  const data = useCached(url);
  useEffect(() => { if (url && tick) loadCached(url, true); }, [url, tick]);
  return data;
}

// tips: per-dot hover text (the banner); in a player's schedule cell the whole cell, dots included, shows one hover:
// the dots spelled out on the first line, then his full week
function Counts({ done, today, left, className = "", tips = true }) {
  const t = (n, what) => (tips ? `${n} ${n === 1 ? "game" : "games"} ${what}` : undefined);
  return (
    <span className={`mu-counts ${className}`}>
      <span title={t(done, "complete")}><i className="mu-k done" />{done}</span>
      <span title={t(today, "in progress")}><i className="mu-k today" />{today}</span>
      <span title={t(left, "left")}><i className="mu-k later" />{left}</span>
    </span>
  );
}

const countsOf = list => list.reduce((c, e) => ({
  done: c.done + (e.games_done || 0), today: c.today + (e.games_today || 0),
  left: c.left + Math.max(0, (e.games_left || 0) - (e.games_today || 0)),
}), { done: 0, today: 0, left: 0 });

function Side({ team, record, right }) {
  // the whole team panel opens that team's roster (2026-10-25)
  const nav = useNavigate();
  const go = () => team?.owner_user_id && nav(teamPath(team.owner_user_id));
  return (
    <div className={`mu-side go${right ? " r" : ""}`} role="link" tabIndex={0} onClick={go} onKeyDown={e => e.key === "Enter" && go()}
      style={{ "--team": team?.color || "var(--surface-2)", "--on": textOnColor(team?.color) }}>
      <TeamIcon team={team} size={52} />
      <div className="mu-plate">
        <span className="mu-abbr">{team?.abbreviation || team?.name}</span>
        <span className="mu-tname"><TeamLink ownerId={team?.owner_user_id} name={team?.name} />{record ? ` · ${record}` : ""}</span>
      </div>
    </div>
  );
}

// Which updates to animate: on a fresh page, whatever landed in the last 60 seconds (two 30s pulls), added up into one; after that, each new one as it
// arrives. Several at once play one after another, ~1.3s apart, each pulsing its blocks.
function useReplay(id, updates) {
  const newest = updates?.[0]?.at;
  const [play, setPlay] = useState({ newest: null, queue: [], i: 0 });
  const [openedAt] = useState(() => new Date(Date.now() - 60000).toISOString());  // page opened: the last 60s replay
  if (newest && play.newest !== newest) {
    const since = play.newest || openedAt;
    let fresh = (updates || []).filter(u => u.at > since).reverse();
    if (!play.newest && fresh.length > 1) {  // fresh page: the last 60s added up into one update
      const parts = {};
      for (const u of fresh) for (const x of u.parts) {
        const p = (parts[x.label] ||= { label: x.label, points: 0, n: 0 });
        p.points = Math.round((p.points + x.points) * 10) / 10;
        p.n = (p.n || 0) + (x.n || 0);
      }
      const last = fresh[fresh.length - 1];
      fresh = [{ ...last, delta: Math.round(fresh.reduce((a, u) => a + u.delta, 0) * 10) / 10,
        parts: Object.values(parts).filter(p => p.points !== 0).map(p => ({ ...p, n: p.n || null })) }];
    }
    setPlay({ newest, queue: fresh, i: 0 });
  }
  useEffect(() => {
    if (play.i >= play.queue.length - 1) return undefined;
    const t = setTimeout(() => setPlay(p => ({ ...p, i: p.i + 1 })), 1300);
    return () => clearTimeout(t);
  }, [play]);
  return play.queue.length ? play.queue[play.i] : null;
}

// A live NBA team (2026-10-20): the bar = how its game is projected to END (every stat on pace), in the same blocks as
// the others; hovering it lists every category, zeros included — its count now → on pace, its points now → projected.
// Before the 4th nothing counts yet ("–" now), only the pace.
const num = v => (v == null ? "–" : Math.round(v));
const pts = v => (v == null ? "–" : `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(Math.round(v * 10) / 10)}`);
const endParts = cats => cats.filter(c => c.pts_end).map(c => ({ label: c.label, points: c.pts_end }))
  .sort((x, y) => (x.points < 0) - (y.points < 0) || Math.abs(y.points) - Math.abs(x.points));
// every category side by side (a grid, not a table: the matchup table's cell styles stay out). Rows: the count, then
// what it's worth — each "now → end of game" (end in italics = projected on the current pace).
function TeamCats({ cats }) {
  const arrow = (a, b) => <>{a} <i>→ {b}</i></>;
  return (
    <div className="mu-tcats" style={{ gridTemplateColumns: `auto repeat(${cats.length}, auto)` }}>
      <span />{cats.map(c => <b key={c.label} title={c.name}>{c.label}</b>)}
      <span className="l">Count</span>{cats.map(c => <span key={c.label}>{arrow(num(c.now), num(c.end))}</span>)}
      <span className="l">Points</span>{cats.map(c => <span key={c.label}>{arrow(pts(c.pts_now), pts(c.pts_end))}</span>)}
    </div>
  );
}
function TeamLive({ live, best, scale }) {
  const end = endParts(live.cats);
  const size = ps => (ps || []).reduce((a, p) => a + Math.abs(p.points), 0);
  const sc = Math.max(scale || 1, size(best), size(end), 1);
  return (
    <div className="mu-live2">
      <div className="mu-lrow"><span className="mu-lmin" /><ContribBar parts={best || []} scale={sc} /></div>
      <div className="mu-lrow now"><span className="mu-lmin" /><ContribBar parts={end} scale={sc} extra={<TeamCats cats={live.cats} />} /></div>
    </div>
  );
}

function LiveBar({ id, live, best, scale }) {
  const replaying = useReplay(id, live.updates);
  const last = replaying || live.updates?.[0];
  const fresh = !!replaying;
  const parts = (live.parts || []).map(p => ({ ...p }));  // tonight's blocks, as of the update being shown
  if (replaying) {
    for (const u of live.updates || []) {
      if (u.at <= replaying.at) break;
      for (const d of u.parts) {
        const p = parts.find(x => x.label === d.label);
        if (p) p.points = Math.round((p.points - d.points) * 10) / 10;
      }
    }
  }
  const size = ps => (ps || []).reduce((a, p) => a + Math.abs(p.points), 0);
  if (live.cats) return <TeamLive live={live} best={best} scale={scale} />;  // an NBA team: projected end + breakdown
  // an NBA team before the 4th: its best game as the thin bar, nothing live yet (a player not in yet is just at 0)
  if (live.now == null && live.min == null) {
    return (
      <div className="mu-live2">
        <div className="mu-lrow"><span className="mu-lmin" /><ContribBar parts={best || []} scale={Math.max(scale || 1, size(best), 1)} /></div>
        <div className="mu-lrow now"><span className="mu-lmin" /><span className="mu-q4">No Live Proj. before Q4</span></div>
      </div>
    );
  }
  const hit = new Set(fresh && last ? last.parts.map(p => p.label) : []);
  // zero lines up: both bars reserve the same room for minus blocks (the larger of the two), so the grey/red divider
  // sits in the same spot; the scale covers the longest plus run + that room
  const pos = ps => (ps || []).filter(p => p.points > 0).reduce((a, p) => a + p.points, 0);
  const neg = ps => -(ps || []).filter(p => p.points < 0).reduce((a, p) => a + p.points, 0);
  const negRoom = Math.max(neg(best), neg(parts));
  const rowScale = Math.max(scale || 1, Math.max(pos(best), pos(parts)) + negRoom, 1);
  return (
    <div className="mu-live2">
      <div className="mu-lrow"><span className="mu-lmin">{live.best_game?.min != null ? live.best_game.min : ""}</span><ContribBar parts={best || []} scale={rowScale} negPad={negRoom - neg(best)} /></div>
      <div className="mu-lrow now"><span className="mu-lmin now">{live.min != null ? live.min : ""}</span><ContribBar parts={parts.filter(p => p.points)} scale={rowScale} hit={hit} negPad={negRoom - neg(parts)} />
        {live.clutch && live.oncourt && <span className="mu-clutch">CLUTCH</span>}
        {last && fresh && (
          <span key={last.at} className={`mu-lpop2${Math.round(last.delta * 10) === 0 ? " even" : last.delta < 0 ? " down" : ""}${last.parts.some(x => x.label === "CLUTCH") ? " clutch" : ""}`}>
            <b>{Math.round(last.delta * 10) === 0 ? "0" : `${last.delta > 0 ? "+" : "−"}${Math.abs(last.delta).toFixed(1)}`}</b> {last.parts.map(x => `${x.n ?? ""} ${x.label}`.trim()).join(", ")}
          </span>
        )}
      </div>
    </div>
  );
}
const liveClock = l => {
  const m = /PT(\d+)M([\d.]+)S/.exec(l.clock || "");
  const q = l.period > 4 ? `OT${l.period - 4 > 1 ? l.period - 4 : ""}` : `Q${l.period}`;
  return m ? `${q} ${Number(m[1])}:${String(Math.floor(Number(m[2]))).padStart(2, "0")}` : q;
};

// The best game as one bar: every category its own block, plus parts biggest first, then minus parts (red). Width =
// share of the biggest best game on the page, so rows compare. A block gets its number inside (no sign — red is
// minus) and its label on a callout line underneath when it's at least FIT_PX wide on screen — room for a two-digit
// number — so a monster game shrinks everyone else's blocks and fewer get called out. Mirrored for the right team.
const FIT_PX = 14;
// Flat blocks that step darker one by one (biggest plus brightest; minus parts step down in red) — tells neighbours
// apart without a gradient. Returns the block's mix strength, in %.
const shade = (c, parts) => {
  const same = parts.filter(x => (x.points < 0) === (c.points < 0));
  const i = same.indexOf(c), n = Math.max(1, same.length - 1);
  return c.points < 0 ? Math.round(78 - (i / n) * 34) : Math.round(46 - (i / n) * 26);
};
const W3_PX = 18; // room for "2.5"; narrower blocks round to a whole number
function ContribBar({ parts, scale, hit, negPad = 0, extra = null }) {
  const [px, setPx] = useState(0);
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const ro = new ResizeObserver(([e]) => setPx(e.contentRect.width));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  if (!parts.length) return <div className="mu-bar2" ref={ref} tabIndex={extra ? 0 : undefined}>{extra && <Zoom parts={[]} extra={extra} />}</div>;
  const sorted = [...parts.filter(c => c.points > 0).sort((a, b) => b.points - a.points),
    ...parts.filter(c => c.points < 0).sort((a, b) => a.points - b.points)];
  return (
    <div className="mu-bar2" ref={ref} tabIndex={0}>
      <Zoom parts={sorted} extra={extra} />
      {sorted.map(c => {
        const w = Math.abs(c.points) / scale;
        const wpx = w * px;
        const v = Math.abs(c.points);
        const text = wpx >= W3_PX || Number.isInteger(v) ? String(v) : String(Math.round(v));
        const big = wpx >= FIT_PX;
        // the label only when it fits under its own block (no callouts running into each other); hover lists all
        const fits = wpx >= Math.max(FIT_PX, c.label.length * 6.5 + 4);
        return (
          <span key={c.label} className={`mu-part${c.points < 0 ? " neg" : ""}${hit?.has(c.label) ? " hit" : ""}`} style={{ width: `${w * 100}%`, "--l": `${shade(c, sorted)}%` }} title={`${c.label} ${signed(c.points)}`}>
            <span className="seg">{big ? text : ""}</span>
            {fits && <span className="call">{c.label}</span>}
          </span>
        );
      })}
      {/* live rows: empty room after the minus blocks so both bars' plus/minus divider sits in the same spot */}
      {negPad > 0 && <span className="mu-negpad" style={{ width: `${(negPad / scale) * 100}%` }} />}
    </div>
  );
}

// Hovering a bar: the bar outlined, and a pop-up with the same parts zoomed in — every block labelled, tiny ones
// held at a minimum width so they can be read, the rest in proportion.
const ZOOM_PX = 380, ZOOM_MIN = 28;
function Zoom({ parts, extra = null }) {
  const total = parts.reduce((n, c) => n + Math.abs(c.points), 0) || 1;
  const small = parts.filter(c => (Math.abs(c.points) / total) * ZOOM_PX < ZOOM_MIN);
  const room = ZOOM_PX - small.length * ZOOM_MIN - parts.length; // what's left for the in-proportion blocks (minus 1px gaps)
  const bigTotal = parts.filter(c => !small.includes(c)).reduce((n, c) => n + Math.abs(c.points), 0) || 1;
  const fmt1 = v => String(Math.abs(v));
  return (
    <div className="mu-zoom" role="tooltip">
      <div className="mu-zoom-bar">
        {parts.map(c => (
          <span key={c.label} className={`mu-part${c.points < 0 ? " neg" : ""}`}
            style={{ width: small.includes(c) ? ZOOM_MIN : (Math.abs(c.points) / bigTotal) * room, "--l": `${shade(c, parts)}%` }}>
            <span className="seg">{fmt1(c.points)}</span>
            <span className="call">{c.label}</span>
          </span>
        ))}
      </div>
      {extra}
    </div>
  );
}

// Schedule view (2026-10-23): the schedule + best game columns become the week's days, Mon → Sun on both sides. A
// game day shows the opponent and that game's fantasy score (live: so far; coming up: its projection, in italics);
// hovering it zooms that game's blocks, like the best-game bar.
const byBlock = ps => [...ps.filter(c => c.points > 0).sort((a, b) => b.points - a.points),
  ...ps.filter(c => c.points < 0).sort((a, b) => a.points - b.points)];
function DayGame({ g }) {
  const parts = byBlock(g.parts || []);
  const out = <b className="mu-miss">OUT</b>;  // a game he missed or is ruled out of: one label, same as Roster
  const val = g.live ? (g.points != null ? fmt(g.points) : "–")
    : g.played ? (g.points != null ? fmt(g.points) : out)
    : g.out ? out : g.proj != null ? <i>{fmt(g.proj)}</i> : "";
  return (
    <span className={`mu-day g${g.live ? " live" : ""}${parts.length ? " has" : ""}`} tabIndex={parts.length ? 0 : undefined}>
      <span className="o">{g.home ? "vs" : "@"} {g.opp}</span>
      <span className="v">{val}</span>
      {parts.length > 0 && <Zoom parts={parts} />}
    </span>
  );
}
function Days({ e, days }) {
  const by = Object.fromEntries((e.games || []).map(g => [g.date, g]));
  return (
    <div className="mu-dgrid" style={{ "--n": days.length }}>
      {days.map(d => (by[d] ? <DayGame key={d} g={by[d]} /> : <span key={d} className="mu-day" />))}
    </div>
  );
}
const weekDays = w => {
  if (!w) return [];
  const out = [];
  for (let d = new Date(`${w.start}T12:00:00`); d <= new Date(`${w.end}T12:00:00`); d.setDate(d.getDate() + 1)) {
    out.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`);
  }
  return out;
};

// One side's cells, left to right for the left team (mirrored for the right). days = the Schedule view: one cell
// across the schedule + best game columns, plus a hidden one so every side still has five cells (the row styles
// count cells from each end).
function cells(e, side, scale, days = null) {
  const r = side === "r";
  if (days) {
    const out = cells(e, side, scale);
    const [hs, who, , , sc] = r ? [...out].reverse() : out;
    const mid = [<td key="d" className={`mu-days ${r ? "rs" : "ls"}`} colSpan={2}>{e && <Days e={e} days={days} />}</td>,
      <td key="x" className="mu-dx" />];
    const row = [hs, who, ...mid, sc];
    return r ? row.reverse() : row;
  }
  if (!e) {
    const empty = [<td key="h" className="mu-hs" />, <td key="p" className="mu-who"><span className="mu-last">Empty</span></td>,
      <td key="s" className="mu-sched" />, <td key="c" className="mu-ct" />, <td key="v" className="mu-sc" />];
    return r ? empty.reverse() : empty;
  }
  const [, last] = nameLines(e);
  const sub = e.kind === "nba_team" ? "TM" : `${e.position || "—"} · ${e.nba_team || ""}`;
  const next = e.games?.find(g => !g.played && !g.out);  // a game he's ruled out of isn't his next game
  const contrib = e.contrib || []; // players: every category of his best game; NBA teams: the team scoring parts
  // The game the best-game bar comes from (highest points so far this week).
  const best = (e.games || []).filter(g => g.played && g.points != null).reduce((m, g) => (!m || g.points > m.points ? g : m), null);
  const out = [
    <td key="h" className="mu-hs">
      {e.kind === "player"
        ? <Headshot playerId={e.id} tricode={e.nba_team} width={48} height={35} />
        : <NbaTeamSquare tricode={e.id} size={44} />}
      {/* injury status, the same dot as Roster — never on a player who has played since the report (live tonight, or a
          finished game on or after the report's date): he's in the box score */}
      <InjuryDot inj={e.live?.min > 0 || (e.games || []).some(g => g.min > 0 && e.injury?.reported_at && g.date >= e.injury.reported_at.slice(0, 10)) ? null : e.injury} />
    </td>,
    <td key="p" className="mu-who">
      <EntityLink id={e.id} name={<FitText text={last} max={15} min={11} />} style={{ color: "inherit", textDecoration: "none" }} />
      <span className="mu-sub">{sub}</span>
    </td>,
    <td key="s" className={`mu-sched${e.live ? " live" : ""}`} title={scheduleTip(e)}>
      {e.live
        ? <span className="mu-next mu-livesched">
            <span className="l1">{e.live.best_game ? <><i className="mu-k done" />{`${WEEKDAY(e.live.best_game.date)} ${MD(e.live.best_game.date)} ${e.live.best_game.home ? "vs" : "@"} ${e.live.best_game.opp}`}</> : ""}</span>
            <span className="l2"><span className="mu-live-tag">{liveClock(e.live)}</span>
              <span>{e.live.team} {e.live.score?.[0] ?? "–"}–{e.live.score?.[1] ?? "–"} {e.live.opp}</span></span>
          </span>
        : <span className="mu-next">{next ? <><i className="mu-k later" />{`${WEEKDAY(next.date)} ${MD(next.date)} ${next.home ? "vs" : "@"} ${next.opp}`}</> : ""}</span>}
      <Counts tips={false} done={e.games_done || 0} today={e.games_today || 0} left={Math.max(0, (e.games_left || 0) - (e.games_today || 0))} />
    </td>,
    // live: two identical bars on one scale and alignment — his best game this week, then tonight's game growing
    e.live ? <td key="c" className="mu-ct mu-ct-live"><LiveBar id={e.id} live={e.live} best={e.live.best_parts || []} scale={scale} /></td> :
    <td key="c" className="mu-ct">
      {best && <span className="mu-when"><i className="mu-k done" />{`${WEEKDAY(best.date)} ${MD(best.date)} ${best.home ? "vs" : "@"} ${best.opp}`}</span>}
      <ContribBar parts={contrib} scale={scale} />
    </td>,
    // live: tonight's score so far, in green; no weekly projection until the game is over
    // live: the two totals, level with their bars — best before tonight on top, tonight's so far in green
    e.live
      ? (() => {
          const b = e.live.best, n = e.live.now;
          const nowCounts = n != null && (b == null || n > b);
          return (
            <td key="v" className="mu-sc live">
              {/* the line beside the thin best-game bar: empty (but kept) when there's no earlier game, so tonight's score
                  always sits level with tonight's bar and the projection right under it (2026-10-22) */}
              <span className={`b${b != null && !nowCounts ? " counts" : ""}`}>{b != null ? fmt(b) : ""}</span>
              {n != null || e.kind === "player"
                ? <span className={`a${nowCounts ? " counts" : ""}`}>{fmt(n ?? 0)}</span>
                : <span className="a proj">–</span>}
              {/* his projected week, live too (an NBA team before the 4th: its pregame projection is in the total) */}
              <span className="p">{e.projected != null ? fmt(e.projected) : ""}</span>
            </td>
          );
        })()
      : <td key="v" className="mu-sc">
          <span className="a">{fmt(e.week_score)}</span>
          {e.live ? e.live.pace != null && <span className="p">{fmt(e.live.pace)}</span>
            : e.projected != null && <span className="p">{fmt(e.projected)}</span>}
        </td>,
  ];
  return r ? out.reverse() : out;
}

// The NBA team color for a row's wash (player's team, or the NBA team itself).
const nbaColor = e => (e ? NBA_TEAMS[e.kind === "nba_team" ? e.id : e.nba_team]?.primary : null);

function Rows({ left, right, scale, days = null }) {
  return left.map(({ slot, entry: a }, i) => {
    const b = right[i]?.entry;
    return (
      <tr key={i} className={slot === "IR" ? "ir" : ""} data-on={[a?.live && (a.live.oncourt || a.kind === "nba_team") ? "l" : "", b?.live && (b.live.oncourt || b.kind === "nba_team") ? "r" : ""].join("")} style={{ "--ca": nbaColor(a) || "transparent", "--cb": nbaColor(b) || "transparent" }}>
        {cells(a, "l", scale, days)}
        <td className="mu-slot">{slot === "BENCH" ? "" : SPOT[slot]}</td>
        {cells(b, "r", scale, days)}
      </tr>
    );
  });
}

// This week's matchup cards on one row, like a sports site's scores strip: arrow buttons at each end slide it along
// (no scrollbar); an arrow greys out at its end, and both hide when everything fits.
function Ticker({ children }) {
  const ref = useRef(null);
  const [edge, setEdge] = useState({ left: false, right: false });
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const check = () => setEdge({ left: el.scrollLeft > 1, right: el.scrollLeft + el.clientWidth < el.scrollWidth - 1 });
    check();
    el.addEventListener("scroll", check, { passive: true });
    const ro = new ResizeObserver(check);
    ro.observe(el);
    return () => { el.removeEventListener("scroll", check); ro.disconnect(); };
  }, []);
  const slide = dir => ref.current?.scrollBy({ left: dir * ref.current.clientWidth * 0.8, behavior: "smooth" });
  const fits = !edge.left && !edge.right;
  return (
    <div className={`mu-ticker${fits ? " fits" : ""}`}>
      <button className="mu-tick-btn page-btn" onClick={() => slide(-1)} disabled={!edge.left} aria-label="Earlier matchups">‹</button>
      <div className="mu-cards" ref={ref}>{children}</div>
      <button className="mu-tick-btn page-btn" onClick={() => slide(1)} disabled={!edge.right} aria-label="More matchups">›</button>
    </div>
  );
}

// Same column widths as the starters table, no header text (bench section).
function Cols() {
  return (
    <thead className="mu-cols">
      <tr><th className="w-hs" /><th className="w-who" /><th className="w-sched" /><th /><th className="w-sc" /><th className="w-slot" /><th className="w-sc" /><th /><th className="w-sched" /><th className="w-who" /><th className="w-hs" /></tr>
    </thead>
  );
}

function Head({ live, days = null }) {
  if (days) {  // Schedule view: a widths row (same columns as Scoring), then the day names over each side's days
    const dh = <th colSpan={2} className="mu-dh"><div className="mu-dgrid" style={{ "--n": days.length }}>{days.map(d => <span key={d}>{WEEKDAY(d)}</span>)}</div></th>;
    return (
      <thead>
        <tr className="mu-wrow"><th className="w-hs" /><th className="w-who" /><th className="w-sched" /><th className="mu-th-bar" /><th className="w-sc" /><th className="w-slot" /><th className="w-sc" /><th className="mu-th-bar" /><th className="w-sched" /><th className="w-who" /><th className="w-hs" /></tr>
        <tr><th /><th className="l">Player</th>{dh}<th /><th /><th />{dh}<th className="r">Player</th><th /></tr>
      </thead>
    );
  }
  // while a game is live the bar cells start with a minutes slot: labelled once here
  return (
    <thead>
      <tr>
        <th className="w-hs" /><th className="w-who l">Player</th><th className="w-sched l">Schedule</th><th className="r mu-th-bar">{live && <span className="mu-th-min">Min</span>}Best game<GlossaryButton terms={["FPTS", "FG-", "FT-", "3PTM", "Δ"]} /></th>
        <th className="w-sc" /><th className="w-slot" /><th className="w-sc" />
        <th className="l mu-th-bar">Best game{live && <span className="mu-th-min r">Min</span>}</th><th className="w-sched r">Schedule</th><th className="w-who r">Player</th><th className="w-hs" />
      </tr>
    </thead>
  );
}

// All teams, in the standings table style (team-color edge + row wash, body font): # · team · score · projected ·
// win % · points by spot · game counts. Click a row to open that matchup.
function AllTeams({ teams, week, final, slotTypes, scenario, onOpen }) {
  const weeks = useTeamWeeks((teams || []).map(t => t.id), week, scenario);
  const probOf = useWinProbs(week, scenario);
  // sortable (2026-10-20): click a header — biggest first, click again to flip; Games = most games left first
  const [sort, setSort] = useState({ k: "score", dir: -1 });
  if (!weeks) return <p className="mu-note">Loading…</p>;
  const rows = (teams || []).map(t => {
    const d = weeks[t.id];
    const st = (d?.entries || []).filter(e => e.slot !== "BENCH" && e.slot !== "IR");
    const by = Object.fromEntries(slotTypes.map(k => [k, st.filter(e => e.slot === k).reduce((n, e) => n + (e.week_score || 0), 0)]));
    return { team: t, opp: d?.opponent?.id, score: d?.starters_score ?? 0, proj: d?.starters_projected ?? 0, by, counts: countsOf(st) };
  });
  const byId = Object.fromEntries(rows.map(r => [r.team.id, r]));
  rows.forEach(r => { r.win = byId[r.opp] ? (final ? winProb(r, byId[r.opp], final) : probOf(r.team.id, r.opp) ?? null) : null; });
  const key = {
    score: r => r.score, proj: r => r.proj, win: r => r.win ?? -1, team: r => r.team.name.toLowerCase(),
    games: r => (r.counts.left || 0) + (r.counts.today || 0), ...Object.fromEntries(slotTypes.map(k => [k, r => r.by[k] ?? 0])),
  };
  const val = key[sort.k] || key.score;
  rows.sort((a, b) => {
    const x = val(a), y = val(b);
    const c = typeof x === "string" ? x.localeCompare(y) : x - y;
    // first click: numbers biggest first, team names A→Z
    return (sort.k === "team" ? -sort.dir : sort.dir) * c || b.score - a.score;
  });
  const th = (k, label, cls = "") => (
    <th className={`${cls} mu-sort${sort.k === k ? " on" : ""}`} aria-sort={sort.k === k ? (sort.dir < 0 ? "descending" : "ascending") : "none"}>
      <button type="button" onClick={() => setSort(s => ({ k, dir: s.k === k ? -s.dir : -1 }))}>{label}{sort.k === k ? (sort.dir < 0 ? " ▾" : " ▴") : ""}</button>
    </th>
  );
  return (
    <section className="mu-card">
      <table className="mu-all">
        <thead>
          <tr>
            <th className="w-edge" /><th className="l w-rank">#</th>{th("team", "Team", "l")}{th("score", "Score")}{th("proj", "Projected")}{th("win", "Win %")}
            {slotTypes.map(k => <Fragment key={k}>{th(k, SPOT[k])}</Fragment>)}{th("games", "Games", "c")}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.team.id} onClick={() => onOpen(r.team)} tabIndex={0} onKeyDown={e => e.key === "Enter" && onOpen(r.team)}
              style={{ "--tc": accent(r.team.color) }}>
              <td className="edge" />
              <td className="l rk">{i + 1}</td>
              <td className="l"><span className="mu-allteam"><TeamIcon team={r.team} size={24} /><b>{r.team.name}</b></span></td>
              <td><b>{r.score.toFixed(1)}</b></td>
              <td><i>{r.proj.toFixed(1)}</i></td>
              <td>{winText(r.win)}</td>
              {slotTypes.map(k => <td key={k}>{Number(r.by[k] ?? 0).toFixed(1)}</td>)}
              <td className="c"><Counts {...r.counts} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export default function Matchup() {
  const user = useCurrentUser();
  const [scenario] = useFantasyScenario();
  const teams = useFantasyApi("teams");
  const results = useFantasyApi("results");
  const [params, setParams] = useSearchParams();
  const set = changes => setParams(p => { Object.entries(changes).forEach(([k, v]) => p.set(k, v)); return p; }, { replace: true });

  const view = params.get("view") === "all" ? "all" : "matchup";
  const cols = params.get("cols") === "schedule" ? "schedule" : "scoring";  // the lineup table: Scoring (default) or Schedule
  // Matchup shows the week being played (Roster is the one that jumps ahead once lineups lock)
  const weekParam = Number(params.get("week")) || results?.current_week || null;
  const focusOwner = params.get("team") || user?.discordId;
  const team = teams?.find(t => t.owner_user_id === focusOwner) || teams?.[0];
  const [tick, setTick] = useState(0);
  // both sides straight from every team's week (already loaded): switching matchups is instant (2026-10-21); a team
  // not in it yet is fetched on its own
  const allWeeks = useTeamWeeks((teams || []).map(t => t.id), weekParam, scenario);
  const ownFromAll = allWeeks?.[team?.id];
  const ownFetched = useWeek(ownFromAll ? null : team?.id, weekParam, scenario, tick);
  const own = ownFromAll || ownFetched;
  const weekNo = own?.week?.week ?? weekParam;
  const oppFromAll = allWeeks?.[own?.opponent?.id];
  const oppFetched = useWeek(oppFromAll ? null : own?.opponent?.id, own?.week?.week, scenario, tick);
  const other = oppFromAll || oppFetched;
  // sides as the schedule has them (home left), whoever is viewing or was clicked — same as the cards (2026-10-24)
  const flip = !!other && scheduleOf(results, weekNo).side.get(own?.team_id) === 1;
  const data = flip ? other : own, opp = flip ? own : other;
  const teamL = (flip ? teams?.find(t => t.id === other.team_id) : team) || team;
  useEffect(() => { if (tick) refreshTeamWeeks(weekParam, scenario); }, [tick, weekParam, scenario]);
  // A game on: refresh every 30 seconds (the live pull runs every 30), and remember each player's points to flash
  // what he just added.
  const anyLive = [...(data?.entries || []), ...(opp?.entries || [])].some(e => e.live);
  useEffect(() => {
    if (!anyLive) return undefined;
    const t = setInterval(() => setTick(x => x + 1), 30000);
    const back = () => { if (document.visibilityState === "visible") setTick(x => x + 1); };  // back on the tab: refresh now
    document.addEventListener("visibilitychange", back);
    return () => { clearInterval(t); document.removeEventListener("visibilitychange", back); };
  }, [anyLive]);

  const probOf = useWinProbs(data?.week?.week, scenario, tick);

  const resWeek = results?.weeks?.find(w => w.week === weekNo);
  const record = id => {
    const r = results?.standings?.find(s => s.team.id === id);
    return r ? `${r.w}-${r.l}${r.t ? `-${r.t}` : ""}` : null;
  };
  const weeks = data?.weeks || [];
  const wi = weeks.findIndex(w => w.week === weekNo);
  const slotTypes = [...new Set((data?.slot_list || []).filter(s => s !== "BENCH"))];

  const left = data ? rosterBySlot(data.entries, data.slot_list) : [];
  const right = opp ? rosterBySlot(opp.entries, opp.slot_list) : left.map(({ slot }) => ({ slot, entry: null }));
  const starters = left.filter(r => r.slot !== "BENCH").length;
  const meStarters = (data?.entries || []).filter(e => e.slot !== "BENCH");
  const oppStarters = (opp?.entries || []).filter(e => e.slot !== "BENCH");
  const sa = data?.starters_score ?? 0, sb = opp?.starters_score ?? 0;
  const pa = data?.starters_projected ?? 0, pb = opp?.starters_projected ?? 0;
  const finalWeek = resWeek?.status === "final";
  const liveP = data && opp ? probOf(data.team_id, opp.team_id) : undefined;
  // the server's simulation only; empty until it arrives (a local estimate used to show first and then jump)
  const winP = finalWeek ? winProb({ score: sa, proj: pa }, { score: sb, proj: pb }, finalWeek) : liveP ?? null;
  const oppTeam = teams?.find(t => t.id === data?.opponent?.id) || data?.opponent;

  // Every matchup this week, from each team's week view (so upcoming weeks have cards too). Your own first, then
  // biggest game first (standings.bigGameFirst).
  const all = useTeamWeeks((teams || []).map(t => t.id), weekNo, scenario);
  const cards = [];
  if (all && teams) {
    const seen = new Set();
    const left = id => (all[id]?.entries || []).filter(e => e.slot !== "BENCH" && e.slot !== "IR").reduce((n, e) => n + (e.games_left || 0), 0);
    const side = id => ({ team: teams.find(t => t.id === id), score: all[id]?.starters_score ?? 0, proj: all[id]?.starters_projected ?? 0, left: left(id) });
    teams.forEach(t => {
      if (seen.has(t.id) || !all[t.id]) return;
      const o = all[t.id].opponent?.id;
      seen.add(t.id); if (o) seen.add(o);
      cards.push([side(t.id), o ? side(o) : null]);
    });
    cards.splice(0, cards.length, ...bigGameFirst(cards, standingsFrom(results, teams), scheduleOf(results, weekNo)));  // steady order, sides; yours on top
    // your own matchup first — the logged-in owner's, never the one being viewed: clicking a card only highlights it,
    // so the strip doesn't reshuffle or jump (2026-10-20)
    const mine = teams.find(t => t.owner_user_id === user?.discordId)?.id;
    cards.sort((x, y) => ([y[0].team.id, y[1]?.team.id].includes(mine) ? 1 : 0) - ([x[0].team.id, x[1]?.team.id].includes(mine) ? 1 : 0));
  }

  // Bench and IR live in their own section under the starters.
  const irLeft = data ? rosterBySlot((data.entries || []).filter(e => e.slot === "IR"), data.ir_list || []) : [];
  const irRight = opp ? rosterBySlot((opp.entries || []).filter(e => e.slot === "IR"), opp.ir_list || []) : irLeft.map(({ slot }) => ({ slot, entry: null }));
  while (irRight.length < irLeft.length) irRight.push({ slot: "IR", entry: null });
  while (irLeft.length < irRight.length) irLeft.push({ slot: "IR", entry: null });
  const benchLeft = [...left.slice(starters), ...irLeft], benchRight = [...right.slice(starters), ...irRight];
  // Contribution bars share one scale: the biggest best game on the page.
  const scale = Math.max(1, ...[...(data?.entries || []), ...(opp?.entries || [])].map(e => (e.contrib || []).reduce((n, c) => n + Math.abs(c.points), 0)));
  const days = cols === "schedule" ? weekDays(data?.week) : null;

  return (
    <FantasyShell title="Matchup">
      <div className="mu-bar">
        <button className="mu-btn page-btn" disabled={wi <= 0} onClick={() => set({ week: weeks[wi - 1].week })} aria-label="Previous week">‹</button>
        <span className="mu-week">{data ? <><b>{data.week.label}</b><span className="wk-range">{RANGE(data.week.start, data.week.end)}</span></> : "…"}</span>
        <button className="mu-btn page-btn" disabled={wi < 0 || wi >= weeks.length - 1} onClick={() => set({ week: weeks[wi + 1].week })} aria-label="Next week">›</button>
        <span className="mu-seg" role="tablist">
          <button role="tab" aria-selected={view === "matchup"} className={view === "matchup" ? "on" : ""} onClick={() => set({ view: "matchup" })}>Matchup</button>
          <button role="tab" aria-selected={view === "all"} className={view === "all" ? "on" : ""} onClick={() => set({ view: "all" })}>All teams</button>
        </span>
        {view === "matchup" && (
          <span className="mu-seg mu-seg2" role="tablist">
            <button role="tab" aria-selected={cols === "scoring"} className={cols === "scoring" ? "on" : ""} onClick={() => set({ cols: "scoring" })}>Scoring</button>
            <button role="tab" aria-selected={cols === "schedule"} className={cols === "schedule" ? "on" : ""} onClick={() => set({ cols: "schedule" })}>Schedule</button>
          </span>
        )}
      </div>

      {view === "matchup" && cards.length > 0 && (
        <Ticker>
          {cards.map(([a, b]) => {
            const on = [a.team.id, b?.team.id].includes(team?.id);
            return (
              <button key={a.team.id} className={`mu-mini${on ? " on" : ""}`} aria-pressed={on}
                onClick={() => set({ team: a.team.owner_user_id, view: "matchup" })}>
                {[a, b].map((x, k) => (x
                  ? <span key={x.team.id} className="mu-mini-row" style={{ "--team": x.team.color || "var(--surface-2)" }}>
                      <i /><TeamIcon team={x.team} size={20} /><span className="n">{x.team.name}</span><b>{x.score.toFixed(1)}</b>
                    </span>
                  : <span key={k} className="mu-mini-row bye"><i /><span /><span className="n">Bye</span><b /></span>))}
                {b && (() => {  // the banner's win chance, small: top team's share on the left (2026-10-24)
                  const p = finalWeek ? winProb(a, b, finalWeek) : probOf(a.team.id, b.team.id) ?? null;
                  return (
                    <span className="mu-mini-wp">
                      <span>{winText(p)}</span>
                      <span className="mu-wp-bar">
                        {p != null && p > 0 && <span style={{ flexGrow: p, background: a.team.color || "var(--text)" }} />}
                        {p != null && p < 1 && <span style={{ flexGrow: 1 - p, background: b.team.color || "var(--surface-3)" }} />}
                      </span>
                      <span className="r">{winText(p == null ? null : 1 - p)}</span>
                    </span>
                  );
                })()}
              </button>
            );
          })}
        </Ticker>
      )}

      {teams === undefined || (team && data === undefined) ? <p className="mu-note">Loading…</p> : null}
      {teams && !team && <p className="mu-note">No teams in this league yet.</p>}
      {data === null && <p className="mu-note">Couldn't load this week.</p>}

      {view === "all" && data && <AllTeams teams={teams} week={weekNo} final={resWeek?.status === "final"} slotTypes={slotTypes} scenario={scenario} onOpen={t => set({ team: t.owner_user_id, view: "matchup" })} />}

      {view === "matchup" && data && (
        <>
          <section className="mu-banner">
            <Side team={teamL} record={record(teamL.id)} />
            <div className="mu-mid">
              {/* Each score in its own recessed window, padded to three digits with unlit ones (070.5) */}
              <div className="mu-score">
                <span className="mu-led"><LedScore text={sa.toFixed(1).padStart(5, " ")} color={teamL.color} label={`${teamL.name} ${sa.toFixed(1)}`} /></span>
                <LedScore text="-" color={null} label="to" />
                <span className="mu-led">{oppTeam
                  ? <LedScore text={sb.toFixed(1).padStart(5, " ")} color={oppTeam.color} label={`${oppTeam.name} ${sb.toFixed(1)}`} />
                  : <LedScore text="  0.0" color={null} />}</span>
              </div>
              {/* Projections and each side's game counts, under the score on the black */}
              <div className="mu-under">
                <Counts {...countsOf(meStarters)} />
                {oppTeam && <span className="mu-proj">{pa.toFixed(1)} – {pb.toFixed(1)}</span>}
                {oppTeam ? <Counts {...countsOf(oppStarters)} /> : <span />}
              </div>
              {oppTeam && (
                <div className="mu-wp">
                  <span className="r">{winText(winP)}</span>
                  <div className="mu-wp-bar">
                    {/* a side at exactly 0% gets no sliver */}
                    {winP != null && winP > 0 && <span style={{ flexGrow: winP, background: teamL.color || "var(--text)" }} />}
                    {winP != null && winP < 1 && <span style={{ flexGrow: 1 - winP, background: oppTeam.color || "var(--surface-3)" }} />}
                  </div>
                  <span>{winText(winP == null ? null : 1 - winP)}</span>
                </div>
              )}
            </div>
            {oppTeam ? <Side team={oppTeam} record={record(oppTeam.id)} right /> : <div className="mu-side r"><span className="mu-tname">No opponent this week</span></div>}
          </section>

          <section className="mu-card">
            <table className="mu-table">
              <Head live={anyLive} days={days} />
              <tbody><Rows left={left.slice(0, starters)} right={right.slice(0, starters)} scale={scale} days={days} /></tbody>
            </table>
          </section>
          {benchLeft.length > 0 && (
            <section className="mu-card mu-bench">
              <h3 className="mu-bench-h">Bench</h3>
              <table className="mu-table">
                <Cols />
                <tbody><Rows left={benchLeft} right={benchRight} scale={scale} days={days} /></tbody>
              </table>
            </section>
          )}
        </>
      )}
    </FantasyShell>
  );
}
