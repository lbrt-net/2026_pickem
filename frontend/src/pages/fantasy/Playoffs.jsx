import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { TeamLink } from "../../components/fantasy/links";
import { BASE, PLAYOFF_TEAMS, REGULAR_SEASON_WEEKS, SEASON, record, standingsThrough, useFantasyApi } from "../../components/fantasy/data";

const box = { border: "1px solid var(--border)", padding: 8, fontSize: 13 };
const heading = { fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em" };

export default function Playoffs() {
  const teams = useFantasyApi("teams");
  const seeds = teams ? standingsThrough(teams, REGULAR_SEASON_WEEKS).slice(0, PLAYOFF_TEAMS) : [];
  const seed = n => {
    const r = seeds[n - 1];
    return r ? <>{n}. <TeamLink ownerId={r.team.owner_user_id} name={r.team.name} /> ({record(r)})</> : <>{n}. TBD</>;
  };

  return (
    <FantasyShell title="Fantasy Playoffs" season={SEASON}>
      <p style={{ fontSize: 13, marginBottom: 14 }}>
        Top {PLAYOFF_TEAMS} seeds from the final <Link to={`${BASE}/standings`}>Standings</Link> (projected) — weeks {REGULAR_SEASON_WEEKS + 1}-{REGULAR_SEASON_WEEKS + 3} — seeds 1 &amp; 2 get a first-round bye.
      </p>
      {teams === undefined ? <p style={{ fontSize: 13 }}>Loading…</p> : (
        <div style={{ display: "flex", gap: 40, alignItems: "center", flexWrap: "wrap" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 30, flex: 1, minWidth: 220 }}>
            <div style={heading}>Round 1</div>
            <div style={box}>{seed(1)}<br />(bye)</div>
            <div style={box}>{seed(3)}<br />vs {seed(6)}</div>
            <div style={box}>{seed(4)}<br />vs {seed(5)}</div>
            <div style={box}>{seed(2)}<br />(bye)</div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 90, flex: 1, minWidth: 220 }}>
            <div style={heading}>Semifinals</div>
            <div style={box}>{seed(1)}<br />vs winner 4/5</div>
            <div style={box}>{seed(2)}<br />vs winner 3/6</div>
          </div>
          <div style={{ flex: 1, minWidth: 220 }}>
            <div style={heading}>Championship</div>
            <div style={{ border: "2px solid var(--text)", padding: 14, fontSize: 13, fontWeight: 700, textAlign: "center" }}>TBD vs TBD</div>
          </div>
        </div>
      )}
    </FantasyShell>
  );
}
