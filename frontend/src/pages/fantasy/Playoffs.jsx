import FantasyShell from "../../components/fantasy/FantasyShell";
import { TeamLink } from "../../components/fantasy/links";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { SEASON, useFantasyApi } from "../../components/fantasy/data";
import "./Playoffs.css";

// Playoffs (GET /results → playoffs, engine._bracket). A real bracket: each round is a column; a game's slot fed by an
// earlier game lines up with it and a connector joins them; seeds 1–2 (bye) wait in the semifinals opposite the
// quarterfinal that feeds them; the final sits between the semis and the champion beside it.
// A 2-week round is two legs, added up (each leg shown under the team's total).
const COL = 224, GAP = 44, ROW = 50, BOX = ROW * 2, VGAP = 44, HEAD = 56;
const range = (a, b) => {
  const o = { month: "short", day: "numeric" };
  return `${new Date(`${a}T12:00:00`).toLocaleDateString(undefined, o)} – ${new Date(`${b}T12:00:00`).toLocaleDateString(undefined, o)}`;
};

function layout(rounds) {
  // top of every game box, round by round; centers line up with the slot each feeder fills
  const tops = [];
  rounds.forEach((r, i) => {
    tops[i] = r.games.map((g, j) => {
      if (i === 0) return j * (BOX + VGAP);
      const [fa, fb] = g.from;
      const c = k => tops[i - 1][k] + BOX / 2;
      if (fa != null && fb != null) return (c(fa) + c(fb)) / 2 - BOX / 2;   // both from winners: centered between them
      if (fb != null) return c(fb) - ROW * 1.5;                              // a seed waits on top, the winner below
      if (fa != null) return c(fa) - ROW * 0.5;
      return j * (BOX + VGAP);
    });
  });
  const min = Math.min(0, ...tops.flat());
  return tops.map(col => col.map(t => t - min + HEAD));
}

function Side({ s, score, won, legs, which }) {
  if (!s) return <div className="po-team tbd"><span className="po-seed" /><span className="po-team-name">TBD</span></div>;
  return (
    <div className={`po-team${won ? " won" : ""}`}>
      <span className="po-seed">{s.seed}</span>
      <TeamIcon team={s.team} size={24} />
      <span className="po-team-name"><TeamLink ownerId={s.team.owner_user_id} name={s.team.name} />
        {legs && <small>{legs.map(l => `L${l.leg} ${l[which].toFixed(1)}`).join(" · ")}</small>}</span>
      {score != null && <span className="po-score">{score.toFixed(1)}</span>}
    </div>
  );
}

export default function Playoffs() {
  const res = useFantasyApi("results");
  const p = res?.playoffs;
  if (!p) return <FantasyShell title="Playoffs" season={SEASON} />;
  const tops = layout(p.rounds);
  const nCols = p.rounds.length + 1;
  const width = nCols * COL + (nCols - 1) * GAP;
  const height = Math.max(...tops.flat()) + BOX + 8;
  const x = i => i * (COL + GAP);
  const final = p.rounds.length - 1;
  const champTop = tops[final][0];
  const lines = [];
  p.rounds.forEach((r, i) => r.games.forEach((g, j) => g.from.forEach((f, side) => {
    if (f == null) return;
    const x1 = x(i - 1) + COL, y1 = tops[i - 1][f] + BOX / 2;
    const x2 = x(i), y2 = tops[i][j] + ROW * (side === 0 ? 0.5 : 1.5);
    const mx = x1 + GAP / 2;
    lines.push(<path key={`${i}-${j}-${side}`} d={`M${x1},${y1} H${mx} V${y2} H${x2}`} />);
  })));
  lines.push(<path key="champ" d={`M${x(final) + COL},${champTop + BOX / 2} H${x(final + 1)}`} />);
  return (
    <FantasyShell title="Playoffs" season={SEASON}>
      <div className="po-scroll">
        <div className="po-bracket" style={{ width, height }}>
          <svg className="po-lines" width={width} height={height}>{lines}</svg>
          {p.rounds.map((r, i) => (
            <div key={r.name} className="po-head" style={{ left: x(i), width: COL }}>
              <b>{r.name}</b><span>{r.start ? range(r.start, r.end) : ""}{r.legs > 1 ? ` · ${r.legs} legs` : ""}</span>
            </div>
          ))}
          <div className="po-head" style={{ left: x(nCols - 1), width: COL }}><b>Champion</b></div>
          {p.rounds.map((r, i) => r.games.map((g, j) => (
            <div key={`${i}-${j}`} className={`po-match${i === final ? " final" : ""}`} style={{ left: x(i), top: tops[i][j], width: COL, height: BOX }}>
              <Side s={g.a} score={g.a_score} won={g.winner && g.a && g.winner.seed === g.a.seed} legs={g.legs} which="a" />
              <Side s={g.b} score={g.b_score} won={g.winner && g.b && g.winner.seed === g.b.seed} legs={g.legs} which="b" />
            </div>
          )))}
          <div className="po-champ" style={{ left: x(nCols - 1), top: champTop, width: COL, height: BOX }}>
            {p.champion ? <><TeamIcon team={p.champion.team} size={44} /><b>{p.champion.team.name}</b></> : <b>TBD</b>}
          </div>
        </div>
      </div>
    </FantasyShell>
  );
}
