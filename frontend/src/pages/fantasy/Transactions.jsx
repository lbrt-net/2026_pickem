import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { Headshot, NbaTeamSquare } from "../../components/fantasy/RosterBits";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { SEASON, useFantasyApi } from "../../components/fantasy/data";
import { ctDateTime, ctMonthDay } from "../../components/fantasy/format";
import { hasTie, recordText } from "../../components/fantasy/standings";
import "./DraftRoom.css";
import "./Transactions.css";

// Transaction Log: every add / drop, waiver claims won, and every draft pick — newest first, grouped by fantasy week.
// One row per move (2026-10-27): a drop and the same team's next add in that week are one row, each time stacked beside
// its player (adds first, then the drop). Draft picks come from GET /draft. ?player=<id> narrows it to moves involving
// that player (the player page links here). Injuries tab (2026-10-30): every change to the injury report for pool
// players (newly listed, status changed, return date moved, cleared), with the fantasy team that has him now. Only the
// ones that matter by default: red (Out) changes, players at 15+ MPG this season (in 20%+ of his team's games) OR
// over the 2 seasons before (a rookie who plays now is in; so is a regular who's missing now; a one-game call-up
// isn't); filters for yellow (Day-To-Day), MPG, AVG (FP per game) and out for season.

const TYPES = [["all", "All"], ["moves", "Adds & drops"], ["waivers", "Waiver claims"], ["trades", "Trades"], ["draft", "Draft"], ["injuries", "Injuries"], ["order", "Waiver order"]];
const sub = e => (e.kind === "nba_team" ? `TM · ${e.id}` : [e.position || "—", e.nba_team].filter(Boolean).join(" · "));
const when = ctDateTime;
const PAGE_ROWS = 25; // lines per page, like the Players list
const day = ctMonthDay;
// how a row's players moved: per player, via = "waivers" | "trade" | null
// one injury update in words: "Out · Left Ankle Sprain · back 11/5", "Day-To-Day → Out", "Off the report (was Out)"
const back = d => (d ? `back ${Number(d.slice(5, 7))}/${Number(d.slice(8, 10))}` : null);
function injuryText(e) {
  if (e.kind === "cleared") return `Off the report (was ${e.prev_status || "listed"})`;
  const head = e.kind === "status" ? `${e.prev_status} → ${e.status}` : e.status;
  const ret = e.kind === "return" ? `${back(e.return_date) || "no return date"}${e.prev_return ? ` (was ${back(e.prev_return).slice(5)})` : ""}` : back(e.return_date);
  return [head, e.injury, ret].filter(Boolean).join(" · ");
}
// red = Out / Out For Season / Suspension, yellow = Day-To-Day; a change counts as both when it moves between them
const RED = new Set(["Out", "Out For Season", "Suspension"]);
const sevOf = e => new Set([e.status, e.prev_status].filter(Boolean).map(x => (RED.has(x) ? "red" : "yellow")));
const ofsOf = e => e.status === "Out For Season" || e.prev_status === "Out For Season";
const SEV = [["red", "Red"], ["yellow", "Yellow"], ["both", "Both"]];
const OFS = [["show", "Show"], ["hide", "Hide"], ["only", "Only"]];
// a floor passes on this season's number (only once he's played 20%+ of his team's games) or the 2 seasons before's
const regular = e => e.gp_now > 0 && e.gp_now >= 0.2 * e.team_games;
const passes = (e, k, min) => !(Number(min) > 0) || [regular(e) ? e[`${k}_now`] : null, e[`${k}2`]].some(v => v != null && v >= Number(min));
// the numbers that put him on the list: this season's ('27, games of his team's) when they clear the floor, else the
// 2 seasons before ('25–'26), else whichever he has
function usageText(e, min) {
  const yy = n => `'${String(Number(SEASON.slice(2, 4)) + 1 - n).padStart(2, "0")}`;
  const now = e.mpg_now != null && { m: e.mpg_now, a: e.avg_now, tag: `${yy(0)} · ${e.gp_now} of ${e.team_games} games` };
  const two = e.mpg2 != null && { m: e.mpg2, a: e.avg2, tag: `${yy(2)}–${yy(1)}` };
  const u = (now && regular(e) && now.m >= (Number(min) || 0) && now) || (two && two.m >= (Number(min) || 0) && two) || now || two;
  return u ? `${u.m.toFixed(1)} MPG · ${u.a.toFixed(1)} AVG · ${u.tag}` : "No games";
}
const viaOf = g => new Set([...g.adds, ...g.drops].map(e => e.via).concat(g.via).filter(Boolean));  // (g.via: older payloads)

