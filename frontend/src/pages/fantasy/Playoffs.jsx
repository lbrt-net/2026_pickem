import { useLayoutEffect, useRef, useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { TeamLink } from "../../components/fantasy/links";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { SEASON, useFantasyApi } from "../../components/fantasy/data";
import "./Playoffs.css";

// Playoffs (GET /results → playoffs, engine._bracket), broadcast-bracket style: every team is its own bar (seed tab,
// team-color logo square, dark name bar, score). A pair of bars joins into the next column's bar; a bye seed waits in
// the second column right under the slot its opponent will fill; the final pair joins into the champion bar.
// A 2-week round is two legs, added up. 3rd place (semifinal losers) sits under the final.
const BAR = 44, GROUP = 26, HEAD = 62, LEGW = 46, NAT = 240;
const range = (a, b) => {
  const o = { month: "short", day: "numeric" };
  return `${new Date(`${a}T12:00:00`).toLocaleDateString(undefined, o)} – ${new Date(`${b}T12:00:00`).toLocaleDateString(undefined, o)}`;
};

function Bar({ s, score, won, lost, legs, nLegs, which, style, big, top, bottom }) {
  return (
    <div className={`po-bar${s ? "" : " empty"}${won ? " won" : ""}${lost ? " lost" : ""}${big ? " big" : ""}${top ? " top" : ""}${bottom ? " bottom" : ""}`}
      style={{ ...style, ...(s ? { "--tc": s.team.color } : {}) }}>
      <span className="po-seed">{s ? s.seed : ""}</span>
      {s && <TeamIcon team={s.team} size={big ? 32 : 24} />}
      <span className="po-name">{s && <TeamLink ownerId={s.team.owner_user_id} name={s.team.name} />}</span>
      {nLegs > 1 && Array.from({ length: nLegs }, (_, i) => <span key={i} className="po-leg">{legs?.[i] ? legs[i][which].toFixed(1) : ""}</span>)}
      <span className="po-sc">{s && score != null ? score.toFixed(1) : ""}</span>
    </div>
  );
}

// Each game is a card of two flush bars. A slot fed by an earlier game sits on top (the waiting seed below it) and
// lines up with that game's card; a game fed twice is centered between its two feeders. No line into the champion.
function cardsOf(p) {
  return p.rounds.map(r => r.games.map(g => {
    const nLegs = r.legs || 1;
    const side = k => {
      const me = k === 0 ? g.a : g.b;
      const won = Boolean(g.winner && me && g.winner.seed === me.seed);
      return { s: me, score: k === 0 ? g.a_score : g.b_score, legs: g.legs, nLegs, which: k === 0 ? "a" : "b", won, lost: Boolean(g.winner && me && !won), from: g.from[k] };
    };
    const a = side(0), b = side(1);
    return a.from == null && b.from != null ? [b, a] : [a, b];  // the fed slot on top
  }));
}

function useWidth() {
  const ref = useRef(null);
  const [w, setW] = useState(1000);
  useLayoutEffect(() => {
    if (!ref.current) return undefined;
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, w];
}

export default function Playoffs() {
  const p = useFantasyApi("results")?.playoffs;
  const [ref, avail] = useWidth();
  if (!p) return <FantasyShell title="Playoffs" season={SEASON}><div ref={ref} /></FantasyShell>;
  const R = p.rounds, cards = cardsOf(p);
  const nCols = R.length;  // no champion column: the final's winner is the champion
  // columns share the width; a multi-leg round gets room for its week columns
  // natural, compact widths; only shrink if the page is narrower than that
  const GAP = 36;
  const extra = R.map(r => (r.legs > 1 ? r.legs * LEGW : 0));
  const base = Math.max(170, Math.min(NAT, (avail - 8 - (nCols - 1) * GAP - extra.reduce((a, b) => a + b, 0)) / R.length));
  const widths = extra.map(e => base + e);
  const x = i => widths.slice(0, i).reduce((a, w) => a + w + GAP, 0);
  const H = 2 * BAR;
  const tops = cards.map(() => []), mid = (i, j) => tops[i][j] + BAR;
  cards[0].forEach((_, j) => { tops[0][j] = HEAD + j * (H + GROUP); });
  const lines = [];
  for (let i = 1; i < cards.length; i++) {
    cards[i].forEach((c, j) => {
      const fed = c.map((sl, k) => [sl.from, k]).filter(([f]) => f != null);
      tops[i][j] = fed.length === 2 ? (mid(i - 1, fed[0][0]) + mid(i - 1, fed[1][0])) / 2 - BAR
        : fed.length === 1 ? mid(i - 1, fed[0][0]) - BAR * (fed[0][1] + 0.5)
        : HEAD + j * (H + GROUP);
      fed.forEach(([f, k]) => {
        const x1 = x(i - 1) + widths[i - 1], y1 = mid(i - 1, f), mx = x1 + GAP / 2, y2 = tops[i][j] + BAR * (k + 0.5);
        lines.push(<path key={`${i}-${j}-${k}`} d={`M${x1},${y1} H${mx} V${y2} H${x(i)}`} />);
      });
    });
  }
  const fin = R.length - 1;
  const bottom = Math.max(...tops.flat()) + H;
  const thirdTop = tops[fin][0] + H + 78;  // right under the championship
  const t = p.third;
  const height = Math.max(bottom, t ? thirdTop + H : 0) + 12;
  const width = x(nCols - 1) + widths[nCols - 1];
  return (
    <FantasyShell title="Playoffs" season={SEASON}>
      <div ref={ref} className="po-scroll">
        <div className="po-bracket" style={{ width, height }}>
          <svg className="po-lines" width={width} height={height}>{lines}</svg>
          {R.map((r, i) => (
            <div key={r.name} className="po-head" style={{ left: x(i), width: widths[i] }}>
              <b>{r.name}</b>{r.start && <span>{range(r.start, r.end)}{r.legs > 1 ? ` · ${r.legs} legs` : ""}</span>}
            </div>
          ))}
          {cards.map((col, i) => col.map((c, j) => c.map((sl, k) => (
            <Bar key={`${i}-${j}-${k}`} s={sl.s} score={sl.score} won={sl.won} lost={sl.lost} legs={sl.legs} nLegs={sl.nLegs} which={sl.which}
              top={k === 0} bottom={k === 1} style={{ left: x(i), top: tops[i][j] + k * BAR, width: widths[i], height: BAR }} />
          ))))}
          {R[fin].legs > 1 && [tops[fin][0], ...(t ? [thirdTop] : [])].map((y0, n) => (
            <div key={`wk${n}`} className="po-weeks" style={{ left: x(fin), top: y0 - 18, width: widths[fin] }}>
              {Array.from({ length: R[fin].legs }, (_, i) => <span key={i}>W{i + 1}</span>)}<span className="tot">Tot</span>
            </div>
          ))}
          {t && (
            <>
              <div className="po-head third" style={{ left: x(fin), top: thirdTop - 34, width: widths[fin] }}><b>3rd place</b></div>
              {[["a", t.a, t.a_score], ["b", t.b, t.b_score]].map(([w, sd, sc], k) => (
                <Bar key={w} s={sd} score={sc} won={Boolean(t.winner && sd && t.winner.seed === sd.seed)} lost={Boolean(t.winner && sd && t.winner.seed !== sd.seed)}
                  legs={t.legs} nLegs={R[fin].legs} which={w} top={k === 0} bottom={k === 1} style={{ left: x(fin), top: thirdTop + k * BAR, width: widths[fin], height: BAR }} />
              ))}
            </>
          )}
        </div>
      </div>
    </FantasyShell>
  );
}
