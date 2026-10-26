import TeamIcon from "../../components/fantasy/TeamIcon";
import { PositionBadge } from "../../components/fantasy/RosterBits";
import { NBA_TEAMS } from "../../components/fantasy/nbaTeams";
import { headshotUrl, logoUrl } from "../../components/fantasy/media";
import { textOnColor } from "../../components/fantasy/teamColors";
import { useFantasyApi } from "../../components/fantasy/data";
import "./RecapWeek.css";

// A finished week's report (GET /recap/week/{n}, recap.py) — canvas "Weekly Report" + "optional awards".
// Optional award cards only exist when they qualified; every award card is half width (2026-10-25).
const fmt = v => (v ?? 0).toFixed(1);
const signed = v => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(1)}`;
const short = n => { const p = (n || "").split(" "); return p.length < 2 ? n : `${p[0][0]}. ${p.slice(1).join(" ")}`; };
const nbaColor = tri => NBA_TEAMS[tri]?.primary || "var(--surface-3)";
const nbaSecond = tri => NBA_TEAMS[tri]?.secondary || "var(--border)";
// behind a face: the NBA team's primary for a player; for an NBA team (its logo, drawn in its primary) a dark plate
const faceBg = e => (e?.kind === "nba_team" ? "var(--surface-3)" : nbaColor(e?.nba_team));
const disp = e => (e.kind === "nba_team" ? (NBA_TEAMS[e.id]?.nickname || e.name) : short(e.name));
const abbr = t => t?.abbreviation || (t?.name || "").slice(0, 4);
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const dayName = iso => DAYS[(new Date(`${iso}T12:00:00`).getDay() + 6) % 7];
const range = (a, b) => {
  const o = { month: "short", day: "numeric" };
  return `${new Date(`${a}T12:00:00`).toLocaleDateString(undefined, o)} – ${new Date(`${b}T12:00:00`).toLocaleDateString(undefined, o)}`;
};

function Face({ e, w = 62, h = 46 }) {
  return e.kind === "nba_team"
    ? <img className="rw-logo" src={logoUrl(e.id)} alt="" style={{ width: h * 0.7, height: h * 0.7 }} />
    // full-size photos everywhere: the live page is what the server photographs (at 2×) for the recap picture
    : <img className="rw-face" src={headshotUrl(e.id)} alt="" width={w} height={h} style={{ width: w, height: h }} />;
}

// Players: the best game's three biggest positive parts. NBA teams: what happened, the 3 parts that scored most.
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
    ].filter(p => p[0] > 0).sort((a, b) => b[0] - a[0] || a[1] - b[1]).slice(0, 3);
    return <div className="rw-ln">{parts.map((p, i) => <span key={i}>{p[2]}</span>)}</div>;
  }
  const top = Object.entries(bd).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]).slice(0, 3);
  return <div className="rw-ln">{top.map(([k, v]) => <span key={k}>{labels[k] || k} <b>+{+v.toFixed(1)}</b></span>)}</div>;
}

// Player cards: top = the NBA team (its color, the slant edged in its secondary color); bottom band = the fantasy team.
function PlayerCard({ e, teams, labels }) {
  const t = e.team_id ? teams[e.team_id] : null;
  return (
    <div className="rw-pc" style={{ "--nc": nbaColor(e.nba_team), "--tc": t?.color || "transparent" }}>
      <div className="rw-pc-edge" style={{ "--ns": nbaSecond(e.nba_team) }}>
        <div className="rw-pc-top">
          <span className="rw-pos"><PositionBadge entry={{ kind: e.kind, position: e.position }} size={20} /></span>
          {e.kind === "player" && e.nba_team && <img className="rw-mark" src={logoUrl(e.nba_team)} alt="" />}
          <div className="rw-pc-face"><Face e={e} w={140} h={102} /></div>
        </div>
      </div>
      <div className={`rw-pc-body${t ? "" : " fa"}`}>
        <div className="rw-pc-nm">{disp(e)}</div>
        <div className="rw-pc-sc">{fmt(e.score)}</div>
        <Line e={e} labels={labels} />
        {t && <div className="rw-pc-foot" style={{ "--ink": textOnColor(t.color) }}><TeamIcon team={t} size={22} />{t.name}</div>}
      </div>
    </div>
  );
}

// Team cards (2026-10-25): flag = label, icon, acronym big, full name small; a big faded emoji behind; the score + result
// at the top right; the starters on plates in their NBA team's color, names above (hyphenated → initials, long ones
// smaller), the NBA team as its logo + tricode.
const EMOJI = { "Best team": "🏆", "Worst team": "💩", "Biggest win": "💥", "Closest win": "🥶" };
const SUFFIX = new Set(["Jr.", "Sr.", "II", "III", "IV"]);
const faceName = n => {
  const parts = (n || "").split(" ").filter(w => !SUFFIX.has(w));
  let last = parts.at(-1) || "";
  if (last.includes("-")) last = parts[0][0] + last.split("-").map(w => w[0]).join("");  // SGA, NAW, KCP…
  return last;
};
function TcFace({ e }) {
  if (e.kind === "nba_team") {
    return <span className="tcf logo" style={{ "--nc": nbaColor(e.id) }}><img src={logoUrl(e.id)} alt="" /><em>{e.id}</em></span>;
  }
  const n = faceName(e.name);
  return (
    <span className="tcf" style={{ "--nc": nbaColor(e.nba_team) }}>
      <img src={headshotUrl(e.id)} alt="" />
      <em style={{ fontSize: n.length <= 10 ? 12 : n.length <= 12 ? 10.5 : 9.5 }}>{n}</em>
    </span>
  );
}
function TeamCard({ label, t, score, faces, line }) {
  return (
    <div className="rw-tc v-a" style={{ "--tc": t.color, "--ink": textOnColor(t.color) }}>
      <div className="rw-tc-flag"><span className="rw-tc-k">{label}</span><TeamIcon team={t} size={44} />
        <span className="rw-tc-id"><b>{abbr(t)}</b><small>{t.name}</small></span></div>
      <span className="tc-emoji" aria-hidden="true">{EMOJI[label]}</span>
      <div className="rw-tc-body">
        <div className="rw-tc-main"><div className="rw-tc-sc"><b>{score}</b></div>{line}</div>
        <div className="rw-tc-faces">{(faces || []).map(e => <TcFace key={e.id} e={e} />)}</div>
      </div>
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
      <span className={`rw-sf${gray ? " gray" : ""}`} style={{ "--nc": faceBg(e) }}><i /><Face e={e} w={small ? 72 : 96} h={small ? 52 : 70} /></span>
      <b>{disp(e)}</b><span>{note}</span>
    </div>
  );
}

const SWAP_IC = <svg className="sx-ic" viewBox="0 0 24 24" aria-label="should have swapped"><path d="M4 8h14l-4-4M20 16H6l4 4" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" /></svg>;
const IN_IC = <svg className="sx-ic" viewBox="0 0 24 24" aria-label="replaced"><path d="M20 12H5m6-6-6 6 6 6" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" /></svg>;
const CHEV = <svg className="bb-chev" viewBox="0 0 24 40" aria-hidden="true"><path d="M2 2 L20 20 L2 38 L10 20 Z" fill="currentColor" /></svg>;

function Awards({ a, teams }) {
  const cards = [];
  if (a.improbable) {
    const x = a.improbable, w = teams[x.winner], l = teams[x.loser];
    cards.push(
      <div className="rw-card rw-imp" style={{ "--tc": w.color }} key="imp">
        <div className="rw-tab">Improbable win</div>
        <div className="rw-imp-body">
          <div className="rw-imp-side">
            <div className="rw-imp-who"><TeamIcon team={w} size={36} /><div><b>{w.name}</b><span className="ovr">over <TeamIcon team={l} size={18} />{l.name}</span></div></div>
            <div className="rw-imp-low"><div className="rw-imp-pct">{Math.round(x.low * 100)}<small>%</small></div><div className="rw-k">before {dayName(x.low_date)}</div></div>
          </div>
          <WinChart curve={x.curve} days={x.days} wcol={w.color} lcol={l.color} />
        </div>
      </div>,
    );
  }
  if (a.buzzer) {
    const x = a.buzzer, w = teams[x.winner], l = teams[x.loser];
    const tile = (k, s, fin) => (
      <div className={`bb-tile${fin ? " fin" : ""}`}><span className="rw-k">{k}</span>
        <div className="bb-row"><TeamIcon team={w} size={30} /><b>{fmt(s[0])}</b></div>
        <div className="bb-row"><TeamIcon team={l} size={30} /><b>{fmt(s[1])}</b></div></div>
    );
    cards.push(
      <div className="rw-card rw-bb" style={{ "--tc": w.color }} key="bb">
        <div className="rw-tab">Buzzer Beater</div>
        <div className="bb-vs"><span className="bb-t"><TeamIcon team={w} size={44} /><b>{w.name}</b></span><span className="bb-over">over</span>
          <span className="bb-t"><TeamIcon team={l} size={44} /><b>{l.name}</b></span></div>
        <div className="bb-flow">{tile("Saturday", x.sat)}{CHEV}
          <div className="bb-rs">{x.risers.map(r => <Swap key={r.id} e={r} note={<>{fmt(r.before)} → <b>{fmt(r.score)}</b></>} />)}</div>
          {CHEV}{tile("Final", x.final, true)}</div>
      </div>,
    );
  }
  // Left on the bench + Pickup of the week: one layout. Grey = gone from the roster (to IR / dropped, marked on the face);
  // a starter's points in orange; lost points red; a pickup who started green, one who sat plain.
  const swapRows = (rows, kind) => rows.map((q, i) => {
    const t = teams[q.team_id];
    let L, R, lw, rw, gray, num, cls, mark = "";
    if (kind === "bench") {
      [L, R, lw, rw, gray, num, cls] = [q.sat, q.started, "bench", "started", false, `−${fmt(q.points)}`, "neg"];
    } else {
      const g = q.gain ?? q.added.score;
      [L, R, lw, rw, gray, num] = [q.added, q.dropped, q.started ? "started" : "bench", q.dropped?.ir ? "to IR" : "dropped", true, signed(g)];
      cls = q.started ? "pos" : "idle";
      mark = q.dropped?.ir ? "ir" : "drop";
    }
    const side = (e, w, g) => (
      <div className={`sx-p${g ? " gray" : ""}`}>
        {e ? <span className="sx-f" style={{ "--nc": faceBg(e) }}><Face e={e} w={72} h={53} />
          {g && mark === "ir" && <i className="sx-m ir">IR</i>}{g && mark === "drop" && <i className="sx-m drop">−</i>}</span>
          : <span className="sx-f empty" />}
        <div className="sx-t"><b>{e ? disp(e) : "—"}</b><span><b className={w === "started" ? "ct" : ""}>{e ? fmt(e.score) : ""}</b> · {w}</span></div>
      </div>
    );
    return (
      <div key={i} className="sx-row" style={{ "--tc": t.color }}>
        <div className="sx-team" style={{ "--ink": textOnColor(t.color) }}><TeamIcon team={t} size={30} /><b>{abbr(t)}</b></div>
        {side(L, lw, false)}{kind === "bench" ? SWAP_IC : IN_IC}{side(R, rw, gray)}
        <div className="sx-r"><b className={`sx-n ${cls}`}>{num}</b></div>
      </div>
    );
  });
  const benchRows = a.bench_top || (a.bench ? [a.bench] : []);
  if (benchRows.length) {
    cards.push(<div className="rw-card sx" style={{ "--tc": teams[benchRows[0].team_id].color }} key="bench"><div className="rw-tab">Left on the bench</div>{swapRows(benchRows, "bench")}</div>);
  }
  if (a.pickups?.length) {
    cards.push(<div className="rw-card sx" style={{ "--tc": teams[a.pickups[0].team_id].color }} key="pick"><div className="rw-tab">Pickup of the week</div>{swapRows(a.pickups, "pick")}</div>);
  }
  if (!cards.length) return null;
  return <section className="rw-sec"><h2>Awards</h2><div className="rw-aw-grid">{cards.map((el, i) => <div key={i} className="rw-aw">{el}</div>)}</div></section>;
}

// Games behind as a graph (2026-10-25): every team starts level at Start and its line runs week by week to where it
// stands now, ending at its icon + acronym; teams level on games behind fan out so every line and icon shows.
function GbChart({ gb: weeks, teams, standings }) {
  const ids = Object.keys(teams);
  const gb = [{ week: 0, gb: Object.fromEntries(ids.map(t => [t, 0])) }, ...weeks];
  const W = 600, H = 760, pl = 44, pr = 150, pt = 34, pb = 40, n = gb.length;
  const xs = gb.map((_, i) => pl + i * (W - pl - pr) / (n - 1));
  const top = Math.max(1, Math.ceil(Math.max(...gb.flatMap(w => ids.map(t => w.gb[t] ?? 0)))));
  const unit = (H - pt - pb) / (top + 0.6);
  const ys = v => pt + unit * 0.3 + unit * v;
  const rank = Object.fromEntries((standings || []).map(s => [s.team_id, s.rank]));
  const off = {};
  gb.forEach((w, k) => {
    const groups = {};
    [...ids].sort((a, b) => (rank[a] ?? 99) - (rank[b] ?? 99)).forEach(t => (groups[w.gb[t] ?? 0] ||= []).push(t));
    Object.values(groups).forEach(g => {
      const span = k === 0 ? 0 : k === n - 1 ? Math.min(unit * 0.78, 34 * (g.length - 1)) : Math.min(unit * 0.5, 12 * (g.length - 1));
      g.forEach((t, j) => { off[`${t}|${k}`] = g.length > 1 ? (j / (g.length - 1) - 0.5) * span : 0; });
    });
  });
  const order = [...ids].sort((a, b) => (rank[b] ?? 99) - (rank[a] ?? 99));  // best drawn last (on top)
  const pt_ = (t, k) => [xs[k], ys(gb[k].gb[t] ?? 0) + (off[`${t}|${k}`] || 0)];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="rw-ch gb2">
      <defs>{ids.map((t, i) => <clipPath key={t} id={`rw-ci-${i}`}><circle r="15" /></clipPath>)}</defs>
      <rect x={xs.at(-1) - 26} y={pt - 14} width="52" height={H - pt - pb + 22} rx="8" className="band" />
      {Array.from({ length: top + 1 }, (_, v) => (
        <g key={v}><line x1={pl} x2={W - 12} y1={ys(v)} y2={ys(v)} className="gmaj" />
          <text x={pl - 12} y={ys(v) + 4} textAnchor="end" className="yl">{v}</text></g>
      ))}
      <text x={pl - 12} y={pt - 16} textAnchor="end" className="ax">GB</text>
      {gb.map((w, k) => <text key={k} x={xs[k]} y={H - 12} textAnchor="middle" className={k === n - 1 ? "xl on" : "xl"}>{w.week === 0 ? "Start" : `W${w.week}`}</text>)}
      {order.map(t => {
        const p = gb.map((_, k) => pt_(t, k));
        const d = `M${p[0][0]},${p[0][1]}` + p.slice(1).map((q, i) => { const m = (p[i][0] + q[0]) / 2; return ` C${m},${p[i][1]} ${m},${q[1]} ${q[0]},${q[1]}`; }).join("");
        return (
          <g key={t}><path d={d} fill="none" stroke={teams[t].color} strokeWidth="3" strokeLinecap="round" opacity=".9" />
            {p.slice(1, -1).map((q, i) => <circle key={i} cx={q[0]} cy={q[1]} r="4" fill={teams[t].color} />)}</g>
        );
      })}
      <circle cx={xs[0]} cy={ys(0)} r="7" fill="var(--text)" />
      {order.map(t => {
        const [x, y] = pt_(t, n - 1), tm = teams[t], i = ids.indexOf(t);
        return (
          <g key={t}>
            <g transform={`translate(${x},${y})`}><circle r="18" fill={tm.color} />
              {tm.logo_url ? <image href={tm.logo_url} x="-15" y="-15" width="30" height="30" clipPath={`url(#rw-ci-${i})`} preserveAspectRatio="xMidYMid slice" />
                : <text y="4" textAnchor="middle" className="lab" style={{ fontSize: 10 }}>{abbr(tm).slice(0, 3)}</text>}</g>
            <text x={x + 26} y={y + 5} className="gb2-lab" fill={tm.color}>{abbr(tm)}</text>
          </g>
        );
      })}
    </svg>
  );
}

