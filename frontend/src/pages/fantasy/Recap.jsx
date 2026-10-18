import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { NBA_TEAMS } from "../../components/fantasy/nbaTeams";
import FitText from "../../components/fantasy/FitText";
import { Headshot, NbaTeamSquare, PositionBadge } from "../../components/fantasy/RosterBits";
import { textOnColor } from "../../components/fantasy/teamColors";
import { SEASON, useFantasyApi } from "../../components/fantasy/data";
import RecapWeek from "./RecapWeek";
import "./Recap.css";

// Recap (GET /recap, recap.py): Draft Grades once the draft is done; Draft Value appears once Week 1 is over, then a tab
// per finished week. Draft Grades are in fantasy points a week over the best player left at the position.
const SLOT_RANK = { G: 0, F: 1, C: 2, FLEX: 3, TEAM: 4, BENCH: 5, IR: 6 };
const short = n => { const p = (n || "").split(" "); return p.length < 2 ? n : `${p[0][0]}. ${p.slice(1).join(" ")}`; };
const signed = v => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(1)}`;
const tone = v => (v > 0.05 ? "pos" : v < -0.05 ? "neg" : "");
const pickLabel = (p, n) => `R${Math.ceil(p.pick_no / n)}·${((p.pick_no - 1) % n) + 1}`;
const last = n => (n || "").split(" ").slice(1).join(" ") || n;

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

// One award card: the winner as a row (face · name + fantasy team · the number), one detail line, then #2–3 as
// compact rows. Entries: {face, name, team, num, cls, unit, detail}.
function Award({ title, entries }) {
  if (!entries?.length) return null;
  const [w, ...rest] = entries;
  return (
    <div className="rc-award" style={{ "--nc": w.color || "var(--surface-3)", "--tc": (w.team || w.teamColorOf)?.color || "var(--surface-3)" }}>
      <div className="rc-aw-top"><span className="rc-aw-label">{title}</span>{w.big}</div>
      <div className="rc-aw-win">
        <span className="rc-aw-id"><FitText text={w.name} max={15} min={11} />{w.team && <span className="rc-aw-team"><TeamIcon team={w.team} size={16} /><span>{w.team.name}</span></span>}</span>
      </div>
      <div className={`rc-aw-big ${w.cls || ""}`}>{w.num}<small>{w.unit}</small></div>
      <div className="rc-aw-detail">{w.detail}</div>
      {rest.length > 0 && (
        <div className="rc-awl">
          {rest.map((e, k) => (
            <div key={k} className="rc-awl-row">
              <span className="rc-awl-rk" style={e.team || e.teamColorOf ? { background: (e.team || e.teamColorOf).color, color: textOnColor((e.team || e.teamColorOf).color) } : undefined}>{k + 2}</span>
              <span className="rc-awl-nm"><FitText text={e.name} max={13} min={10} /><span>{e.sub ?? e.detail}</span></span>
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
  const nameOf = p => (p.kind === "nba_team" ? p.name : short(p.name));
  const nbaColor = p => NBA_TEAMS[p.kind === "nba_team" ? p.id : p.nba_team]?.primary;
  const bigFace = p => (p.kind === "nba_team" ? <span className="rc-aw-logo"><NbaTeamSquare tricode={p.id} size={56} /></span>
    : <Headshot playerId={p.id} tricode={p.nba_team} width={124} height={90} />);
  const playerEntries = (ids, detail, sub) => (ids || []).map(id => picks[id]).filter(Boolean).map(p => (
    { big: bigFace(p), color: nbaColor(p), name: nameOf(p), team: teams[p.team_id], num: signed(p.added), cls: tone(p.added), unit: "a week", detail: detail(p), sub: (sub || detail)(p) }));
  const repl = pos => d.replacement[pos]?.name;
  // Biggest overpay is about money: the number is what he cost over his worth (red); his value explains it.
  const overpayEntries = (aw.overpay || []).map(id => picks[id]).filter(Boolean).map(p => (
    { big: bigFace(p), color: nbaColor(p), name: nameOf(p), team: teams[p.team_id], num: `−$${p.price - p.worth}`, cls: "neg", unit: "over worth",
      detail: `$${p.price} vs fair $${p.worth} · ${signed(p.added)} a week`, sub: `$${p.price} vs fair $${p.worth}` }));
  const benchEntries = (aw.bench || []).map(b => {
    const t = teams[b.team_id];
    const ps = b.players.map(id => picks[id]).filter(Boolean);
    return { big: <span className="rc-aw-logo"><TeamIcon team={t} size={56} /></span>, color: t.color, name: t.name, team: null, teamColorOf: t, num: signed(b.added), cls: tone(b.added), unit: "a week",
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
            <span key={t.id}><TeamIcon team={t} size={18} />{t.name}<b className="neg">${t.unspent}</b></span>
          ))}
        </div>
      )}

      <section className="rc-awards">
        {auction ? (
          <>
            <Award title="Best buy" entries={playerEntries(aw.best_buy, p => `$${p.price} vs fair $${p.worth}`)} />
            <Award title={`Best buy under $${cheapCap}`} entries={playerEntries(aw.best_cheap, p => `$${p.price} vs fair $${p.worth}`, p => `$${p.price}`)} />
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
                    <td className="l"><span className="rc-tn"><TeamIcon team={t} size={26} /><FitText text={t.name} max={16} min={11} /></span></td>
                    <td className="l"><div className="rc-barcell"><span className="rc-bar"><i style={{ width: `${Math.max(0, t.added) / maxAdded * 100}%`, background: t.color }} /></span><b>{signed(t.added)}</b></div></td>
                    <td className="l">{top && <span className="rc-top">{face(top)}<b>{nameOf(top)}</b></span>}</td>
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
        <div className="rc-board" style={{ gridTemplateColumns: `repeat(${Math.min(nTeams, 6)}, minmax(0, 1fr))` }}>{/* at most 6 teams a row (12 = two rows) so names and "vs fair" stay readable */}
          {d.teams.map(t => {
            const mine = d.picks.filter(p => p.team_id === t.id).sort((a, b) => (SLOT_RANK[a.slot] ?? 9) - (SLOT_RANK[b.slot] ?? 9) || (auction ? b.price - a.price : a.pick_no - b.pick_no));
            return (
              <div key={t.id} className="rc-col">
                <div className="rc-col-h" style={{ background: t.color, color: textOnColor(t.color) }}><FitText text={t.name} max={15} min={10} /></div>
                {mine.map(p => (
                  <div key={p.id} className={`rc-cell ${{ pos: "good", neg: "bad" }[tone(p.vs)] || ""}`} style={{ "--k": `${Math.round(8 + Math.min(1, Math.abs(p.vs) / 8) * 42)}%` }}>
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
    <div key={r.id} className="rc-bo-row" style={{ "--tc": teams[r.team_id]?.color }}>
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

// Draft Value (after Week 1): each pick's actual points added a week (while he was the drafting team's) next to the
// draft-day projection; color = actual − projected. A dropped pick counts only through the week he left.
function DraftValue({ v }) {
  const teams = Object.fromEntries(v.teams.map(t => [t.id, t]));
  const picks = Object.fromEntries(v.picks.map(p => [p.id, p]));
  const max = Math.max(1, ...v.teams.map(t => Math.abs(t.actual)));
  const nTeams = v.teams.length;
  const auction = v.type === "auction";
  const regret = v.regret && picks[v.regret.id];
  return (
    <>
      <div className="rc-meta"><b>Through Week {v.through}</b><span>Drafting value based on the actual results of the 2026-27 NBA season</span></div>
      <div className="rc-two">
        <section className="rc-panel">
          <div className="rc-strip"><b>Draft Value</b></div>
          <table className="rc-table">
            <colgroup><col style={{ width: 6 }} /><col style={{ width: "34%" }} /><col style={{ width: "36%" }} /><col /></colgroup>
            <thead><tr><th /><th className="l">Team</th><th className="l">Added / wk</th><th>Projected</th></tr></thead>
            <tbody>{v.teams.map(t => (
              <tr key={t.id}>
                <td className="rc-edge" style={{ background: t.color }} />
                <td className="l"><span className="rc-tn"><TeamIcon team={t} size={24} /><FitText text={t.name} max={18} min={11} /></span></td>
                <td className="l"><div className="rc-barcell"><span className="rc-bar"><i style={{ width: `${Math.max(0, t.actual) / max * 100}%`, background: t.color }} /></span><b className={tone(t.actual)}>{signed(t.actual)}</b></div></td>
                <td><i>{signed(t.added)}</i></td>
              </tr>
            ))}</tbody>
          </table>
        </section>
        {regret && (
          <section className="rc-panel">
            <div className="rc-strip"><b>Biggest regret</b></div>
            <div className="rc-regret">
              <Who p={regret} teams={teams} />
              <div className="rc-aw-num">{v.regret.since.toFixed(1)}<small>points since</small></div>
              <div className="rc-aw-foot">dropped after Week {v.regret.left_week} · {v.regret.weeks_since} {v.regret.weeks_since === 1 ? "week" : "weeks"} since</div>
            </div>
          </section>
        )}
      </div>
      <section className="rc-panel">
        <div className="rc-strip"><b>Rosters</b></div>
        <div className="rc-board" style={{ gridTemplateColumns: `repeat(${Math.min(nTeams, 6)}, minmax(0, 1fr))` }}>{/* at most 6 teams a row (12 = two rows) so names and "vs fair" stay readable */}
          {v.teams.map(t => {
            const mine = v.picks.filter(p => p.team_id === t.id).sort((a, b) => (SLOT_RANK[a.slot] ?? 9) - (SLOT_RANK[b.slot] ?? 9) || (auction ? (b.price || 0) - (a.price || 0) : a.pick_no - b.pick_no));
            return (
              <div key={t.id} className="rc-col">
                <div className="rc-col-h" style={{ background: t.color, color: textOnColor(t.color) }}><FitText text={t.name} max={15} min={10} /></div>
                {mine.map(p => {
                  const d = p.actual == null ? 0 : p.actual - p.added;
                  return (
                    <div key={p.id} className={`rc-cell ${{ pos: "good", neg: "bad" }[tone(d)] || ""}`} style={{ "--k": `${Math.round(8 + Math.min(1, Math.abs(d) / 8) * 42)}%` }}>
                      <span className="rc-c1"><Pos p={p} /><span className="rc-cn">{p.kind === "nba_team" ? p.name : short(p.name)}</span><span className="rc-ct">{auction ? `$${p.price}` : pickLabel(p, nTeams)}</span></span>
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

// The recap index (2026-10-17): the draft's report as a lead card with its headline awards, then every finished week
// as a tile, newest first. Each recap links back here.
function RecapIndex({ data }) {
  const d = data.draft;
  const teams = d ? Object.fromEntries(d.teams.map(t => [t.id, t])) : {};
  const picks = d ? Object.fromEntries(d.picks.map(p => [p.id, p])) : {};
  const one = ids => (ids || []).map(id => picks[id]).find(Boolean);
  const best = d && one(d.awards?.best_buy), over = d && one(d.awards?.overpay);
  const top = d ? [...d.teams].sort((x, y) => y.added - x.added)[0] : null;
  const face = p => (p.kind === "nba_team" ? <NbaTeamSquare tricode={p.id} size={40} /> : <Headshot playerId={p.id} tricode={p.nba_team} width={60} height={44} />);
  const weeks = [...(data.weeks || [])].reverse();
  return (
    <div className="rx">
      {d && (
        <Link to="?tab=draft" className="rx-lead">
          <div className="rx-lead-h">
            <span className="rx-kicker">The draft · {d.type === "auction" ? "auction" : "snake"} · {d.picks.length} picks</span>
            <b className="rx-title">Draft Grades</b>
            <span className="rx-go">Read the report →</span>
          </div>
          <div className="rx-hl">
            {top && <div className="rx-hl-i" style={{ "--tc": top.color }}><span className="rx-hl-l">Best draft</span>
              <span className="rx-hl-who"><TeamIcon team={top} size={40} /><b>{top.name}</b></span><span className="rx-hl-n">{signed(top.added)} a week</span></div>}
            {best && <div className="rx-hl-i" style={{ "--tc": teams[best.team_id]?.color }}><span className="rx-hl-l">Best buy</span>
              <span className="rx-hl-who">{face(best)}<b>{best.name}</b></span><span className="rx-hl-n">${best.price} · fair ${best.worth}</span></div>}
            {over && <div className="rx-hl-i" style={{ "--tc": teams[over.team_id]?.color }}><span className="rx-hl-l">Biggest overpay</span>
              <span className="rx-hl-who">{face(over)}<b>{over.name}</b></span><span className="rx-hl-n">${over.price} · fair ${over.worth}</span></div>}
          </div>
        </Link>
      )}
      {data.value && (
        <Link to="?tab=value" className="rx-tile wide"><span className="rx-kicker">The draft, a few weeks in</span><b className="rx-tname">Draft Value</b>
          <span>Who's getting the most out of what they drafted</span></Link>
      )}
      <h2 className="rx-h">Weekly recaps</h2>
      {weeks.length === 0 ? <p className="rx-empty">The first weekly recap appears when Week 1 ends.</p> : (
        <div className="rx-weeks">
          {weeks.map(w => (
            <Link key={w.week} to={`?tab=w${w.week}`} className="rx-tile">
              <span className="rx-wk">{w.week}</span><b className="rx-tname">{w.label || `Week ${w.week}`}</b><span>Scores, awards, the week's story</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Recap() {
  const data = useFantasyApi("recap");
  const tabs = [data?.draft && ["draft", "Draft Grades"], data?.value && ["value", "Draft Value"], ...(data?.weeks || []).map(w => [`w${w.week}`, `Week ${w.week}`])].filter(Boolean);
  const [params] = useSearchParams();
  const tab = params.get("tab");
  const on = tab && tabs.some(t => t[0] === tab) ? tab : null;
  const label = on ? tabs.find(t => t[0] === on)[1] : null;
  // No recap picked: the index of every recap (2026-10-17). A recap: "← All recaps" back to it.
  return (
    <FantasyShell title={label ? `Recap · ${label}` : "Recaps"} season={SEASON}>
      {data === undefined ? null : !tabs.length ? <p className="rc-empty">The recap starts once the draft is done.</p>
        : !on ? <RecapIndex data={data} />
        : (
          <>
            <Link className="rc-back" to="?">← All recaps</Link>
            {on === "draft" ? <DraftGrades d={data.draft} />
              : on === "value" ? <DraftValue v={data.value} />
                : <RecapWeek week={Number(on.slice(1))} />}
          </>
        )}
    </FantasyShell>
  );
}
