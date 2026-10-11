import { useMemo, useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { PositionBadge } from "../../components/fantasy/RosterBits";
import { textOnColor } from "../../components/fantasy/teamColors";
import { SEASON, useFantasyApi } from "../../components/fantasy/data";
import "./Recap.css";

// Recap (GET /recap, recap.py): Draft Grades once the draft is done; Draft Value appears once Week 1 is over, then a tab
// per finished week. Draft Grades are in fantasy points a week over the best player left at the position.
const SLOT_RANK = { G: 0, F: 1, C: 2, FLEX: 3, TEAM: 4, BENCH: 5, IR: 6 };
const short = n => { const p = (n || "").split(" "); return p.length < 2 ? n : `${p[0][0]}. ${p.slice(1).join(" ")}`; };
const signed = v => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(1)}`;
const money = v => `${v < 0 ? "−" : ""}$${Math.abs(v)}`;
const tone = v => (v > 0.05 ? "pos" : v < -0.05 ? "neg" : "");
const pickLabel = (p, n) => `R${Math.ceil(p.pick_no / n)}·${((p.pick_no - 1) % n) + 1}`;

function Pos({ p }) {
  return <PositionBadge entry={{ kind: p.kind, position: p.pos }} size={18} />;
}

function Who({ p, teams }) {
  const t = teams[p.team_id];
  return (
    <span className="rc-who"><Pos p={p} /><b>{p.kind === "nba_team" ? p.name : short(p.name)}</b>
      {t && <span className="rc-team"><TeamIcon team={t} size={18} />{t.name}</span>}</span>
  );
}

function Award({ title, items, render }) {
  if (!items?.length) return null;
  const [first, ...rest] = items;
  return (
    <div className="rc-award">
      <span className="rc-tab">{title}</span>
      {render(first, true)}
      {rest.length > 0 && <div className="rc-aw-rest">{rest.map((x, i) => <div key={i} className="rc-aw-row"><span className="rc-rk">{i + 2}</span>{render(x, false)}</div>)}</div>}
    </div>
  );
}

function DraftGrades({ d }) {
  const teams = useMemo(() => Object.fromEntries(d.teams.map(t => [t.id, t])), [d]);
  const picks = useMemo(() => Object.fromEntries(d.picks.map(p => [p.id, p])), [d]);
  const auction = d.type === "auction";
  const nTeams = d.teams.length;
  const [one, two, three] = d.teams;
  const maxAdded = Math.max(...d.teams.map(t => t.added), 1);
  const aw = d.awards;

  const playerAward = (key, line) => (id, big) => {
    const p = picks[id];
    if (!p) return null;
    return big ? (
      <div className="rc-aw-main"><Who p={p} teams={teams} /><div className={`rc-aw-num ${tone(p.added)}`}>{signed(p.added)}<small>a week</small></div><div className="rc-aw-foot">{line(p)}</div></div>
    ) : (
      <div className="rc-aw-mini"><Who p={p} teams={teams} /><b className={tone(p.added)}>{signed(p.added)}</b><span>{line(p)}</span></div>
    );
  };
  const benchAward = (b, big) => {
    const t = teams[b.team_id];
    const names = b.players.map(id => picks[id]).filter(Boolean);
    return big ? (
      <div className="rc-aw-main"><span className="rc-who"><TeamIcon team={t} size={22} /><b>{t.name}</b></span><div className={`rc-aw-num ${tone(b.added)}`}>{signed(b.added)}<small>a week</small></div>
        <div className="rc-aw-list">{names.map(p => <span key={p.id}><Pos p={p} />{short(p.name)} <b className={tone(p.added)}>{signed(p.added)}</b></span>)}</div></div>
    ) : (
      <div className="rc-aw-mini"><span className="rc-who"><TeamIcon team={t} size={18} /><b>{t.name}</b></span><b className={tone(b.added)}>{signed(b.added)}</b><span>{names.map(p => short(p.name)).join(" · ")}</span></div>
    );
  };
  const repl = pos => d.replacement[pos]?.name;
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

      <section className="rc-hero">
        {one && (
          <div className="rc-champ" style={{ "--tc": one.color, "--ink": textOnColor(one.color) }}>
            <span className="rc-bigrank">1</span>
            <span className="rc-champ-nm"><TeamIcon team={one} size={44} /><b>{one.name}</b></span>
            <span className="rc-champ-sc"><b>{signed(one.added)}</b><small>a week</small></span>
          </div>
        )}
        <div className="rc-podium">
          {[two, three].filter(Boolean).map((t, i) => (
            <div key={t.id} className="rc-bug"><span className="rc-bug-rk" style={{ background: t.color, color: textOnColor(t.color) }}>{i + 2}</span>
              <span className="rc-bug-nm"><TeamIcon team={t} size={26} /><b>{t.name}</b></span><span className="rc-bug-sc">{signed(t.added)}</span></div>
          ))}
        </div>
      </section>

      <section className="rc-awards">
        {auction ? (
          <>
            <Award title="Best buy" items={aw.best_buy} render={playerAward("best_buy", p => `paid $${p.price} · worth $${p.worth}`)} />
            <Award title={`Best buy under $${cheapCap}`} items={aw.best_cheap} render={playerAward("best_cheap", p => `paid $${p.price}`)} />
            <Award title="Deepest bench" items={aw.bench} render={benchAward} />
            <Award title="Biggest overpay" items={aw.overpay} render={playerAward("overpay", p => `paid $${p.price} · $${p.price} usually gets ${signed(p.usual)}`)} />
            <Award title="Worst drafted player" items={aw.worst} render={playerAward("worst", p => `$${p.price} · vs ${repl(p.pos)}`)} />
          </>
        ) : (
          <>
            <Award title="Best pick" items={aw.best_pick} render={playerAward("best_pick", p => `${pickLabel(p, nTeams)} usually gets ${signed(p.usual)}`)} />
            <Award title="Best late pick" items={aw.best_late} render={playerAward("best_late", p => `${pickLabel(p, nTeams)} usually gets ${signed(p.usual)}`)} />
            <Award title="Deepest bench" items={aw.bench} render={benchAward} />
            <Award title="Biggest reach" items={aw.reach} render={playerAward("reach", p => `${pickLabel(p, nTeams)} usually gets ${signed(p.usual)}`)} />
            <Award title="Worst drafted player" items={aw.worst} render={playerAward("worst", p => `${pickLabel(p, nTeams)} · vs ${repl(p.pos)}`)} />
          </>
        )}
      </section>

      <div className="rc-two">
        <section className="rc-panel">
          <div className="rc-strip"><b>Draft Value (Projected)</b></div>
          <table className="rc-table">
            <colgroup><col style={{ width: 6 }} /><col style={{ width: "30%" }} /><col style={{ width: "32%" }} />{auction && <col style={{ width: 72 }} />}<col /></colgroup>
            <thead><tr><th /><th className="l">Team</th><th className="l">Added / wk</th>{auction && <th>Unspent</th>}<th className="l">Top player</th></tr></thead>
            <tbody>
              {d.teams.map(t => {
                const top = picks[t.top];
                return (
                  <tr key={t.id}>
                    <td className="rc-edge" style={{ background: t.color }} />
                    <td className="l"><span className="rc-tn"><TeamIcon team={t} size={24} /><b>{t.name}</b></span></td>
                    <td className="l"><div className="rc-barcell"><span className="rc-bar"><i style={{ width: `${Math.max(0, t.added) / maxAdded * 100}%`, background: t.color }} /></span><b>{signed(t.added)}</b></div></td>
                    {auction && <td className={t.unspent > 0 ? "neg" : ""}>{t.unspent > 0 ? money(-t.unspent) : ""}</td>}
                    <td className="l">{top && <span className="rc-who"><Pos p={top} />{top.kind === "nba_team" ? top.name : short(top.name)}</span>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
        {auction && <Bargains d={d} teams={teams} />}
      </div>

      <section className="rc-panel">
        <div className="rc-strip"><b>Rosters</b></div>
        <div className="rc-board" style={{ gridTemplateColumns: `repeat(${nTeams}, minmax(0, 1fr))` }}>
          {d.teams.map(t => {
            const mine = d.picks.filter(p => p.team_id === t.id).sort((a, b) => (SLOT_RANK[a.slot] ?? 9) - (SLOT_RANK[b.slot] ?? 9) || (auction ? b.price - a.price : a.pick_no - b.pick_no));
            return (
              <div key={t.id} className="rc-col">
                <div className="rc-col-h" style={{ background: t.color, color: textOnColor(t.color) }}>{t.name}</div>
                {mine.map(p => (
                  <div key={p.id} className={`rc-cell ${{ pos: "good", neg: "bad" }[tone(p.vs)] || ""}`}>
                    <span className="rc-c1"><Pos p={p} /><span className="rc-cn">{p.kind === "nba_team" ? p.name : short(p.name)}</span><span className="rc-ct">{auction ? `$${p.price}` : pickLabel(p, nTeams)}</span></span>
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
  const rows = d.picks.map(p => ({ ...p, delta: p.worth - p.price }));
  const good = [...rows].sort((a, b) => b.delta - a.delta).filter(r => r.delta > 0).slice(0, 6);
  const bad = [...rows].sort((a, b) => a.delta - b.delta).filter(r => r.delta < 0).slice(0, 6);
  const max = Math.max(1, ...rows.map(r => Math.abs(r.delta)));
  const line = (r, kind) => (
    <div key={r.id} className="rc-bo-row">
      <TeamIcon team={teams[r.team_id]} size={18} /><span className="rc-cn">{r.kind === "nba_team" ? r.name : short(r.name)}</span>
      <span className={tone(r.added)}>{signed(r.added)}</span>
      <span className={`rc-bo-bar ${kind}`}><i style={{ width: `${Math.abs(r.delta) / max * 100}%` }} /></span>
      <b className={kind}>{kind === "pos" ? "+" : "−"}${Math.abs(r.delta)}</b>
    </div>
  );
  return (
    <section className="rc-panel">
      <div className="rc-strip"><b>Bargains &amp; Overpays</b></div>
      <div className="rc-bo">
        <div><div className="rc-k pos">Bargains</div>{good.map(r => line(r, "pos"))}</div>
        <div><div className="rc-k neg">Overpays</div>{bad.map(r => line(r, "neg"))}</div>
      </div>
    </section>
  );
}

export default function Recap() {
  const data = useFantasyApi("recap");
  const tabs = [data?.draft && ["draft", "Draft Grades"], data?.value && ["value", "Draft Value"], ...(data?.weeks || []).map(w => [`w${w.week}`, `Week ${w.week}`])].filter(Boolean);
  const [tab, setTab] = useState(null);
  const on = tab && tabs.some(t => t[0] === tab) ? tab : tabs[0]?.[0];
  return (
    <FantasyShell title="Recap" season={SEASON}>
      {tabs.length > 1 && (
        <nav className="rc-tabs" aria-label="Recaps">{tabs.map(([k, label]) => <button key={k} type="button" className={k === on ? "on" : ""} onClick={() => setTab(k)}>{label}</button>)}</nav>
      )}
      {data === undefined ? null : !tabs.length ? <p className="rc-empty">The recap starts once the draft is done.</p>
        : on === "draft" ? <DraftGrades d={data.draft} /> : null}
    </FantasyShell>
  );
}
