import { useCallback, useEffect, useMemo, useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { Headshot, NbaTeamSquare } from "../../components/fantasy/RosterBits";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import RangeBar from "../../components/fantasy/RangeBar";
import { InjuryDot } from "../../components/fantasy/InjuryDot";
import { HEALTH_OPTS, healthMatch, injuryKind, useInjuries } from "../../components/fantasy/injuries";
import GlossaryButton from "../../components/fantasy/GlossaryButton";
import LockClock from "../../components/fantasy/LockClock";
import { useCached } from "../../components/fantasy/cache";
import { NBA_TEAMS } from "../../components/fantasy/nbaTeams";
import { Pager, Seg } from "../../components/fantasy/ListControls";
import useFloatHead from "../../components/fantasy/useFloatHead";
import { rowTeam } from "../../components/fantasy/rowTeam";
import { shortName as fitName } from "../../components/fantasy/playerNames";
import { setCardActions } from "../../components/fantasy/cardEvents";
import { API_BASE, SEASON, useFantasyApi } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";
import { teamsMatching } from "../../components/fantasy/nbaTeams";
import "./DraftRoom.css";
import "./Players.css";

// Players (design: "lbrt.net Design" canvas, Players row). Research + free agency in one list.
// Views: Actual (this season so far: Season / Last 14 days / Last 28 days / Last 6 weeks), Projected (preseason),
// past seasons, Schedule (the next week that hasn't started). Add / Drop collect into Moves (a box floating at the bottom); review shows the roster after
// the moves and the server says whether it's legal (POST /team/:id/checkout). No waiver wire: drops go straight back.

const HISTORY = ["2025-26", "2024-25", "2023-24", "2022-23"];
const label = s => `'${s.slice(-2)}`;
const WINDOWS = [["season", "Season"], ["d14", "Last 14 days"], ["d28", "Last 28 days"], ["w6", "Last 6 weeks"]];
const WHO = [["all", "All"], ["fa", "Free agents"], ["waivers", "Waivers"], ["rostered", "Rostered"]];
// When a waiver player clears: the live league's moment (Central time, "Thu 3:00 AM CT"), or the replay's date.
const clears = w => (w?.until ? `${new Date(w.until).toLocaleString(undefined, { weekday: "short", hour: "numeric", minute: "2-digit", timeZone: "America/Chicago" })} CT`
  : w?.until_date ? new Date(`${w.until_date}T00:00:00`).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" }) : "");
const POS = ["All", "G", "F", "C", "TM"];
const SPOT = { G: "G", F: "F", C: "C", TEAM: "TM", FLEX: "Flex", BENCH: "Bench" };
// Schedule day headers, as Roster has them: "Mon" over "10/26"
const WEEKDAY = d => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { weekday: "short" });
const MD = d => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { month: "numeric", day: "numeric" });
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const PAGE = 25;
const TIPS = {
  max: "Average weekly score (his best game each week)", avg: "Fantasy points per game", gp: "Games played",
  total: "Weekly scores added up", pmax: "Expected weekly score (best game of the week), averaged over the season's weeks",
  pavg: "Expected fantasy points per game", pgp: "Games he's expected to play, scaled to a full 82",
  range: "MAX low (a bad week) to MAX high (a big week); dot = MAX; thin line = AVG",
};
const f1 = v => (v == null ? "" : Number(v).toFixed(1));

function SortTh({ k, sort, setSort, className = "", title, children }) {
  const on = sort.key === k;
  return (
    <th className={`${className} dr-sort${on ? " on" : ""}`} title={title} aria-sort={on ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}>
      <button type="button" onClick={() => setSort(on ? { key: k, dir: sort.dir === "asc" ? "desc" : "asc" } : { key: k, dir: k === "rk" ? "asc" : "desc" })}>
        {children}<span className="dr-sort-arrow" aria-hidden="true">{on ? (sort.dir === "asc" ? "▲" : "▼") : ""}</span>
      </button>
    </th>
  );
}

