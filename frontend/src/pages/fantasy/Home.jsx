import { Link, useNavigate } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import JoinBanner from "../../components/fantasy/JoinBanner";
import LeagueHeader from "../../components/fantasy/LeagueHeader";
import LeagueActivity from "../../components/fantasy/LeagueActivity";
import FitText from "../../components/fantasy/FitText";
import TeamIcon from "../../components/fantasy/TeamIcon";
import LastFive from "../../components/fantasy/LastFive";
import LockClock from "../../components/fantasy/LockClock";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { Headshot, NbaTeamSquare } from "../../components/fantasy/RosterBits";
import { NBA_TEAMS } from "../../components/fantasy/nbaTeams";
import { base, SEASON, useFantasyApi } from "../../components/fantasy/data";
import { ctDayDateTime, entityShort, signed } from "../../components/fantasy/format";
import { accent, bigGameFirst, hasTie, recordText, scheduleOf, standingsFrom } from "../../components/fantasy/standings";
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
    : d.draft_start_at ? ctDayDateTime(d.draft_start_at)
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
  const plain = { color: "inherit", textDecoration: "none" };
  // every tile's picture is the same height and sits on the same line (the bottom of the colored band)
  const teamTile = (label, t, num, cls) => t && { label, color: t.color, art: <TeamIcon team={t} size={58} />, name: t.name, team: null, num, cls,
    link: <TeamLink ownerId={t.owner_user_id} name={t.name} style={plain} /> };
  const playerTile = (label, p, t, num, cls) => p && {
    label, color: NBA_TEAMS[p.kind === "nba_team" ? p.id : p.nba_team]?.primary || t?.color, team: t, num, cls,
    art: p.kind === "nba_team" ? <NbaTeamSquare tricode={p.id} size={58} /> : <Headshot playerId={p.id} tricode={p.nba_team} width={80} height={58} />,
    face: p.kind !== "nba_team",
    name: entityShort(p), link: <EntityLink id={p.id} name={entityShort(p)} style={plain} /> };
  // the latest week's recap and Draft Grades, stacked (2026-10-23: the box matches League activity's height)
  const blocks = [];
  if (week) {
    const T = week.teams;
    const mvp = [...(week.players || [])].sort((a, b) => b.score - a.score)[0];
    blocks.push({ key: "week", title: `Week ${week.week}`, to: `${base()}/recap?tab=w${week.week}`, link: `Week ${week.week} recap →`,
      tiles: [teamTile("Best team", T[week.best], fmt(week.scores[week.best])),
        mvp && playerTile("Player of the week", mvp, T[mvp.team_id], `${mvp.kind === "nba_team" && mvp.score > 0 ? "+" : ""}${fmt(mvp.score)}`),
        week.closest && teamTile("Closest win", T[week.closest.winner], `+${fmt(week.closest.margin)}`)].filter(Boolean) });
  }
  if (draft) {
    const picks = Object.fromEntries(draft.picks.map(p => [p.id, p]));
    const aw = draft.awards || {};
    const best = picks[(aw.best_buy || aw.best_pick || [])[0]];
    const bench = (aw.bench || [])[0];
    const worst = picks[(aw.worst || [])[0]];
    blocks.push({ key: "draft", title: "The draft", to: `${base()}/recap?tab=draft`, link: "Draft Grades →",
      tiles: [best && playerTile(draft.type === "auction" ? "Best value" : "Best pick", best, byId[best.team_id], signed(best.added), "pos"),
        bench && teamTile("Deepest bench", byId[bench.team_id], signed(bench.added), "pos"),
        worst && playerTile("Worst drafted", worst, byId[worst.team_id], signed(worst.added), worst.added < 0 ? "neg" : "")].filter(Boolean) });
  }
  const shown = blocks.filter(b => b.tiles.length);
  return (
    <section className="hm-panel hm-recap" aria-label="Recap">
      <Head aside="All recaps →" to={`${base()}/recap`}>Recap</Head>
      {preDraft && !shown.length && <p className="hm-empty">Draft Grades and each week's recap will show here after the draft.</p>}
      {shown.map(b => (
        <div key={b.key} className="hm-rc-block">
          <div className="hm-rc-sub"><span>{b.title}</span><Link to={b.to}>{b.link}</Link></div>
          <div className="hm-rc-tiles">
            {b.tiles.map(x => (
              <div key={x.label} className="hm-rc-tile" style={{ "--nc": x.color, "--tc": (x.team || {}).color || x.color }}>
                <span className="hm-rc-tag">{x.label}</span>
                <div className={`hm-rc-top${x.face ? " face" : ""}`}>{x.art}</div>
                <div className="hm-rc-body">
                  <FitText className="hm-rc-name" text={x.name} max={15} min={11}>{x.link}</FitText>
                  {x.team && <span className="hm-rc-team"><TeamIcon team={x.team} size={14} /><TeamLink ownerId={x.team.owner_user_id} name={x.team.name} style={plain} /></span>}
                  <span className={`hm-rc-num ${x.cls || ""}`}>{x.num}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}

function Standings({ rows, tie }) {
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
              <td className="c">{recordText(r, tie)}</td>
              <td className="num">{r.pf.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</td>
              <td className="l5"><LastFive results={r.results} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function MatchupCard({ a, b, recOf, final, probOf, week }) {
  // clicking the card opens the matchup; the team names still open that team (2026-10-25)
  const nav = useNavigate();
  const to = `${base()}/matchup?${new URLSearchParams({ team: a.team.owner_user_id, ...(week ? { week } : {}) })}`;
  const live = final ? undefined : probOf?.(a.team.id, b.team.id);
  // the server's simulation only (2026-10-17): a quick local estimate used to show first and then jump
  const p = final ? winProb(a, b, final) : live ?? null;
  const row = (s, lead) => (
    <div className="hm-mrow" style={{ "--tc": accent(s.team.color) }}>
      <span className="hm-team"><TeamIcon team={s.team} size={26} /><span onClick={e => e.stopPropagation()}><TeamLink ownerId={s.team.owner_user_id} name={s.team.name} /></span><span className="hm-rec">{recOf(s.team.id)}</span></span>
      <b className={lead ? "lead" : ""}>{s.score.toFixed(1)}</b>
    </div>
  );
  return (
    <div className="hm-mcard go" role="link" tabIndex={0} onClick={() => nav(to)} onKeyDown={e => e.key === "Enter" && nav(to)}>
      {row(a, a.score > b.score)}
      {row(b, b.score > a.score)}
      <div className="hm-wp">
        <span>{winText(p)}</span>
        <div className="bar">{p != null && p > 0 && <i style={{ flexGrow: p, background: accent(a.team.color) }} />}{p != null && p < 1 && <i style={{ flexGrow: 1 - p, background: accent(b.team.color) }} />}</div>
        <span>{winText(p == null ? null : 1 - p)}</span>
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
  const tie = hasTie(rows);
  const recOf = id => { const r = rows.find(x => x.team.id === id); return r ? recordText(r, tie) : "0-0"; };
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
    const left = w => (w.entries || []).filter(e => e.slot !== "BENCH" && e.slot !== "IR").reduce((n, e) => n + (e.games_left || 0), 0);
    pairs.push([
      { team: t, score: v.starters_score ?? 0, proj: v.starters_projected ?? 0, left: left(v) },
      o ? { team: byId[o.team_id] || v.opponent, score: o.starters_score ?? 0, proj: o.starters_projected ?? 0, left: left(o) } : null,
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
          <Standings rows={rows} tie={tie} />
          <section className="hm-panel" aria-label="This week's matchups">
            <Head aside="All matchups →" to={`${base()}/matchup${weekNo ? `?week=${weekNo}` : ""}`}>{weekNo ? `Week ${weekNo} matchups` : "Matchups"}</Head>
            <div className="hm-mlist">
              {weeks === undefined && weekNo && <p style={{ fontSize: 13, margin: 0 }}>Loading…</p>}
              {bigGameFirst(pairs, rows, scheduleOf(results, weekNo)).map(([a, b]) => (b
                ? <MatchupCard key={a.team.id} a={a} b={b} recOf={recOf} final={resWeek?.status === "final"} probOf={probOf} week={weekNo} />
                : <div key={a.team.id} className="hm-mcard"><div className="hm-mrow"><span className="hm-team"><TeamIcon team={a.team} size={26} /><TeamLink ownerId={a.team.owner_user_id} name={a.team.name} /></span><span>Bye</span></div></div>))}
            </div>
          </section>
        </div>
        <div className="hm-grid hm-pair">
          <LeagueActivity teams={teams} preDraft={d && d.status !== "complete"} />
          <RecapSlot teams={teams} preDraft={d && d.status !== "complete"} />
        </div>
      </div>
    </FantasyShell>
  );
}
