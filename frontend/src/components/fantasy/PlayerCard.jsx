import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CARD_EVENT, getCardActions } from "./cardEvents";
import { API_BASE, TEST_SEASON, entityPath, seasonOf, useFantasyApi } from "./data";
import { Headshot, NbaTeamSquare } from "./RosterBits";
import { NBA_TEAMS, nameLines } from "./nbaTeams";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";
import GlossaryButton from "./GlossaryButton";
import "./PlayerCard.css";

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

function ProjectedTab({ proj, weeks }) {
  if (!proj) return <p className="pc-empty">No projection for him this season.</p>;
  const wk = (proj.weeks || []).filter(w => w.games);
  const low = mean(wk.map(w => w.p25)), high = mean(wk.map(w => w.p90));
  const groups = {};
  for (const w of wk) if (w.games < FUSED) (groups[w.games] ||= []).push(w);
  const dates = Object.fromEntries((weeks || []).map(w => [w.week, range(w.start, w.end)]));
  return (
    <>
      <Kv items={[["Proj max", f1(proj.proj_max), null, true], ["Proj avg", f1(proj.proj_avg), null, true],
        [<>Proj max<sub>low</sub></>, f1(low), null, true], [<>Proj max<sub>high</sub></>, f1(high), null, true]]} />
      <div className="pc-two">
        <div>
          <div className="pc-st">Weeks by games</div>
          <table className="pc-tb">
            <thead><tr><th className="l">Games</th><th>Weeks</th><th>Max<sub>low</sub></th><th>Max</th><th>Max<sub>high</sub></th></tr></thead>
            <tbody>
              {Object.entries(groups).map(([g, ws]) => (
                <tr key={g}><td className="l">{g}</td><td>{ws.length}</td><td className="pj">{f1(mean(ws.map(w => w.p25)))}</td>
                  <td className="pj">{f1(mean(ws.map(w => w.e)))}</td><td className="pj">{f1(mean(ws.map(w => w.p90)))}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <div>
          <div className="pc-st">Every week</div>
          <div className="pc-scroll">
            <table className="pc-tb weeks">
              <thead><tr><th className="l">Wk</th><th className="l">Dates</th><th>Games</th><th>Proj max</th></tr></thead>
              <tbody>{(proj.weeks || []).map(w => <tr key={w.week}><td className="l">{w.week}</td><td className="l">{dates[w.week] || ""}</td><td>{w.games}</td><td className="pj">{f1(w.e)}</td></tr>)}</tbody>
            </table>
          </div>
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
          <div className="pc-st">His max game, average · {s.team}</div>
          <Breakdown bd={s.max_breakdown} rules={rules} />
        </div>
        <div>
          <div className="pc-st">Every week</div>
          <div className="pc-scroll">
            <table className="pc-tb weeks">
              <thead><tr><th className="l">Wk</th><th>Games</th><th>Max</th></tr></thead>
              <tbody>{(s.weeks || []).map(w => <tr key={w.week}><td className="l">{w.week}</td><td>{w.games}</td><td>{f1(w.max)}</td></tr>)}</tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}

function ActualTab({ log, proj }) {
  const played = (log?.games || []).filter(g => g.fantasy_points != null && !g.dnp);
  if (!played.length) return <p className="pc-empty">No games yet this season.</p>;
  const byWeek = {};
  for (const g of played) (byWeek[g.week] ||= []).push(g);
  const weekRows = Object.entries(byWeek).map(([w, gs]) => ({ week: Number(w), games: gs.length, max: Math.max(...gs.map(g => g.fantasy_points)) }));
  const projByWeek = Object.fromEntries((proj?.weeks || []).map(w => [w.week, w.e]));
  const best = new Set(Object.values(byWeek).map(gs => gs.reduce((a, b) => (b.fantasy_points > a.fantasy_points ? b : a)).game_id));
  const avgMax = mean(weekRows.map(w => w.max)), avg = mean(played.map(g => g.fantasy_points));
  return (
    <>
      <Kv items={[["Max", f1(avgMax), proj && f1(proj.proj_max)], ["Avg", f1(avg), proj && f1(proj.proj_avg)], ["GP", played.length], ["Weeks", weekRows.length]]} />
      <div className="pc-two">
        <div>
          <div className="pc-st">Weeks</div>
          <table className="pc-tb weeks">
            <thead><tr><th className="l">Wk</th><th>Games</th><th>Max</th><th>Proj max</th><th>Δ</th></tr></thead>
            <tbody>
              {weekRows.map(w => {
                const p = projByWeek[w.week], dlt = p != null ? w.max - p : null;
                return <tr key={w.week}><td className="l">{w.week}</td><td>{w.games}</td><td>{f1(w.max)}</td><td className="pj">{f1(p)}</td><td className={dlt < 0 ? "neg" : ""}>{dlt == null ? "" : signed(dlt)}</td></tr>;
              })}
            </tbody>
          </table>
        </div>
        <div>
          <div className="pc-st">Game log</div>
          <div className="pc-scroll">
            <table className="pc-tb">
              <thead><tr><th className="l">Date</th><th className="l">Opp</th><th>MIN</th><th>PTS</th><th>REB</th><th>AST</th><th>STL</th><th>BLK</th><th>TO</th><th>FPTS</th></tr></thead>
              <tbody>
                {[...played].reverse().map(g => (
                  <tr key={g.game_id} className={g.week % 2 ? "wk-alt" : ""}>
                    <td className="l">{MD(g.date)}</td><td className="l">{g.home ? "vs" : "@"} {g.opponent}</td><td>{Math.round(g.minutes)}</td>
                    <td>{g.pts}</td><td>{g.reb}</td><td>{g.ast}</td><td>{g.stl}</td><td>{g.blk}</td><td>{g.tov}</td>
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

export default function PlayerCardHost() {
  const [id, setId] = useState(null);
  const [tab, setTab] = useState("proj");
  const [scenario] = useFantasyScenario();
  const players = useFantasyApi("players");
  const nbaTeams = useFantasyApi("nba-teams");
  const scoring = useFantasyApi("scoring");
  const settings = useFantasyApi("league/settings");
  const leagueSeason = seasonOf() === TEST_SEASON ? "2025-26" : "2026-27";
  const hist = useJson(id ? `${API}${API_BASE}/players/${encodeURIComponent(id)}/history?scenario=${scenario}` : null);
  const log = useJson(id && tab === "actual" ? `${API}${API_BASE}/entity/${encodeURIComponent(id)}/games?season=${leagueSeason}&scenario=${scenario}` : null);

  useEffect(() => {
    const open = e => { setId(e.detail.id); setTab("proj"); };
    const esc = e => { if (e.key === "Escape") setId(null); };
    window.addEventListener(CARD_EVENT, open);
    window.addEventListener("keydown", esc);
    return () => { window.removeEventListener(CARD_EVENT, open); window.removeEventListener("keydown", esc); };
  }, []);
  if (!id) return null;

  const p = (players || []).find(x => x.id === id);
  const t = !p && (nbaTeams || []).find(x => x.id === id);
  const e = p ? { ...p, kind: "player" } : t ? { ...t, kind: "nba_team" } : null;
  const [first, last] = e ? nameLines(e) : ["", id];
  const team = e && (e.kind === "player" ? NBA_TEAMS[e.nba_team] : NBA_TEAMS[e.id]);
  const actions = getCardActions();
  const rules = scoring?.rules || [];
  const proj = hist?.projection || null;
  const season = s => (hist?.seasons || []).find(x => x.season === s) || null;

  return (
    <div className="pc-overlay" onClick={() => setId(null)}>
      <div className="pc-card" role="dialog" aria-modal="true" aria-label={e ? e.name : "Player"} onClick={ev => ev.stopPropagation()}>
        <div className="pc-head" style={{ "--team": team?.primary || "var(--surface-3)" }}>
          {e?.kind === "player" ? <Headshot playerId={e.id} tricode={e.nba_team} width={120} height={88} />
            : e ? <span className="pc-logo"><NbaTeamSquare tricode={e.id} size={72} /></span> : null}
          <div className="pc-name">
            <b>{first} {last}</b>
            {e?.kind === "player" && <span>{[e.position, e.nba_team, e.proj_flags].filter(Boolean).join(" · ")}</span>}
          </div>
          <div className="pc-acts">
            {actions && e ? actions(e) : e?.team_name ? <span className="pc-own">{e.team_name}{e.slot ? ` · ${e.slot}` : ""}</span> : null}
            <button type="button" className="pc-close" aria-label="Close" onClick={() => setId(null)}>✕</button>
          </div>
        </div>
        {e?.kind === "player" ? (
          <>
            <nav className="pc-tabs" role="tablist">
              {TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}
              <span className="pc-gl"><GlossaryButton align="right" terms={["MAX", "AVG", "PROJ MAX", "PROJ AVG", "MAX low / high", "Weeks by games", "FPTS", "Δ", "GP"]} /></span>
            </nav>
            <div className="pc-body">
              {hist === undefined ? <p className="pc-empty">Loading…</p>
                : tab === "actual" ? (log === undefined ? <p className="pc-empty">Loading…</p> : <ActualTab log={log} proj={proj} />)
                  : tab === "proj" ? <ProjectedTab proj={proj} weeks={settings?.weeks} />
                    : <SeasonTab s={season(tab)} rules={rules} />}
            </div>
          </>
        ) : (
          <div className="pc-body"><p className="pc-empty">NBA team projections and history aren't built yet.</p></div>
        )}
        <div className="pc-foot">
          <Link className="pc-full" to={entityPath(id)} onClick={() => setId(null)}>Full page →</Link>
        </div>
      </div>
    </div>
  );
}