// Versus projection: Mon → Sun, each game's points (his best in orange); a day his NBA team played without him = OUT.
function WeekStrip({ x, start }) {
  if (!x.days) return <>{x.games} {x.games === 1 ? "game" : "games"}</>;
  const d0 = new Date(`${start}T12:00:00`);
  const best = Math.max(...Object.values(x.days));
  const team = new Set(x.team_days || []);
  return (
    <span className="wstrip" style={{ "--nc": nbaColor(x.nba_team) }}>
      {DAYS.map((dn, i) => {
        const d = new Date(d0); d.setDate(d.getDate() + i);
        const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
        const on = iso in x.days, out = !on && team.has(iso);
        return (
          <span key={dn} className="wd"><small>{dn[0]}</small>
            <i className={`ws${on ? " on" : ""}${on && x.days[iso] === best ? " best" : ""}${out ? " out" : ""}`}>{on ? fmt(x.days[iso]) : out ? "OUT" : ""}</i></span>
        );
      })}
    </span>
  );
}
const ordinal = p => `${p}${p % 100 >= 11 && p % 100 <= 13 ? "th" : { 1: "st", 2: "nd", 3: "rd" }[p % 10] || "th"}`;

export default function RecapWeek({ week }) {
  const r = useFantasyApi(`recap/week/${week}`);
  if (!r) return null;
  const T = r.teams;
  const winLine = m => <div className="rw-tc-line">{fmt(r.scores[m.winner])} – {fmt(r.scores[m.loser])} vs <TeamIcon team={T[m.loser]} size={18} />{abbr(T[m.loser])}</div>;
  return (
    <div className="rw">
      <header className="rw-hero"><div className="rw-wm">WEEK {r.week}</div><h2 className="rw-h1">Week {r.week}</h2><span className="rw-dates">{range(r.start, r.end)}</span></header>
      <div className="rw-two">
        <TeamCard label="Best team" t={T[r.best]} score={fmt(r.scores[r.best])} faces={r.faces[r.best]} />
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
              return (
                <div className="rw-card" key={title}><div className="rw-tab">{title}</div>
                  {rows.map(x => (
                    <div className="rw-vp" key={x.id} style={{ "--tc": T[x.team_id].color }}>
                      <div className="vp-team" style={{ "--ink": textOnColor(T[x.team_id].color) }}><TeamIcon team={T[x.team_id]} size={26} /><b>{abbr(T[x.team_id])}</b></div>
                      <span className="rw-vf" style={{ "--nc": faceBg(x) }}><i /><Face e={x} w={62} h={46} /></span>
                      <div className="rw-vp-nm"><b>{disp(x)}</b><WeekStrip x={x} start={r.start} /></div>
                      <div className="rw-vp-n"><b>{fmt(x.score)}</b><i>{fmt(x.proj)}</i></div>
                      <div className="vp-end"><em className={kind}>{signed(x.diff)}</em>
                        {x.pctile != null && <span className="vp-pct">{ordinal(Math.min(99, Math.max(1, x.pctile))).replace(/\D+$/, "")}<sup>{ordinal(Math.min(99, Math.max(1, x.pctile))).replace(/^\d+/, "")}</sup> pctile</span>}</div>
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
            <table className="rw-st"><colgroup><col style={{ width: 6 }} /><col /><col style={{ width: 62 }} /><col style={{ width: 78 }} /><col style={{ width: 78 }} /></colgroup>
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
          <div className="rw-card data"><div className="rw-tab">Games behind</div><GbChart gb={r.gb} teams={T} standings={r.standings} /></div>
        </div>
      </section>
    </div>
  );
}