function Who({ e, inj, own }) {
  // NBA teams: the full name when it fits, else the 3-letter code in the team's primary color — never "P. 76ers"
  const long = e.kind === "nba_team" && (e.name || "").length > 16;
  const { text, small } = e.kind === "nba_team" ? { text: long ? e.id : e.name, small: false } : fitName(e.name);
  const tc = long ? NBA_TEAMS[e.id]?.primary : null;
  const sub = e.kind === "nba_team" ? `TM · ${e.id}` : [e.position || "—", e.nba_team].filter(Boolean).join(" · ");
  return (
    <>
      <td className="hs">{e.kind === "player" ? <Headshot playerId={e.id} tricode={e.nba_team} width={40} height={46} /> : <span className="dr-tm-logo"><NbaTeamSquare tricode={e.id} size={36} /></span>}<InjuryDot inj={inj} /></td>
      <td className="who"><EntityLink id={e.id} name={text} style={{ color: "inherit", textDecoration: "none", fontSize: small ? 13 : undefined, ...(tc ? { fontWeight: 700, boxShadow: `inset 3px 0 0 ${tc}`, paddingLeft: 6 } : {}) }} /><span className="sb">{sub}</span>{own && <span className="sb pl-own-sm">{own}</span>}</td>
    </>
  );
}

// Fetch JSON for a key; undefined while loading, null on failure.
// through the visit's store (cache.js): the lists are preloaded in the background, so the page opens at once
const useJson = url => useCached(url);

