import { useEffect, useState } from "react";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import StatsNav from "./StatsNav";
import { TeamChip } from "./StatsControls";
import { winRamp, winInk } from "./statsRamp";
import "./Rebounding.css";
import "./Standings.css";
import "./Games.css";

// /stats/nba/games (2026-10-21): each day's games, predicted the night before from what was known then — the same
// player ratings x projected minutes as the standings (nba-pipeline/models/standings.py, "next" on each date): expected
// margin = strength gap x pace + home court, win chance from that margin and one game's spread. Expected score = the
// league's average team score ± half the margin. Scoreboard layout (2026-10-25): two lines per game, one per team,
// every number on its team's line, in large upright centered type. Finished games add the final and the shot-based
// score (models/analytic_score.py: what each team's shots and free throws were worth). Stats never link into fantasy.
const niceDate = d => new Date(`${d}T12:00:00`).toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
const tipTime = iso => (iso ? new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: "America/Chicago" }) : "TBD");
const pct = v => `${Math.round(100 * v)}%`;

// points lines (2026-10-25, commissioner: "predicted number lines in absolute number scale … post-game actual dots and
// expected dots … two number lines, one for each team"): one row per team, one fixed points scale. Before the game: a dot
// at its predicted points. After: a dot at its actual points, a ring at what its shots and free throws were worth, the
// bar between them = shooting luck.
const W = 228, PAD = 12, Y = 15;
// the scale fits the day's slate (2026-10-25, commissioner: "the scale should adjust based on the slate of games and what
// happens that day"): from just below the lowest number that day (predicted, final, by shots) to just above the highest,
// in steps of 5, shared by every game and both lines that day
function dayScale(games) {
  const v = games.flatMap(g => [g.away_pred, g.home_pred, g.away_score, g.home_score, g.away_xp, g.home_xp]).filter(x => x != null);
  const lo = Math.floor((Math.min(...v) - 3) / 5) * 5, hi = Math.ceil((Math.max(...v) + 3) / 5) * 5;
  const step = hi - lo > 50 ? 10 : 5, ticks = []; for (let t = lo; t <= hi; t += step) ticks.push(t);
  return { lo, hi, ticks, x: val => PAD + ((Math.max(lo, Math.min(hi, val)) - lo) / (hi - lo)) * (W - 2 * PAD) };
}
const one = v => (v == null ? "" : v.toFixed(1));
// one points line per team (2026-10-25 review: predicted and final are the same quantity, so one axis — a
// before → after dumbbell): diamond = predicted, ring = what its shots and free throws were worth, dot = final; the bar
// between ring and dot is shooting luck. At most two dots on a line (commissioner): predicted alone; final + by shots.
const W2 = 240, LY = 21;
function TeamLine({ pred, pts, xp, sc, won, mode }) {
  if (mode === "pred") { pts = null; xp = null; } else pred = null;
  const Y = LY;
  const x = v => PAD + ((Math.max(sc.lo, Math.min(sc.hi, v)) - sc.lo) / (sc.hi - sc.lo)) * (W2 - 2 * PAD);
  // the label sits against its own mark (the final, or the predicted before the game): on a side with no other mark
  // within reach, else just above it
  const lx = x(pts != null ? pts : pred), lab = pts != null ? String(pts) : one(pred);
  const others = xp != null ? [x(xp)] : [];
  const toward = pts != null && xp != null ? Math.sign(x(xp) - lx) : 0;      // the luck bar runs that way: never label over it
  const free = d => d !== toward && lx + d * 43 >= 0 && lx + d * 43 <= W2 && !others.some(o => (o - lx) * d > 2 && (o - lx) * d < 46);
  const d = free(1) ? 1 : free(-1) ? -1 : 0;
  const tip = [pred != null && `predicted ${one(pred)}`, pts != null && `final ${pts}`, xp != null && `by shots ${one(xp)}`,
    pts != null && xp != null && `shooting luck ${pts - xp >= 0 ? "+" : "−"}${Math.abs(pts - xp).toFixed(1)}`].filter(Boolean).join(" · ");
  return (
    <svg width={W2} height={34} className="gm-line"><title>{tip}</title>
      {sc.ticks.map(t => <line key={t} x1={x(t)} x2={x(t)} y1={Y - 3} y2={Y + 3} className="tick" />)}
      <line x1={x(sc.lo)} x2={x(sc.hi)} y1={Y} y2={Y} className="axis" />
      {pts != null && xp != null && <line x1={x(xp)} x2={x(pts)} y1={Y} y2={Y} className="luck" />}
      {pred != null && <circle cx={x(pred)} cy={Y} r={5.5} className="dot" />}
      {xp != null && <circle cx={x(xp)} cy={Y} r={5} className="ring" />}
      {pts != null && <circle cx={x(pts)} cy={Y} r={5.5} className="dot" />}
      <text x={d ? lx + d * 9 : lx} y={d ? LY + 4.5 : LY - 9} textAnchor={d > 0 ? "start" : d < 0 ? "end" : "middle"} className={won ? "b" : ""}>{lab}</text>
    </svg>);
}

