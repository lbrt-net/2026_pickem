import TeamIcon from "../../components/fantasy/TeamIcon";
import { PositionBadge } from "../../components/fantasy/RosterBits";
import { NBA_TEAMS } from "../../components/fantasy/nbaTeams";
import { headshotUrl, logoUrl } from "../../components/fantasy/media";
import { textOnColor } from "../../components/fantasy/teamColors";
import { useFantasyApi } from "../../components/fantasy/data";
import "./RecapWeek.css";

// A finished week's report (GET /recap/week/{n}, recap.py) — canvas "Weekly Report" + "optional awards".
// Optional award cards only exist when they qualified; they pack at their natural size (wide 6 / narrow 4 of 12).
const fmt = v => (v ?? 0).toFixed(1);
const signed = v => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(1)}`;
const short = n => { const p = (n || "").split(" "); return p.length < 2 ? n : `${p[0][0]}. ${p.slice(1).join(" ")}`; };
const nbaColor = tri => NBA_TEAMS[tri]?.primary || "var(--surface-3)";
const disp = e => (e.kind === "nba_team" ? (NBA_TEAMS[e.id]?.nickname || e.name) : short(e.name));
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const dayName = iso => DAYS[(new Date(`${iso}T12:00:00`).getDay() + 6) % 7];
const range = (a, b) => {
  const o = { month: "short", day: "numeric" };
  return `${new Date(`${a}T12:00:00`).toLocaleDateString(undefined, o)} – ${new Date(`${b}T12:00:00`).toLocaleDateString(undefined, o)}`;
};

function Face({ e, w = 62, h = 46 }) {
  return e.kind === "nba_team"
    ? <img className="rw-logo" src={logoUrl(e.id)} alt="" style={{ width: h * 0.7, height: h * 0.7 }} />
    : <img className="rw-face" src={headshotUrl(e.id)} alt="" style={{ width: w, height: h }} />;
}

// Players: the best game's three biggest positive parts. NBA teams: what happened, only the parts that scored, most points first.
function Line({ e, labels }) {
  const bd = e.bd || {};
  if (e.kind === "nba_team" && e.facts) {
    const f = e.facts;
    const parts = [
      [(bd.under125 || 0) + (bd.under100 || 0), 0, <>Allowed <b>{f.opp_pts}</b></>],
      [bd.glass || 0, 1, <><b>{f.dreb}</b> DREB vs {f.opp_dreb}</>],
      [bd.paint || 0, 2, <>Allowed <b>{f.paint}</b> PITP</>],
      [bd.fast_break || 0, 3, <>Allowed <b>{f.fb}</b> FB PTS</>],
      [bd.tov15 || 0, 4, <>Forced <b>{f.tov}</b> TOV</>],
      [bd.shot_clock || 0, 5, <>Forced <b>{f.scv}</b> shot clock {f.scv === 1 ? "violation" : "violations"}</>],
    ].filter(p => p[0] > 0).sort((a, b) => b[0] - a[0] || a[1] - b[1]);
    return <div className="rw-ln">{parts.map((p, i) => <span key={i}>{p[2]}</span>)}</div>;
  }
  const top = Object.entries(bd).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]).slice(0, 3);
  return <div className="rw-ln">{top.map(([k, v]) => <span key={k}>{labels[k] || k} <b>+{+v.toFixed(1)}</b></span>)}</div>;
}

function PlayerCard({ e, teams, labels }) {
  const t = e.team_id ? teams[e.team_id] : null;
  return (
    <div className="rw-pc" style={{ "--nc": nbaColor(e.nba_team), "--tc": t?.color || "transparent" }}>
      <div className="rw-pc-top">
        <span className="rw-pos"><PositionBadge entry={{ kind: e.kind, position: e.position }} size={20} /></span>
        {e.kind === "player" && e.nba_team && <img className="rw-mark" src={logoUrl(e.nba_team)} alt="" />}
        <div className="rw-pc-face"><Face e={e} w={140} h={102} /></div>
      </div>
      <div className={`rw-pc-body${t ? "" : " fa"}`}>
        <div className="rw-pc-nm">{disp(e)}</div>
        <div className="rw-pc-sc">{fmt(e.score)}</div>
        <Line e={e} labels={labels} />
        {t && <div className="rw-pc-foot"><TeamIcon team={t} size={20} />{t.name}</div>}
      </div>
    </div>
  );
}

const TROPHY = (
  <svg viewBox="0 0 64 64" className="rw-tro" aria-hidden="true"><path d="M18 8h28v10a14 14 0 0 1-28 0z" fill="currentColor" />
    <path d="M18 12H8v4a10 10 0 0 0 10 10M46 12h10v4a10 10 0 0 1-10 10" fill="none" stroke="currentColor" strokeWidth="4" />
    <path d="M28 32h8v10h-8z M20 46h24v6H20z" fill="currentColor" /></svg>
);

function TeamCard({ label, t, score, faces, line, trophy }) {
  return (
    <div className="rw-tc" style={{ "--tc": t.color, "--ink": textOnColor(t.color) }}>
      <div className="rw-tc-flag"><span className="rw-tc-k">{label}</span><TeamIcon team={t} size={44} /><b>{t.name}</b></div>
      <div className="rw-tc-faces">{(faces || []).map(e => <Face key={e.id} e={e} w={62} h={46} />)}</div>
      <div className="rw-tc-main"><div className="rw-tc-sc">{trophy && TROPHY}<b>{score}</b></div>{line}</div>
    </div>
  );
}

function WinChart({ curve, days, wcol, lcol }) {
  const n = curve.length, W = 420, H = 190;
  const xy = curve.map((p, i) => [i * W / (n - 1), H - p * H]);
  const line = xy.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `0,${H / 2} ${line} ${W},${H / 2}`;
  const lo = curve.slice(0, -1).reduce((m, p, i) => (p < curve[m] ? i : m), 0);
  const labels = [...days.map(dayName), "Final"];
  return (
    <svg viewBox={`0 -6 ${W} ${H + 28}`} className="rw-wp">
      <defs><clipPath id="rw-up"><rect width={W} height={H / 2} /></clipPath><clipPath id="rw-dn"><rect y={H / 2} width={W} height={H / 2} /></clipPath></defs>
      <line x1="0" y1={H / 2} x2={W} y2={H / 2} className="mid" />
      <polygon points={area} fill={wcol} clipPath="url(#rw-up)" /><polygon points={area} fill={lcol} clipPath="url(#rw-dn)" />
      <polyline points={line} fill="none" stroke="#fff" strokeWidth="3" strokeLinejoin="round" />
      <circle cx={xy[lo][0]} cy={xy[lo][1]} r="7" fill="#fff" />
      {labels.map((d, i) => <text key={i} x={i * W / (n - 1)} y={H + 18} textAnchor={i === 0 ? "start" : i === n - 1 ? "end" : "middle"}>{d}</text>)}
    </svg>
  );
}

function Swap({ e, gray, note, small }) {
  return (
    <div className={`rw-sw${small ? " small" : ""}`}>
      <span className={`rw-sf${gray ? " gray" : ""}`} style={{ "--nc": nbaColor(e.nba_team) }}><i /><Face e={e} w={small ? 72 : 96} h={small ? 52 : 70} /></span>
      <b>{disp(e)}</b><span>{note}</span>
    </div>
  );
}

function Awards({ a, teams }) {
  const cards = [];
  if (a.improbable) {
    const x = a.improbable, w = teams[x.winner], l = teams[x.loser];
    cards.push(["wide", (
      <div className="rw-card rw-imp" style={{ "--tc": w.color }} key="imp">
        <div className="rw-tab">Improbable win</div>
        <div className="rw-imp-body">
          <div className="rw-imp-side">
            <div className="rw-imp-who"><TeamIcon team={w} size={36} /><div><b>{w.name}</b><span>over {l.name}</span></div></div>
            <div className="rw-imp-low"><div className="rw-imp-pct">{Math.round(x.low * 100)}<small>%</small></div><div className="rw-k">before {dayName(x.low_date)}</div></div>
          </div>
          <WinChart curve={x.curve} days={x.days} wcol={w.color} lcol={l.color} />
        </div>
      </div>
    )]);
  }
  if (a.buzzer) {
    const x = a.buzzer, w = teams[x.winner], l = teams[x.loser];
    const pair = (s, fin) => (
      <div className={`rw-bb-s${fin ? " fin" : ""}`}><div><TeamIcon team={w} size={16} /><b>{fmt(s[0])}</b></div><div><TeamIcon team={l} size={16} /><b>{fmt(s[1])}</b></div></div>
    );
    cards.push(["narrow", (
      <div className="rw-card rw-bb" style={{ "--tc": w.color }} key="bb">
        <div className="rw-tab">Buzzer Beater</div>
        <div className="rw-bb-who"><TeamIcon team={w} size={34} /><b>{w.name}</b><span>over {l.name}</span></div>
        <div className="rw-bb-flow">
          <div className="rw-bb-col"><span className="rw-k">Saturday</span>{pair(x.sat)}</div>
          <span className="rw-ar">→</span>
          <div className="rw-bb-rs">{x.risers.map(r => <Swap key={r.id} e={r} small note={<>{fmt(r.before)} → <b>{fmt(r.score)}</b></>} />)}</div>
          <span className="rw-ar">→</span>
          <div className="rw-bb-col fin"><span className="rw-k">Final</span>{pair(x.final, true)}</div>
        </div>
      </div>
    )]);
  }
  if (a.bench) {
    const x = a.bench, t = teams[x.team_id];
    cards.push(["narrow", (
      <div className="rw-card rw-razz" style={{ "--tc": t.color }} key="bench">
        <div className="rw-tab">Left on the bench</div>
        <div className="rw-rz-main"><TeamIcon team={t} size={44} /><b className="rw-rz-t">{t.name}</b><b className="rw-rz-n">{fmt(x.points)}</b></div>
        <div className="rw-pair">{x.sat && <Swap e={x.sat} note={`sat · ${fmt(x.sat.score)}`} />}{x.started && <Swap e={x.started} gray note={`started · ${fmt(x.started.score)}`} />}</div>
      </div>
    )]);
  }
  if (a.pickups?.length) {
    const [f, ...rest] = a.pickups, t = teams[f.team_id];
    cards.push(["narrow", (
      <div className="rw-card rw-pick" style={{ "--tc": t.color }} key="pick">
        <div className="rw-tab">Pickup of the week</div>
        <div className="rw-pair">
          <Swap e={f.added} note={fmt(f.added.score)} /><span className="rw-k">for</span><Swap e={f.dropped} gray note={fmt(f.dropped.score)} />
          <div className="rw-gain"><b>+{fmt(f.gain)}</b><TeamIcon team={t} size={22} /><span>{t.name}</span></div>
        </div>
        {rest.map((r, i) => <div key={i} className="rw-pk-row"><TeamIcon team={teams[r.team_id]} size={20} /><b>{teams[r.team_id].name}</b><span>{disp(r.added)} for {disp(r.dropped)}</span><b>+{fmt(r.gain)}</b></div>)}
      </div>
    )]);
  }
  if (!cards.length) return null;
  cards.sort((x, y) => (x[0] === "wide" ? -1 : 0) - (y[0] === "wide" ? -1 : 0));
  return (
    <section className="rw-sec"><h2>Awards</h2>
      <div className="rw-aw-grid">{cards.map(([size, el], i) => <div key={i} style={{ gridColumn: `span ${size === "wide" ? 6 : 4}` }}>{el}</div>)}</div>
    </section>
  );
}

function GbChart({ gb, teams }) {
  const W = 600, H = 290, pl = 40, pt = 30, pb = 34, pr = 100;
  const ids = Object.keys(teams);
  const xs = gb.map((_, i) => pl + (gb.length > 1 ? i * (W - pl - pr) / (gb.length - 1) : (W - pl - pr) / 2));
  const top = Math.max(2, Math.ceil(Math.max(...gb.flatMap(w => ids.map(t => w.gb[t] ?? 0)))) + 1);
  const ys = v => pt + (H - pt - pb) * v / top;
  const major = top > 8 ? 5 : 2;
  const jit = {};
  gb.forEach((w, k) => {
    const groups = {};
    [...ids].sort((a, b) => (w.pf[b] ?? 0) - (w.pf[a] ?? 0)).forEach(t => (groups[w.gb[t]] ||= []).push(t));
    Object.values(groups).forEach(g => g.forEach((t, n) => { jit[`${t}|${k}`] = (n - (g.length - 1) / 2) * 10; }));
  });
  const order = [...ids].sort((a, b) => (gb.at(-1).gb[b] ?? 0) - (gb.at(-1).gb[a] ?? 0));
  const ends = order.map(t => [ys(gb.at(-1).gb[t] ?? 0), t]).sort((a, b) => a[0] - b[0]);
  let last = -99;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="rw-ch">
      <defs><filter id="rw-glow" filterUnits="userSpaceOnUse" x="0" y="0" width={W} height={H}><feGaussianBlur stdDeviation="2.2" result="b" /><feComponentTransfer in="b" result="b"><feFuncA type="linear" slope=".55" /></feComponentTransfer><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>
      <rect x={xs.at(-1) - 22} y={pt - 12} width="44" height={H - pt - pb + 24} rx="6" className="band" />
      {Array.from({ length: top + 1 }, (_, v) => (
        <g key={v}><line x1={pl} x2={xs.at(-1) + 8} y1={ys(v)} y2={ys(v)} className={v % major === 0 ? "gmaj" : "gmin"} />
          {v % major === 0 && <text x={pl - 10} y={ys(v) + 4} textAnchor="end" className="yl">{v}</text>}</g>
      ))}
      <text x={pl - 10} y={pt - 14} textAnchor="end" className="ax">GB</text>
      {order.map(t => {
        const c = teams[t].color;
        const pts = gb.map((w, k) => [xs[k] + (jit[`${t}|${k}`] || 0), ys(w.gb[t] ?? 0)]);
        return (
          <g key={t}>
            <polyline points={pts.map(p => p.join(",")).join(" ")} fill="none" stroke={c} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" filter="url(#rw-glow)" />
            {pts.slice(0, -1).map((p, i) => <circle key={i} cx={p[0]} cy={p[1]} r="5" fill={c} stroke="#0b1220" strokeWidth="2" />)}
            <circle cx={pts.at(-1)[0]} cy={pts.at(-1)[1]} r="8.5" fill={c} stroke="#0b1220" strokeWidth="2.5" />
          </g>
        );
      })}
      {ends.map(([y, t]) => { y = Math.max(y, last + 18); last = y; return <text key={t} x={xs.at(-1) + 18} y={y + 5} className="lab" fill={teams[t].color}>{teams[t].name}</text>; })}
      {gb.map((w, k) => <text key={k} x={xs[k]} y={H - 10} textAnchor="middle" className={k === gb.length - 1 ? "xl on" : "xl"}>W{w.week}</text>)}
    </svg>
  );
}

export default function RecapWeek({ week }) {
  const r = useFantasyApi(`recap/week/${week}`);
  if (!r) return null;
  const T = r.teams;
  const winLine = m => <div className="rw-tc-line">{fmt(r.scores[m.winner])} – {fmt(r.scores[m.loser])} vs <TeamIcon team={T[m.loser]} size={18} />{T[m.loser].name}</div>;
  return (
    <div className="rw">
      <header className="rw-hero"><div className="rw-wm">WEEK {r.week}</div><h2 className="rw-h1">Week {r.week}</h2><span className="rw-dates">{range(r.start, r.end)}</span></header>
      <div className="rw-two">
        <TeamCard label="Best team" t={T[r.best]} score={fmt(r.scores[r.best])} faces={r.faces[r.best]} trophy />
        <TeamCard label="Worst team" t={T[r.worst]} score={fmt(r.scores[r.worst])} faces={r.faces[r.worst]} />
      </div>
      <div className="rw-two">
        <TeamCard label="Biggest win" t={T[r.biggest.winner]} score={`+${fmt(r.biggest.margin)}`} faces={r.faces[r.biggest.winner]} line={winLine(r.biggest)} />
        <TeamCard label="Closest win" t={T[r.closest.winner]} score={`+${fmt(r.closest.margin)}`} faces={r.faces[r.closest.winner]} line={winLine(r.closest)} />
      </div>
      <section className="rw-sec"><h2>Players of the week</h2><div className="rw-pcs">{r.players.map(e => <PlayerCard key={e.id} e={e} teams={T} labels={r.labels} />)}</div></section>
      {r.free_agents.length > 0 && <section className="rw-sec"><h2>Best free agents</h2><div className="rw-pcs">{r.free_agents.map(e => <PlayerCard key={e.id} e={e} teams={T} labels={r.labels} />)}</div></section>}
      {r.versus && (r.versus.short.length > 0 || r.versus.beat.length > 0) && (
        <section className="rw-sec"><h2>Versus projection</h2>
          <div className="rw-two">
            {[["Fell short", r.versus.short, "neg"], ["Beat it", r.versus.beat, "pos"]].map(([title, rows, kind]) => {
              const max = Math.max(1, ...[...r.versus.short, ...r.versus.beat].map(x => Math.abs(x.diff)));
              return (
                <div className="rw-card" key={title}><div className="rw-tab">{title}</div>
                  {rows.map(x => (
                    <div className="rw-vp" key={x.id}>
                      <span className="rw-vf" style={{ "--nc": nbaColor(x.nba_team) }}><i /><Face e={x} w={62} h={46} /></span>
                      <div className="rw-vp-nm"><b>{disp(x)}</b><span><TeamIcon team={T[x.team_id]} size={14} />{T[x.team_id].name} · {x.games} {x.games === 1 ? "game" : "games"}</span></div>
                      <div className="rw-vp-n"><b>{fmt(x.score)}</b><i>{fmt(x.proj)}</i></div>
                      <div className={`rw-vp-bar ${kind}`}><i style={{ width: `${Math.abs(x.diff) / max * 100}%` }} /></div>
                      <em className={kind}>{signed(x.diff)}</em>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </section>
      )}
      <Awards a={r.awards} teams={T} />
      <section className="rw-sec"><h2>Standings</h2>
        <div className="rw-two">
          <div className="rw-card data">
            <table className="rw-st"><colgroup><col style={{ width: 6 }} /><col /><col style={{ width: 90 }} /><col style={{ width: 110 }} /><col style={{ width: 110 }} /></colgroup>
              <thead><tr><th /><th className="l">Team</th><th className="c">W-L</th><th>PF</th><th>PA</th></tr></thead>
              <tbody>{r.standings.map(s => {
                const t = T[s.team_id], mv = s.prev ? s.prev - s.rank : 0;
                return (
                  <tr key={s.team_id} style={{ "--tc": t.color }}><td className="edge" />
                    <td className="l"><span className="rw-st-nm"><b className="rk">{s.rank}</b><TeamIcon team={t} size={30} /><b className="nm">{t.name}</b>
                      {mv > 0 && <span className="mv up">▲{mv}</span>}{mv < 0 && <span className="mv dn">▼{-mv}</span>}</span></td>
                    <td className="c">{s.w}-{s.l}{s.t ? `-${s.t}` : ""}</td><td>{s.pf.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</td>
                    <td>{s.pa.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</td>
                  </tr>
                );
              })}</tbody>
            </table>
          </div>
          <div className="rw-card data"><div className="rw-tab">Games behind</div><GbChart gb={r.gb} teams={T} /></div>
        </div>
      </section>
    </div>
  );
}
