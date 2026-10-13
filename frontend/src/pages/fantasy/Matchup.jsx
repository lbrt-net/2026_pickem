import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import LedScore from "../../components/fantasy/LedScore";
import { Headshot, NbaTeamSquare } from "../../components/fantasy/RosterBits";
import { nameLines } from "../../components/fantasy/nbaTeams";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { API_BASE, rosterBySlot, useFantasyApi } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";
import { useTeamWeeks, useWinProbs, winProb, winText } from "../../components/fantasy/teamWeeks";
import { NBA_TEAMS } from "../../components/fantasy/nbaTeams";
import { accent } from "../../components/fantasy/standings";
import { textOnColor } from "../../components/fantasy/teamColors";
import FitText from "../../components/fantasy/FitText";
import GlossaryButton from "../../components/fantasy/GlossaryButton";
import "./Matchup.css";

// Matchup (design: canvas "Matchup v6"). ?week=N&team=<ownerId>&view=all — state in the URL so
// other pages can link straight in. Data: /results (every matchup's score, records) and
// /team/:id/week for both sides (spots, games, best game's top-5 contributions, projections).
// Row, each side mirrored: headshot · player · schedule · FPTS contribution · score | spot | ...
// Schedule counts: white dot = played, orange = today, outlined = still to play.

const SPOT = { G: "G", F: "F", C: "C", TEAM: "TM", FLEX: "FLX", BENCH: "Bench", IR: "IR" };
const WEEKDAY = d => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { weekday: "short" });
const MD = d => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { month: "numeric", day: "numeric" });
const RANGE = (a, b) => `${new Date(`${a}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })} – ${new Date(`${b}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;
const fmt = (v, kind) => `${kind === "nba_team" && v > 0 ? "+" : ""}${Number(v ?? 0).toFixed(1)}`;
const signed = v => `${v > 0 ? "+" : "−"}${Math.abs(v)}`;

function useWeek(teamId, week, scenario, tick = 0) {
  // `base` = which week; `tick` = a refresh of it — while a refresh loads, the last numbers stay up
  const base = teamId ? `${teamId}|${week ?? ""}|${scenario}` : null;
  const key = base ? `${base}|${tick}` : null;
  const [state, setState] = useState({ base: null, data: undefined });
  useEffect(() => {
    if (!key) return undefined;
    let live = true;
    const q = new URLSearchParams({ scenario, ...(week ? { week } : {}) });
    fetch(`${API}${API_BASE}/team/${encodeURIComponent(teamId)}/week?${q}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null)
      .then(data => { if (live) setState({ base, data }); });
    return () => { live = false; };
  }, [key, base, teamId, week, scenario]);
  return state.base === base ? state.data : undefined;
}

function Counts({ done, today, left, className = "" }) {
  return (
    <span className={`mu-counts ${className}`}>
      <span><i className="mu-k done" />{done}</span>
      <span><i className="mu-k today" />{today}</span>
      <span><i className="mu-k later" />{left}</span>
    </span>
  );
}

const countsOf = list => list.reduce((c, e) => ({
  done: c.done + (e.games_done || 0), today: c.today + (e.games_today || 0),
  left: c.left + Math.max(0, (e.games_left || 0) - (e.games_today || 0)),
}), { done: 0, today: 0, left: 0 });

function Side({ team, record, right }) {
  return (
    <div className={`mu-side${right ? " r" : ""}`} style={{ "--team": team?.color || "var(--surface-2)", "--on": textOnColor(team?.color) }}>
      <TeamIcon team={team} size={52} />
      <div className="mu-plate">
        <span className="mu-abbr">{team?.abbreviation || team?.name}</span>
        <span className="mu-tname"><TeamLink ownerId={team?.owner_user_id} name={team?.name} />{record ? ` · ${record}` : ""}</span>
      </div>
    </div>
  );
}

