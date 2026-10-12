import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import JoinBanner from "../../components/fantasy/JoinBanner";
import LeagueHeader from "../../components/fantasy/LeagueHeader";
import LeagueActivity from "../../components/fantasy/LeagueActivity";
import FitText from "../../components/fantasy/FitText";
import TeamIcon from "../../components/fantasy/TeamIcon";
import LastFive from "../../components/fantasy/LastFive";
import LockClock from "../../components/fantasy/LockClock";
import { TeamLink } from "../../components/fantasy/links";
import { Headshot, NbaTeamSquare } from "../../components/fantasy/RosterBits";
import { NBA_TEAMS } from "../../components/fantasy/nbaTeams";
import { base, SEASON, useFantasyApi } from "../../components/fantasy/data";
import { accent, recordText, standingsFrom } from "../../components/fantasy/standings";
import { useTeamWeeks, useWinProbs, winProb, winText } from "../../components/fantasy/teamWeeks";
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

// The recap slot: before the draft, just its header (same as League activity). After it, a mini of the latest recap —
// the newest finished week, else Draft Grades — with a button to that recap and one to all recaps.
function RecapSlot({ teams, preDraft }) {
  const recap = useFantasyApi("recap");
  const lastWeek = recap?.weeks?.length ? recap.weeks[recap.weeks.length - 1].week : null;
  const wk = useFantasyApi(lastWeek ? `recap/week/${lastWeek}` : "recap");  // same request when there's no week yet
  const week = lastWeek && wk?.week === lastWeek ? wk : null;
  const draft = recap?.draft;
  const byId = Object.fromEntries((teams || []).map(t => [t.id, t]));
  const fmt = v => (v ?? 0).toFixed(1);
  const signed = v => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(1)}`;
  const short = n => { const p = (n || "").split(" "); return p.length < 2 ? n : `${p[0][0]}. ${p.slice(1).join(" ")}`; };
  const teamTile = (label, t, num, cls) => t && { label, color: t.color, art: <TeamIcon team={t} size={48} />, name: t.name, team: null, num, cls };
  const playerTile = (label, p, t, num, cls) => p && {
    label, color: NBA_TEAMS[p.kind === "nba_team" ? p.id : p.nba_team]?.primary || t?.color, team: t, num, cls,
    art: p.kind === "nba_team" ? <NbaTeamSquare tricode={p.id} size={46} /> : <Headshot playerId={p.id} tricode={p.nba_team} width={96} height={70} />,
    name: p.kind === "nba_team" ? p.name : short(p.name) };
  let tiles = null, to = null, label = null;
  if (week) {
    const T = week.teams;
    const mvp = [...(week.players || [])].sort((a, b) => b.score - a.score)[0];
    tiles = [teamTile("Best team", T[week.best], fmt(week.scores[week.best])),
      mvp && playerTile("Player of the week", mvp, T[mvp.team_id], fmt(mvp.score)),
      week.closest && teamTile("Closest win", T[week.closest.winner], `+${fmt(week.closest.margin)}`)];
    to = `${base()}/recap?tab=w${week.week}`; label = `Week ${week.week} recap →`;
  } else if (draft) {
    const picks = Object.fromEntries(draft.picks.map(p => [p.id, p]));
    const aw = draft.awards || {};
    const best = picks[(aw.best_buy || aw.best_pick || [])[0]];
    const bench = (aw.bench || [])[0];
    const worst = picks[(aw.worst || [])[0]];
    tiles = [best && playerTile(draft.type === "auction" ? "Best buy" : "Best pick", best, byId[best.team_id], signed(best.added), "pos"),
      bench && teamTile("Deepest bench", byId[bench.team_id], signed(bench.added), "pos"),
      worst && playerTile("Worst drafted", worst, byId[worst.team_id], signed(worst.added), worst.added < 0 ? "neg" : "")];
    to = `${base()}/recap?tab=draft`; label = "Draft Grades →";
  }
  tiles = tiles?.filter(Boolean);
  return (
    <section className="hm-panel hm-recap" aria-label="Recap">
      <Head aside={label} to={to}>Recap</Head>
      {preDraft && !tiles?.length && <p className="hm-empty">Draft Grades and each week's recap will show here after the draft.</p>}
      {tiles?.length > 0 && (
        <div className="hm-rc-tiles">
          {tiles.map(x => (
            <div key={x.label} className="hm-rc-tile" style={{ "--nc": x.color, "--tc": (x.team || {}).color || x.color }}>
              <span className="hm-rc-tag">{x.label}</span>
              <div className="hm-rc-top">{x.art}</div>
              <div className="hm-rc-body">
                <FitText className="hm-rc-name" text={x.name} max={15} min={11} />
                {x.team && <span className="hm-rc-team"><TeamIcon team={x.team} size={14} />{x.team.name}</span>}
                <span className={`hm-rc-num ${x.cls || ""}`}>{x.num}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function Standings({ rows }) {
  return (
    <section className="hm-panel" aria-label="Standings">
      <Head aside="Full standings →" to={`${base()}/standings`}>Standings</Head>
      <table className="hm-table">
        <thead><tr><th className="w-edge" /><th className="w-rk">Rk</th><th>Team</th><th className="c w-wl" title="Wins-losses(-ties)">W-L</th><th className="num w-pf" title="Total fantasy points scored">Pts For</th><th className="w-l5" title="Last 5 weeks">Last 5</th></tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.team.id} style={{ "--tc": accent(r.team.color) }}>
              <td className="edge" />
              <td className="rk">{i + 1}</td>
              <td><span className="hm-team"><TeamIcon team={r.team} size={26} /><TeamLink ownerId={r.team.owner_user_id} name={r.team.name} /></span></td>
              <td className="c">{recordText(r)}</td>
              <td className="num">{r.pf.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</td>
              <td><LastFive results={r.results} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function MatchupCard({ a, b, recOf, final, probOf }) {
  const live = final ? undefined : probOf?.(a.team.id, b.team.id);
  const p = live ?? winProb(a, b, final);
  const row = (s, lead) => (
    <div className="hm-mrow" style={{ "--tc": accent(s.team.color) }}>
      <span className="hm-team"><TeamIcon team={s.team} size={26} /><TeamLink ownerId={s.team.owner_user_id} name={s.team.name} /><span className="hm-rec">{recOf(s.team.id)}</span></span>
      <b className={lead ? "lead" : ""}>{s.score.toFixed(1)}</b>
    </div>
  );
  return (
    <div className="hm-mcard">
      {row(a, a.score > b.score)}
      {row(b, b.score > a.score)}
      <div className="hm-wp">
        <span>{winText(p)}</span>
        <div className="bar"><i style={{ flexGrow: p, background: accent(a.team.color) }} /><i style={{ flexGrow: 1 - p, background: accent(b.team.color) }} /></div>
        <span>{winText(1 - p)}</span>
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
  const probOf = useWinProbs(weekNo, scenario);

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

  const lockSrc = weeks && Object.values(weeks)[0];

  return (
    <FantasyShell title={title} season={SEASON}>
      <div className="hm">
        <LeagueHeader showName={false} />
        <JoinBanner />
        <DraftCard d={d} />
        {lockSrc && <LockClock lock={lockSrc.week_lock} next={lockSrc.next_lock} asOf={lockSrc.as_of} />}
        <div className="hm-top">
          <Standings rows={rows} />
          <section className="hm-panel" aria-label="This week's matchups">
            <Head aside="All matchups →" to={`${base()}/matchup${weekNo ? `?week=${weekNo}` : ""}`}>{weekNo ? `Week ${weekNo} matchups` : "Matchups"}</Head>
            <div className="hm-mlist">
              {weeks === undefined && weekNo && <p style={{ fontSize: 13, margin: 0 }}>Loading…</p>}
              {pairs.map(([a, b]) => (b
                ? <MatchupCard key={a.team.id} a={a} b={b} recOf={recOf} final={resWeek?.status === "final"} probOf={probOf} />
                : <div key={a.team.id} className="hm-mcard"><div className="hm-mrow"><span className="hm-team"><TeamIcon team={a.team} size={26} /><TeamLink ownerId={a.team.owner_user_id} name={a.team.name} /></span><span>Bye</span></div></div>))}
            </div>
          </section>
        </div>
        <div className="hm-grid">
          <LeagueActivity teams={teams} preDraft={d && d.status !== "complete"} />
          <RecapSlot teams={teams} preDraft={d && d.status !== "complete"} />
        </div>
      </div>
    </FantasyShell>
  );
}
