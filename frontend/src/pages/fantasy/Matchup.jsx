import { useEffect, useState } from "react";
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
import { useTeamWeeks, winProb } from "../../components/fantasy/teamWeeks";
import "./Matchup.css";

// Matchup (design: canvas "Matchup v6"). ?week=N&team=<ownerId>&view=all — state in the URL so
// other pages can link straight in. Data: /results (every matchup's score, records) and
// /team/:id/week for both sides (spots, games, best game's top-5 contributions, projections).
// Row, each side mirrored: headshot · player · schedule · FPTS contribution · score | spot | ...
// Schedule counts: white dot = played, orange = today, outlined = still to play.

const SPOT = { G: "G", F: "F", C: "C", TEAM: "TM", FLEX: "FLX", BENCH: "Bench" };
const WEEKDAY = d => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { weekday: "short" });
const MD = d => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { month: "numeric", day: "numeric" });
const RANGE = (a, b) => `${new Date(`${a}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })} – ${new Date(`${b}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;
const fmt = (v, kind) => `${kind === "nba_team" && v > 0 ? "+" : ""}${Number(v ?? 0).toFixed(1)}`;
const signed = v => `${v > 0 ? "+" : "−"}${Math.abs(v)}`;

function useWeek(teamId, week, scenario) {
  const key = teamId ? `${teamId}|${week ?? ""}|${scenario}` : null;
  const [state, setState] = useState({ key: null, data: undefined });
  useEffect(() => {
    if (!key) return undefined;
    let live = true;
    const q = new URLSearchParams({ scenario, ...(week ? { week } : {}) });
    fetch(`${API}${API_BASE}/team/${encodeURIComponent(teamId)}/week?${q}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null)
      .then(data => { if (live) setState({ key, data }); });
    return () => { live = false; };
  }, [key, teamId, week, scenario]);
  return state.key === key ? state.data : undefined;
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

function Side({ team, record, counts, right }) {
  return (
    <div className={`mu-side${right ? " r" : ""}`} style={{ "--team": team?.color || "var(--surface-2)" }}>
      <TeamIcon team={team} size={44} />
      <div className="mu-plate">
        <span className="mu-abbr">{team?.abbreviation || team?.name}</span>
        <span className="mu-tname"><TeamLink ownerId={team?.owner_user_id} name={team?.name} />{record ? ` · ${record}` : ""}</span>
        <Counts {...counts} />
      </div>
    </div>
  );
}

// One side's cells, left to right for the left team (mirrored for the right).
function cells(e, side, win) {
  const r = side === "r";
  if (!e) {
    const empty = [<td key="h" className="mu-hs" />, <td key="p" className="mu-who"><span className="mu-last">Empty</span></td>,
      <td key="s" />, <td key="c" />, <td key="v" className="mu-sc" />];
    return r ? empty.reverse() : empty;
  }
  const [, last] = nameLines(e);
  const sub = e.kind === "nba_team" ? "TM" : `${e.position || "—"} · ${e.nba_team || ""}`;
  const next = e.games?.find(g => !g.played);
  const contrib = e.kind === "nba_team"
    ? (e.week_score != null ? [{ label: "Δ", points: e.week_score }] : [])
    : e.contrib || [];
  const out = [
    <td key="h" className="mu-hs">
      {e.kind === "player"
        ? <Headshot playerId={e.id} tricode={e.nba_team} width={48} height={35} />
        : <NbaTeamSquare tricode={e.id} size={26} />}
    </td>,
    <td key="p" className="mu-who">
      <EntityLink id={e.id} name={last} style={{ color: "inherit", textDecoration: "none" }} />
      <span className="mu-sub">{sub}</span>
    </td>,
    <td key="s" className="mu-sched">
      <span className="mu-next">{next ? `${WEEKDAY(next.date)} ${MD(next.date)} ${next.home ? "vs" : "@"} ${next.opp}` : ""}</span>
      <Counts done={e.games_done || 0} today={e.games_today || 0} left={Math.max(0, (e.games_left || 0) - (e.games_today || 0))} />
    </td>,
    <td key="c" className="mu-ct">
      <div className="mu-ct-wrap">
        {contrib.map(c => <span key={c.label} className={c.points < 0 ? "neg" : ""}>{c.label} {signed(c.points)}</span>)}
      </div>
    </td>,
    <td key="v" className={`mu-sc${win ? " win" : ""}`}>
      <span className="a">{fmt(e.week_score, e.kind)}</span>
      {e.projected != null && <span className="p">{fmt(e.projected, e.kind)}</span>}
    </td>,
  ];
  return r ? out.reverse() : out;
}