// Catch-up: updates this browser hasn't shown yet (since the last one it played, remembered per player) replay one
// by one, ~1.3s apart — each burst lands and the bar steps — until it's caught up with now.
const SEEN_KEY = "fantasyLiveSeen";
const readSeen = () => { try { return JSON.parse(localStorage.getItem(SEEN_KEY) || "{}"); } catch { return {}; } };
const writeSeen = (id, at) => { try { const m = readSeen(); m[id] = at; localStorage.setItem(SEEN_KEY, JSON.stringify(m)); } catch { /* storage unavailable */ } };

function useReplay(id, updates) {
  const newest = updates?.[0]?.at;
  const [play, setPlay] = useState({ newest: null, queue: [], i: 0 });
  if (newest && play.newest !== newest) {
    const seen = readSeen()[id];
    const missed = seen ? updates.filter(u => u.at > seen).reverse() : updates.slice(0, 1);
    setPlay({ newest, queue: missed, i: 0 });
  }
  useEffect(() => {
    if (!play.queue.length) return undefined;
    if (play.i >= play.queue.length - 1) { writeSeen(id, play.newest); return undefined; }
    const t = setTimeout(() => setPlay(p => ({ ...p, i: p.i + 1 })), 1300);
    return () => clearTimeout(t);
  }, [play, id]);
  return play.queue.length ? play.queue[play.i] : null;
}