export default function Games() {
  const [data, setData] = useState(null);
  const [k, setK] = useState(null);
  useEffect(() => {
    fetch(`${API}/nba/stats/standings`, { credentials: "include" }).then(r => r.json())
      .then(d => {
        const days = (d.dates || []).map(x => x.next).filter(x => x && x.games?.length);
        // open on today's games (Central), else the latest day predicted
        const today = new Date().toLocaleDateString("en-CA", { timeZone: "America/Chicago" });
        const ti = days.findIndex(x => x.date === today);
        setData(days); setK(ti >= 0 ? ti : Math.max(0, days.length - 1));
      })
      .catch(() => setData([]));
  }, []);
  const day = data?.[k];
  // every finished game so far: did the favored team win
  const done = (data || []).flatMap(x => x.games).filter(g => g.final && g.home_score != null);
  const called = done.filter(g => (g.p_home >= 0.5) === (g.home_score > g.away_score)).length;
  const anyFinal = day?.games.some(g => g.final);
  const sc = day ? dayScale(day.games) : null;
  return (
    <div className="site-ui stats-ui" style={{ minHeight: "100vh" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1100, boxSizing: "border-box", minWidth: 0 }}>
        <StatsNav />
        <div className="rb-head">
          <h1 className="rb-title">Games</h1>
          <span className="rb-meta">{done.length ? `favorites ${called}-${done.length - called} so far` : "predicted the night before"}</span>
        </div>
        {data && !data.length && <p className="rb-empty">No games predicted yet.</p>}
        {day && <>
          <div className="gm-day">
            <button onClick={() => setK(k - 1)} disabled={k === 0} aria-label="Previous day">‹</button>
            <span>{niceDate(day.date)}</span>
            <button onClick={() => setK(k + 1)} disabled={k === data.length - 1} aria-label="Next day">›</button>
          </div>
          <div className="gm-key">
            {anyFinal && <><span><svg width="14" height="14"><circle cx="7" cy="7" r="5.5" className="dot" /></svg>points</span>
            <span><svg width="14" height="14"><circle cx="7" cy="7" r="5" className="ring" /></svg>by shots (what its shots and free throws were worth) — the bar to the final is shooting luck</span></>}
          </div>
          <div className="gm-card">
            <table className="gm-t">
              <colgroup><col className="c-tip" /><col className="c-team" /><col className="c-win" /><col className="c-line2" />{anyFinal && <col className="c-line2" />}</colgroup>
              <thead><tr>
                <th className="l">Tip (CT)</th><th className="l">Team</th><th>Win</th>
                <th className="g">Predicted points<svg width={W2} height={18} className="gm-scale">{sc.ticks.map((t, k) => (k % 2 === 0 || sc.ticks.length <= 7) && <text key={t} x={PAD + ((t - sc.lo) / (sc.hi - sc.lo)) * (W2 - 2 * PAD)} y={13} textAnchor="middle">{t}</text>)}</svg></th>{anyFinal && <th className="g">Final points · by shots<svg width={W2} height={18} className="gm-scale">{sc.ticks.map((t, k) => (k % 2 === 0 || sc.ticks.length <= 7) && <text key={t} x={PAD + ((t - sc.lo) / (sc.hi - sc.lo)) * (W2 - 2 * PAD)} y={13} textAnchor="middle">{t}</text>)}</svg></th>}
              </tr></thead>
              {day.games.map(g => {
                const sides = [{ team: g.away, p: 1 - g.p_home, pred: g.away_pred, pts: g.away_score, xp: g.away_xp },
                               { team: g.home, p: g.p_home, pred: g.home_pred, pts: g.home_score, xp: g.home_xp }];
                return (
                  <tbody key={g.game_id} className="gm-game">{sides.map((x, i) => {
                    const won = g.final && x.pts != null && x.pts > sides[1 - i].pts;
                    return (
                      <tr key={i}>
                        {i === 0 && <td className="l tip" rowSpan={2}>{tipTime(g.tip)}</td>}
                        <td className={`l team${won ? " won" : ""}`}>{i === 1 && <span className="at">@</span>}<TeamChip team={x.team} /></td>
                        <td className="win" style={{ background: winRamp(x.p), color: winInk(x.p) }}>{pct(x.p)}</td>
                        <td className="g line"><TeamLine mode="pred" pred={x.pred} sc={sc} /></td>
                        {anyFinal && <td className="g line">{g.final && x.pts != null ? <TeamLine mode="post" pts={x.pts} xp={x.xp} sc={sc} won={won} /> : null}</td>}
                      </tr>);
                  })}</tbody>);
              })}
            </table>
          </div>
        </>}
      </div>
    </div>
  );
}
