import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import JoinBanner from "../../components/fantasy/JoinBanner";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { BASE, SEASON, rosterBySlot, useFantasyApi, weekPairings } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import "./Home.css";

// Fantasy Home (design: "lbrt.net Design" canvas, row N). Everything here is real data:
// join → draft → your team + this week's matchups → standings → under-construction blocks.
// No projections anywhere (ROADMAP TODO).

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
      <Link className="hm-btn" to={`${BASE}/draft`}>{running ? "Go draft →" : "Draft room →"}</Link>
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

  if (teams === undefined || results === undefined) {
    return <FantasyShell title="Home" season={SEASON}><JoinBanner /><p style={{ fontSize: 13 }}>Loading…</p></FantasyShell>;
  }

  const all = teams || [];
  const byId = Object.fromEntries(all.map(t => [t.id, t]));
  const mine = user ? all.find(t => t.owner_user_id === user.discordId) : null;
  const standings = results?.standings || [];
  const anyTie = standings.some(r => r.t > 0);
  const rec = r => (anyTie ? `${r.w}-${r.t}-${r.l}` : `${r.w}-${r.l}`); // W-T-L only when some team has a tie

  // This week: real matchups (with real scores once games are played) from the results engine;
  // before the season, week 1's pairings with no scores.
  const week = results?.weeks?.find(w => w.week === results.current_week);
  const weekNo = week ? week.week : 1;
  const weekStart = week ? week.start : results?.season_start;
  const weekEnd = week ? week.end : weekStart && addDays(weekStart, 6);
  const matchups = week
    ? week.matchups.map(m => ({ a: byId[m.home.team.id] || m.home.team, b: byId[m.away.team.id] || m.away.team, as: m.home.score, bs: m.away.score }))
    : weekPairings(all, 1).map(([a, b]) => ({ a, b }));
  const paired = new Set(matchups.flatMap(m => [m.a.id, m.b.id]));
  const byes = all.filter(t => !paired.has(t.id));

  const myRow = mine && standings.find(r => r.team.id === mine.id);
  const myRank = myRow ? standings.indexOf(myRow) + 1 : null;
  const mySide = mine && week?.matchups.flatMap(m => [m.home, m.away]).find(s => s.team.id === mine.id);
  const slotScore = Object.fromEntries((mySide?.slots || []).map(s => [s.id, s]));

  return (
    <FantasyShell title="Home" season={SEASON}>
      <div className="hm">
        <JoinBanner />
        <DraftCard d={d} />

        <div className="hm-grid">
          {mine && (
            <section className="hm-panel" aria-label="Your team">
              <div className="hm-team-head">
                <TeamIcon team={mine} size={60} />
                <div>
                  <div className="hm-team-name"><TeamLink ownerId={mine.owner_user_id} name={mine.name} /></div>
                  <div style={{ fontSize: 14 }}>{myRow ? rec(myRow) : "0-0"}{myRank ? ` · ${myRank} of ${standings.length}` : ""}</div>
                </div>
                <Link to={`${BASE}/team`}>My team →</Link>
              </div>
              {mine.roster.length === 0 ? (
                <p style={{ padding: 16, fontSize: 14 }}>Nobody drafted yet.</p>
              ) : (
                <>
                  <table className="hm-table">
                    <thead><tr><th>Slot</th><th>Player</th><th className="num" title="Best single game so far this week (NBA teams: point margin, week total)">Best game</th></tr></thead>
                    <tbody>
                      {rosterBySlot(mine.roster, mine.slot_list).map(({ slot, entry }, i) => {
                        const s = entry && slotScore[entry.id];
                        return (
                          <tr key={i}>
                            <td className="hm-slot">{slot === "PLAYER" ? "Player" : slot === "TEAM" ? "Team" : slot}</td>
                            <td>{entry ? <><EntityLink id={entry.id} name={entry.name} /><span className="hm-sub">{entry.kind === "player" ? `${entry.position || "—"} · ${entry.nba_team}` : "Point margin, week total"}</span></> : "Empty"}</td>
                            <td className="num"><span className="hm-big">{s ? (s.kind === "nba_team" ? (s.games ? (s.score > 0 ? `+${s.score}` : s.score) : "—") : (s.best_game_date ? s.score : "—")) : "—"}</span></td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                  {mySide && <div className="hm-total"><span>Week total so far</span><span className="hm-big">{mySide.score}</span></div>}
                </>
              )}
            </section>
          )}

          <section className="hm-panel" aria-label="This week's matchups">
            <Head aside={weekStart ? `${fmtDay(weekStart)} – ${fmtDay(weekEnd)}` : null}>Week {weekNo} matchups</Head>
            {matchups.length === 0 && <p style={{ padding: 16, fontSize: 14 }}>Not enough teams yet.</p>}
            {matchups.map((m, i) => (
              <div key={i} className={`hm-matchup${mine && (m.a.id === mine.id || m.b.id === mine.id) ? " mine" : ""}`}>
                <Side team={m.a} score={week ? m.as : undefined} />
                {!week && <span className="hm-vs">vs</span>}
                <Side team={m.b} score={week ? m.bs : undefined} />
              </div>
            ))}
            {byes.map(t => (
              <div key={t.id} className="hm-matchup"><Side team={t} score={undefined} /><span className="hm-vs">Bye this week</span></div>
            ))}
            <Link className="hm-more" to={`${BASE}/matchup`}>All matchups →</Link>
          </section>

          {!mine && (
            <section className="hm-panel" aria-label="Standings">
              <Head aside="Full standings →" to={`${BASE}/standings`}>Standings</Head>
              <StandingsTable standings={standings} rec={rec} anyTie={anyTie} byId={byId} mine={mine} />
            </section>
          )}
        </div>

        {mine && (
          <section className="hm-panel" aria-label="Standings">
            <Head aside="Full standings →" to={`${BASE}/standings`}>Standings</Head>
            <StandingsTable standings={standings} rec={rec} anyTie={anyTie} byId={byId} mine={mine} />
          </section>
        )}

        <div className="hm-grid">
          <section className="hm-uc" aria-label="League activity">League activity<span>Under construction</span></section>
          <section className="hm-uc" aria-label="Weekly recap">Weekly recap<span>Under construction</span></section>
        </div>
      </div>
    </FantasyShell>
  );
}

function StandingsTable({ standings, rec, anyTie, byId, mine }) {
  if (standings.length === 0) return <p style={{ padding: 16, fontSize: 14 }}>No teams yet.</p>;
  return (
    <table className="hm-table">
      <thead>
        <tr>
          <th>Rk</th><th>Team</th>
          <th className="num" title={anyTie ? "Wins-ties-losses" : "Wins-losses"}>{anyTie ? "W-T-L" : "W-L"}</th>
          <th className="num" title="Total points scored">Pts For</th><th className="num" title="Total points scored against">Pts Agst</th>
        </tr>
      </thead>
      <tbody>
        {standings.map((r, i) => {
          const team = byId[r.team.id] || r.team;
          return (
            <tr key={r.team.id} className={mine && r.team.id === mine.id ? "mine" : ""}>
              <td className="rank">{i + 1}</td>
              <td><span className="hm-team-cell"><TeamIcon team={team} size={24} /><TeamLink ownerId={team.owner_user_id} name={team.name} /></span></td>
              <td className="num"><span className="hm-big" style={{ fontSize: 20 }}>{rec(r)}</span></td>
              <td className="num">{r.pf.toFixed(1)}</td>
              <td className="num">{r.pa.toFixed(1)}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