function Who({ e, sign, via = e.via }) {
  return (
    <span className="tx-who">
      {sign && <i className={`tx-sign ${sign === "+" ? "add" : "drop"}`} aria-label={sign === "+" ? "added" : "dropped"}>{sign === "+" ? "+" : "−"}</i>}
      {e.kind === "player" ? <Headshot playerId={e.id} tricode={e.nba_team} width={26} height={28} /> : <NbaTeamSquare tricode={e.id} size={24} />}
      <span className="tx-name"><EntityLink id={e.id} name={e.name} style={{ color: "inherit", textDecoration: "none" }} /><small>{sub(e)}</small>
        {sign === "+" && via === "waivers" && <small className="tx-via">via waivers</small>}{via === "trade" && <small className="tx-via">via trade</small>}</span>
    </span>
  );
}

function Seg({ options, value, onChange }) {
  return (
    <span className="dr-seg" role="radiogroup">
      {options.map(([k, label]) => <button key={k} type="button" role="radio" aria-checked={value === k} onClick={() => onChange(k)}>{label}</button>)}
    </span>
  );
}

export default function Transactions() {
  const log = useFantasyApi("transactions");
  const draft = useFantasyApi("draft");
  const teams = useFantasyApi("teams");
  const [type, setType] = useState("all");
  const [team, setTeam] = useState("");
  const [page, setPage] = useState(0);
  const [sev, setSev] = useState("red");
  const [minMpg, setMinMpg] = useState("15");
  const [minAvg, setMinAvg] = useState("");
  const [ofs, setOfs] = useState("show");
  const [params, setParams] = useSearchParams();
  const player = params.get("player") || "";

  const teamById = useMemo(() => Object.fromEntries((teams || []).map(t => [t.id, t])), [teams]);
  const items = useMemo(() => (log?.items || []).filter(g =>
    (!team || g.team_id === team) && (!player || [...g.adds, ...g.drops].some(e => e.id === player)) && (type === "all" || (type === "moves" && !viaOf(g).size) || viaOf(g).has({ waivers: "waivers", trades: "trade" }[type]))),
  [log, type, team, player]);
  // Newest week first; each week's entries newest first (the server's order).
  const byWeek = useMemo(() => {
    const out = [];
    for (const g of items) {
      const k = g.week ?? "pre";
      let w = out.find(x => x.key === k);
      if (!w) { w = { key: k, week: g.week, label: g.week_label, items: [] }; out.push(w); }
      w.items.push(g);
    }
    return out;
  }, [items]);
  const weekInfo = Object.fromEntries((log?.weeks || []).map(w => [w.week, w]));
  const picks = (draft?.picks || []).filter(p => (!team || p.team_id === team) && (!player || p.id === player));
  const playerName = player ? ((log?.items || []).flatMap(g => [...g.adds, ...g.drops]).concat((log?.injuries || []).map(e => e.player)).find(e => e.id === player)?.name
    || (draft?.picks || []).find(p => p.id === player)?.name || "this player") : null;
  const auction = draft?.draft_type === "auction";
  const claimsWon = (log?.items || []).reduce((n, g) => n + g.adds.filter(e => (e.via ?? g.via) === "waivers").length, 0);
  const loading = log === undefined || draft === undefined;
  const tie = hasTie(log?.waiver_order);

  // Every line of the log (each week's moves, newest first, then the draft), 25 to a page; each page starts with its
  // week's header even when the week runs across pages.
  const lines = [];
  if (type !== "draft" && type !== "order" && type !== "injuries") {
    for (const w of byWeek) {
      const group = { key: `w${w.key}`, label: w.week ? (w.label || `Week ${w.week}`) : "Before the season",
        sub: w.week && weekInfo[w.week] ? `${day(weekInfo[w.week].start)} – ${day(weekInfo[w.week].end)}` : null };
      for (const g of w.items) {
        const t = teamById[g.team_id];
        lines.push({ key: `${g.team_id}-${g.at}`, group, el: (
          <div className="tx-row">
            <span className="tx-time">{when(g.at)}{g.drop_at && <><br />{when(g.drop_at)}</>}</span>
            <span className="tx-team-cell" title={g.team_name} style={{ boxShadow: t?.color ? `inset 3px 0 0 ${t.color}` : undefined }}>{t && <TeamIcon team={t} size={24} />}<TeamLink ownerId={t?.owner_user_id} name={t?.abbreviation || g.team_name} style={{ color: "inherit", textDecoration: "none", fontWeight: 600 }} /></span>
            <span className="tx-moves">
              {g.adds.map(e => <Who key={`a${e.id}`} e={e} sign="+" via={e.via ?? g.via} />)}
              {g.drops.map(e => <Who key={`d${e.id}`} e={e} sign="-" />)}
            </span>
            <span className="tx-tags">
              {g.by === "commissioner" && <span className="dr-tag">commissioner</span>}
            </span>
          </div>
        ) });
      }
    }
  }
  if (type === "injuries") {
    let group = null;
    for (const e of log?.injuries || []) {
      if ((team && e.team_id !== team) || (player && e.player.id !== player)) continue;
      if (!player && ((sev !== "both" && !sevOf(e).has(sev)) || (ofs === "hide" && ofsOf(e)) || (ofs === "only" && !ofsOf(e))
        || !passes(e, "mpg", minMpg) || !passes(e, "avg", minAvg))) continue;
      const k = e.week ?? "pre";
      if (group?.key !== `i${k}`) group = { key: `i${k}`, label: e.week ? (e.week_label || `Week ${e.week}`) : "Before the season",
        sub: e.week && weekInfo[e.week] ? `${day(weekInfo[e.week].start)} – ${day(weekInfo[e.week].end)}` : null };
      const t = teamById[e.team_id];
      lines.push({ key: `i${e.id}`, group, el: (
        <div className="tx-row">
          <span className="tx-time">{when(e.at)}</span>
          <span className="tx-team-cell" title={e.team_name || "Free agent"} style={{ boxShadow: t?.color ? `inset 3px 0 0 ${t.color}` : undefined }}>{t ? <><TeamIcon team={t} size={24} /><TeamLink ownerId={t.owner_user_id} name={t.abbreviation || e.team_name} style={{ color: "inherit", textDecoration: "none", fontWeight: 600 }} /></> : "FA"}</span>
          <span className="tx-moves tx-inj"><Who e={e.player} /><small className="tx-3y">{usageText(e, minMpg)}</small></span>
          <span className="tx-tags"><span className="tx-note" title={e.comment || undefined}>{injuryText(e)}</span></span>
        </div>
      ) });
    }
  }
  if ((type === "all" || type === "draft") && picks.length > 0) {
    const group = { key: "draft", label: "Draft", sub: `${picks.length} drafted${picks[0]?.picked_at ? ` · ${ctMonthDay(picks[0].picked_at)}` : ""}` };
    for (const p of [...picks].reverse()) {
      const t = teamById[p.team_id];
      const e = { id: p.id, kind: p.kind, name: p.name, position: p.position, nba_team: p.kind === "nba_team" ? p.id : null };
      lines.push({ key: `p${p.pick}`, group, el: (
        <div className="tx-row">
          <span className="tx-time">{p.picked_at ? when(p.picked_at) : ""}</span>
          <span className="tx-team-cell" title={p.team_name} style={{ boxShadow: t?.color ? `inset 3px 0 0 ${t.color}` : undefined }}>{t && <TeamIcon team={t} size={24} />}<TeamLink ownerId={t?.owner_user_id} name={t?.abbreviation || p.team_name} style={{ color: "inherit", textDecoration: "none", fontWeight: 600 }} /></span>
          <span className="tx-moves"><Who e={e} sign="+" /></span>
          <span className="tx-tags">
            <span className="tx-note">{auction ? `Drafted for $${p.price ?? 0}` : `Drafted · round ${p.round}, pick ${p.pick}`}</span>
            {p.auto && <span className="dr-tag">auto</span>}
          </span>
        </div>
      ) });
    }
  }
  const pages = Math.max(1, Math.ceil(lines.length / PAGE_ROWS));
  const at = Math.min(page, pages - 1);
  const pageRows = lines.slice(at * PAGE_ROWS, (at + 1) * PAGE_ROWS);

  return (
    <FantasyShell title="Transaction Log" season={SEASON}>
      <section className="tx-sum" aria-label="Summary">
        <div><b>{log?.adds ?? "—"}</b><span>Adds</span></div>
        <div><b>{log?.drops ?? "—"}</b><span>Drops</span></div>
        <div><b>{log ? claimsWon : "—"}</b><span>Waiver claims won</span></div>
        <div><b>{draft?.picks?.length ?? "—"}</b><span>Draft picks</span></div>
      </section>

      <section className="dr-panel tx-panel" aria-label="Transactions">
        <div className="tx-tools">
          <Seg options={TYPES} value={type} onChange={k => { setType(k); setPage(0); }} />
          {type !== "order" && <select className="tx-team" value={team} onChange={e => { setTeam(e.target.value); setPage(0); }} aria-label="Team">
            <option value="">All teams</option>
            {(teams || []).map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>}
          {type === "injuries" && (
            <>
              <Seg options={SEV} value={sev} onChange={k => { setSev(k); setPage(0); }} />
              <label className="tx-f">MPG ≥ <input type="number" min="0" step="1" value={minMpg} onChange={e => { setMinMpg(e.target.value); setPage(0); }} /></label>
              <label className="tx-f">AVG ≥ <input type="number" min="0" step="1" value={minAvg} placeholder="0" onChange={e => { setMinAvg(e.target.value); setPage(0); }} /></label>
              <span className="tx-f">Out for season <Seg options={OFS} value={ofs} onChange={k => { setOfs(k); setPage(0); }} /></span>
            </>
          )}
          {player && (
            <button type="button" className="tx-player" onClick={() => { setParams({}); setPage(0); }} aria-label="Show all players">
              {playerName} <span aria-hidden="true">✕</span>
            </button>
          )}
        </div>

        {loading && <p className="tx-msg">Loading…</p>}
        {!loading && type === "injuries" && lines.length === 0 && <p className="tx-msg">{(log?.injuries || []).length ? "No injury updates match these filters." : "No injury updates yet. They're logged from 10/30 on."}</p>}
        {!loading && type !== "draft" && type !== "order" && type !== "injuries" && byWeek.length === 0 && <p className="tx-msg">{type === "trades" ? "No trades yet." : "No adds or drops yet."}</p>}

        {/* Waiver order (2026-10-27): who wins the next claim. Resets at each scoring period's first lock to reverse
            standings as they stood then; a team that wins a claim goes to the back until the next reset. The record
            shown is the one at the reset, so it can differ from Standings mid-period. */}
        {!loading && type === "order" && (
          <>
            <div className="tx-week-h"><b>Claim order</b><span>{log?.waiver_reset ? `Record and points as of the reset · ${when(log.waiver_reset)}` : "Record and points as of the reset"}</span></div>
            {(log?.waiver_order || []).map((o, i) => {
              const t = teamById[o.team_id];
              return (
                <div key={o.team_id} className="tx-row">
                  <span className="tx-time">#{i + 1}</span>
                  <span className="tx-team-cell" title={o.team_name} style={{ boxShadow: t?.color ? `inset 3px 0 0 ${t.color}` : undefined }}>{t && <TeamIcon team={t} size={24} />}<TeamLink ownerId={t?.owner_user_id} name={t?.abbreviation || o.team_name} style={{ color: "inherit", textDecoration: "none", fontWeight: 600 }} /></span>
                  <span className="tx-moves">{recordText(o, tie)} · {o.pf.toFixed(1)} PF</span>
                  <span className="tx-tags">{o.won.length > 0 && <span className="tx-note">Won {o.won.map(x => x.name).join(", ")}</span>}</span>
                </div>
              );
            })}
          </>
        )}

        {pageRows.map((r, i) => (
          <div key={r.key}>
            {(i === 0 || pageRows[i - 1].group.key !== r.group.key) && (
              <div className="tx-week-h"><b>{r.group.label}</b>{r.group.sub && <span>{r.group.sub}</span>}</div>
            )}
            {r.el}
          </div>
        ))}

        {lines.length > PAGE_ROWS && (
          <div className="dr-pager">
            <span>{at * PAGE_ROWS + 1}–{Math.min(lines.length, (at + 1) * PAGE_ROWS)} of {lines.length}</span>
            <span className="dr-pager-btns">
              <button type="button" className="dr-btn small" disabled={at === 0} onClick={() => setPage(0)} aria-label="First page">«</button>
              <button type="button" className="dr-btn small" disabled={at === 0} onClick={() => setPage(at - 1)}>‹ Prev</button>
              <span className="dr-pager-at">Page {at + 1} of {pages}</span>
              <button type="button" className="dr-btn small" disabled={at >= pages - 1} onClick={() => setPage(at + 1)}>Next ›</button>
              <button type="button" className="dr-btn small" disabled={at >= pages - 1} onClick={() => setPage(pages - 1)} aria-label="Last page">»</button>
            </span>
          </div>
        )}
      </section>
    </FantasyShell>
  );
}
