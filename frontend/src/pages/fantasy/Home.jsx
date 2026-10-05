import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import JoinBanner from "../../components/fantasy/JoinBanner";
import TeamIcon from "../../components/fantasy/TeamIcon";
import LastFive from "../../components/fantasy/LastFive";
import { TeamLink } from "../../components/fantasy/links";
import { base, SEASON, useFantasyApi } from "../../components/fantasy/data";
import { recordText, standingsFrom } from "../../components/fantasy/standings";
import { useTeamWeeks, winProb } from "../../components/fantasy/teamWeeks";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import "./Home.css";

// Fantasy Home (design: canvas "Home v2"). Join → Draft → [Standings | this week's matchups]
// → [League activity | Weekly recap]. This week = the league-wide current week (/results home_week:
// week N until 5 min before week N+1's first game). Current scores; win % is the only projection.

const DRAFT_TYPES = { snake: "Snake", snake_3rr: "Snake, 3rd-round reversal", linear: "Normal order", auction: "Auction" };

function Head({ children, aside, to }) {
  return (
    <div className="hm-head">
      <span className="hm-tick" aria-hidden="true" />{children}
      {aside && (to ? <Link className="hm-head-aside" to={to}>{aside}</Link> : <span className="hm-head-aside">{aside}</span>)}
    </div>
  );
}

function DraftCard({ d }) {
  if (!d || d.status === "complete") return null;
  const running = d.status === "in_progress";
  const when = running ? "Drafting now"
    : d.draft_start_at ? new Date(d.draft_start_at).toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })
      : "Not scheduled yet";
  const detail = running && d.on_clock ? `On the clock: ${d.on_clock.name}`
    : `${DRAFT_TYPES[d.draft_type]} · ${d.rounds} rounds${d.draft_type === "auction" ? "" : ` · ${Math.round(d.pick_seconds / 60)} min per pick`}`;
  return (
    <section className="hm-draft" aria-label="Draft">
      <span className="hm-draft-label"><span className="hm-tick" aria-hidden="true" />Draft</span>
      <span className="hm-draft-when">{when}</span>
      <span style={{ fontSize: 14 }}>{detail}</span>
      <Link className="hm-btn" to={`${base()}/draft`}>{running ? "Go draft →" : "Draft room →"}</Link>
    </section>
  );
}

function UnderConstruction({ title }) {
  return <section className="hm-uc" aria-label={title}>{title}<span>Under construction</span></section>;
}

function Standings({ rows }) {
  const bestPf = Math.max(...rows.map(r => r.pf));
  return (
    <section className="hm-panel" aria-label="Standings">
      <Head aside="Full standings →" to={`${base()}/standings`}>Standings</Head>
      <table className="hm-table">
        <thead><tr><th className="w-rk">Rk</th><th>Team</th><th className="num w-wl" title="Wins-losses(-ties)">W-L</th><th className="num w-pf" title="Total fantasy points scored">Pts For</th><th className="w-l5" title="Last 5 weeks">Last 5</th></tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.team.id}>
              <td>{i + 1}</td>
              <td><span className="hm-team"><TeamIcon team={r.team} size={24} /><TeamLink ownerId={r.team.owner_user_id} name={r.team.name} /></span></td>
              <td className="num">{recordText(r)}</td>
              <td className={`num${r.pf > 0 && r.pf === bestPf ? " lit" : ""}`}>{r.pf.toFixed(1)}</td>
              <td><LastFive results={r.results} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function MatchupCard({ a, b, recOf, final }) {
  const p = winProb(a, b, final);
  const row = (s, lead) => (
    <div className="hm-mrow">
      <span className="hm-team"><TeamIcon team={s.team} size={26} /><TeamLink ownerId={s.team.owner_user_id} name={s.team.name} /><span className="hm-rec">{recOf(s.team.id)}</span></span>
      <b className={lead ? "lead" : ""}>{s.score.toFixed(1)}</b>
    </div>
  );
  return (
    <div className="hm-mcard">
      {row(a, a.score > b.score)}
      {row(b, b.score > a.score)}
      <div className="hm-wp">
        <span>{Math.round(p * 100)}%</span>
        <div className="bar"><i style={{ width: `${p * 100}%`, background: a.team.color || "var(--text)" }} /><i style={{ width: `${(1 - p) * 100}%`, background: b.team.color || "var(--surface-3)" }} /></div>
        <span>{100 - Math.round(p * 100)}%</span>
      </div>
    </div>
  );
}

export default function FantasyHome() {
  const [scenario] = useFantasyScenario();
  const teams = useFantasyApi("teams");
  const results = useFantasyApi("results");
  const d = useFantasyApi("draft");
  const info = useFantasyApi("league/members");
  const title = info?.league_name || "Home"; // the commissioner's league name, once set
  const weekNo = results ? (results.home_week ?? results.current_week ?? 1) : null;
  const weeks = useTeamWeeks((teams || []).map(t => t.id), weekNo, scenario);

  if (teams === undefined || results === undefined) {
    return <FantasyShell title={title} season={SEASON}><div className="hm"><JoinBanner /><p style={{ fontSize: 13 }}>Loading…</p></div></FantasyShell>;
  }

  const all = teams || [];
  const byId = Object.fromEntries(all.map(t => [t.id, t]));
  const rows = standingsFrom(results, all);
  const recOf = id => { const r = rows.find(x => x.team.id === id); return r ? recordText(r) : "0-0"; };
  const resWeek = results?.weeks?.find(w => w.week === weekNo);

  // This week's pairs from the week views (each team's opponent), with current scores + projections.
  const seen = new Set();
  const pairs = [];
  for (const t of all) {
    const v = weeks?.[t.id];
    const o = v?.opponent && weeks?.[v.opponent.id];
    if (!v || seen.has(t.id)) continue;
    seen.add(t.id);
    if (o) seen.add(o.team_id);
    pairs.push([
      { team: t, score: v.starters_score ?? 0, proj: v.starters_projected ?? 0 },
      o ? { team: byId[o.team_id] || v.opponent, score: o.starters_score ?? 0, proj: o.starters_projected ?? 0 } : null,
    ]);
  }

  return (
    <FantasyShell title={title} season={SEASON}>
      <div className="hm">
        <JoinBanner />
        <DraftCard d={d} />
        <div className="hm-top">
          <Standings rows={rows} />
          <section className="hm-panel" aria-label="This week's matchups">
            <Head aside="All matchups →" to={`${base()}/matchup${weekNo ? `?week=${weekNo}` : ""}`}>{weekNo ? `Week ${weekNo} matchups` : "Matchups"}</Head>
            <div className="hm-mlist">
              {weeks === undefined && weekNo && <p style={{ fontSize: 13, margin: 0 }}>Loading…</p>}
              {pairs.map(([a, b]) => (b
                ? <MatchupCard key={a.team.id} a={a} b={b} recOf={recOf} final={resWeek?.status === "final"} />
                : <div key={a.team.id} className="hm-mcard"><div className="hm-mrow"><span className="hm-team"><TeamIcon team={a.team} size={26} /><TeamLink ownerId={a.team.owner_user_id} name={a.team.name} /></span><span>Bye</span></div></div>))}
            </div>
          </section>
        </div>
        <div className="hm-grid">
          <UnderConstruction title="League activity" />
          <UnderConstruction title="Weekly recap" />
        </div>
      </div>
    </FantasyShell>
  );
}
