import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CARD_EVENT, getCardActions } from "./cardEvents";
import { API_BASE, TEST_SEASON, entityPath, seasonOf, useFantasyApi } from "./data";
import { Headshot, NbaTeamSquare } from "./RosterBits";
import { NBA_TEAMS, nameLines } from "./nbaTeams";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";
import GlossaryButton from "./GlossaryButton";
import { InjuryDot } from "./InjuryDot";
import { backText, injuryKind, injuryWord, useInjuries } from "./injuries";
import "./PlayerCard.css";
import "../../pages/fantasy/player/PlayerPage.css";
import { popupBorder, popupStats } from "../../pages/fantasy/player/art";

// The pop-up any player / NBA team name opens (one per page, mounted by FantasyShell). Design: canvas
// "Player card" boards. Tabs: Actual (this season so far) · Projected · '26 · '25 · '24 · '23, all tables.
// MAX = best game of a fantasy week, AVG = fantasy points per game; projections in italics. A page can put
// its own buttons in the header (the draft room: + Queue / Draft) via setCardActions. Esc / tap outside closes.

const TABS = [["actual", "Actual"], ["proj", "Projected"], ["2025-26", "'26"], ["2024-25", "'25"], ["2023-24", "'24"], ["2022-23", "'23"]];
const f1 = v => (v == null ? "—" : Number(v).toFixed(1));
const signed = v => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(Math.round(v * 10) / 10)}`;
const MD = d => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });
const range = (a, b) => (a && b ? `${MD(a)} – ${MD(b)}` : "");
const mean = xs => (xs.length ? xs.reduce((s, x) => s + x, 0) / xs.length : null);
const FUSED = 6; // a week with 6+ games is two calendar weeks counted as one (All-Star, the final)

function useJson(url) {
  const [state, setState] = useState({ url: null, data: undefined });
  useEffect(() => {
    if (!url) return undefined;
    let live = true;
    fetch(url, { credentials: "include" }).then(r => (r.ok ? r.json() : null)).catch(() => null)
      .then(data => { if (live) setState({ url, data }); });
    return () => { live = false; };
  }, [url]);
  return state.url === url ? state.data : undefined;
}

function Kv({ items }) {
  return (
    <div className="pc-kv">
      {items.map(([label, value, sub, italic]) => (
        <div key={label}><b className={italic ? "pj" : ""}>{value}{sub != null && <small>{sub}</small>}</b><span>{label}</span></div>
      ))}
    </div>
  );
}

function Breakdown({ bd, rules }) {
  if (!bd) return null;
  const cats = rules.filter(r => r.key in bd);
  const half = Math.ceil(cats.length / 2);
  return [cats.slice(0, half), cats.slice(half)].map((part, i) => (
    <table key={i} className="pc-tb">
      <thead><tr>{part.map(r => <th key={r.key} title={r.name}>{r.label}</th>)}</tr></thead>
      <tbody><tr>{part.map(r => <td key={r.key} className={bd[r.key] < 0 ? "neg" : ""}>{signed(bd[r.key])}</td>)}</tr></tbody>
    </table>
  ));
}

// The pop-up is a glance and never scrolls (commissioner, 2026-10-14): summaries and the last few weeks / games only;
// every week, the full game log and the rest live on the player page.
const RECENT = 5;
const STRIP = 8; // weeks in the pop-up's schedule strip

// The schedule, condensed: his next STRIP fantasy weeks — dates, his NBA team's games (big), the projection for the week.
function ScheduleStrip({ proj, weeks }) {
  if (!proj?.weeks?.length || !weeks?.length) return null;
  const today = new Date().toISOString().slice(0, 10);
  const byWeek = Object.fromEntries(proj.weeks.map(w => [w.week, w]));
  const next = weeks.filter(w => w.end >= today && byWeek[w.week]).slice(0, STRIP);
  if (!next.length) return null;
  return (
    <div className="pc-sched" aria-label="Schedule">
      {next.map(w => {
        const p = byWeek[w.week], out = p.games && p.plays === 0;
        return (
          <div key={w.week} className={`pc-wk${out ? " out" : ""}`}>
            <span className="pc-wk-l">{w.label || `Week ${w.week}`}</span>
            <span className="pc-wk-d">{range(w.start, w.end)}</span>
            <b>{p.games}</b><span className="pc-wk-g">{p.games === 1 ? "game" : "games"}</span>
            <span className="pc-wk-p">{out ? "Out" : f1(p.e_on ?? p.e)}</span>
          </div>
        );
      })}
    </div>
  );
}

function ProjectedTab({ proj }) {
  if (!proj) return <p className="pc-empty">No projection for him this season.</p>;
  // Weeks he's ruled out for entirely (a known return date: games but 0 expected to play) are left out of PROJ MAX /
  // low / high — they show how good his weeks are when he's active; occasional missed games (availability) stay in.
  const out = w => w.games && w.plays === 0;
  const wk = (proj.weeks || []).filter(w => w.games && !out(w));
  const active = (proj.weeks || []).filter(w => !out(w));
  // shown values are his weeks when he plays them (the *_on values): only his scattered misses inside a week count
  const projMax = active.length ? mean(active.map(w => w.e_on ?? w.e)) : proj.proj_max;
  const low = wk.length ? mean(wk.map(w => w.p25_on ?? w.p25)) : proj.max_low, high = wk.length ? mean(wk.map(w => w.p90_on ?? w.p90)) : proj.max_high;
  // Games he's expected to play this season (availability + current injuries); "plays" per week below.
  // scaled to a full 82: the fantasy season stops before the NBA's does
  const sched = (proj.weeks || []).reduce((n, w) => n + (w.games || 0), 0);
  const games = sched && (proj.weeks || []).some(w => w.plays != null)
    ? (proj.weeks || []).reduce((n, w) => n + (w.plays || 0), 0) / sched * 82 : null;
  const groups = {};
  for (const w of wk) if (w.games < FUSED) (groups[w.games] ||= []).push(w);
  return (
    <>
      <Kv items={[["Proj max", f1(projMax), null, false], ["Proj avg", f1(proj.proj_avg), null, false],
        [<>Proj max<sub>low</sub></>, f1(low), null, false], [<>Proj max<sub>high</sub></>, f1(high), null, false],
        ...(games != null ? [["Exp. games / 82", Math.round(games), null, false]] : [])]} />
      <div className="pc-two">
        <div>
          <div className="pc-st">Weeks by games</div>
          <table className="pc-tb">
            <thead><tr><th className="l">Games</th><th>Weeks</th><th>Max<sub>low</sub></th><th>Max</th><th>Max<sub>high</sub></th></tr></thead>
            <tbody>
              {Object.entries(groups).map(([g, ws]) => (
                <tr key={g}><td className="l">{g}</td><td>{ws.length}</td><td>{f1(mean(ws.map(w => w.p25)))}</td>
                  <td>{f1(mean(ws.map(w => w.e)))}</td><td>{f1(mean(ws.map(w => w.p90)))}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function SeasonTab({ s, rules }) {
  if (!s) return <p className="pc-empty">He didn't play that season.</p>;
  return (
    <>
      <Kv items={[["Max", f1(s.avg_max)], ["Avg", f1(s.fp_per_game)], ["GP", s.games], ["Weeks", `${s.weeks_played} / ${s.weeks_in_season}`]]} />
      <div className="pc-two">
        <div>
          <div className="pc-st">Weeks by games</div>
          <table className="pc-tb">
            <thead><tr><th className="l">Games</th><th>Weeks</th><th>Max</th></tr></thead>
            <tbody>{(s.by_games || []).map(b => <tr key={b.games}><td className="l">{b.games}</td><td>{b.weeks}</td><td>{f1(b.avg_max)}</td></tr>)}</tbody>
          </table>
          <div className="pc-st">Max game, average · {s.team}</div>
          <Breakdown bd={s.max_breakdown} rules={rules} />
        </div>
      </div>
    </>
  );
}

function ActualTab({ log, proj, team = false }) {
  const played = (log?.games || []).filter(g => g.fantasy_points != null && !g.dnp);
  if (!played.length) return <p className="pc-empty">No games yet this season.</p>;
  const byWeek = {};
  for (const g of played) (byWeek[g.week] ||= []).push(g);
  const weekRows = Object.entries(byWeek).map(([w, gs]) => ({ week: Number(w), games: gs.length, max: Math.max(...gs.map(g => g.fantasy_points)) }));
  const projByWeek = Object.fromEntries((proj?.weeks || []).map(w => [w.week, w.e]));
  const best = new Set(Object.values(byWeek).map(gs => gs.reduce((a, b) => (b.fantasy_points > a.fantasy_points ? b : a)).game_id));
  const avgMax = mean(weekRows.map(w => w.max)), avg = mean(played.map(g => g.fantasy_points));
  // PROJ MAX = the draft list's number (projections.shown_max: his weeks when he isn't out all week), never the raw column
  const active = (proj?.weeks || []).filter(w => !(w.games && w.plays === 0));
  const shownMax = proj ? (active.length ? mean(active.map(w => w.e_on ?? w.e)) : proj.proj_max) : null;
  return (
    <>
      <Kv items={[["Max", f1(avgMax), proj && f1(shownMax)], ["Avg", f1(avg), proj && f1(proj.proj_avg)], ["GP", played.length], ["Weeks", weekRows.length]]} />
      <div className="pc-two">
        <div>
          <div className="pc-st">Weeks</div>
          <table className="pc-tb weeks">
            <thead><tr><th className="l">Wk</th><th>Games</th><th>Max</th><th>Proj max</th><th>Δ</th></tr></thead>
            <tbody>
              {weekRows.slice(-RECENT).map(w => {
                const p = projByWeek[w.week], dlt = p != null ? w.max - p : null;
                return <tr key={w.week}><td className="l">{w.week}</td><td>{w.games}</td><td>{f1(w.max)}</td><td className="pj">{f1(p)}</td><td className={dlt < 0 ? "neg" : ""}>{dlt == null ? "" : signed(dlt)}</td></tr>;
              })}
            </tbody>
          </table>
        </div>
        <div>
          <div className="pc-st">Last {RECENT} games</div>
          <div>
            <table className="pc-tb">
              <thead><tr><th className="l">Date</th><th className="l">Opp</th>{team ? <th className="l">Result</th> : <><th>MIN</th><th>PTS</th><th>REB</th><th>AST</th><th>STL</th><th>BLK</th><th>TO</th></>}<th>FPTS</th></tr></thead>
              <tbody>
                {[...played].reverse().slice(0, RECENT).map(g => (
                  <tr key={g.game_id} className={g.week % 2 ? "wk-alt" : ""}>
                    <td className="l">{MD(g.date)}</td><td className="l">{g.home ? "vs" : "@"} {g.opponent}</td>
                    {team ? <td className="l">{g.result}</td> : <><td>{Math.round(g.minutes)}</td><td>{g.pts}</td><td>{g.reb}</td><td>{g.ast}</td><td>{g.stl}</td><td>{g.blk}</td><td>{g.tov}</td></>}
                    <td className={best.has(g.game_id) ? "best" : ""}><span>{f1(g.fantasy_points)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}

// "a:b;c:d" → React style object (the frame helpers return CSS text)
const styleObj = css => Object.fromEntries(css.split(";").map(s => s.trim()).filter(Boolean).map(s => {
  const i = s.indexOf(":"); return [s.slice(0, i).trim().replace(/-([a-z])/g, (_, c) => c.toUpperCase()), s.slice(i + 1).trim()];
}));

export default function PlayerCardHost({ initialId = null }) {
  const [id, setId] = useState(initialId);
  const [tab, setTab] = useState("proj");
  const [scenario] = useFantasyScenario();
  const players = useFantasyApi("players");
  const nbaTeams = useFantasyApi("nba-teams");
  const scoring = useFantasyApi("scoring");
  const injuries = useInjuries();
  const settings = useFantasyApi("league/settings");
  const leagueSeason = seasonOf() === TEST_SEASON ? "2025-26" : "2026-27";
  const hist = useJson(id ? `${API}${API_BASE}/players/${encodeURIComponent(id)}/history?scenario=${scenario}` : null);
  // players: the player page's payload, for the header pieces (stats panel, season cloud, wheel) and the tier border
  const page = useJson(id ? `${API}${API_BASE}/players/${encodeURIComponent(id)}/page?scenario=${scenario}` : null);
  const log = useJson(id && tab === "actual" ? `${API}${API_BASE}/entity/${encodeURIComponent(id)}/games?season=${leagueSeason}&scenario=${scenario}` : null);

  useEffect(() => {
    const open = e => { setId(e.detail.id); setTab("proj"); };
    const esc = e => { if (e.key === "Escape") setId(null); };
    window.addEventListener(CARD_EVENT, open);
    window.addEventListener("keydown", esc);
    return () => { window.removeEventListener(CARD_EVENT, open); window.removeEventListener("keydown", esc); };
  }, []);
  // built once per player payload, not on every render (the frame and stats are heavy; 2026-10-17)
  const borderStyle = useMemo(() => (page ? styleObj(popupBorder(page)) : undefined), [page]);
  const statsHtml = useMemo(() => (page ? { __html: popupStats(page) } : null), [page]);
  if (!id) return null;

  const p = (players || []).find(x => x.id === id);
  const t = !p && (nbaTeams || []).find(x => x.id === id);
  const e = p ? { ...p, kind: "player" } : t ? { ...t, kind: "nba_team" } : null;
  const [first, last] = e ? nameLines(e) : ["", id];
  const team = e && (e.kind === "player" ? NBA_TEAMS[e.nba_team] : NBA_TEAMS[e.id]);
  const actions = getCardActions();
  const rules = scoring?.rules || [];
  // NBA teams score by the league's team rules (TEAM draft 6): their breakdowns use those parts' labels.
  const teamRules = (scoring?.team?.components || []).map(c => ({ key: c.id, label: c.label, name: c.name }));
  const isTeam = e?.kind === "nba_team";
  const inj = e?.kind === "player" ? injuries[e.id] : null; // current status only
  const proj = hist?.projection || null;
  const season = s => (hist?.seasons || []).find(x => x.season === s) || null;

  return (
    <div className="pc-overlay" onClick={() => setId(null)}>
      <div className="pc-card" role="dialog" aria-modal="true" aria-label={e ? e.name : "Player"} onClick={ev => ev.stopPropagation()}
        style={borderStyle}>
        <div className="pc-head" style={{ "--team": team?.primary || "var(--surface-3)" }}>
          {e?.kind === "player" ? <span className="pc-hs"><Headshot playerId={e.id} tricode={e.nba_team} width={120} height={88} /><InjuryDot inj={inj} /></span>
            : e ? <span className="pc-logo"><NbaTeamSquare tricode={e.id} size={72} /></span> : null}
          <div className="pc-name">
            <b>{first} {last}</b>
            {e?.kind === "player" && <span>{[e.position, e.nba_team].filter(Boolean).join(" · ")}</span>}
            {/* opens in a new tab (2026-10-15): the page you were on — and this card — stay put */}
            {e && <Link className="pc-page" to={entityPath(e.id)} target="_blank" rel="noopener">{isTeam ? "Team page" : "Player page"} →</Link>}
          </div>
          <div className="pc-acts">
            {actions && e ? actions(e) : e?.team_name ? <span className="pc-own">{e.team_name}{e.slot ? ` · ${e.slot}` : ""}</span> : null}
            <button type="button" className="pc-close" aria-label="Close" onClick={() => setId(null)}>✕</button>
          </div>
        </div>
        {page && <div className="ppg pc-ppg" dangerouslySetInnerHTML={statsHtml} />}
        {page === undefined && <div className="pc-loading" aria-busy="true" />}
        {page && <ScheduleStrip proj={proj} weeks={settings?.weeks} />}
        {injuryKind(inj) && (
          <dl className="pc-inj">
            <dt>Status</dt><dd><b className={`inj-word ${injuryKind(inj)}`}>{injuryWord(inj)}</b>{inj.injury ? ` · ${inj.injury}` : ""}</dd>
            {backText(inj) && <><dt>Expected back</dt><dd>{backText(inj)}</dd></>}
            {inj.reported_at && <><dt>Updated</dt><dd>{new Date(inj.reported_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}</dd></>}
          </dl>
        )}
        {e && page === null ? ( // players: the header pieces above replace the tabs (the player page holds the rest)
          <>
            <nav className="pc-tabs" role="tablist">
              {TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}
              <span className="pc-gl"><GlossaryButton align="right" terms={["MAX", "AVG", "PROJ MAX", "PROJ AVG", "MAX low / high", "Weeks by games", "FPTS", "Δ", "GP"]} /></span>
            </nav>
            <div className="pc-body">
              {hist === undefined ? <p className="pc-empty">Loading…</p>
                : tab === "actual" ? (log === undefined ? <p className="pc-empty">Loading…</p> : <ActualTab log={log} proj={proj} team={isTeam} />)
                  : tab === "proj" ? <ProjectedTab proj={proj} />
                    : <SeasonTab s={season(tab)} rules={isTeam ? teamRules : rules} />}
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}

