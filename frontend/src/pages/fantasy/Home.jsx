import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { BASE, SEASON, record, rosterBySlot, standingsThrough, weekPairings, weekScore, useFantasyApi } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import JoinBanner from "../../components/fantasy/JoinBanner";

const box = { border: "1px solid var(--border)", padding: 14, marginBottom: 14 };
const label = { fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 8 };
const more = { fontSize: 13, display: "inline-block", marginTop: 8 };
// No real calendar yet — Home shows week 1 until the season clock exists.
const WEEK = 1;

function MatchupLine({ pair, week }) {
  if (!pair) return <div style={{ fontSize: 13 }}>No matchup.</div>;
  const [a, b] = pair;
  return (
    <div style={{ fontSize: 13 }}>
      <TeamLink ownerId={a.owner_user_id} name={a.name} /> {weekScore(a)} &ndash; {weekScore(b)}{" "}
      <TeamLink ownerId={b.owner_user_id} name={b.name} />
      <div><Link to={`${BASE}/matchup?week=${week}&team=${a.owner_user_id}`} style={more}>View matchup &rarr;</Link></div>
    </div>
  );
}

export default function FantasyHome() {
  const user = useCurrentUser();
  const teams = useFantasyApi("teams");
  const players = useFantasyApi("players");

  if (teams === undefined) {
    return <FantasyShell title="Fantasy Home" season={SEASON}><p style={{ fontSize: 13 }}>Loading…</p></FantasyShell>;
  }

  const all = teams || [];
  const standings = standingsThrough(all, WEEK);
  const myTeam = user ? all.find(t => t.owner_user_id === user.discordId) : null;
  const pairFor = week => {
    const pairs = weekPairings(all, week);
    return (myTeam && pairs.find(p => p.some(t => t.id === myTeam.id))) || pairs[0];
  };
  const pickups = (players || []).filter(p => !p.team_id).sort((a, b) => b.fantasy_points - a.fantasy_points).slice(0, 3);

  return (
    <FantasyShell title="Fantasy Home" season={SEASON} skeleton>
      <JoinBanner />
      <div style={box}>
        <div style={label}>League standings</div>
        <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
          <tbody>
            {standings.slice(0, 5).map((r, i) => (
              <tr key={r.team.id} style={{ fontWeight: myTeam && r.team.id === myTeam.id ? 700 : 400 }}>
                <td style={{ padding: "3px 6px" }}>{i + 1}</td>
                <td style={{ padding: "3px 6px" }}><TeamLink ownerId={r.team.owner_user_id} name={r.team.name} /></td>
                <td style={{ padding: "3px 6px", textAlign: "right" }}>{record(r)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <Link to={`${BASE}/standings`} style={more}>View full standings &rarr;</Link>
      </div>

      <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
        <div style={{ ...box, flex: 1, minWidth: 240 }}>
          <div style={label}>Week {WEEK} matchup (projected)</div>
          <MatchupLine pair={pairFor(WEEK)} week={WEEK} />
        </div>
        <div style={{ ...box, flex: 1, minWidth: 240 }}>
          <div style={label}>Next week — week {WEEK + 1}</div>
          <MatchupLine pair={pairFor(WEEK + 1)} week={WEEK + 1} />
        </div>
      </div>

      <div style={box}>
        <div style={label}>Suggested pickups (best free agents)</div>
        {pickups.length === 0 && <div style={{ fontSize: 13 }}>No free agents left.</div>}
        {pickups.map(p => (
          <div key={p.id} style={{ fontSize: 13, display: "flex", justifyContent: "space-between", padding: "3px 0" }}>
            <span><EntityLink id={p.id} name={p.name} /> — {p.position}, {p.nba_team}</span>
            <span>{p.fantasy_points} Fantasy Pts</span>
          </div>
        ))}
        <Link to={`${BASE}/players`} style={more}>Browse all players &rarr;</Link>
      </div>

      <div style={box}>
        <div style={label}>Your team</div>
        {!user && <div style={{ fontSize: 13 }}>Log in to see your team.</div>}
        {user && !myTeam && <div style={{ fontSize: 13 }}>You don't have a team in this league.</div>}
        {myTeam && (
          <>
            <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 6 }}><TeamLink ownerId={myTeam.owner_user_id} name={myTeam.name} /></div>
            {myTeam.roster.length === 0 && <div style={{ fontSize: 13 }}>Nobody drafted yet. <Link to={`${BASE}/draft`}>Go to the draft</Link></div>}
            {myTeam.roster.length > 0 && rosterBySlot(myTeam.roster, myTeam.slot_list).map(({ slot, entry }, i) => (
              <div key={i} style={{ fontSize: 13, padding: "2px 0" }}>
                <b style={{ display: "inline-block", width: 48 }}>{slot}</b>
                {entry ? <EntityLink id={entry.id} name={entry.name} /> : "Empty"}
              </div>
            ))}
            <Link to={`${BASE}/team`} style={{ ...more, border: "1px solid var(--border)", padding: "6px 12px", textDecoration: "none" }}>Manage Team &rarr;</Link>
          </>
        )}
      </div>
    </FantasyShell>
  );
}