function Review({ moveList, entities, teamId, scenario, onRemove, onClose, onDone }) {
  const [res, setRes] = useState(undefined);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const post = useCallback(apply => fetch(`${API}${API_BASE}/team/${encodeURIComponent(teamId)}/checkout?scenario=${scenario}`, {
    method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ adds: moveList.adds, drops: moveList.drops, apply }),
  }).then(async r => ({ ok: r.ok, body: await r.json().catch(() => ({})) })), [moveList, teamId, scenario]);

  useEffect(() => {
    let live = true;
    if (!moveList.adds.length && !moveList.drops.length) return undefined;
    post(false).then(({ ok, body }) => { if (live) { setRes(ok ? body : null); setError(ok ? null : body.detail || "Couldn't check these moves"); } });
    return () => { live = false; };
  }, [moveList, post]);

  const confirm = async () => {
    setBusy(true);
    const { ok, body } = await post(true);
    setBusy(false);
    if (ok) onDone(); else setError(body.detail || "Couldn't make these moves");
  };
  const n = moveList.adds.length + moveList.drops.length;
  const line = id => {
    const e = entities[id];
    if (!e) return id;
    return <>{e.name}<small>{e.kind === "nba_team" ? `TM · ${e.id}` : [e.position, e.nba_team].filter(Boolean).join(" · ")}</small></>;
  };
  return (
    <div className="pl-modal" role="dialog" aria-modal="true" aria-label="Review moves" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="pl-co">
        <div className="pl-co-h">Review {n} {n === 1 ? "move" : "moves"}<button type="button" className="pl-x" aria-label="Close" onClick={onClose}>×</button></div>
        <div className="pl-co-mv">
          {[["Add", moveList.adds, "adds"], ["Drop", moveList.drops, "drops"]].map(([t, ids, k]) => (
            <div key={k}>
              <div className="pl-co-t">{t}</div>
              {ids.length === 0 && <div className="pl-co-r">—</div>}
              {ids.map(id => (
                <div className="pl-co-r" key={id}><span>{line(id)}</span><button type="button" className="pl-link" onClick={() => onRemove(k, id)}>Remove</button></div>
              ))}
            </div>
          ))}
        </div>
        {res && (
          <>
            <div className="pl-co-t pl-co-sec">Your roster after these moves</div>
            <table className="pl-ro">
              <tbody>
                {res.roster.map(e => (
                  <tr key={`${e.change}-${e.id}`} className={e.change === "keep" ? "" : e.change === "add" ? (e.slot ? "new" : "new over") : "gone"}>
                    <td className="s">{e.slot ? SPOT[e.slot] || e.slot : "—"}</td>
                    <td>{e.change === "add" ? "+ " : ""}{e.name}{e.moved_from ? <small className="pl-was">moves from {SPOT[e.moved_from] || e.moved_from}</small> : null}</td>
                    <td className="p">{e.kind === "nba_team" ? `TM · ${e.id}` : [e.position, e.nba_team].filter(Boolean).join(" · ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className={`pl-chk ${res.ok ? "ok" : "bad"}`}>
              <span className="ic" aria-hidden="true">{res.ok ? "✓" : "!"}</span>
              {res.ok ? `Roster is legal · ${res.spots_used} of ${res.spots_total} spots` : res.error}
            </div>
          </>
        )}
        {res === undefined && !error && <div className="pl-co-r">Checking…</div>}
        {error && <div className="pl-chk bad"><span className="ic" aria-hidden="true">!</span>{error}</div>}
        <div className="pl-co-f">
          {res?.ok && <span>Takes effect now</span>}
          <span className="pl-go">
            <button type="button" className="dr-btn" onClick={onClose}>Back</button>
            <button type="button" className="dr-btn primary" disabled={!res?.ok || busy} onClick={confirm}>{busy ? "Saving…" : "Confirm moves"}</button>
          </span>
        </div>
      </div>
    </div>
  );
}

// Claim a player on waivers: optionally name who you'd drop if you win. Settled when his 2 days are up; the claim
// from the team first in the claim order wins (reverse standings as of each scoring period's first lock; a winner goes to the back).
function ClaimBox({ e, myTeam, scenario, priority, onClose, onDone }) {
  const [drop, setDrop] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const send = async () => {
    setBusy(true); setError(null);
    const r = await fetch(`${API}${API_BASE}/team/${encodeURIComponent(myTeam.id)}/claims?scenario=${scenario}`, {
      method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entity_id: e.id, drop_id: drop || null }),
    });
    const out = await r.json().catch(() => ({}));
    setBusy(false);
    if (r.ok) onDone(out); else setError(out.detail || "Couldn't put in the claim");
  };
  return (
    <div className="pl-modal" role="dialog" aria-modal="true" aria-label={`Claim ${e.name}`} onClick={x => { if (x.target === x.currentTarget) onClose(); }}>
      <div className="pl-co pl-claim">
        <div className="pl-co-h">Claim {e.name}<button type="button" className="pl-x" aria-label="Close" onClick={onClose}>×</button></div>
        <div className="pl-claim-b">
          <p>He's on waivers until <b>{clears(e.waivers)}</b>. Claims are settled then: the team first in the claim order wins{priority ? <> — you're <b>#{priority.priority} of {priority.teams}</b></> : null}.</p>
          <label className="pl-claim-drop">If you win, drop
            <select value={drop} onChange={x => setDrop(x.target.value)}>
              <option value="">Nobody (I have an open spot)</option>
              {(myTeam.roster || []).map(r => <option key={r.id} value={r.id}>{r.name} · {SPOT[r.slot] || r.slot}</option>)}
            </select>
          </label>
        </div>
        {error && <div className="pl-chk bad"><span className="ic" aria-hidden="true">!</span>{error}</div>}
        <div className="pl-co-f">
          <span className="pl-go">
            <button type="button" className="dr-btn" onClick={onClose}>Back</button>
            <button type="button" className="dr-btn primary" disabled={busy} onClick={send}>{busy ? "Saving…" : "Put in claim"}</button>
          </span>
        </div>
      </div>
    </div>
  );
}

export default function Players() {
  const user = useCurrentUser();
  const [scenario] = useFantasyScenario();
  const [version, setVersion] = useState(0); // bump to reload ownership after a checkout
  const players = useJson(`${API}${API_BASE}/players?scenario=${scenario}&v=${version}`);
  const nbaTeams = useJson(`${API}${API_BASE}/nba-teams?scenario=${scenario}&v=${version}`);
  const teams = useFantasyApi("teams");
  const results = useFantasyApi("results");
  const injuries = useInjuries();

  // Projected until week 1 is in the books (no finished weeks yet), then Actual; a tab you pick sticks
  const [picked, setView] = useState(null);
  const view = picked ?? (results?.weeks?.length ? "actual" : "proj");
  const [win, setWin] = useState("season");
  const [who, setWho] = useState("all");
  const [health, setHealth] = useState("all");
  const [playedOnly, setPlayedOnly] = useState(true);  // hide players with 0 games in the numbers being shown
  const [pos, setPos] = useState("All");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState({ key: "rk", dir: "asc" });
  const [page, setPage] = useState(0);
  // Drops handed over from Roster's Moves box ("Add players →") start in this Moves box.
  const [moveList, setMoveList] = useState(() => {
    try {
      const h = JSON.parse(sessionStorage.getItem("fantasyMoves") || "null");
      sessionStorage.removeItem("fantasyMoves");
      if (h && h.scenario === scenario && Array.isArray(h.drops)) return { adds: [], drops: h.drops };
    } catch { /* storage unavailable */ }
    return { adds: [], drops: [] };
  });
  const [reviewing, setReviewing] = useState(false);
  const [weekNo, setWeekNo] = useState(null);
  const [claiming, setClaiming] = useState(null);

  const season = results?.season;
  const asOf = results?.as_of;
  const past = HISTORY.filter(s => season && s < season);
  const views = [["actual", "Actual"], ["proj", "Projected"], ...past.map(s => [s, label(s)]), ["schedule", "Schedule"]];

  // Numbers for the view: /players/actual (Actual, and the Schedule view's order) or /players/board (Projected / past).
  const numUrl = view === "actual" ? `${API}${API_BASE}/players/actual?window=${win}&scenario=${scenario}`
    : view === "schedule" ? `${API}${API_BASE}/players/actual?window=season&scenario=${scenario}`
      : `${API}${API_BASE}/players/board?view=${view}&scenario=${scenario}`;
  const nums = useJson(numUrl);

  // Schedule: the league's weeks; default = the next week that hasn't started. That week is known from /results up front
  // (its weeks run through the current one; the next is one past the last that has started), so /schedule and
  // /players/week-scores load alongside /weeks instead of after it; /weeks only clamps it at the season's end.
  const weeks = useJson(view === "schedule" && season ? `${API}${API_BASE}/weeks?season=${season}&scenario=${scenario}` : null);
  const nextWeek = useMemo(() => {
    const rw = results?.weeks || [];
    const guess = rw.find(w => asOf && w.start > asOf)?.week ?? (rw.length ? rw[rw.length - 1].week + 1 : null);
    const ws = weeks?.weeks;
    if (!ws || ws.some(w => w.week === guess)) return guess;
    return (ws.find(w => asOf && w.start > asOf) || ws[ws.length - 1])?.week ?? null;
  }, [results, weeks, asOf]);
  const wk = weekNo ?? nextWeek;
  const sched = useJson(view === "schedule" && season && wk ? `${API}${API_BASE}/schedule?season=${season}&week=${wk}&scenario=${scenario}` : null);
  // each finished game's fantasy score (players), shown under the opponent — past weeks and this week so far
  const wkScores = useJson(view === "schedule" && wk ? `${API}${API_BASE}/players/week-scores?week=${wk}&scenario=${scenario}` : null);
  const schedByTeam = useMemo(() => {
    const out = {};
    if (!sched?.week) return out;
    const start = new Date(`${sched.week.start}T00:00:00`);
    for (const g of sched.games || []) {
      if (g.game_type !== "regular" || ["postponed", "cancelled"].includes(g.status)) continue;
      const day = Math.round((new Date(`${g.game_date}T00:00:00`) - start) / 86400000);
      (out[g.home_team] ||= {})[day] = { opp: `vs ${g.away_team}`, date: g.game_date, done: g.status === "final" };
      (out[g.away_team] ||= {})[day] = { opp: `@ ${g.home_team}`, date: g.game_date, done: g.status === "final" };
    }
    return out;
  }, [sched]);

  const myTeam = useMemo(() => (teams || []).find(t => user && t.owner_user_id === user.discordId) || null, [teams, user]);
  const teamById = useMemo(() => Object.fromEntries((teams || []).map(t => [t.id, t])), [teams]);
  const entities = useMemo(() => {
    const out = {};
    for (const p of players || []) if (p.in_pool !== false) out[p.id] = { ...p, kind: "player" };
    for (const t of nbaTeams || []) out[t.id] = { ...t, kind: "nba_team", nba_team: t.id };
    return out;
  }, [players, nbaTeams]);

  // Your pending waiver claims (private) and your place in the claim order.
  const claimsUrl = myTeam ? `${API}${API_BASE}/team/${encodeURIComponent(myTeam.id)}/claims?scenario=${scenario}&v=${version}` : null;
  const claimsData = useJson(claimsUrl);
  const [claimsOverride, setClaimsOverride] = useState(null);
  const claims = (claimsOverride?.url === claimsUrl ? claimsOverride.data : claimsData) || null;
  const claimed = useMemo(() => new Map((claims?.claims || []).map(c => [c.entity_id, c])), [claims]);
  const cancelClaim = useCallback(async c => {
    const r = await fetch(`${API}${API_BASE}/team/${encodeURIComponent(myTeam.id)}/claims/${c.id}?scenario=${scenario}`, { method: "DELETE", credentials: "include" });
    if (r.ok) setClaimsOverride({ url: claimsUrl, data: await r.json() });
  }, [myTeam, scenario, claimsUrl]);

  // Adds, drops and claims open once the draft is done (no shopping mid-draft); the server refuses them too.
  const draftState = useJson(`${API}${API_BASE}/draft?scenario=${scenario}`);
  const draftDone = draftState?.status === "complete" || (draftState?.status === "not_started" && (teams || []).some(t => (t.roster || []).length));

  const inMoves = id => moveList.adds.includes(id) || moveList.drops.includes(id);
  const toggle = useCallback((k, id) => setMoveList(c => ({ ...c, [k]: c[k].includes(id) ? c[k].filter(x => x !== id) : [...c[k], id] })), []);
  const action = useCallback(e => {
    if (!myTeam || !draftDone) return null;
    if (!e.team_id && e.waivers) {
      const c = claimed.get(e.id);
      return c
        ? <button type="button" className="dr-btn small pl-undo" onClick={() => cancelClaim(c)}>Claimed ✕</button>
        : <button type="button" className="dr-btn small primary" onClick={() => setClaiming(e)}>Claim</button>;
    }
    const mine = e.team_id === myTeam.id;
    if (!e.team_id || mine) {
      const k = mine ? "drops" : "adds";
      if (moveList[k].includes(e.id)) return <button type="button" className="dr-btn small pl-undo" onClick={() => toggle(k, e.id)}>{mine ? "Dropping ✕" : "Added ✕"}</button>;
      return mine
        ? <button type="button" className="dr-btn small pl-drop" onClick={() => toggle(k, e.id)}>Drop</button>
        : <button type="button" className="dr-btn small primary" onClick={() => toggle(k, e.id)}>Add</button>;
    }
    return null;
  }, [myTeam, draftDone, moveList, toggle, claimed, cancelClaim]);
  useEffect(() => { setCardActions(action); }, [action]);
  useEffect(() => () => setCardActions(null), []);

  const v = useMemo(() => nums?.players || {}, [nums]);
  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    const teamHits = teamsMatching(q);
    const anyPlayed = Object.values(v || {}).some(n => (n?.gp ?? 0) > 0);  // before anyone's played (Actual, preseason): show all
    const val = (e, k) => {
      const n = v[e.id];
      if (k === "rk") return n?.rank;
      if (k === "games") return Object.keys(schedByTeam[e.nba_team] || {}).length;
      if (k.startsWith("w")) return n?.weeks?.[k.slice(1)];
      return n?.[k];
    };
    return Object.values(entities)
      .filter(e => who === "all" || (who === "fa" ? !e.team_id && !e.waivers : who === "waivers" ? !e.team_id && !!e.waivers : !!e.team_id))
      .filter(e => healthMatch(health, injuries[e.id]))
      .filter(e => pos === "All" || (pos === "TM" ? e.kind === "nba_team" : e.kind === "player" && (e.position || "").includes(pos)))
      .filter(e => !q || e.name.toLowerCase().includes(q) || teamHits.includes(e.nba_team) || (e.kind === "nba_team" && teamHits.includes(e.id)))
      .filter(e => !playedOnly || !anyPlayed || e.kind === "nba_team" || (v[e.id]?.gp ?? 0) > 0)
      .map(e => [e, val(e, sort.key)])
      .sort(([a, x], [b, y]) => (x == null ? (y == null ? a.name.localeCompare(b.name) : 1) : y == null ? -1 : sort.dir === "asc" ? x - y : y - x))
      .map(([e]) => e);
  }, [entities, who, health, injuries, playedOnly, pos, search, sort, v, schedByTeam]);

  const changeView = k => { setView(k); setSort({ key: "rk", dir: "asc" }); setPage(0); };
  const proj = view === "proj", actual = view === "actual", schedule = view === "schedule";
  const hist = !proj && !actual && !schedule;
  const w6 = actual && win === "w6";
  const pageRows = rows.slice(page * PAGE, (page + 1) * PAGE);
  const scale = Math.max(10, Math.ceil(Math.max(0, ...pageRows.map(e => v[e.id]?.max_high ?? 0)) / 10) * 10);
  const loading = players === undefined || nbaTeams === undefined;
  const moves = [...moveList.adds.map(id => ["adds", id]), ...moveList.drops.map(id => ["drops", id])];
  const weekList = weeks?.weeks || [];
  const wkInfo = weekList.find(w => w.week === wk);
  // the week's dates (from the schedule, or the week list while it loads); today gets Roster's highlight
  const wkStart = sched?.week?.start || wkInfo?.start;
  const dayDate = i => {
    if (!wkStart) return null;
    const d = new Date(`${wkStart}T12:00:00`);
    d.setDate(d.getDate() + i);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  };
  const dayCls = i => `pl-day${dayDate(i) && dayDate(i) === asOf ? " today" : ""}`;
  const fmtDate = s => new Date(`${s}T00:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });

  // the header row: in the table, and again in the copy that floats under the site bar on a long scroll
  const headRow = (
    <tr>
      <SortTh k="rk" sort={sort} setSort={setSort} className="rk">Rk</SortTh><th className="hs" /><th className="who">Player</th>
      <th className="pl-own">Fantasy team</th>
      {(actual || hist) && <>
        {hist && <SortTh k="total" sort={sort} setSort={setSort} className="num w-tot c-tot" title={TIPS.total}>Total</SortTh>}
        <SortTh k="max" sort={sort} setSort={setSort} className="num w-n" title={TIPS.max}>Max</SortTh>
        <SortTh k="avg" sort={sort} setSort={setSort} className="num w-n" title={TIPS.avg}>Avg</SortTh>
        <SortTh k="gp" sort={sort} setSort={setSort} className="num w-gp c-gp" title={TIPS.gp}>GP</SortTh>
        {actual && !w6 && <SortTh k="total" sort={sort} setSort={setSort} className="num w-tot c-tot" title={TIPS.total}>Total</SortTh>}
        {w6 && (nums?.weeks || []).map(n => <SortTh key={n} k={`w${n}`} sort={sort} setSort={setSort} className="num w-wk" title={`Week ${n} score`}>Wk {n}</SortTh>)}
        <th className="w-bar" title={TIPS.range}>Max<sub>low</sub> – Max<sub>high</sub></th>
      </>}
      {proj && <>
        <SortTh k="max" sort={sort} setSort={setSort} className="num w-n" title={TIPS.pmax}>Proj max</SortTh>
        <SortTh k="avg" sort={sort} setSort={setSort} className="num w-n" title={TIPS.pavg}>Proj avg</SortTh>
        <SortTh k="gp" sort={sort} setSort={setSort} className="num w-gp c-gp" title={TIPS.pgp}>Proj GP</SortTh>
        <th className="w-bar" title={TIPS.range}>Max<sub>low</sub> – Max<sub>high</sub></th>
      </>}
      {schedule && <>
        {DAYS.map((d, i) => <th key={d} className={dayCls(i)}>{dayDate(i) ? <>{WEEKDAY(dayDate(i))}<br /><span>{MD(dayDate(i))}</span></> : d}</th>)}
        <SortTh k="games" sort={sort} setSort={setSort} className="num w-gp" title="Games this week">Games</SortTh>
      </>}
      <th className="act" />
    </tr>
  );
  const { scrollRef, floatRef } = useFloatHead([loading, view, win, page, schedule]);

  return (
    <FantasyShell title="Players" season={SEASON}>
      {claims?.claims?.length > 0 && (
        <section className="pl-claims" aria-label="Your waiver claims">
          <b>Your claims</b>
          <span className="pl-claims-order">#{claims.priority} of {claims.teams} in claim order</span>
          {claims.claims.map(c => (
            <span key={c.id} className="pl-mv">
              {c.name}{c.drop_name ? ` (drop ${c.drop_name})` : ""} · clears {clears(c)}
              <button type="button" className="pl-link" onClick={() => cancelClaim(c)}>Cancel</button>
            </span>
          ))}
        </section>
      )}
      <section className="dr-panel pl-panel" aria-label="Players">
        {/* tabs = what you're looking at; then two rows of switches: position + week / who (status, health) + search */}
        <div className="pl-tabrow">
          <Seg kind="tabs" options={views} value={view} onChange={changeView} />
          {results && <LockClock lock={results.week_lock} next={results.next_lock} asOf={results.as_of} />}
          <GlossaryButton terms={["RK", "MAX", "AVG", "TOTAL", "GP", "PROJ MAX", "PROJ AVG", "PROJ GP", "MAX low / high"]} />
        </div>
        <div className="pl-tools">
          <Seg options={POS} value={pos} onChange={k => { setPos(k); setPage(0); }} />
          {schedule && wkInfo && (
            <span className="pl-wk">
              <button type="button" className="pl-ar page-btn" aria-label="Previous week" disabled={!weekList.some(w => w.week === wk - 1)} onClick={() => setWeekNo(wk - 1)}>‹</button>
              {wkInfo.label || `Week ${wk}`} · {fmtDate(wkInfo.start)} – {fmtDate(wkInfo.end)}
              <button type="button" className="pl-ar page-btn" aria-label="Next week" disabled={!weekList.some(w => w.week === wk + 1)} onClick={() => setWeekNo(wk + 1)}>›</button>
            </span>
          )}
        </div>
        <div className="pl-tools">
          <Seg options={WHO} value={who} onChange={k => { setWho(k); setPage(0); }} />
          <Seg options={HEALTH_OPTS} value={health} onChange={k => { setHealth(k); setPage(0); }} />
          <Seg options={[["played", "Played"], ["any", "Incl. 0 GP"]]} value={playedOnly ? "played" : "any"} onChange={k => { setPlayedOnly(k === "played"); setPage(0); }} />
          <input className="dr-search" placeholder="Search players and teams" value={search} onChange={e => { setSearch(e.target.value); setPage(0); }} />
        </div>
        {actual && <div className="pl-tools pl-tools2"><Seg options={WINDOWS} value={win} onChange={k => { setWin(k); setSort({ key: "rk", dir: "asc" }); }} /></div>}

        {loading ? <p className="pl-msg">Loading…</p> : (
          <>
          <div className="lc-float" ref={floatRef} aria-hidden="true"><div><table className={`dr-table dr-pl pl-table${schedule ? " pl-sched" : ""} lc-float-t`}><thead>{headRow}</thead></table></div></div>
          <div className="dr-scroll" ref={scrollRef}>
            <table className={`dr-table dr-pl pl-table${schedule ? " pl-sched" : ""}`}>
              <thead>
                {headRow}
              </thead>
              <tbody>
                {pageRows.map((e, i0) => {
                  const i = i0 + page * PAGE, n = v[e.id];
                  const owner = e.team_id ? teamById[e.team_id] : null;
                  const games = schedByTeam[e.nba_team] || {};
                  return (
                    <tr key={e.id} className={inMoves(e.id) ? "pl-moverow lc-row" : "lc-row"} style={rowTeam(e.nba_team)}>
                      <td className="rk">{sort.key === "rk" && sort.dir === "asc" ? i + 1 : n?.rank ?? ""}</td>
                      <Who e={e} inj={injuries[e.id]} own={e.team_id ? e.team_name : e.waivers ? `Waivers · ${clears(e.waivers)}` : "Free agent"} />
                      <td className="pl-own">{e.team_id ? <span className="pl-team">{owner && <TeamIcon team={owner} size={20} />}<TeamLink ownerId={owner?.owner_user_id || e.owner_user_id} name={e.team_name} style={{ color: "inherit", textDecoration: "none" }} /></span> : e.waivers ? <span title="On waivers: claim him; settled when his 2 days are up">Waivers · {clears(e.waivers)}</span> : "Free agent"}</td>
                      {(actual || hist) && <>
                        {hist && <td className="num c-tot">{f1(n?.total)}</td>}
                        <td className="num">{f1(n?.max)}</td>
                        <td className="num">{f1(n?.avg)}</td>
                        <td className="num c-gp">{n?.gp ?? ""}</td>
                        {actual && !w6 && <td className="num c-tot">{n?.total == null ? "" : Math.round(n.total).toLocaleString()}</td>}
                        {w6 && (nums?.weeks || []).map(w => <td key={w} className="num">{f1(n?.weeks?.[w])}</td>)}
                        <td className="bar">{n?.max_low != null && <RangeBar low={n?.max_low} mid={n?.max} high={n?.max_high} avg={n?.avg} width={180} scale={scale} />}</td>
                      </>}
                      {proj && <>
                        <td className="num">{f1(n?.max)}</td>
                        <td className="num">{f1(n?.avg)}</td>
                        <td className="num c-gp">{n?.gp == null ? "" : Math.round(n.gp)}</td>
                        <td className="bar"><RangeBar low={n?.max_low} mid={n?.max} high={n?.max_high} avg={n?.avg} width={180} scale={scale} /></td>
                      </>}
                      {schedule && <>
                        {DAYS.map((d, j) => {
                          const g = games[j];
                          if (!g) return <td key={d} className={dayCls(j)} />;
                          const sc = e.kind === "player" && g.done ? wkScores?.[e.id] : undefined;
                          const has = sc && g.date in sc;
                          // still to come: OUT when he's ruled out of it — Roster's rule (Out on the injury report, before
                          // his return date). No per-game projection here (Players has none), so just the opponent.
                          const inj = injuries[e.id];
                          const ruledOut = !g.done && e.kind === "player" && injuryKind(inj) === "out" && (!inj.return_date || g.date < inj.return_date);
                          return (
                            <td key={d} className={dayCls(j)}>
                              <span className={`pl-dg${g.done ? " played" : ""}`}>{g.opp}
                                {has && (sc[g.date] == null ? <b className="pl-miss">OUT</b> : <b>{sc[g.date].toFixed(1)}</b>)}
                                {e.kind === "player" && g.done && !has && wkScores && <b className="pl-miss">OUT</b>}
                                {ruledOut && <b className="pl-miss">OUT</b>}
                              </span>
                            </td>
                          );
                        })}
                        <td className="num">{Object.keys(games).length || ""}</td>
                      </>}
                      <td className="act">{action(e)}</td>
                    </tr>
                  );
                })}
                {rows.length === 0 && <tr><td colSpan={20} className="pl-msg">Nothing matches.</td></tr>}
              </tbody>
            </table>
          </div>
          </>
        )}
        <Pager page={page} total={rows.length} size={PAGE} onPage={setPage} />
        {moves.length > 0 && (
          <div className="pl-moves" aria-label="Moves">
            <b>Moves</b>
            {moves.map(([k, id]) => <span key={id} className={`pl-mv ${k}`}><i>{k === "adds" ? "+" : "−"}</i>{entities[id]?.name || id}</span>)}
            <span className="pl-go">
              <button type="button" className="dr-btn small" onClick={() => setMoveList({ adds: [], drops: [] })}>Clear</button>
              <button type="button" className="dr-btn primary" onClick={() => setReviewing(true)}>Review {moves.length} {moves.length === 1 ? "move" : "moves"}</button>
            </span>
          </div>
        )}
      </section>
      {claiming && myTeam && (
        <ClaimBox e={claiming} myTeam={myTeam} scenario={scenario} priority={claims} onClose={() => setClaiming(null)}
          onDone={out => { setClaiming(null); setClaimsOverride({ url: claimsUrl, data: out }); }} />
      )}
      {reviewing && myTeam && (
        <Review moveList={moveList} entities={entities} teamId={myTeam.id} scenario={scenario}
          onRemove={(k, id) => { if (moves.length === 1) setReviewing(false); toggle(k, id); }} onClose={() => setReviewing(false)}
          onDone={() => { setReviewing(false); setMoveList({ adds: [], drops: [] }); setVersion(x => x + 1); }} />
      )}
    </FantasyShell>
  );
}

