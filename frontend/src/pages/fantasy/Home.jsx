import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import JoinBanner from "../../components/fantasy/JoinBanner";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { NbaTeamSquare, PositionBadge } from "../../components/fantasy/RosterBits";
import { nameLines } from "../../components/fantasy/nbaTeams";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { base, rosterBySlot, SEASON, useFantasyApi, weekPairings } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import "./Home.css";

// Fantasy Home (design: "lbrt.net Design" canvas, row N). Real data only, no projections.
//   Join (full) → Draft (full) → Standings (full)
//   → [after the draft] Your team | League activity → Matchups | Weekly recap

const fmtDay = iso => new Date(`${iso}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });
const addDays = (iso, n) => { const d = new Date(`${iso}T12:00:00`); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };
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

// Standings stats from the results engine: Pct, GB, per-week averages, last 5 results.
function standingsRows(results) {
  const rows = results?.standings || [];
  const finals = (results?.weeks || []).filter(w => w.status === "final" && w.kind === "regular");
  const resultsFor = id => finals.map(w => {
    const m = w.matchups.find(x => x.home.team.id === id || x.away.team.id === id);
    if (!m) return null;
    const [me, them] = m.home.team.id === id ? [m.home.score, m.away.score] : [m.away.score, m.home.score];
    return me > them ? "W" : me < them ? "L" : "T";
  }).filter(Boolean);
  const lead = rows[0];
  return rows.map(r => {
    const games = r.w + r.l + r.t;
    const gb = lead ? ((lead.w - r.w) + (r.l - lead.l)) / 2 : 0;
    return {
      ...r, games,
      pct: games ? ((r.w + r.t / 2) / games).toFixed(3).replace(/^0/, "") : "—",
      gb: !games || gb === 0 ? "—" : gb.toFixed(1),
      avgFor: games ? (r.pf / games).toFixed(1) : "0.0",
      avgAgst: games ? (r.pa / games).toFixed(1) : "0.0",
      last: resultsFor(r.team.id).slice(-5),
    };
  });
}

function Standings({ rows, anyTie, mine, byId }) {
  return (
    <section className="hm-panel" aria-label="Standings">
      <Head aside="Full standings →" to={`${base()}/standings`}>Standings</Head>
      {rows.length === 0 ? <p style={{ padding: 16, fontSize: 14 }}>No teams yet.</p> : (
        <div className="hm-scroll">
          <table className="hm-table">
            <thead>
              <tr>
                <th>Rk</th><th>Team</th>
                <th className="num" title={anyTie ? "Wins-ties-losses" : "Wins-losses"}>{anyTie ? "W-T-L" : "W-L"}</th>
                <th className="num" title="Win percentage">Pct</th>
                <th className="num" title="Games behind first place">GB</th>
                <th className="num" title="Average points scored per week">Avg For</th>
                <th className="num" title="Average points scored against per week">Avg Agst</th>
                <th title="Last five weeks">Last 5</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => {
                const team = { ...r.team, ...byId[r.team.id] };
                const you = mine && r.team.id === mine.id;
                return (
                  <tr key={r.team.id} className={you ? "mine" : ""}>
                    <td className="rank">{i + 1}</td>
                    <td>
                      <span className="hm-team-cell">
                        <TeamIcon team={team} size={32} />
                        <span className="hm-team-names">
                          <TeamLink ownerId={team.owner_user_id} name={team.name} />
                          {team.owner_name && team.owner_name !== team.name && <span className="hm-sub">{team.owner_name}</span>}
                        </span>
                        {you && <span className="hm-you">You</span>}
                      </span>
                    </td>
                    <td className="num"><span className="hm-big">{anyTie ? `${r.w}-${r.t}-${r.l}` : `${r.w}-${r.l}`}</span></td>
                    <td className="num">{r.pct}</td>
                    <td className="num">{r.gb}</td>
                    <td className="num">{r.avgFor}</td>
                    <td className="num">{r.avgAgst}</td>
                    <td>
                      {r.last.length === 0 ? "—" : (
                        <span className="hm-pips" aria-label={`Last ${r.last.length}: ${r.last.join(" ")}`}>
                          {r.last.map((x, j) => <span key={j} className={`hm-pip ${x}`} />)}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function YourTeam({ mine, myRow, myRank, total, mySide }) {
  const slotScore = Object.fromEntries((mySide?.slots || []).map(s => [s.id, s]));
  return (
    <section className="hm-panel" aria-label="Your team">
      <div className="hm-team-head">
        <TeamIcon team={mine} size={52} />
        <div>
          <div className="hm-team-name"><TeamLink ownerId={mine.owner_user_id} name={mine.name} /></div>
          <div style={{ fontSize: 14 }}>{myRow ? `${myRow.w}-${myRow.l}` : "0-0"}{myRank ? ` · ${myRank} of ${total}` : ""}</div>
        </div>
        <Link to={`${base()}/team`}>My team →</Link>
      </div>
      {rosterBySlot(mine.roster, mine.slot_list).map(({ entry }, i) => {
        if (!entry) return <div key={i} className="hm-roster-row"><span /><span /><span>Empty spot</span><span /></div>;
        const s = slotScore[entry.id];
        const [first, last] = nameLines(entry);
        const best = !s ? "—" : entry.kind === "nba_team" ? (s.games ? (s.score > 0 ? `+${s.score}` : `${s.score}`) : "—") : (s.best_game_date ? s.score : "—");
        return (
          <div key={i} className="hm-roster-row">
            <PositionBadge entry={entry} />
            <NbaTeamSquare tricode={entry.kind === "nba_team" ? entry.id : entry.nba_team} />
            <EntityLink id={entry.id} name={<span className="hm-name2"><span>{first}</span><b>{last}</b></span>} />
            <span className="hm-big" title="Best single game so far this week (NBA team: point margin, week total)">{best}</span>
          </div>
        );
      })}
      {mySide && <div className="hm-total"><span>This week so far</span><span className="hm-big">{mySide.score}</span></div>}
    </section>
  );
}

function Side({ team, score }) {
  return (
    <div className="hm-side">
      <TeamIcon team={team} size={28} />
      <TeamLink ownerId={team.owner_user_id} name={team.name} />
      {score !== undefined && <span className="hm-score">{score}</span>}
    </div>
  );
}

export default function FantasyHome() {
  const user = useCurrentUser();
  const teams = useFantasyApi("teams");
  const results = useFantasyApi("results");
  const d = useFantasyApi("draft");
  const info = useFantasyApi("league/members");
  const title = info?.league_name || "Home"; // the commissioner's league name, once set

  if (teams === undefined || results === undefined) {
    return <FantasyShell title={title} season={SEASON}><div className="hm"><JoinBanner /><p style={{ fontSize: 13 }}>Loading…</p></div></FantasyShell>;
  }

  const all = teams || [];
  const byId = Object.fromEntries(all.map(t => [t.id, t]));
  const mine = user ? all.find(t => t.owner_user_id === user.discordId) : null;
  const rows = standingsRows(results);
  const anyTie = rows.some(r => r.t > 0); // W-T-L only when some team has a tie
  const drafted = d?.status === "complete";

  // This week: real matchups (real scores once games are played); before the season, week 1's pairings.
  const week = results?.weeks?.find(w => w.week === results.current_week);
  const weekNo = week ? week.week : 1;
  const weekStart = week ? week.start : results?.season_start;
  const weekEnd = week ? week.end : weekStart && addDays(weekStart, 6);
  const matchups = week
    ? week.matchups.map(m => ({ a: byId[m.home.team.id] || m.home.team, b: byId[m.away.team.id] || m.away.team, as: m.home.score, bs: m.away.score }))
    : weekPairings(all, 1).map(([a, b]) => ({ a, b }));
  const paired = new Set(matchups.flatMap(m => [m.a.id, m.b.id]));
  const byes = all.filter(t => !paired.has(t.id));

  const myRow = mine && rows.find(r => r.team.id === mine.id);
  const myRank = myRow ? rows.indexOf(myRow) + 1 : null;
  const mySide = mine && week?.matchups.flatMap(m => [m.home, m.away]).find(s => s.team.id === mine.id);

  return (
    <FantasyShell title={title} season={SEASON}>
      <div className="hm">
        <JoinBanner />
        <DraftCard d={d} />
        <Standings rows={rows} anyTie={anyTie} mine={mine} byId={byId} />

        {drafted && (
          <div className="hm-grid">
            {mine ? <YourTeam mine={mine} myRow={myRow} myRank={myRank} total={rows.length} mySide={mySide} /> : <div />}
            <UnderConstruction title="League activity" />
          </div>
        )}

        <div className="hm-grid">
          <section className="hm-panel" aria-label="This week's matchups">
            <Head aside={weekStart ? `${fmtDay(weekStart)} – ${fmtDay(weekEnd)}` : null}>Week {weekNo} matchups</Head>
            {matchups.length === 0 && byes.length === 0 && <p style={{ padding: 16, fontSize: 14 }}>Not enough teams yet.</p>}
            {matchups.map((m, i) => (
              <div key={i} className={`hm-matchup${mine && (m.a.id === mine.id || m.b.id === mine.id) ? " mine" : ""}`}>
                <Side team={m.a} score={week ? m.as : undefined} />
                {!week && <span className="hm-vs">vs</span>}
                <Side team={m.b} score={week ? m.bs : undefined} />
              </div>
            ))}
            {byes.map(t => (
              <div key={t.id} className="hm-matchup"><Side team={t} /><span className="hm-vs">Bye this week</span></div>
            ))}
            <Link className="hm-more" to={`${base()}/matchup`}>All matchups →</Link>
          </section>
          <UnderConstruction title="Weekly recap" />
        </div>
      </div>
    </FantasyShell>
  );
}
