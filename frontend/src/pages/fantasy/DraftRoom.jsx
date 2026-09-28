import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { BASE, SEASON, useFantasyApi } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";

const box = { border: "1px solid var(--border)", padding: 12 };
const heading = { fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 6 };
const cell = { padding: "5px 6px" };

export default function DraftRoom() {
  const user = useCurrentUser();
  const draft = useFantasyApi("draft");
  const players = useFantasyApi("players");
  const nbaTeams = useFantasyApi("nba-teams");

  if (draft === undefined) {
    return <FantasyShell title="Draft Room" season={SEASON}><p style={{ fontSize: 13 }}>Loading…</p></FantasyShell>;
  }

  const order = draft?.order || [];
  const picks = draft?.picks || [];
  const totalPicks = order.length * (draft?.rounds || 0);
  const done = totalPicks > 0 && picks.length >= totalPicks;
  const n = order.length || 1;
  // Snake: odd rounds go in order, even rounds reverse.
  const nextIndex = picks.length;
  const nextRound = Math.floor(nextIndex / n) + 1;
  const posInRound = nextIndex % n;
  const onClock = order[nextRound % 2 === 1 ? posInRound : n - 1 - posInRound];
  const available = [...(players || []), ...(nbaTeams || []).map(t => ({ ...t, position: "TEAM" }))]
    .filter(e => !e.team_id)
    .sort((a, b) => b.fantasy_points - a.fantasy_points)
    .slice(0, 15);

  return (
    <FantasyShell title="Draft Room" season={SEASON}>
      <p style={{ fontSize: 13, marginBottom: 10 }}>
        Snake draft, {draft?.rounds} rounds. {done
          ? <>The draft is over — see the <Link to={`${BASE}/draft/recap`}>Draft Recap</Link>.</>
          : "Live drafting (pick clock, making picks) isn't built yet; this shows the real order and pool."}
      </p>

      <div style={{ ...box, marginBottom: 10, display: "flex", gap: 6, overflowX: "auto", alignItems: "center" }}>
        <span style={{ fontSize: 12, fontWeight: 700 }}>ROUND 1 ORDER:</span>
        {order.map((t, i) => (
          <span key={t.id} style={{ fontSize: 12, border: !done && onClock?.id === t.id ? "2px solid var(--text)" : "1px solid var(--border)", padding: "3px 7px", fontWeight: user && t.owner_user_id === user.discordId ? 700 : 400 }}>
            {i + 1}. <TeamLink ownerId={t.owner_user_id} name={t.name} />
          </span>
        ))}
      </div>

      {!done && onClock && (
        <div style={{ border: "2px solid var(--text)", padding: 10, display: "flex", justifyContent: "space-between", marginBottom: 14, fontSize: 13 }}>
          <span style={{ fontWeight: 700 }}>Round {nextRound}, Pick {posInRound + 1}</span>
          <span>On the clock: <b><TeamLink ownerId={onClock.owner_user_id} name={onClock.name} /></b></span>
        </div>
      )}

      <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
        {!done && (
          <div style={{ ...box, flex: 1.4, minWidth: 300 }}>
            <div style={heading}>Best available</div>
            <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ fontSize: 12, textAlign: "left" }}>
                  <th style={cell}>#</th><th style={cell}>Name</th><th style={cell} title="Position">Pos</th>
                  <th style={{ ...cell, textAlign: "right" }} title="Fantasy points per game so far">Fantasy Pts</th>
                </tr>
              </thead>
              <tbody>
                {available.map((e, i) => (
                  <tr key={e.id} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                    <td style={cell}>{i + 1}</td>
                    <td style={cell}><EntityLink id={e.id} name={e.name} /></td>
                    <td style={cell}>{e.position}</td>
                    <td style={{ ...cell, textAlign: "right" }}>{e.fantasy_points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Link to={`${BASE}/players`} style={{ fontSize: 13, display: "inline-block", marginTop: 8 }}>All players &rarr;</Link>
          </div>
        )}

        <div style={{ ...box, flex: 1, minWidth: 300 }}>
          <div style={heading}>{done ? "Every pick" : "Recent picks"}</div>
          {picks.length === 0 && <div style={{ fontSize: 13 }}>No picks yet.</div>}
          <div style={{ maxHeight: done ? "none" : 360, overflowY: "auto" }}>
            {[...picks].reverse().slice(0, done ? undefined : 12).reverse().map(p => (
              <div key={p.pick} style={{ fontSize: 13, padding: "3px 0", borderBottom: "1px solid var(--border-subtle)" }}>
                Rd {p.round} · Pick {p.pick} — <TeamLink ownerId={p.owner_user_id} name={p.team_name} /> take{" "}
                <EntityLink id={p.id} name={p.name} /> ({p.position})
              </div>
            ))}
          </div>
        </div>
      </div>
    </FantasyShell>
  );
}
