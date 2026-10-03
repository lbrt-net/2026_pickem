import { Link, useSearchParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { base, REGULAR_SEASON_WEEKS, SEASON, standingsThrough, useFantasyApi, weekPairings, weekScore } from "../../components/fantasy/data";

const box = { border: "1px solid var(--border)", padding: 12, marginBottom: 12 };
const heading = { fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em" };

const Score = ({ pair: [a, b] }) => (
  <>
    <TeamLink ownerId={a.owner_user_id} name={a.name} /> {weekScore(a)} – {weekScore(b)}{" "}
    <TeamLink ownerId={b.owner_user_id} name={b.name} />
  </>
);

// Same template reused for the season-end recap. Built on projected weekly scores for now.
export default function Recap() {
  const [params] = useSearchParams();
  const week = Math.min(Math.max(Number(params.get("week")) || 1, 1), REGULAR_SEASON_WEEKS);
  const teams = useFantasyApi("teams");

  const all = teams || [];
  const pairs = weekPairings(all, week);
  const margin = ([a, b]) => Math.abs(weekScore(a) - weekScore(b));
  const blowout = [...pairs].sort((x, y) => margin(y) - margin(x))[0];
  const closest = [...pairs].sort((x, y) => margin(x) - margin(y))[0];
  const best = [...all].sort((a, b) => weekScore(b) - weekScore(a))[0];
  const topPlayer = best && [...best.roster].sort((a, b) => b.fantasy_points - a.fantasy_points)[0];
  const before = week > 1 ? standingsThrough(all, week - 1).map(r => r.team.id) : null;
  const movers = before
    ? standingsThrough(all, week).map((r, i) => ({ team: r.team, move: before.indexOf(r.team.id) - i })).filter(m => m.move !== 0)
    : [];

  return (
    <FantasyShell title={`Week ${week} Recap`} season={SEASON}>
      <div style={{ display: "flex", gap: 12, marginBottom: 12, fontSize: 13, flexWrap: "wrap" }}>
        {week > 1 && <Link to={`${base()}/recap?week=${week - 1}`}>&larr; Week {week - 1}</Link>}
        {week < REGULAR_SEASON_WEEKS && <Link to={`${base()}/recap?week=${week + 1}`}>Week {week + 1} &rarr;</Link>}
        <Link to={`${base()}/matchup?week=${week}`}>Week {week} matchups</Link>
        <Link to={`${base()}/standings`}>Standings</Link>
      </div>
      <p style={{ fontSize: 13, marginBottom: 12 }}>Scores are projected from per-game averages until real box scores are hooked up.</p>

      {teams === undefined ? <p style={{ fontSize: 13 }}>Loading…</p> : pairs.length === 0 ? <p style={{ fontSize: 13 }}>No matchups this week.</p> : (
        <>
          <div style={box}>
            <div style={heading}>Team of the week</div>
            <div style={{ fontSize: 13, marginTop: 4 }}>
              <TeamLink ownerId={best.owner_user_id} name={best.name} /> — {weekScore(best)} pts
              {topPlayer && <> · top scorer: <EntityLink id={topPlayer.id} name={topPlayer.name} /> ({topPlayer.fantasy_points})</>}
            </div>
          </div>
          <div style={{ display: "flex", gap: 12, marginBottom: 12, flexWrap: "wrap" }}>
            <div style={{ ...box, flex: 1, minWidth: 260, marginBottom: 0 }}>
              <div style={heading}>Biggest blowout</div>
              <div style={{ fontSize: 13, marginTop: 4 }}><Score pair={blowout} /></div>
            </div>
            <div style={{ ...box, flex: 1, minWidth: 260, marginBottom: 0 }}>
              <div style={heading}>Closest matchup</div>
              <div style={{ fontSize: 13, marginTop: 4 }}><Score pair={closest} /></div>
            </div>
          </div>
          <div style={box}>
            <div style={{ ...heading, marginBottom: 6 }}>Standings movers</div>
            {movers.length === 0 && <div style={{ fontSize: 13 }}>No movement.</div>}
            {movers.map(m => (
              <div key={m.team.id} style={{ fontSize: 13 }}>
                <TeamLink ownerId={m.team.owner_user_id} name={m.team.name} /> {m.move > 0 ? `up ${m.move}` : `down ${-m.move}`}
              </div>
            ))}
          </div>
        </>
      )}
    </FantasyShell>
  );
}