function Rows({ left, right }) {
  return left.map(({ slot, entry: a }, i) => {
    const b = right[i]?.entry;
    const va = a?.week_score ?? null, vb = b?.week_score ?? null;
    const bench = slot === "BENCH";
    return (
      <tr key={i} className={bench ? "bench" : ""}>
        {cells(a, "l", !bench && va != null && (vb == null || va > vb))}
        <td className="mu-slot">{SPOT[slot]}</td>
        {cells(b, "r", !bench && vb != null && (va == null || vb > va))}
      </tr>
    );
  });
}

function Head() {
  return (
    <thead>
      <tr>
        <th className="w-hs" /><th className="w-who l">Player</th><th className="w-sched l">Schedule</th><th className="r">FPTS contribution</th>
        <th className="w-sc" /><th className="w-slot" /><th className="w-sc" />
        <th className="l">FPTS contribution</th><th className="w-sched r">Schedule</th><th className="w-who r">Player</th><th className="w-hs" />
      </tr>
    </thead>
  );
}

// All teams (design: canvas "All teams"): # · team · score · projected · win % · points by spot ·
// game counts (dots). Best score in each column lit, only once someone has points.
function AllTeams({ teams, week, final, slotTypes, scenario }) {
  const weeks = useTeamWeeks((teams || []).map(t => t.id), week, scenario);
  if (!weeks) return <p className="mu-note">Loading…</p>;
  const rows = (teams || []).map(t => {
    const d = weeks[t.id];
    const st = (d?.entries || []).filter(e => e.slot !== "BENCH");
    const by = Object.fromEntries(slotTypes.map(k => [k, st.filter(e => e.slot === k).reduce((n, e) => n + (e.week_score || 0), 0)]));
    return { team: t, opp: d?.opponent?.id, score: d?.starters_score ?? 0, proj: d?.starters_projected ?? 0, by, counts: countsOf(st) };
  });
  const byId = Object.fromEntries(rows.map(r => [r.team.id, r]));
  rows.forEach(r => { r.win = byId[r.opp] ? winProb(r, byId[r.opp], final) : null; });
  rows.sort((a, b) => b.score - a.score || b.proj - a.proj);
  const best = k => Math.max(...rows.map(r => (k === "score" ? r.score : r.by[k])));
  const lit = (v, k) => (v > 0 && v === best(k) ? "win" : "");
  return (
    <section className="mu-card">
      <table className="mu-all">
        <thead>
          <tr>
            <th className="l w-rank">#</th><th className="l">Team</th><th>Score</th><th>Projected</th><th>Win %</th>
            {slotTypes.map(k => <th key={k}>{SPOT[k]}</th>)}<th>Games</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.team.id}>
              <td className="l">{i + 1}</td>
              <td className="l"><span className="mu-allteam"><TeamIcon team={r.team} size={22} /><TeamLink ownerId={r.team.owner_user_id} name={r.team.name} /></span></td>
              <td className={lit(r.score, "score")}><b>{r.score.toFixed(1)}</b></td>
              <td><i>{r.proj.toFixed(1)}</i></td>
              <td>{r.win == null ? "" : `${Math.round(r.win * 100)}%`}</td>
              {slotTypes.map(k => <td key={k} className={lit(r.by[k], k)}>{fmt(r.by[k], k === "TEAM" ? "nba_team" : "player")}</td>)}
              <td><Counts {...r.counts} /></td>
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
  const [benchOpen, setBenchOpen] = useState(false);
  const set = changes => setParams(p => { Object.entries(changes).forEach(([k, v]) => p.set(k, v)); return p; }, { replace: true });

  const view = params.get("view") === "all" ? "all" : "matchup";
  const weekParam = Number(params.get("week")) || null;
  const focusOwner = params.get("team") || user?.discordId;
  const team = teams?.find(t => t.owner_user_id === focusOwner) || teams?.[0];
  const data = useWeek(team?.id, weekParam, scenario);
  const weekNo = data?.week?.week ?? weekParam;
  const opp = useWeek(data?.opponent?.id, data?.week?.week, scenario);

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
  const winP = winProb({ score: sa, proj: pa }, { score: sb, proj: pb }, finalWeek);
  const oppTeam = teams?.find(t => t.id === data?.opponent?.id) || data?.opponent;

  return (
    <FantasyShell title="Matchup">
      <div className="mu-bar">
        <button className="mu-btn" disabled={wi <= 0} onClick={() => set({ week: weeks[wi - 1].week })} aria-label="Previous week">‹</button>
        <span className="mu-week">{data ? `${data.week.label} · ${RANGE(data.week.start, data.week.end)}` : "…"}</span>
        <button className="mu-btn" disabled={wi < 0 || wi >= weeks.length - 1} onClick={() => set({ week: weeks[wi + 1].week })} aria-label="Next week">›</button>
        <span className="mu-seg" role="tablist">
          <button role="tab" aria-selected={view === "matchup"} className={view === "matchup" ? "on" : ""} onClick={() => set({ view: "matchup" })}>Matchup</button>
          <button role="tab" aria-selected={view === "all"} className={view === "all" ? "on" : ""} onClick={() => set({ view: "all" })}>All teams</button>
        </span>
      </div>

      {resWeek && (
        <div className="mu-cards">
          {resWeek.matchups.map(m => {
            const on = [m.home.team.id, m.away.team.id].includes(team?.id);
            return (
              <button key={m.home.team.id} className={`mu-mini${on ? " on" : ""}`}
                onClick={() => set({ team: m.home.team.owner_user_id, view: "matchup" })}>
                {[m.home, m.away].map(s => (
                  <span key={s.team.id} className="mu-mini-row" style={{ "--team": s.team.color || "var(--surface-2)" }}>
                    <i /><span className="n">{s.team.name}</span><b>{s.score.toFixed(1)}</b>
                  </span>
                ))}
              </button>
            );
          })}
        </div>
      )}

      {teams === undefined || (team && data === undefined) ? <p className="mu-note">Loading…</p> : null}
      {teams && !team && <p className="mu-note">No teams in this league yet.</p>}
      {data === null && <p className="mu-note">Couldn't load this week.</p>}

      {view === "all" && data && <AllTeams teams={teams} week={weekNo} final={resWeek?.status === "final"} slotTypes={slotTypes} scenario={scenario} />}

      {view === "matchup" && data && (
        <>
          <section className="mu-banner">
            <Side team={team} record={record(team.id)} counts={countsOf(meStarters)} />
            <div className="mu-mid">
              <div className="mu-score">
                <LedScore text={sa.toFixed(1)} color={team.color} label={`${team.name} ${sa.toFixed(1)}`} />
                <LedScore text="-" color={null} label="to" />
                {oppTeam
                  ? <LedScore text={sb.toFixed(1)} color={oppTeam.color} label={`${oppTeam.name} ${sb.toFixed(1)}`} />
                  : <LedScore text="0.0" color={null} />}
              </div>
              {oppTeam && <span className="mu-proj">{pa.toFixed(1)} – {pb.toFixed(1)}</span>}
              {oppTeam && (
                <div className="mu-wp">
                  <span className="r">{Math.round(winP * 100)}%</span>
                  <div className="mu-wp-bar">
                    <span style={{ flexGrow: winP, background: team.color || "var(--text)" }} />
                    <span style={{ flexGrow: 1 - winP, background: oppTeam.color || "var(--surface-3)" }} />
                  </div>
                  <span>{100 - Math.round(winP * 100)}%</span>
                </div>
              )}
            </div>
            {oppTeam ? <Side team={oppTeam} record={record(oppTeam.id)} counts={countsOf(oppStarters)} right /> : <div className="mu-side r"><span className="mu-tname">No opponent this week</span></div>}
          </section>

          <section className="mu-card">
            <table className="mu-table">
              <Head />
              <tbody>
                <Rows left={left.slice(0, starters)} right={right.slice(0, starters)} />
                {benchOpen && <Rows left={left.slice(starters)} right={right.slice(starters)} />}
              </tbody>
            </table>
          </section>
          {left.length > starters && (
            <div className="mu-benchbar">
              <button onClick={() => setBenchOpen(o => !o)} aria-expanded={benchOpen}>Bench {benchOpen ? "▾" : "▸"}</button>
            </div>
          )}
        </>
      )}
    </FantasyShell>
  );
}
