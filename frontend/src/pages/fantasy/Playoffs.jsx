import FantasyShell from "../../components/fantasy/FantasyShell";
import { TeamLink } from "../../components/fantasy/links";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { SEASON, useFantasyApi } from "../../components/fantasy/data";
import "./Playoffs.css";

// Playoffs (GET /results → playoffs, engine._bracket), broadcast-bracket style: every team is its own bar (seed tab,
// team-color logo square, dark name bar, score). A pair of bars joins into the next column's bar; a bye seed waits in
// the second column right under the slot its opponent will fill; the final pair joins into the champion bar.
// A 2-week round is two legs, added up. 3rd place (semifinal losers) sits under the final.
const COL = 232, GAP = 52, BAR = 42, IN = 10, GROUP = 34, HEAD = 58;
const range = (a, b) => {
  const o = { month: "short", day: "numeric" };
  return `${new Date(`${a}T12:00:00`).toLocaleDateString(undefined, o)} – ${new Date(`${b}T12:00:00`).toLocaleDateString(undefined, o)}`;
};

function Bar({ s, score, won, legs, which, style, big }) {
  return (
    <div className={`po-bar${s ? "" : " empty"}${won ? " won" : ""}${big ? " big" : ""}`} style={style}>
      <span className="po-seed">{s ? s.seed : ""}</span>
      {s && <span className="po-logo" style={{ background: s.team.color }}><TeamIcon team={s.team} size={big ? 34 : 26} /></span>}
      <span className="po-name">{s && <TeamLink ownerId={s.team.owner_user_id} name={s.team.name} />}
        {legs && s && <small>{legs.map(l => `L${l.leg} ${l[which].toFixed(1)}`).join(" · ")}</small>}</span>
      {s && score != null && <span className="po-sc">{score.toFixed(1)}</span>}
    </div>
  );
}

// Columns of slots, in order; `into` = the slot index in the next column that a pair (2k, 2k+1) feeds.
function columns(p) {
  const R = p.rounds, slot = (g, side) => ({ s: side === 0 ? g.a : g.b, score: side === 0 ? g.a_score : g.b_score, legs: g.legs, which: side === 0 ? "a" : "b",
    won: g.winner && (side === 0 ? g.a : g.b) && g.winner.seed === (side === 0 ? g.a : g.b).seed });
  const cols = [];
  R.forEach((r, i) => {
    const col = [];
    r.games.forEach(g => {
      const fed = g.from.findIndex(f => f != null), seedSide = g.from.findIndex(f => f == null);
      if (i > 0 && fed >= 0 && seedSide >= 0) col.push({ ...slot(g, fed), fedBy: g.from[fed] }, { ...slot(g, seedSide), bye: true });  // winner slot, then the waiting seed
      else col.push(slot(g, 0), slot(g, 1));
    });
    cols.push({ name: r.name, start: r.start, end: r.end, legs: r.legs, slots: col });
  });
  cols.push({ name: "Champion", slots: [{ s: p.champion, champ: true }] });
  return cols;
}

export default function Playoffs() {
  const p = useFantasyApi("results")?.playoffs;
  if (!p) return <FantasyShell title="Playoffs" season={SEASON} />;
  const cols = columns(p);
  const ys = cols.map(() => []);
  // first column: pairs of bars, groups spaced apart
  cols[0].slots.forEach((_, k) => { ys[0][k] = HEAD + Math.floor(k / 2) * (2 * BAR + IN + GROUP) + (k % 2) * (BAR + IN); });
  const lines = [];
  const x = i => i * (COL + GAP);
  for (let i = 1; i < cols.length; i++) {
    const col = cols[i].slots;
    let feedPair = 0;
    col.forEach((sl, k) => {
      if (sl.bye) { ys[i][k] = ys[i][k - 1] + BAR + IN; return; }              // the waiting seed: right under the slot above
      const a = ys[i - 1][2 * feedPair], b = ys[i - 1][2 * feedPair + 1];
      ys[i][k] = (a + b) / 2;                                                   // centered on the pair that feeds it
      const x1 = x(i - 1) + COL, mx = x1 + GAP / 2, x2 = x(i);
      lines.push(<path key={`${i}-${k}`} className={i === cols.length - 1 ? "hot" : ""}
        d={`M${x1},${a + BAR / 2} H${mx} M${x1},${b + BAR / 2} H${mx} M${mx},${a + BAR / 2} V${b + BAR / 2} M${mx},${ys[i][k] + BAR / 2} H${x2}`} />);
      feedPair++;
    });
  }
  const nCols = cols.length;
  const width = nCols * COL + (nCols - 1) * GAP;
  const bottom = Math.max(...ys.flat()) + BAR;
  const fin = nCols - 2;
  const thirdTop = bottom + 60;
  const height = (p.third ? thirdTop + 2 * BAR + IN : bottom) + 12;
  const t = p.third;
  return (
    <FantasyShell title="Playoffs" season={SEASON}>
      <div className="po-scroll">
        <div className="po-bracket" style={{ width, height }}>
          <svg className="po-lines" width={width} height={height}>{lines}</svg>
          {cols.map((c, i) => (
            <div key={c.name} className="po-head" style={{ left: x(i), width: COL }}>
              <b>{c.name}</b>{c.start && <span>{range(c.start, c.end)}{c.legs > 1 ? ` · ${c.legs} legs` : ""}</span>}
            </div>
          ))}
          {cols.map((c, i) => c.slots.map((sl, k) => (
            <Bar key={`${i}-${k}`} s={sl.s} score={sl.score} won={sl.won} legs={sl.legs} which={sl.which} big={sl.champ}
              style={{ left: x(i), top: ys[i][k] - (sl.champ ? 8 : 0), width: COL, height: BAR + (sl.champ ? 16 : 0) }} />
          )))}
          {t && (
            <>
              <div className="po-head third" style={{ left: x(fin), top: thirdTop - 30, width: COL }}><b>3rd place</b></div>
              <Bar s={t.a} score={t.a_score} won={t.winner && t.a && t.winner.seed === t.a.seed} legs={t.legs} which="a" style={{ left: x(fin), top: thirdTop, width: COL, height: BAR }} />
              <Bar s={t.b} score={t.b_score} won={t.winner && t.b && t.winner.seed === t.b.seed} legs={t.legs} which="b" style={{ left: x(fin), top: thirdTop + BAR + IN, width: COL, height: BAR }} />
            </>
          )}
        </div>
      </div>
    </FantasyShell>
  );
}
