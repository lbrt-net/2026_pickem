import FantasyShell from "../../components/fantasy/FantasyShell";
import { TeamLink } from "../../components/fantasy/links";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { textOnColor } from "../../components/fantasy/teamColors";
import { SEASON, useFantasyApi } from "../../components/fantasy/data";
import "./Playoffs.css";

// Playoffs (GET /results → playoffs, engine._bracket). A real bracket: seeds 1–2 get a Bye card in the first column so
// every later game sits centered between the two things that feed it; elbow connectors join each feeder to the slot it
// fills. A 2-week round is two legs, added up (legs shown under the total). 3rd place sits under the final.
const COL = 236, GAP = 46, ROW = 52, BOX = ROW * 2, BYE = ROW, VGAP = 22, PAIRGAP = 46, HEAD = 64;
const range = (a, b) => {
  const o = { month: "short", day: "numeric" };
  return `${new Date(`${a}T12:00:00`).toLocaleDateString(undefined, o)} – ${new Date(`${b}T12:00:00`).toLocaleDateString(undefined, o)}`;
};

function Row({ s, score, won, lost, legs, which }) {
  if (!s) return <div className="po-row tbd"><span className="po-sb">–</span><span className="po-nm">TBD</span></div>;
  const c = s.team.color;
  return (
    <div className={`po-row${won ? " won" : ""}${lost ? " lost" : ""}`} style={{ "--tc": c }}>
      <span className="po-sb" style={{ background: c, color: textOnColor(c) }}>{s.seed}</span>
      <TeamIcon team={s.team} size={26} />
      <span className="po-nm"><TeamLink ownerId={s.team.owner_user_id} name={s.team.name} />
        {legs && <small>{legs.map(l => `Leg ${l.leg} ${l[which].toFixed(1)}`).join(" · ")}</small>}</span>
      {score != null && <span className="po-sc">{score.toFixed(1)}</span>}
    </div>
  );
}

function Match({ g, style, final }) {
  const aw = g.winner && g.a && g.winner.seed === g.a.seed, bw = g.winner && g.b && g.winner.seed === g.b.seed;
  return (
    <div className={`po-match${final ? " final" : ""}`} style={style}>
      <Row s={g.a} score={g.a_score} won={aw} lost={bw} legs={g.legs} which="a" />
      <Row s={g.b} score={g.b_score} won={bw} lost={aw} legs={g.legs} which="b" />
    </div>
  );
}

export default function Playoffs() {
  const p = useFantasyApi("results")?.playoffs;
  if (!p) return <FantasyShell title="Playoffs" season={SEASON} />;
  const R = p.rounds;
  // first column: games, plus Bye cards for seeds waiting in round 2 — ordered by the round-2 slot each feeds
  const byeRound = R.length > 1 && R[1].games.some(g => g.from.includes(null));
  const col0 = [];
  if (byeRound) {
    R[1].games.forEach((g, gi) => g.from.forEach((f, side) => col0.push(f == null ? { bye: side === 0 ? g.a : g.b, to: [gi, side] } : { game: f, to: [gi, side] })));
  } else {
    R[0].games.forEach((_, j) => col0.push({ game: j }));
  }
  let y = HEAD;
  const pos0 = col0.map((it, k) => {
    const h = it.bye ? BYE : BOX;
    if (k > 0) y += (byeRound && k % 2 === 0) ? PAIRGAP : VGAP;
    const top = y; y += h;
    return { ...it, top, h, c: top + h / 2 };
  });
  const center = {}; // `${round}-${game}` → center y
  pos0.forEach(it => { if (it.game != null) center[`0-${it.game}`] = it.c; });
  const tops = R.map(() => []);
  pos0.forEach(it => { if (it.game != null) tops[0][it.game] = it.top; });
  const feederC = (i, g, side) => {
    if (i === 1 && byeRound) return pos0.find(it => it.to && it.to[0] === R[1].games.indexOf(g) && it.to[1] === side).c;
    return center[`${i - 1}-${g.from[side]}`];
  };
  for (let i = 1; i < R.length; i++) {
    R[i].games.forEach((g, j) => {
      const c = (feederC(i, g, 0) + feederC(i, g, 1)) / 2;
      tops[i][j] = c - BOX / 2;
      center[`${i}-${j}`] = c;
    });
  }
  const fin = R.length - 1;
  const x = i => i * (COL + GAP);
  const nCols = R.length + 1;
  const width = nCols * COL + (nCols - 1) * GAP;
  const bottom = Math.max(y, ...tops.flat().map(t => t + BOX));
  const thirdTop = bottom + 56;
  const height = (p.third ? thirdTop + BOX : bottom) + 12;

  const lines = [];
  const link = (x1, y1, x2, y2, k, hot) => lines.push(<path key={k} className={hot ? "hot" : ""} d={`M${x1},${y1} H${x1 + GAP / 2} V${y2} H${x2}`} />);
  if (byeRound) pos0.forEach((it, k) => link(x(0) + COL, it.c, x(1), tops[1][it.to[0]] + ROW * (it.to[1] + 0.5), `b${k}`, false));
  for (let i = byeRound ? 2 : 1; i < R.length; i++) {
    R[i].games.forEach((g, j) => g.from.forEach((f, side) => link(x(i - 1) + COL, center[`${i - 1}-${f}`], x(i), tops[i][j] + ROW * (side + 0.5), `${i}${j}${side}`, false)));
  }
  lines.push(<path key="champ" className="hot" d={`M${x(fin) + COL},${center[`${fin}-0`]} H${x(fin + 1)}`} />);
  const champ = p.champion?.team;

  return (
    <FantasyShell title="Playoffs" season={SEASON}>
      <div className="po-scroll">
        <div className="po-bracket" style={{ width, height }}>
          <svg className="po-lines" width={width} height={height}>{lines}</svg>
          {R.map((r, i) => (
            <div key={r.name} className="po-head" style={{ left: x(i), width: COL }}>
              <b>{r.name}</b><span>{r.start ? range(r.start, r.end) : ""}{r.legs > 1 ? ` · ${r.legs} legs` : ""}</span>
            </div>
          ))}
          <div className="po-head" style={{ left: x(nCols - 1), width: COL }}><b>Champion</b></div>
          {pos0.filter(it => it.bye).map((it, k) => (
            <div key={`bye${k}`} className="po-match bye" style={{ left: x(0), top: it.top, width: COL, height: BYE }}>
              <Row s={it.bye} /><span className="po-byetag">Bye</span>
            </div>
          ))}
          {R.map((r, i) => r.games.map((g, j) => (
            <Match key={`${i}-${j}`} g={g} final={i === fin} style={{ left: x(i), top: tops[i][j], width: COL, height: BOX }} />
          )))}
          {p.third && (
            <>
              <div className="po-head small" style={{ left: x(fin), top: thirdTop - 30, width: COL }}><b>3rd place</b></div>
              <Match g={p.third} style={{ left: x(fin), top: thirdTop, width: COL, height: BOX }} />
            </>
          )}
          <div className={`po-champ${champ ? "" : " tbd"}`} style={{ left: x(nCols - 1), top: center[`${fin}-0`] - BOX / 2, width: COL, height: BOX,
            ...(champ ? { background: champ.color, color: textOnColor(champ.color) } : {}) }}>
            {champ ? <><TeamIcon team={champ} size={46} /><b>{champ.name}</b></> : <b>TBD</b>}
          </div>
        </div>
      </div>
    </FantasyShell>
  );
}
