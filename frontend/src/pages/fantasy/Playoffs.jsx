import FantasyShell from "../../components/fantasy/FantasyShell";
import { TeamLink } from "../../components/fantasy/links";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { SEASON, useFantasyApi } from "../../components/fantasy/data";
import "./Playoffs.css";

// Playoffs (GET /results → playoffs, engine._bracket): seeds from the standings (final once the regular season ends),
// one column per round with scores once its week starts, the winner once it's over, then the champion.
// The sidebar link opens once half the regular season is done.
const range = (a, b) => {
  const o = { month: "short", day: "numeric" };
  return `${new Date(`${a}T12:00:00`).toLocaleDateString(undefined, o)} – ${new Date(`${b}T12:00:00`).toLocaleDateString(undefined, o)}`;
};

function Side({ s, score, won, bye }) {
  if (!s) return <div className="po-team placeholder"><span className="po-seed">–</span><span className="po-team-name">TBD</span></div>;
  return (
    <div className={`po-team${won ? " won" : ""}`}>
      <span className="po-seed">{s.seed}</span>
      <TeamIcon team={s.team} size={26} />
      <span className="po-team-name"><TeamLink ownerId={s.team.owner_user_id} name={s.team.name} /></span>
      {bye && <span className="po-bye">Bye</span>}
      {score != null && <span className="po-score">{score.toFixed(1)}</span>}
    </div>
  );
}

export default function Playoffs() {
  const res = useFantasyApi("results");
  const p = res?.playoffs;
  return (
    <FantasyShell title="Playoffs" season={SEASON}>
      {p && (
        <div className="po-cols" style={{ gridTemplateColumns: `repeat(${p.rounds.length + 1}, minmax(0, 1fr))` }}>
          {p.rounds.map(r => (
            <section key={r.name} className="po-col">
              <div className="po-round-head"><span className="po-round-name">{r.name}</span>{r.start && <span className="po-round-week">{range(r.start, r.end)}</span>}</div>
              <div className="po-games">
                {r.byes.map(s => <div key={s.id} className="po-match bye"><Side s={p.seeds.find(x => x.team.id === s.id)} bye /></div>)}
                {r.games.map((g, i) => (
                  <div key={i} className="po-match">
                    <Side s={g.a} score={g.a_score} won={g.winner && g.a && g.winner.seed === g.a.seed} />
                    <Side s={g.b} score={g.b_score} won={g.winner && g.b && g.winner.seed === g.b.seed} />
                  </div>
                ))}
              </div>
            </section>
          ))}
          <section className="po-col">
            <div className="po-round-head"><span className="po-round-name">Champion</span></div>
            <div className="po-games">
              <div className="po-champ">
                {p.champion ? <><TeamIcon team={p.champion.team} size={56} /><span className="po-champ-name">{p.champion.team.name}</span></> : <span className="po-champ-name">TBD</span>}
              </div>
            </div>
          </section>
        </div>
      )}
    </FantasyShell>
  );
}