// While his game is live, the best-game bar becomes tonight's game: the same labelled category blocks growing as he
// racks them up (misses / turnovers as a red stretch eating back into the end, so the solid end = his total), a line at
// his best game this week, "3.0 to beat" → "New best +1.5". Each update (every 30s) flashes the blocks it changed and
// pops "+2.5" with what made it ("1 AST +1 · 1 DREB +0.5"), then fades. Coming back replays what you missed, step by
// step. An NBA team shows no score before the 4th, only its pace.
function LiveBar({ id, live, best }) {
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
  const now = replaying?.total ?? live.now ?? (live.pace == null && live.min != null ? 0 : null);
  if (now == null) {
    return <div className="mu-livetext"><i>{live.pace != null ? `On pace for ${live.pace.toFixed(1)} · counts from the 4th` : "Counts from the 4th quarter"}</i></div>;
  }
  const beat = live.best != null && now > live.best;
  const gap = live.best != null ? Math.round((live.best - now) * 10) / 10 : null;
  const hit = new Set(fresh && last ? last.parts.map(p => p.label) : []);
  // this row's own scale (Best vs Now fill the cell and compare directly)
  const size = ps => (ps || []).reduce((a, p) => a + Math.abs(p.points), 0);
  const rowScale = Math.max(size(best), size(parts), 1) * 1.05;
  return (
    <div className={`mu-live2${beat ? " beat" : gap != null && gap <= 6 ? " close" : ""}`}>
      <div className="mu-lrow"><span className="mu-llbl">Best</span><ContribBar parts={best || []} scale={rowScale} /></div>
      <div className="mu-lrow now"><span className="mu-llbl">Now</span><ContribBar parts={parts.filter(p => p.points)} scale={rowScale} hit={hit} /></div>
      <div className="mu-livetext">
        {live.clutch && live.oncourt && <span className="mu-clutch">CLUTCH</span>}
        <b className="ch">{beat ? `New best +${(now - live.best).toFixed(1)}` : gap === 0 ? "Tied with his best" : gap != null ? `${gap.toFixed(1)} to beat` : ""}</b>
        {last && fresh && (
          <span key={last.at} className={`mu-lpop2${last.delta < 0 ? " down" : ""}${last.parts.some(x => x.label === "CLUTCH") ? " clutch" : ""}`}>
            <b>{last.delta > 0 ? "+" : "−"}{Math.abs(last.delta).toFixed(1)}</b> {last.parts.map(x => `${x.n ?? ""} ${x.label}`.trim()).join(", ")}
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
function ContribBar({ parts, scale, hit }) {
  const [px, setPx] = useState(0);
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const ro = new ResizeObserver(([e]) => setPx(e.contentRect.width));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  if (!parts.length) return <div className="mu-bar2" ref={ref} />;
  const sorted = [...parts.filter(c => c.points > 0).sort((a, b) => b.points - a.points),
    ...parts.filter(c => c.points < 0).sort((a, b) => a.points - b.points)];
  return (
    <div className="mu-bar2" ref={ref} tabIndex={0}>
      <Zoom parts={sorted} />
      {sorted.map(c => {
        const w = Math.abs(c.points) / scale;
        const wpx = w * px;
        const v = Math.abs(c.points);
        const text = wpx >= W3_PX || Number.isInteger(v) ? String(v) : String(Math.round(v));
        const big = wpx >= FIT_PX;
        return (
          <span key={c.label} className={`mu-part${c.points < 0 ? " neg" : ""}${hit?.has(c.label) ? " hit" : ""}`} style={{ width: `${w * 100}%`, "--l": `${shade(c, sorted)}%` }} title={`${c.label} ${signed(c.points)}`}>
            <span className="seg">{big ? text : ""}</span>
            {big && <span className="call">{c.label}</span>}
          </span>
        );
      })}
    </div>
  );
}

// Hovering a bar: the bar outlined, and a pop-up with the same parts zoomed in — every block labelled, tiny ones
// held at a minimum width so they can be read, the rest in proportion.
const ZOOM_PX = 380, ZOOM_MIN = 28;
function Zoom({ parts }) {
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
    </div>
  );
}

// One side's cells, left to right for the left team (mirrored for the right).
function cells(e, side, scale) {
  const r = side === "r";
  if (!e) {
    const empty = [<td key="h" className="mu-hs" />, <td key="p" className="mu-who"><span className="mu-last">Empty</span></td>,
      <td key="s" />, <td key="c" />, <td key="v" className="mu-sc" />];
    return r ? empty.reverse() : empty;
  }
  const [, last] = nameLines(e);
  const sub = e.kind === "nba_team" ? "TM" : `${e.position || "—"} · ${e.nba_team || ""}`;
  const next = e.games?.find(g => !g.played);
  const contrib = e.contrib || []; // players: every category of his best game; NBA teams: the team scoring parts
  // The game the best-game bar comes from (highest points so far this week).
  const best = (e.games || []).filter(g => g.played && g.points != null).reduce((m, g) => (!m || g.points > m.points ? g : m), null);
  const out = [
    <td key="h" className={`mu-hs${e.live?.oncourt ? " oncourt" : ""}`}>
      {e.kind === "player"
        ? <Headshot playerId={e.id} tricode={e.nba_team} width={48} height={35} />
        : <NbaTeamSquare tricode={e.id} size={30} />}
    </td>,
    <td key="p" className={`mu-who${e.live?.oncourt ? " oncourt" : ""}`}>
      <EntityLink id={e.id} name={<FitText text={last} max={15} min={11} />} style={{ color: "inherit", textDecoration: "none" }} />
      <span className="mu-sub">{sub}</span>
      {e.live?.oncourt && <span className="mu-oncourt">On court</span>}
    </td>,
    <td key="s" className={`mu-sched${e.live ? " live" : ""}`}>
      {e.live
        ? <span className="mu-next mu-livesched"><span className="mu-live-tag"><i className={e.live.oncourt ? "on" : ""} />{liveClock(e.live)}</span>
            <b>{e.live.team} {e.live.score?.[0] ?? "–"}–{e.live.score?.[1] ?? "–"} {e.live.opp}</b></span>
        : <span className="mu-next">{next ? `${WEEKDAY(next.date)} ${MD(next.date)} ${next.home ? "vs" : "@"} ${next.opp}` : ""}</span>}
      <Counts done={e.games_done || 0} today={e.games_today || 0} left={Math.max(0, (e.games_left || 0) - (e.games_today || 0))} />
    </td>,
    // live: two identical bars on one scale and alignment — his best game this week, then tonight's game growing
    e.live ? <td key="c" className="mu-ct mu-ct-live"><LiveBar id={e.id} live={e.live} best={contrib} /></td> :
    <td key="c" className="mu-ct">
      {best && <span className="mu-when">{`${WEEKDAY(best.date)} ${MD(best.date)} ${best.home ? "vs" : "@"} ${best.opp}${best.min != null ? ` · ${best.min} min` : ""}`}</span>}
      <ContribBar parts={contrib} scale={scale} />
    </td>,
    <td key="v" className="mu-sc">
      <span className="a">{fmt(e.week_score)}</span>
      {e.projected != null && <span className="p">{fmt(e.projected)}</span>}
    </td>,
  ];
  return r ? out.reverse() : out;
}

// The NBA team color for a row's wash (player's team, or the NBA team itself).
const nbaColor = e => (e ? NBA_TEAMS[e.kind === "nba_team" ? e.id : e.nba_team]?.primary : null);

function Rows({ left, right, scale }) {
  return left.map(({ slot, entry: a }, i) => {
    const b = right[i]?.entry;
    return (
      <tr key={i} className={slot === "IR" ? "ir" : ""} style={{ "--ca": nbaColor(a) || "transparent", "--cb": nbaColor(b) || "transparent" }}>
        {cells(a, "l", scale)}
        <td className="mu-slot">{slot === "BENCH" ? "" : SPOT[slot]}</td>
        {cells(b, "r", scale)}
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

function Head() {
  return (
    <thead>
      <tr>
        <th className="w-hs" /><th className="w-who l">Player</th><th className="w-sched l">Schedule</th><th className="r">Best game<GlossaryButton terms={["FPTS", "FG-", "FT-", "3PTM", "Δ"]} /></th>
        <th className="w-sc" /><th className="w-slot" /><th className="w-sc" />
        <th className="l">Best game</th><th className="w-sched r">Schedule</th><th className="w-who r">Player</th><th className="w-hs" />
      </tr>
    </thead>
  );
}

// All teams, in the standings table style (team-color edge + row wash, body font): # · team · score · projected ·
// win % · points by spot · game counts. Click a row to open that matchup.
function AllTeams({ teams, week, final, slotTypes, scenario, onOpen }) {
  const weeks = useTeamWeeks((teams || []).map(t => t.id), week, scenario);
  const probOf = useWinProbs(week, scenario);
  if (!weeks) return <p className="mu-note">Loading…</p>;
  const rows = (teams || []).map(t => {
    const d = weeks[t.id];
    const st = (d?.entries || []).filter(e => e.slot !== "BENCH" && e.slot !== "IR");
    const by = Object.fromEntries(slotTypes.map(k => [k, st.filter(e => e.slot === k).reduce((n, e) => n + (e.week_score || 0), 0)]));
    return { team: t, opp: d?.opponent?.id, score: d?.starters_score ?? 0, proj: d?.starters_projected ?? 0, by, counts: countsOf(st) };
  });
  const byId = Object.fromEntries(rows.map(r => [r.team.id, r]));
  rows.forEach(r => { r.win = byId[r.opp] ? (final ? winProb(r, byId[r.opp], final) : probOf(r.team.id, r.opp) ?? winProb(r, byId[r.opp], final)) : null; });
  rows.sort((a, b) => b.score - a.score || b.proj - a.proj);
  return (
    <section className="mu-card">
      <table className="mu-all">
        <thead>
          <tr>
            <th className="w-edge" /><th className="l w-rank">#</th><th className="l">Team</th><th>Score</th><th>Projected</th><th>Win %</th>
            {slotTypes.map(k => <th key={k}>{SPOT[k]}</th>)}<th className="c">Games</th>
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
  // Matchup shows the week being played (Roster is the one that jumps ahead once lineups lock)
  const weekParam = Number(params.get("week")) || results?.current_week || null;
  const focusOwner = params.get("team") || user?.discordId;
  const team = teams?.find(t => t.owner_user_id === focusOwner) || teams?.[0];
  const [tick, setTick] = useState(0);
  const data = useWeek(team?.id, weekParam, scenario, tick);
  const weekNo = data?.week?.week ?? weekParam;
  const opp = useWeek(data?.opponent?.id, data?.week?.week, scenario, tick);
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

  const probOf = useWinProbs(data?.week?.week, scenario);

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
  const winP = finalWeek || liveP === undefined ? winProb({ score: sa, proj: pa }, { score: sb, proj: pb }, finalWeek) : liveP;
  const oppTeam = teams?.find(t => t.id === data?.opponent?.id) || data?.opponent;

  // Every matchup this week, from each team's week view (so upcoming weeks have cards too). Your own first.
  const all = useTeamWeeks((teams || []).map(t => t.id), weekNo, scenario);
  const cards = [];
  if (all && teams) {
    const seen = new Set();
    const side = id => ({ team: teams.find(t => t.id === id), score: all[id]?.starters_score ?? 0 });
    teams.forEach(t => {
      if (seen.has(t.id) || !all[t.id]) return;
      const o = all[t.id].opponent?.id;
      seen.add(t.id); if (o) seen.add(o);
      cards.push([side(t.id), o ? side(o) : null]);
    });
    cards.sort((x, y) => ([y[0].team.id, y[1]?.team.id].includes(team?.id) ? 1 : 0) - ([x[0].team.id, x[1]?.team.id].includes(team?.id) ? 1 : 0));
  }

  // Bench and IR live in their own section under the starters.
  const irLeft = data ? rosterBySlot((data.entries || []).filter(e => e.slot === "IR"), data.ir_list || []) : [];
  const irRight = opp ? rosterBySlot((opp.entries || []).filter(e => e.slot === "IR"), opp.ir_list || []) : irLeft.map(({ slot }) => ({ slot, entry: null }));
  while (irRight.length < irLeft.length) irRight.push({ slot: "IR", entry: null });
  while (irLeft.length < irRight.length) irLeft.push({ slot: "IR", entry: null });
  const benchLeft = [...left.slice(starters), ...irLeft], benchRight = [...right.slice(starters), ...irRight];
  // Contribution bars share one scale: the biggest best game on the page.
  const scale = Math.max(1, ...[...(data?.entries || []), ...(opp?.entries || [])].map(e => (e.contrib || []).reduce((n, c) => n + Math.abs(c.points), 0)));

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
            <Side team={team} record={record(team.id)} />
            <div className="mu-mid">
              {/* Each score in its own recessed window, padded to three digits with unlit ones (070.5) */}
              <div className="mu-score">
                <span className="mu-led"><LedScore text={sa.toFixed(1).padStart(5, " ")} color={team.color} label={`${team.name} ${sa.toFixed(1)}`} /></span>
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
                    <span style={{ flexGrow: winP, background: team.color || "var(--text)" }} />
                    <span style={{ flexGrow: 1 - winP, background: oppTeam.color || "var(--surface-3)" }} />
                  </div>
                  <span>{winText(winP == null ? null : 1 - winP)}</span>
                </div>
              )}
            </div>
            {oppTeam ? <Side team={oppTeam} record={record(oppTeam.id)} right /> : <div className="mu-side r"><span className="mu-tname">No opponent this week</span></div>}
          </section>

          <section className="mu-card">
            <table className="mu-table">
              <Head />
              <tbody><Rows left={left.slice(0, starters)} right={right.slice(0, starters)} scale={scale} /></tbody>
            </table>
          </section>
          {benchLeft.length > 0 && (
            <section className="mu-card mu-bench">
              <h3 className="mu-bench-h">Bench</h3>
              <table className="mu-table">
                <Cols />
                <tbody><Rows left={benchLeft} right={benchRight} scale={scale} /></tbody>
              </table>
            </section>
          )}
        </>
      )}
    </FantasyShell>
  );
}
