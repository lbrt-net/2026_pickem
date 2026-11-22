import { useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { NBA_TEAMS } from "../../components/fantasy/nbaTeams";
import FitText from "../../components/fantasy/FitText";
import { Headshot, NbaTeamSquare, PositionBadge } from "../../components/fantasy/RosterBits";
import { textOnColor } from "../../components/fantasy/teamColors";
import { headshotSmall } from "../../components/fantasy/media";
import { SEASON, useFantasyApi } from "../../components/fantasy/data";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { entityShort, initialLast as short, signed } from "../../components/fantasy/format";
import RecapWeek from "./RecapWeek";
import useCurrentUser from "../../hooks/useCurrentUser";
import "./Recap.css";

// Recap (GET /recap, recap.py): Draft Grades once the draft is done; Draft Value is live from Week 1's start (2026-10-30), then a tab
// per finished week. Draft Grades are in fantasy points a week over the best player left at the position.
const SLOT_RANK = { G: 0, F: 1, C: 2, FLEX: 3, TEAM: 4, BENCH: 5, IR: 6 };
const plain = { color: "inherit", textDecoration: "none" };  // linked names look like the rest of the text
const PName = ({ p }) => <EntityLink id={p.id} name={entityShort(p)} style={plain} />;
// recap index cards (whole-card links, so no links inside): full player names, NBA teams by nickname like every row
const fullName = p => (p.kind === "nba_team" ? entityShort(p) : p.name);
const TName = ({ t }) => <TeamLink ownerId={t.owner_user_id} name={t.name} style={plain} />;
const tone = v => (v > 0.05 ? "pos" : v < -0.05 ? "neg" : "");
const pickLabel = (p, n) => `R${Math.ceil(p.pick_no / n)}·${((p.pick_no - 1) % n) + 1}`;
const last = n => (n || "").split(" ").slice(1).join(" ") || n;

function Pos({ p }) {
  return <PositionBadge entry={{ kind: p.kind, position: p.pos }} size={18} />;
}

function Who({ p, teams }) {
  const t = teams[p.team_id];
  return (
    <span className="rc-who"><Pos p={p} /><b><PName p={p} /></b>
      {t && <span className="rc-team"><TeamIcon team={t} size={18} /><TName t={t} /></span>}</span>
  );
}

// One award card: the winner as a row (face · name + fantasy team · the number), one detail line, then #2–3 as
// compact rows. Entries: {face, name, team, num, cls, unit, detail}.
function Award({ title, entries }) {
  if (!entries?.length) return null;
  const [w, ...rest] = entries;
  return (
    <div className="rc-award" style={{ "--nc": w.color || "var(--surface-3)", "--tc": (w.team || w.teamColorOf)?.color || "var(--surface-3)" }}>
      <div className="rc-aw-top"><span className="rc-aw-label">{title}</span>{w.big}</div>
      <div className="rc-aw-win">
        <span className="rc-aw-id"><FitText text={w.name} max={15} min={11}>{w.link}</FitText>{w.team && <span className="rc-aw-team"><TeamIcon team={w.team} size={16} /><span><TName t={w.team} /></span></span>}</span>
      </div>
      <div className={`rc-aw-big ${w.cls || ""}`}>{w.num}<small>{w.unit}</small></div>
      <div className="rc-aw-detail">{w.detail}</div>
      {rest.length > 0 && (
        <div className="rc-awl">
          {rest.map((e, k) => (
            <div key={k} className="rc-awl-row">
              <span className="rc-awl-rk" style={e.team || e.teamColorOf ? { background: (e.team || e.teamColorOf).color, color: textOnColor((e.team || e.teamColorOf).color) } : undefined}>{k + 2}</span>
              <span className="rc-awl-nm"><FitText text={e.name} max={13} min={10}>{e.link}</FitText><span>{e.sub ?? e.detail}</span></span>
              <span className="rc-awl-tm">{e.team && <TeamIcon team={e.team} size={16} />}</span>
              <b className={`rc-awl-v ${e.cls || ""}`}>{e.num}</b>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DraftGrades({ d }) {
  const teams = useMemo(() => Object.fromEntries(d.teams.map(t => [t.id, t])), [d]);
  const picks = useMemo(() => Object.fromEntries(d.picks.map(p => [p.id, p])), [d]);
  const auction = d.type === "auction";
  const nTeams = d.teams.length;
  const maxAdded = Math.max(...d.teams.map(t => t.added), 1);
  const aw = d.awards;

  const face = p => (p.kind === "nba_team" ? <NbaTeamSquare tricode={p.id} size={28} /> : <Headshot playerId={p.id} tricode={p.nba_team} width={44} height={32} />);
  const nameOf = entityShort;
  const nbaColor = p => NBA_TEAMS[p.kind === "nba_team" ? p.id : p.nba_team]?.primary;
  const bigFace = p => (p.kind === "nba_team" ? <span className="rc-aw-logo"><NbaTeamSquare tricode={p.id} size={56} /></span>
    : <Headshot playerId={p.id} tricode={p.nba_team} width={124} height={90} />);
  const playerEntries = (ids, detail, sub) => (ids || []).map(id => picks[id]).filter(Boolean).map(p => (
    { big: bigFace(p), color: nbaColor(p), name: nameOf(p), link: <PName p={p} />, team: teams[p.team_id], num: signed(p.added), cls: tone(p.added), unit: "a week", detail: detail(p), sub: (sub || detail)(p) }));
  const repl = pos => d.replacement[pos]?.name;
  // Biggest overpay is about money: the number is what he cost over his worth (red); his value explains it.
  const overpayEntries = (aw.overpay || []).map(id => picks[id]).filter(Boolean).map(p => (
    { big: bigFace(p), color: nbaColor(p), name: nameOf(p), link: <PName p={p} />, team: teams[p.team_id], num: `−$${p.price - p.worth}`, cls: "neg", unit: "over worth",
      detail: `$${p.price} vs fair $${p.worth} · ${signed(p.added)} a week`, sub: `$${p.price} vs fair $${p.worth}` }));
  const benchEntries = (aw.bench || []).map(b => {
    const t = teams[b.team_id];
    const ps = b.players.map(id => picks[id]).filter(Boolean);
    return { big: <span className="rc-aw-logo"><TeamIcon team={t} size={56} /></span>, color: t.color, name: t.name, link: <TName t={t} />, team: null, teamColorOf: t, num: signed(b.added), cls: tone(b.added), unit: "a week",
      detail: ps.map(p => `${last(p.name)} ${signed(p.added)}`).join(" · "), sub: ps.map(p => last(p.name)).join(" · ") };
  });
  const cheapCap = Math.round((d.budget || 200) * 0.1);

  return (
    <>
      <div className="rc-meta"><b>{auction ? "Auction" : "Snake"}</b><span>Draft grades based off the projected value</span></div>
      <div className="rc-repl">
        <span className="rc-k">Replacement</span>
        {["G", "F", "C", "TEAM"].map(pos => d.replacement[pos] && (
          <span key={pos}><PositionBadge entry={{ kind: pos === "TEAM" ? "nba_team" : "player", position: pos }} size={18} />{d.replacement[pos].name}<b>{d.replacement[pos].proj.toFixed(1)}</b></span>
        ))}
      </div>

      {auction && d.teams.some(t => t.unspent > 0) && (
        <div className="rc-repl">
          <span className="rc-k">Unspent</span>
          {d.teams.filter(t => t.unspent > 0).sort((a, b) => b.unspent - a.unspent).map(t => (
            <span key={t.id}><TeamIcon team={t} size={18} /><TName t={t} /><b className="neg">${t.unspent}</b></span>
          ))}
        </div>
      )}

      <section className="rc-awards">
        {auction ? (
          <>
            <Award title="Best value" entries={playerEntries(aw.best_buy, p => `$${p.price} vs fair $${p.worth}`)} />
            <Award title={`Best value under $${cheapCap}`} entries={playerEntries(aw.best_cheap, p => `$${p.price} vs fair $${p.worth}`, p => `$${p.price}`)} />
            <Award title="Deepest bench" entries={benchEntries} />
            <Award title="Biggest overpay" entries={overpayEntries} />
            <Award title="Worst drafted player" entries={playerEntries(aw.worst, p => `$${p.price} · vs ${short(repl(p.pos))}`, p => `$${p.price}`)} />
          </>
        ) : (
          <>
            <Award title="Best pick" entries={playerEntries(aw.best_pick, p => `${pickLabel(p, nTeams)} · usually ${signed(p.usual)}`)} />
            <Award title="Best late pick" entries={playerEntries(aw.best_late, p => `${pickLabel(p, nTeams)} · usually ${signed(p.usual)}`)} />
            <Award title="Deepest bench" entries={benchEntries} />
            <Award title="Biggest reach" entries={playerEntries(aw.reach, p => `${pickLabel(p, nTeams)} · usually ${signed(p.usual)}`)} />
            <Award title="Worst drafted player" entries={playerEntries(aw.worst, p => `${pickLabel(p, nTeams)} · vs ${short(repl(p.pos))}`, p => pickLabel(p, nTeams))} />
          </>
        )}
      </section>

      <div className="rc-two">
        <section className="rc-panel">
          <div className="rc-strip"><b>Draft Value (Projected)</b></div>
          <table className="rc-table">
            <colgroup><col style={{ width: 6 }} /><col style={{ width: "34%" }} /><col style={{ width: "34%" }} /><col /></colgroup>
            <thead><tr><th /><th className="l">Team</th><th className="l">Added / wk</th><th className="l">Top player</th></tr></thead>
            <tbody>
              {d.teams.map(t => {
                const top = picks[t.top];
                return (
                  <tr key={t.id} style={{ "--tc": t.color }}>
                    <td className="rc-edge" style={{ background: t.color }} />
                    <td className="l"><span className="rc-tn"><TeamIcon team={t} size={26} /><FitText text={t.name} max={16} min={11}><TName t={t} /></FitText></span></td>
                    <td className="l"><div className="rc-barcell"><span className="rc-bar"><i style={{ width: `${Math.max(0, t.added) / maxAdded * 100}%`, background: t.color }} /></span><b>{signed(t.added)}</b></div></td>
                    <td className="l">{top && <span className="rc-top">{face(top)}<b><PName p={top} /></b></span>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
        {auction && <Bargains d={d} teams={teams} />}
      </div>

      {auction && <Timing d={d} teams={teams} />}

      <section className="rc-panel">
        <div className="rc-strip"><b>Rosters</b></div>
        <div className="rc-board" style={{ gridTemplateColumns: `repeat(${Math.min(nTeams, 6)}, minmax(0, 1fr))` }}>{/* at most 6 teams a row (12 = two rows) so names and "vs fair" stay readable */}
          {d.teams.map(t => {
            const mine = d.picks.filter(p => p.team_id === t.id).sort((a, b) => (SLOT_RANK[a.slot] ?? 9) - (SLOT_RANK[b.slot] ?? 9) || (auction ? b.price - a.price : a.pick_no - b.pick_no));
            return (
              <div key={t.id} className="rc-col">
                <div className="rc-col-h" style={{ background: t.color, color: textOnColor(t.color) }}><FitText text={t.name} max={15} min={10}><TName t={t} /></FitText></div>
                {mine.map(p => (
                  <div key={p.id} className={`rc-cell ${{ pos: "good", neg: "bad" }[tone(p.vs)] || ""}`} style={{ "--k": `${Math.round(8 + Math.min(1, Math.abs(p.vs) / 8) * 42)}%` }}>
                    <span className="rc-c1"><Pos p={p} /><span className="rc-cn"><PName p={p} /></span><span className="rc-ct">{auction ? `$${p.price}` : pickLabel(p, nTeams)}</span></span>
                    <b className="rc-c2">{signed(p.added)}</b>
                    <span className="rc-c3">{auction ? `$${p.price} vs fair $${p.worth}` : `usually ${signed(p.usual)}`}</span>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </section>
    </>
  );
}

function Bargains({ d, teams }) {
  // one line per pick: a column header for each half ("Bargains · Added / wk · Paid · Fair · Gain", then "Overpays · …")
  // with the 6 biggest under each; rows a touch shorter so the panel ends level with Draft Value (2026-10-25)
  const rows = d.picks.map(p => ({ ...p, delta: p.worth - p.price }));
  const good = [...rows].sort((a, b) => b.delta - a.delta).filter(r => r.delta > 0).slice(0, 6);
  const bad = [...rows].sort((a, b) => a.delta - b.delta).filter(r => r.delta < 0).slice(0, 6);
  const head = (txt, cls) => (
    <tr key={txt} className={`rc-bo-head ${cls}`}><th /><th className="l">{txt}</th><th>Added / wk</th><th>Paid</th><th>Fair</th><th>{cls === "pos" ? "Gain" : "Loss"}</th></tr>
  );
  return (
    <section className="rc-panel">
      <div className="rc-strip"><b>Bargains &amp; Overpays</b></div>
      <table className="rc-table rc-bo-t">
        <colgroup><col style={{ width: 6 }} /><col /><col style={{ width: 110 }} /><col style={{ width: 76 }} /><col style={{ width: 76 }} /><col style={{ width: 78 }} /></colgroup>
        <tbody>
          {[head("Bargains", "pos"), ...good.map(r => line(r)), head("Overpays", "neg"), ...bad.map(r => line(r))]}
        </tbody>
      </table>
    </section>
  );
  function line(r) {
            const t = teams[r.team_id], pos = r.delta > 0;
            return (
              <tr key={r.id} style={{ "--tc": t?.color }}>
                <td className="rc-edge" style={{ background: t?.color }} />
                <td className="l"><span className="rc-top">{r.kind === "nba_team" ? <NbaTeamSquare tricode={r.id} size={26} /> : <Headshot playerId={r.id} tricode={r.nba_team} width={36} height={26} />}<b><PName p={r} /></b></span></td>
                <td className={tone(r.added)}>{signed(r.added)}</td>
                <td>${r.price}</td>
                <td>${r.worth}</td>
                <td><b className={pos ? "pos" : "neg"}>{pos ? "+" : "−"}${Math.abs(r.delta)}</b></td>
              </tr>
            );
  }
}

// Timing (2026-10-30): when the money went. The sales in four equal stretches (spent vs fair price), each team's
// spending in the first stretch and what it had left for the rest, and "Should have waited": a buy where a later sale
// at the same position, projected at least as good, went for less (the biggest saving per buy). Hindsight on prices,
// projections on value.
const money = v => (v > 0 ? `+$${v}` : v < 0 ? `−$${-v}` : "$0");
function Timing({ d, teams }) {
  const sales = [...d.picks].sort((a, b) => a.pick_no - b.pick_no);
  const size = Math.ceil(sales.length / 4);
  const stretches = [0, 1, 2, 3].map(i => sales.slice(i * size, (i + 1) * size)).filter(s => s.length)
    .map(s => ({ lo: s[0].pick_no, hi: s[s.length - 1].pick_no, spent: s.reduce((a, p) => a + p.price, 0), fair: s.reduce((a, p) => a + p.worth, 0) }));
  const early = new Set(sales.slice(0, size).map(p => p.id));
  const byTeam = d.teams.map(t => {
    const mine = sales.filter(p => p.team_id === t.id);
    const e = mine.filter(p => early.has(p.id)), l = mine.filter(p => !early.has(p.id));
    const sum = (xs, k) => xs.reduce((a, p) => a + p[k], 0);
    return { t, spent: sum(e, "price"), over: sum(e, "price") - sum(e, "worth"), left: (d.budget || 200) - sum(e, "price"), later: sum(l, "price") - sum(l, "worth") };
  }).sort((a, b) => b.left - a.left);
  const waited = sales.map(p => {
    const alt = sales.filter(q => q.pick_no > p.pick_no && q.pos === p.pos && q.added >= p.added && q.price < p.price)
      .sort((a, b) => a.price - b.price)[0];
    return alt && { p, alt, save: p.price - alt.price };
  }).filter(Boolean).sort((a, b) => b.save - a.save).slice(0, 8);
  const who = p => (
    <span className="rc-top">{p.kind === "nba_team" ? <NbaTeamSquare tricode={p.id} size={26} /> : <Headshot playerId={p.id} tricode={p.nba_team} width={36} height={26} />}<b><PName p={p} /></b></span>
  );
  return (
    <>
      <div className="rc-repl">
        <span className="rc-k">Spent · vs fair</span>
        {stretches.map(s => (
          <span key={s.lo}>#{s.lo}–{s.hi}<b>${s.spent}</b><b className={tone(-(s.spent - s.fair))}>{money(s.spent - s.fair)}</b></span>
        ))}
      </div>
      <div className="rc-two">
        <section className="rc-panel">
          <div className="rc-strip"><b>Money left after sale #{size}</b></div>
          <table className="rc-table">
            <colgroup><col style={{ width: 6 }} /><col /><col style={{ width: 84 }} /><col style={{ width: 84 }} /><col style={{ width: 70 }} /><col style={{ width: 84 }} /></colgroup>
            <thead><tr><th /><th className="l">Team</th><th>Spent</th><th>vs fair</th><th>Left</th><th>After</th></tr></thead>
            <tbody>{byTeam.map(r => (
              <tr key={r.t.id}>
                <td className="rc-edge" style={{ background: r.t.color }} />
                <td className="l"><span className="rc-tn"><TeamIcon team={r.t} size={24} /><FitText text={r.t.name} max={16} min={11}><TName t={r.t} /></FitText></span></td>
                <td>${r.spent}</td>
                <td className={tone(-r.over)}>{money(r.over)}</td>
                <td><b>${r.left}</b></td>
                <td className={tone(-r.later)}>{money(r.later)}</td>
              </tr>
            ))}</tbody>
          </table>
        </section>
        <section className="rc-panel">
          <div className="rc-strip"><b>Should have waited</b></div>
          <table className="rc-table">
            <colgroup><col style={{ width: 6 }} /><col /><col style={{ width: 56 }} /><col /><col style={{ width: 56 }} /><col style={{ width: 64 }} /></colgroup>
            <thead><tr><th /><th className="l">Bought</th><th>Paid</th><th className="l">Later, same spot</th><th>Paid</th><th>Saved</th></tr></thead>
            <tbody>{waited.map(({ p, alt, save }) => {
              const t = teams[p.team_id];
              return (
                <tr key={p.id}>
                  <td className="rc-edge" style={{ background: t?.color }} />
                  <td className="l">{who(p)}</td>
                  <td>${p.price}</td>
                  <td className="l">{who(alt)}</td>
                  <td>${alt.price}</td>
                  <td><b className="pos">${save}</b></td>
                </tr>
              );
            })}</tbody>
          </table>
        </section>
      </div>
    </>
  );
}

// Bid vs points (2026-11-10, commissioner): every auction pick, what he went for against his fantasy points this season
// (finished weeks, whoever had him), colored by position. 2026-11-17: two charts (total points; MAX a week), a log bid
// axis (log of 1 + bid, so $0 sits at the left edge), each spot's replacement level dashed with the background below
// shaded, a monotonic B-spline "Going rate" pinned at $1 to the lowest replacement level, circle = above his spot's
// replacement line, X = below.
const POS_FILL = { G: "var(--pos-g)", F: "var(--pos-f)", C: "var(--pos-c)", TEAM: "var(--pos-tm)" };
// jitter (2026-11-17): a fixed few-pixel nudge per pick from its id, so stacked $1 picks separate and stay put on reload
const jit = (id, salt) => { let h = salt; for (const ch of String(id)) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return ((h % 1000) / 1000 - 0.5) * 9; };
// Markers + hover card. Design pass (2026-11-21, commissioner: "less chaotic, equally informative"):
// - one color per marker = his spot (G/F/C/TM); filled = at or above his spot's replacement line, hollow = below
//   (replaced the two-color circles and the loud X's)
// - the drafting manager is in the card; the team filter keeps every other pick as a faint dot for context
// - the card tells the whole pick: who drafted him, bid and order, both point numbers, weeks played, vs his spot's
//   replacement, vs the Going rate, and what bid the Going rate says his points were worth
// Hover state lives here, so a hover redraws only the markers and the card, never the axes or the Going rate fit.
function BidPlot({ W, H, unit, dots, val, fit, worth, repl, children }) {
  const [hot, setHot] = useState(null);
  const warm = useRef(false);
  const h = hot != null ? dots.find(d => d.p.id === hot && !d.ghost) : null;
  const order = [...dots.filter(d => d.ghost), ...dots.filter(d => !d.ghost && d !== h), ...(h ? [h] : [])];
  const sign = v => `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(1)}`;
  const card = h && (() => {
    const p = h.p, played = p.fp_wk ? Math.round(p.fp_tot / p.fp_wk) : 0, r = repl?.[p.pos], w = worth(p[val]);
    return (
      <div className={`rc-tip${h.cx > W * 0.6 ? " left" : ""}${h.cy < H * 0.42 ? " below" : ""}`}
        style={{ left: `${(h.cx / W) * 100}%`, top: `${(h.cy / H) * 100}%` }}>
        {/* picture (2026-11-21): headshot on his NBA team's glow, or the NBA team's square for a TM pick */}
        <div className="rc-tip-top">
          {p.kind === "nba_team"
            ? <span className="rc-tip-pic"><NbaTeamSquare tricode={p.id} size={48} /></span>
            : <span className="rc-tip-pic" style={{ "--nc": NBA_TEAMS[p.nba_team]?.primary || "var(--surface-3)" }}>
                <img src={headshotSmall(p.id)} alt="" width={76} height={56} onError={e => { e.currentTarget.style.visibility = "hidden"; }} />
              </span>}
          <div>
            <div className="rc-tip-h"><i style={{ background: h.above ? h.pc : "none", borderColor: h.pc }} /><b>{p.name}</b></div>
            <div className="rc-tip-sub">{p.pos === "TEAM" ? "TM" : p.pos}{p.kind !== "nba_team" && p.nba_team ? ` · ${p.nba_team}` : ""}</div>
            <div className="rc-tip-by">{h.tm && <TeamIcon team={h.tm} size={18} />}{h.tn || "—"}</div>
          </div>
        </div>
        <dl>
          <dt>Bid</dt><dd>${p.price}{p.pick_no ? <span> · pick {p.pick_no}</span> : null}</dd>
          <dt>Points</dt><dd>{p.fp_tot}<span> · {played} wk{played === 1 ? "" : "s"} played</span></dd>
          <dt>MAX / wk</dt><dd>{p.fp_wk ?? "—"}</dd>
          {r != null && <><dt>vs replacement</dt><dd>{sign(p[val] - r)}</dd></>}
          <dt>vs Going rate</dt><dd>{sign(p[val] - fit(p.price))}</dd>
          <dt>Played like</dt><dd>{w}</dd>
          {p.left_week != null && <><dt>Left</dt><dd>{p.left_week ? `after Wk ${p.left_week}` : "before Wk 1"}</dd></>}
        </dl>
      </div>
    );
  })();
  return (
    <div className="rc-plot" onMouseLeave={() => setHot(null)} onMouseEnter={() => {
      // fetch every pick's small headshot once the mouse comes onto the chart, so the card's picture is there on hover
      if (warm.current) return; warm.current = true;
      dots.forEach(d => { if (d.p.kind !== "nba_team") new Image().src = headshotSmall(d.p.id); });
    }}>
      <svg className="rc-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Draft bid against ${unit}`}>
        {children}
        {order.map(d => {
          const { p, cx, cy, above, pc, ghost } = d, on = d === h;
          if (ghost) return <circle key={p.id} cx={cx} cy={cy} r={3} className="rc-ghost" />;
          return (
            <g key={p.id} className="rc-mk" onMouseEnter={() => setHot(p.id)}>
              {on && <circle cx={cx} cy={cy} r={11} fill="none" stroke="var(--text)" strokeWidth={1.5} />}
              <circle cx={cx} cy={cy} r={above ? 6 : 5} style={above ? { fill: pc, stroke: "var(--bg)", strokeWidth: 1.5 } : { fill: "var(--surface)", stroke: pc, strokeWidth: 2.5 }} />
              <circle cx={cx} cy={cy} r={11} fill="transparent" />
            </g>
          );
        })}
      </svg>
      {card}
    </div>
  );
}
function BidChart({ picks, val, repl = {}, title, unit, teams = [], team, setTeam }) {
  const tcol = Object.fromEntries(teams.map(t => [t.id, t.color])), tname = Object.fromEntries(teams.map(t => [t.id, t.name]));
  const tobj = Object.fromEntries(teams.map(t => [t.id, t]));  // the manager's glyph icon in the hover card
  const pts = picks.filter(p => p[val] != null && p.price != null);
  if (!pts.length) return null;
  const W = 800, H = 340, L = 44, R = 40, T = 12, B = 34;
  const xMax = Math.max(10, Math.ceil(Math.max(...pts.map(p => p.price)) / 10) * 10);
  const top = Math.max(10, ...pts.map(p => p[val]), ...Object.values(repl || {}));
  const yStep = top > 600 ? 200 : top > 300 ? 100 : top > 120 ? 50 : top > 60 ? 20 : 10;
  const yMax = Math.ceil(top / yStep) * yStep;
  const lg = v => Math.log10(1 + v);
  const x = v => L + (lg(v) / lg(xMax)) * (W - L - R), y = v => H - B - (Math.min(Math.max(v, 0), yMax) / yMax) * (H - T - B);
  const yTicks = Array.from({ length: Math.floor(yMax / yStep) + 1 }, (_, i) => i * yStep);
  const xTicks = [0, 1, 2, 5, 10, 20, 50, 100, 200, 500].filter(v => v <= xMax);
  const lv = Object.entries(repl || {}).filter(([k]) => POS_FILL[k]).map(([, v]) => v).sort((a, b) => a - b);
  // Going rate (2026-11-17, commissioner: "monotonic B-spline"): a cubic B-spline on t = log(1 + bid) - log(2), never
  // going down. Clamped knots from $1 to the top bid, 7 evenly spaced interior knots, a penalty on uneven neighbouring steps; the first
  // coefficient is pinned to the lowest spot's replacement level (a $1 pick is worth replacement), each later one is the
  // one before plus a step >= 0 (non-decreasing coefficients = a non-decreasing curve). Steps fitted by non-negative
  // least squares (coordinate descent) on every pick; a $0 pick counts at $1.
  const t0 = lg(1), y0 = lv.length ? lv[0] : 0, tMax = Math.max(1e-6, lg(xMax) - t0);
  const tOf = v => Math.min(tMax, Math.max(0, lg(v) - t0));
  const ts = pts.map(p => tOf(p.price)).filter(v => v > 0 && v < tMax).sort((a, b) => a - b);
  const inner = ts.length > 10 ? [1, 2, 3, 4, 5, 6, 7].map(i => (i * tMax) / 8) : [];  // evenly spaced (P-spline)
  const knots = [0, 0, 0, 0, ...[...new Set(inner)].filter(k => k > 0 && k < tMax), tMax, tMax, tMax, tMax];
  const nB = knots.length - 4;
  const bsp = t => {  // Cox–de Boor, degree 3; the right end belongs to the last span
    let N = knots.slice(0, -1).map((k, i) => ((t >= k && t < knots[i + 1]) || (t >= tMax && k < tMax && knots[i + 1] === tMax) ? 1 : 0));
    if (t >= tMax) { const last = N.lastIndexOf(1); N = N.map((_, i) => (i === last ? 1 : 0)); }
    for (let d = 1; d <= 3; d++) {
      N = N.slice(0, -1).map((_, i) => {
        const l = knots[i + d] - knots[i], r = knots[i + d + 1] - knots[i + 1];
        return (l ? ((t - knots[i]) / l) * N[i] : 0) + (r ? ((knots[i + d + 1] - t) / r) * N[i + 1] : 0);
      });
    }
    return N.slice(0, nB);
  };
  // step i lifts every coefficient from i on, so its feature is the sum of the basis from i on
  const feats = t => { const B = bsp(t), S = Array(nB).fill(0); let acc = 0; for (let j = nB - 1; j >= 1; j--) { acc += B[j]; S[j] = acc; } return S.slice(1); };
  const F = pts.map(p => feats(tOf(p.price))), Y = pts.map(p => p[val] - y0), k = nB - 1;
  const dstep = Array(k).fill(0), res = [...Y], LAM = 2 * pts.length;
  for (let it = 0; it < 400; it++) {
    for (let i = 0; i < k; i++) {
      let num = 0, den = 0;
      for (let n = 0; n < F.length; n++) { num += F[n][i] * (res[n] + F[n][i] * dstep[i]); den += F[n][i] ** 2; }
      // roughness penalty on neighbouring steps: no flat-then-jump stairs (2026-11-17)
      if (i > 0) { num += LAM * dstep[i - 1]; den += LAM; }
      if (i < k - 1) { num += LAM * dstep[i + 1]; den += LAM; }
      const nd = den ? Math.max(0, num / den) : 0, ch = nd - dstep[i];
      if (ch) { for (let n = 0; n < F.length; n++) res[n] -= F[n][i] * ch; dstep[i] = nd; }
    }
  }
  const fit = v => y0 + feats(tOf(v)).reduce((s, f, i) => s + f * dstep[i], 0);
  const curve = Array.from({ length: 81 }, (_, i) => Math.pow(1 + xMax, lg(1) / lg(xMax) + (i / 80) * (1 - lg(1) / lg(xMax))) - 1)
    .map(v => `${x(v).toFixed(1)},${y(fit(v)).toFixed(1)}`).join(" ");
  const above = p => repl?.[p.pos] == null || p[val] >= repl[p.pos];
  // replacement labels at the right edge, top to bottom, at least 12px apart
  const rlab = Object.entries(repl || {}).filter(([k]) => POS_FILL[k]).map(([k, v]) => ({ k, v, ly: y(v) })).sort((a, b) => a.ly - b.ly);
  rlab.forEach((r, i) => { if (i && r.ly - rlab[i - 1].ly < 12) r.ly = rlab[i - 1].ly + 12; });
  // the bid the Going rate says these points were worth (it never goes down, so halve the bid range)
  const worth = v => {
    if (v <= fit(1)) return "a $1 pick or less";
    if (v >= fit(xMax)) return `more than $${xMax}`;
    let lo = 1, hi = xMax;
    for (let i = 0; i < 30; i++) { const m = (lo + hi) / 2; if (fit(m) < v) lo = m; else hi = m; }
    return `a $${Math.round(hi)} pick`;
  };
  return (
    <section className="rc-panel">
      <div className="rc-strip"><b>{title}</b>
        <select className="tx-team rc-bid-team" value={team} onChange={e => setTeam(e.target.value)} aria-label="Fantasy team">
          <option value="">All teams</option>
          {teams.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        {/* legend (2026-11-21): color = spot; filled = above his spot's replacement line, hollow = below */}
        <span className="rc-legend">
          {[["G", "G"], ["F", "F"], ["C", "C"], ["TEAM", "TM"]].map(([k, l]) => <span key={k}><i style={{ background: POS_FILL[k] }} />{l}</span>)}
          <span className="rc-lg-gap"><svg width="12" height="12" viewBox="0 0 12 12"><circle cx="6" cy="6" r="5" fill="var(--text)" /></svg>Above replacement</span>
          <span><svg width="12" height="12" viewBox="0 0 12 12"><circle cx="6" cy="6" r="4.2" fill="none" stroke="var(--text)" strokeWidth="2" /></svg>Below</span>
        </span>
      </div>
      <BidPlot W={W} H={H} unit={unit} val={val} fit={fit} worth={worth} repl={repl} dots={pts.map(p => ({
        p, cx: x(p.price) + jit(p.id, 7), cy: y(p[val]) + jit(p.id, 13), above: above(p), ghost: !!team && String(p.team_id) !== String(team),
        pc: POS_FILL[p.pos] || "var(--text)", tc: tcol[p.team_id] || "var(--text)", tn: tname[p.team_id], tm: tobj[p.team_id] }))}>
        {/* replacement (2026-11-21): one dark zone below every spot's level; each spot's level a thin line, named at the
            right edge (labels nudged apart when two levels sit close) */}
        {lv.length > 0 && <rect x={L} width={W - L - R} y={y(lv[0])} height={H - B - y(lv[0])} fill="var(--bg)" opacity={0.55} />}
        {rlab.map(({ k, v, ly }) => (
          <g key={`r${k}`}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke={POS_FILL[k]} strokeDasharray="2 4" strokeWidth={1.25} opacity={0.8} />
            <line x1={W - R + 4} x2={W - R + 12} y1={ly} y2={ly} stroke={POS_FILL[k]} strokeWidth={3} />
            <text x={W - R + 15} y={ly + 4}>{k === "TEAM" ? "TM" : k}</text>
          </g>
        ))}
        {yTicks.map(v => (
          <g key={`y${v}`}><line x1={L} x2={W - R} y1={y(v)} y2={y(v)} className="rc-grid" /><text x={L - 6} y={y(v) + 4} textAnchor="end">{v}</text></g>
        ))}
        {xTicks.map(v => <text key={`x${v}`} x={x(v)} y={H - B + 18} textAnchor="middle">${v}</text>)}
        <text x={W - R} y={H - 2} textAnchor="end">Bid</text>
        <text x={L + 4} y={T} dominantBaseline="hanging">{unit}</text>
        <polyline points={curve} fill="none" stroke="var(--text)" strokeWidth={2} opacity={0.8} />
        <text x={x(xMax) - 4} y={y(fit(xMax)) - 8} textAnchor="end">Going rate</text>
      </BidPlot>
    </section>
  );
}

// Draft Value (after Week 1): each pick's actual points added a week (while he was the drafting team's) next to the
// draft-day projection; color = actual − projected. A dropped pick counts only through the week he left.
function DraftValue({ v }) {
  const teams = Object.fromEntries(v.teams.map(t => [t.id, t]));
  const picks = Object.fromEntries(v.picks.map(p => [p.id, p]));
  const max = Math.max(1, ...v.teams.map(t => Math.abs(t.actual)));
  const nTeams = v.teams.length;
  const auction = v.type === "auction";
  const [bidTeam, setBidTeam] = useState("");  // one team filter for both bid charts
  // Biggest regrets (2026-10-31): dropped picks, ranked and shown by points a week above the draft's replacement player
  // at his spot since he left (the number shown is the number ranked)
  const regrets = (v.regrets || (v.regret ? [v.regret] : [])).filter(r => picks[r.id]);
  const face = p => (p.kind === "nba_team" ? <NbaTeamSquare tricode={p.id} size={28} /> : <Headshot playerId={p.id} tricode={p.nba_team} width={44} height={32} />);
  const leftText = r => (r.left_week ? `after Wk ${r.left_week}` : "before Wk 1");
  return (
    <>
      <div className="rc-meta"><span>Drafting value based on the actual results of the 2026-27 NBA season</span></div>
      <div className="rc-two">
        <section className="rc-panel">
          <div className="rc-strip"><b>Draft Value</b></div>
          <table className="rc-table">
            <colgroup><col style={{ width: 6 }} /><col style={{ width: "34%" }} /><col style={{ width: "36%" }} /><col /></colgroup>
            <thead><tr><th /><th className="l">Team</th><th className="l">Added / wk</th><th>Projected</th></tr></thead>
            <tbody>{v.teams.map(t => (
              <tr key={t.id}>
                <td className="rc-edge" style={{ background: t.color }} />
                <td className="l"><span className="rc-tn"><TeamIcon team={t} size={24} /><FitText text={t.name} max={18} min={11}><TName t={t} /></FitText></span></td>
                <td className="l"><div className="rc-barcell"><span className="rc-bar"><i style={{ width: `${Math.max(0, t.actual) / max * 100}%`, background: t.color }} /></span><b className={tone(t.actual)}>{signed(t.actual)}</b></div></td>
                <td><i>{signed(t.added)}</i></td>
              </tr>
            ))}</tbody>
          </table>
        </section>
        {regrets.length > 0 && (
          <section className="rc-panel">
            <div className="rc-strip"><b>Biggest regrets</b></div>
            <table className="rc-table rc-regrets">
              <colgroup><col style={{ width: 6 }} /><col /><col style={{ width: "20%" }} /><col style={{ width: "22%" }} /></colgroup>
              <thead><tr><th /><th className="l">Dropped pick</th><th className="l">Dropped</th><th>Pts above repl. / wk</th></tr></thead>
              <tbody>{regrets.map(r => {
                const p = picks[r.id], t = teams[r.team_id];
                return (
                  <tr key={r.id}>
                    <td className="rc-edge" style={{ background: t?.color }} />
                    <td className="l"><span className="rc-rg-who">{face(p)}<span className="rc-rg-n"><b><PName p={p} /></b>{t && <span className="rc-team"><TeamIcon team={t} size={16} /><TName t={t} /></span>}</span></span></td>
                    <td className="l">{leftText(r)}</td>
                    <td><b className={tone(r.added_wk)}>{signed(r.added_wk)}</b></td>
                  </tr>
                );
              })}</tbody>
            </table>
          </section>
        )}
      </div>
      {auction && <BidChart picks={v.picks} val="fp_tot" repl={v.repl_tot} title="Bid vs points" unit="Fantasy pts" teams={v.teams} team={bidTeam} setTeam={setBidTeam} />}
      {auction && <BidChart picks={v.picks} val="fp_wk" repl={v.repl_wk} title="Bid vs MAX a week" unit="MAX / wk" teams={v.teams} team={bidTeam} setTeam={setBidTeam} />}
      <section className="rc-panel">
        <div className="rc-strip"><b>Rosters</b></div>
        <div className="rc-board" style={{ gridTemplateColumns: `repeat(${Math.min(nTeams, 6)}, minmax(0, 1fr))` }}>{/* at most 6 teams a row (12 = two rows) so names and "vs fair" stay readable */}
          {v.teams.map(t => {
            const mine = v.picks.filter(p => p.team_id === t.id).sort((a, b) => (SLOT_RANK[a.slot] ?? 9) - (SLOT_RANK[b.slot] ?? 9) || (auction ? (b.price || 0) - (a.price || 0) : a.pick_no - b.pick_no));
            return (
              <div key={t.id} className="rc-col">
                <div className="rc-col-h" style={{ background: t.color, color: textOnColor(t.color) }}><FitText text={t.name} max={15} min={10}><TName t={t} /></FitText></div>
                {mine.map(p => {
                  const d = p.actual == null ? 0 : p.actual - p.added;
                  return (
                    <div key={p.id} className={`rc-cell ${{ pos: "good", neg: "bad" }[tone(d)] || ""}`} style={{ "--k": `${Math.round(8 + Math.min(1, Math.abs(d) / 8) * 42)}%` }}>
                      <span className="rc-c1"><Pos p={p} /><span className="rc-cn"><PName p={p} /></span><span className="rc-ct">{auction ? `$${p.price}` : pickLabel(p, nTeams)}</span></span>
                      <b className="rc-c2">{p.actual == null ? "—" : signed(p.actual)}</b>
                      <span className="rc-c3"><i>{signed(p.added)}</i>{p.left_week != null ? ` · dropped Wk ${p.left_week}` : ""}</span>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </section>
    </>
  );
}

// The recap index (2026-10-17): a grid of recap cards — Draft Grades first (headline awards), Draft Value (live from Week 1's start)
// is over, then each finished week, latest first. Each recap links back here.
function RecapIndex({ data, admin }) {
  const d = data.draft;
  const teams = d ? Object.fromEntries(d.teams.map(t => [t.id, t])) : {};
  const picks = d ? Object.fromEntries(d.picks.map(p => [p.id, p])) : {};
  const one = ids => (ids || []).map(id => picks[id]).find(Boolean);
  const best = d && one(d.awards?.best_buy), over = d && one(d.awards?.overpay);
  const top = d ? [...d.teams].sort((x, y) => y.added - x.added)[0] : null;
  const face = p => (p.kind === "nba_team" ? <NbaTeamSquare tricode={p.id} size={40} /> : <Headshot playerId={p.id} tricode={p.nba_team} width={60} height={44} />);
  const weeks = [...(data.weeks || [])].reverse();
  const row = (label, color, who, num) => (
    <div className="rx-row" style={{ "--tc": color }}><span className="rx-row-l">{label}</span><span className="rx-row-who">{who}</span><b className="rx-row-n">{num}</b></div>
  );
  // two groups (2026-11-14): the season's big reports (draft, mid-season, end of season) apart from the weekly recaps
  return (
    <>
    <h2 className="rx-group">Season reports</h2>
    <div className="rx">
      {d && (
        <Link to="?tab=draft" className="rx-card">
          {/* titles only, no small line above (2026-10-30) */}
          <div className="rx-card-h"><b className="rx-title">Draft Grades (Projected)</b></div>
          <div className="rx-rows">
            {top && row("Best draft", top.color, <><TeamIcon team={top} size={28} /><span>{top.name}</span></>, `${signed(top.added)} / wk`)}
            {best && row("Best value", teams[best.team_id]?.color, <>{face(best)}<span>{fullName(best)}</span></>, `$${best.price} · fair $${best.worth}`)}
            {over && row("Biggest overpay", teams[over.team_id]?.color, <>{face(over)}<span>{fullName(over)}</span></>, `$${over.price} · fair $${over.worth}`)}
          </div>
          <span className="rx-go">Read the report →</span>
        </Link>
      )}
      {data.value && (
        <Link to="?tab=value" className="rx-card">
          <div className="rx-card-h"><b className="rx-title">Draft Value (Live)</b></div>
          {(() => {  // the same three rows as Draft Grades (2026-10-25): best draft so far, best pick so far, worst pick so far
            const v = data.value, vt = Object.fromEntries(v.teams.map(t => [t.id, t]));
            const real = v.picks.filter(p => p.actual != null);
            const bestP = [...real].sort((a, b) => b.actual - a.actual)[0], worstP = [...real].sort((a, b) => a.actual - b.actual)[0];
            const lead = v.teams[0];
            return (
              <div className="rx-rows">
                {lead && row("Best draft", lead.color, <><TeamIcon team={lead} size={28} /><span>{lead.name}</span></>, `${signed(lead.actual)} / wk`)}
                {bestP && row("Best pick", vt[bestP.team_id]?.color, <>{face(bestP)}<span>{fullName(bestP)}</span></>, `${signed(bestP.actual)} / wk`)}
                {worstP && row("Worst pick", vt[worstP.team_id]?.color, <>{face(worstP)}<span>{fullName(worstP)}</span></>, `${signed(worstP.actual)} / wk`)}
              </div>
            );
          })()}
          <span className="rx-go">Read the report →</span>
        </Link>
      )}
      {admin && (
        <Link to="?tab=midseason" className="rx-card">
          <div className="rx-card-h"><b className="rx-title">Mid-Season Report</b></div>
          <p className="rx-blurb">Only you can see this for now. The season so far, updated nightly.</p>
          <span className="rx-go">Read the report →</span>
        </Link>
      )}
    </div>
    <h2 className="rx-group">Weekly recaps</h2>
    <div className="rx">
      {data.preview && (
        <Link to={`?tab=p${data.preview.week}`} className="rx-card">
          <div className="rx-card-h"><b className="rx-title">{data.preview.label || `Week ${data.preview.week}`} (Preview)</b></div>
          <p className="rx-blurb">Only you can see this until the week ends. Scores as they stand now.</p>
          <span className="rx-go">Read the recap →</span>
          <span className="rx-wk" aria-hidden="true">{data.preview.week}</span>
        </Link>
      )}
      {weeks.map(w => (
        <Link key={w.week} to={`?tab=w${w.week}`} className="rx-card">
          <div className="rx-card-h"><b className="rx-title">{w.label || `Week ${w.week}`}</b></div>
          {w.best ? (
            <div className="rx-rows">
              {row("Best team", w.best.team.color, <><TeamIcon team={w.best.team} size={28} /><span>{w.best.team.name}</span></>, w.best.score.toFixed(1))}
              {row("Worst team", w.worst.team.color, <><TeamIcon team={w.worst.team} size={28} /><span>{w.worst.team.name}</span></>, w.worst.score.toFixed(1))}
              {w.star && row("Player of the week", w.star.team?.color, <>{face(w.star)}<span>{fullName(w.star)}</span></>, w.star.score.toFixed(1))}
            </div>
          ) : <p className="rx-blurb">Scores, awards and the week's story.</p>}
          <span className="rx-go">Read the recap →</span>
          <span className="rx-wk" aria-hidden="true">{w.week}</span>
        </Link>
      ))}
      {weeks.length === 0 && !data.preview && <p className="rx-empty">Weekly recaps start here when Week 1 ends.</p>}
    </div>
    </>
  );
}

// The Mid-Season Report (admin only; the server page /reports/midseason) shown inside Recaps, sized to its content
function MidSeason() {
  const fit = e => {
    const f = e.currentTarget, doc = f.contentDocument;
    if (!doc?.body) return;
    const size = () => { f.style.height = `${doc.documentElement.scrollHeight}px`; };
    size(); f.style.opacity = 1;  // shown once loaded and sized, not as an empty box first
    new ResizeObserver(size).observe(doc.body);
  };
  return <iframe className="rc-midseason" src="/reports/midseason" title="Mid-Season Report" onLoad={fit} style={{ opacity: 0 }} />;
}

export default function Recap() {
  const data = useFantasyApi("recap");
  const me = useCurrentUser(), admin = !!me?.isAdmin;
  // the commissioner's preview of the week under way (from Saturday noon Central; recap.preview_week): tab p{week}
  const pv = data?.preview;
  const tabs = [data?.draft && ["draft", "Draft Grades"], data?.value && ["value", "Draft Value"], ...(data?.weeks || []).map(w => [`w${w.week}`, `Week ${w.week}`]),
    pv && [`p${pv.week}`, `Week ${pv.week} (Preview)`], admin && ["midseason", "Mid-Season Report"]].filter(Boolean);
  const [params] = useSearchParams();
  const tab = params.get("tab");
  const on = tab && tabs.some(t => t[0] === tab) ? tab : null;
  const label = on ? tabs.find(t => t[0] === on)[1] : null;
  // No recap picked: the index of every recap (2026-10-17). A recap: "← All recaps" back to it.
  return (
    <FantasyShell title={label ? `Recap · ${label}` : "Recaps"} season={SEASON}>
      {/* wait for who you are too: the Mid-Season Report tab is admin-only, so picking a tab before /me answers
          flashed the recap index (or a card list missing the report) first */}
      {data === undefined || me === undefined ? null : !tabs.length ? <p className="rc-empty">The recap starts once the draft is done.</p>
        : !on ? <RecapIndex data={data} admin={admin} />
        : (
          <>
            <Link className="rc-back" to="?">← All recaps</Link>
            {on === "midseason" ? <MidSeason />
              : on === "draft" ? <DraftGrades d={data.draft} />
              : on === "value" ? <DraftValue v={data.value} />
                : <RecapWeek week={Number(on.slice(1))} preview={on[0] === "p"} />}
          </>
        )}
    </FantasyShell>
  );
}
