import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { TeamLink } from "../../components/fantasy/links";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { BASE, PLAYOFF_TEAMS, REGULAR_SEASON_WEEKS, SEASON, record, standingsThrough, useFantasyApi } from "../../components/fantasy/data";
import "./Playoffs.css";

// Top 6 seeds; 1 & 2 get a first-round bye. Grid placement for each piece
// is explicit (see Playoffs.css): columns 1/3/5/7 are rounds, 2/4/6 are
// connector gutters; rows 2 and 3 are the two halves of the bracket.
// `order` only matters on phones, where the grid becomes one stacked column.
const QUARTERS = [[4, 5], [3, 6]];
const SEMIS = [[1, "Winner 4 v 5"], [2, "Winner 3 v 6"]];

function RoundHead({ col, name, week }) {
  return (
    <div className="po-round-head" style={{ gridColumn: col, order: col }}>
      <span className="po-round-name">{name}</span>
      <span className="po-round-week">Week {week}</span>
    </div>
  );
}

function SeedRow({ n, seeds, bye }) {
  const r = seeds[n - 1];
  return (
    <div className="po-team">
      <span className={`po-seed${n <= 2 ? " top" : ""}`}>{n}</span>
      {r && <TeamIcon team={r.team} size={26} />}
      <span className="po-team-name">{r ? <TeamLink ownerId={r.team.owner_user_id} name={r.team.name} /> : "TBD"}</span>
      {bye && <span className="po-bye">Bye</span>}
      {r && <span className="po-team-rec">{record(r)}</span>}
    </div>
  );
}

function PlaceholderRow({ label }) {
  return (
    <div className="po-team placeholder">
      <span className="po-seed">–</span>
      <span className="po-team-name">{label}</span>
    </div>
  );
}

function TrophyIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path d="M5 2.5h8v4a4 4 0 0 1-8 0zM5 4H2.5v1.5A2.5 2.5 0 0 0 5 8M13 4h2.5v1.5A2.5 2.5 0 0 1 13 8M9 10.5V13M6 15.5h6M7 13h4" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Playoffs() {
  const teams = useFantasyApi("teams");
  const seeds = teams ? standingsThrough(teams, REGULAR_SEASON_WEEKS).slice(0, PLAYOFF_TEAMS) : [];
  const week = REGULAR_SEASON_WEEKS;

  return (
    <FantasyShell title="Playoffs" season={SEASON} skeleton>
      <p style={{ fontSize: 14, marginBottom: 24 }}>
        Top {PLAYOFF_TEAMS} from the final <Link to={`${BASE}/standings`}>Standings</Link> (projected until the regular season ends). Seeds 1 &amp; 2 get a first-round bye.
      </p>
      {teams === undefined ? <p style={{ fontSize: 14 }}>Loading…</p> : (
        <div className="po-bracket">
          <RoundHead col={1} name="Quarterfinals" week={week + 1} />
          <RoundHead col={3} name="Semifinals" week={week + 2} />
          <RoundHead col={5} name="Championship" week={week + 3} />
          <div className="po-round-head" style={{ gridColumn: 7, order: 7 }}>
            <span className="po-round-name">Champion</span>
            <span className="po-round-week">2026-27</span>
          </div>

          {QUARTERS.map(([a, b], i) => (
            <div key={`qf${i}`} style={{ display: "contents" }}>
              <div className="po-cell" style={{ gridColumn: 1, gridRow: i + 2, order: 2 }}>
                <div className="po-match">
                  <SeedRow n={a} seeds={seeds} />
                  <SeedRow n={b} seeds={seeds} />
                </div>
              </div>
              <div className="po-line straight" style={{ gridColumn: 2, gridRow: i + 2 }} />
            </div>
          ))}

          {SEMIS.map(([top, feeder], i) => (
            <div key={`sf${i}`} className="po-cell" style={{ gridColumn: 3, gridRow: i + 2, order: 4 }}>
              <div className="po-match">
                <SeedRow n={top} seeds={seeds} bye />
                <PlaceholderRow label={feeder} />
              </div>
            </div>
          ))}

          <div className="po-line join" style={{ gridColumn: 4, gridRow: "2 / 4" }} />

          <div className="po-cell" style={{ gridColumn: 5, gridRow: "2 / 4", order: 6 }}>
            <div className="po-match final">
              <PlaceholderRow label="Winner semifinal 1" />
              <PlaceholderRow label="Winner semifinal 2" />
            </div>
          </div>

          <div className="po-line straight gold" style={{ gridColumn: 6, gridRow: "2 / 4" }} />

          <div className="po-cell" style={{ gridColumn: 7, gridRow: "2 / 4", order: 8 }}>
            <div className="po-champ">
              <span className="po-champ-label"><TrophyIcon />Champion</span>
              <span className="po-champ-name">TBD</span>
            </div>
          </div>
        </div>
      )}
    </FantasyShell>
  );
}
