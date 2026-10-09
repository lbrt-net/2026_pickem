import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import LedClock from "../../components/fantasy/LedClock";
import { Headshot, NbaTeamSquare, PositionBadge } from "../../components/fantasy/RosterBits";
import { nameLines } from "../../components/fantasy/nbaTeams";
import { EntityLink } from "../../components/fantasy/links";
import RangeBar from "../../components/fantasy/RangeBar";
import { InjuryDot } from "../../components/fantasy/InjuryDot";
import { useInjuries } from "../../components/fantasy/injuries";
import GlossaryButton from "../../components/fantasy/GlossaryButton";
import { shortName as fitName } from "../../components/fantasy/playerNames";
import { setCardActions } from "../../components/fantasy/cardEvents";
import { API_BASE, base, useFantasyApi } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";
import "./DraftRoom.css";

// Draft room (design: "lbrt.net Design" canvas, row O). The server owns everything (GET /draft):
// order, picks, who's on the clock, deadlines, auto-picks when a clock runs out. This page polls
// and ticks the clocks locally.
// Look (DESIGN.md + feedback): gold only for you / on the clock; blue = the main action; solid
// secondary buttons; quiet filters; panels with header strips; graphite empty spots; the display
// face only for the title-level moments (clock, high bid, start time).
// Views: before the draft · snake (you up / someone else) · auction (nominate / bidding) · complete.
// Phone: one column with Available / Board / Roster (auction: Budgets) tabs.

const POLL_MS = 4000;
const TYPE_NAMES = { snake: "Snake", snake_3rr: "Snake, 3rd-round reversal", linear: "Normal", auction: "Auction" };
const SLOT_ORDER = ["G", "F", "C", "TEAM", "FLEX", "BENCH"];
const SLOT_LABEL = { G: "G", F: "F", C: "C", TEAM: "TM", FLEX: "FLX", BENCH: "Bench" };
const RULE_NAMES = SLOT_LABEL; // roster rules use the same short names: G / F / C / TM / FLX / Bench
const FILTERS = ["All", "G", "F", "C", "TM"];
// The list's view: projected (the league season's pool) or a past season's actual numbers (/players/board).
const VIEWS = [["proj", "Projected"], ["2025-26", "'26"], ["2024-25", "'25"], ["2023-24", "'24"], ["2022-23", "'23"]];
const TIPS = {
  max: "Weekly score: his best game of the week", avg: "Fantasy points per game",
  pmax: "Expected weekly score (best game of the week), averaged over the 2026-27 weeks", pavg: "Expected fantasy points per game",
  range: "MAX low (a bad week, 25th percentile) to MAX high (a big week, 90th percentile); dot = MAX; thin line = AVG",
  rec: "Your recommended auction bid for him", gp: "Games played",
  total: "His weekly maxes added up over the season — the list sorts by this",
  pgp: "Games he's expected to play, scaled to a full 82 (injuries and availability included)",
};

const mmss = ms => {
  const s = Math.max(0, Math.ceil(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};
// Clock length in words: "30 sec", "5 min", "1 min 30 sec".
const minutes = s => {
  const m = Math.floor(s / 60), sec = s % 60;
  if (!m) return `${sec} sec`;
  return sec ? `${m} min ${sec} sec` : `${m} min`;
};
const shortName = (name, kind) => {
  if (kind === "nba_team") return nameLines({ kind, id: "", name })[1] || name;
  const i = (name || "").indexOf(" ");
  return i === -1 ? name : `${name[0]}. ${name.slice(i + 1)}`;
};
// Dark text on light team colors (e.g. a near-white team), white on everything else.
const inkOn = hex => {
  const h = (hex || "").replace("#", "");
  if (h.length !== 6) return undefined;
  const [r, g, b] = [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16));
  return 0.299 * r + 0.587 * g + 0.114 * b > 170 ? "var(--bg)" : undefined;
};
const slotList = slots => SLOT_ORDER.flatMap(k => Array.from({ length: slots[k] || 0 }, () => k));
// Same rule as the server's open_slot: NBA team → TM, player → his G/F/C spot, then FLX, then Bench.
// Lets the list say "No spot" instead of offering a pick the server would refuse.
function fits(entity, teamId, picks, slots) {
  if (!teamId) return true;
  const used = {};
  for (const p of picks) if (p.team_id === teamId) used[p.slot] = (used[p.slot] || 0) + 1;
  const free = k => (used[k] || 0) < (slots[k] || 0);
  const own = entity.kind === "nba_team" ? ["TEAM"] : ["G", "F", "C"].includes(entity.position) ? [entity.position] : [];
  return [...own, "FLEX", "BENCH"].some(free);
}

// A panel; with `fold` (a name) its header opens / closes it, remembered per browser.
function usePanelOpen(fold, initial = true) {
  const key = fold ? `dr-open-${fold}` : null;
  const [open, setOpen] = useState(() => {
    if (!key) return true;
    try { const v = localStorage.getItem(key); return v == null ? initial : v === "1"; } catch { return initial; }
  });
  const toggle = () => setOpen(o => {
    try { if (key) localStorage.setItem(key, o ? "0" : "1"); } catch { /* private mode */ }
    return !o;
  });
  return [open, toggle];
}

function Panel({ title, aside, extra, top, className = "", fold, foldInitial = true, children }) {
  const [open, toggle] = usePanelOpen(fold, foldInitial);
  return (
    <section className={`dr-panel ${className}${fold && !open ? " folded" : ""}`} aria-label={typeof title === "string" ? title : undefined} style={top ? { borderTop: `3px solid ${top}` } : undefined}>
      <div className="dr-panel-head">
        {fold ? (
          <button type="button" className="dr-fold" aria-expanded={open} onClick={toggle}>
            <span className="dr-fold-arrow" aria-hidden="true">{open ? "▾" : "▸"}</span><span className="dr-h2">{title}</span>
          </button>
        ) : <span className="dr-h2">{title}</span>}
        {open && extra}{aside != null && <span className="dr-aside">{aside}</span>}
      </div>
      {open && children}
    </section>
  );
}

// The clock, anchored to the server: time left = deadline − (this browser's clock + its offset from the server's).
// Only these small pieces tick (4× a second); the rest of the page doesn't redraw.
function useNow(ms = 250) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), ms);
    return () => clearInterval(t);
  }, [ms]);
  return now;
}
function TimeLeft({ deadline, skew, cap, children }) {
  const now = useNow();
  const ms = deadline ? Math.max(0, Math.min(Date.parse(deadline) - (now + skew), cap || Infinity)) : 0;
  return children(ms);
}

function Seg({ options, value, onChange, full }) {
  return (
    <span className={`dr-seg${full ? " full" : ""}`} role="radiogroup">
      {options.map(o => {
        const [key, label] = Array.isArray(o) ? o : [o, o];
        return <button key={key} type="button" role="radio" aria-checked={value === key} onClick={() => onChange(key)}>{label}</button>;
      })}
    </span>
  );
}

const SHIELD = (
  <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
    <path d="M9 1.8 3 4.2v4.3c0 3.7 2.6 6.7 6 7.7 3.4-1 6-4 6-7.7V4.2z" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinejoin="round" />
    <path d="M6.3 9.1 8.2 11l3.6-3.8" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

function Commish({ text, children }) {
  return (
    <section className="dr-commish" aria-label="Commissioner">
      <span className="dr-h2 dr-commish-label">{SHIELD}Commissioner</span>
      {text && <span className="dr-commish-text">{text}</span>}
      <span className="dr-commish-controls">{children}</span>
    </section>
  );
}

function Switch({ on, onChange, label, disabled }) {
  return (
    <label className="dr-switch">
      <button type="button" role="switch" aria-checked={on} disabled={disabled} onClick={() => onChange(!on)} />
      {label}
    </label>
  );
}

function ClockBar({ team, mine, title, sub, deadline, skew, cap }) {
  return (
    <section className={`dr-clockbar${mine ? " mine" : ""}`} aria-label="On the clock">
      <div className="dr-clockbar-who">
        {team && <TeamIcon team={team} size={48} />}
        <div><b>{title}</b><span>{sub}</span></div>
      </div>
      <div className="dr-clockbar-led"><TimeLeft deadline={deadline} skew={skew} cap={cap}>{ms => <LedClock text={mmss(ms)} urgent={ms < 60000} />}</TimeLeft></div>
    </section>
  );
}

// Your own line, right under the clock: what auto-pick takes for YOUR team if your clock runs out.
// Only your team ever gets this from the server.
function MyAuto({ team, autoNext, queuedIds }) {
  if (!team || !autoNext) return null;
  return (
    <section className="dr-myauto" aria-label="Your auto-pick">
      <TeamIcon team={team} size={22} />
      <span>If your clock runs out: <b>{autoNext.name}</b> {queuedIds.includes(autoNext.id) ? "(first in your queue that fits)" : "(best available — your queue is empty or nothing in it fits)"}</span>
    </section>
  );
}

// Red glow around the window edges when it's YOUR turn and 5 seconds or less are left (draft page only).
function UrgentGlow({ on, deadline, skew }) {
  if (!on) return null;
  return <TimeLeft deadline={deadline} skew={skew}>{ms => (ms > 0 && ms <= 5000 ? <div className="dr-urgent-glow" aria-hidden="true" /> : null)}</TimeLeft>;
}

function EntityRow({ e }) {
  const [first, last] = nameLines(e);
  return (
    <span className="dr-entity">
      <PositionBadge entry={e} size={26} />
      <NbaTeamSquare tricode={e.kind === "nba_team" ? e.id : e.nba_team} size={26} />
      <EntityLink id={e.id} name={<span className="dr-name2"><span>{first}</span><b>{last}</b></span>} />
    </span>
  );
}

function PoolName({ e, inj }) {
  const { text, small } = fitName(e.name);
  const sub = e.kind === "nba_team" ? "TM" : [e.position || "—", e.nba_team].filter(Boolean).join(" · ");
  return (
    <>
      <td className="hs">{e.kind === "player" ? <Headshot playerId={e.id} tricode={e.nba_team} width={40} height={46} /> : <span className="dr-tm-logo"><NbaTeamSquare tricode={e.id} size={36} /></span>}<InjuryDot inj={inj} /></td>
      <td className="who"><EntityLink id={e.id} name={text} style={{ color: "inherit", textDecoration: "none", fontSize: small ? 13 : undefined }} /><span className="sb">{sub}</span></td>
    </>
  );
}

// Available: Projected / '26–'23 views from /players/board; MAX + AVG (PROJ MAX / PROJ AVG projected), the
// MAX low–high bar, Rec bid in an auction; + Queue and the pick button on every row.
// A sortable numeric header: click to sort by it (biggest first; Rk smallest first), click again to flip.
function SortTh({ k, sort, setSort, className = "", title, children }) {
  const on = sort.key === k;
  const first = k === "rk" ? "asc" : "desc";
  return (
    <th className={`${className} dr-sort${on ? " on" : ""}`} title={title} aria-sort={on ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}>
      <button type="button" onClick={() => setSort(on ? { key: k, dir: sort.dir === "asc" ? "desc" : "asc" } : { key: k, dir: first })}>
        {children}<span className="dr-sort-arrow" aria-hidden="true">{on ? (sort.dir === "asc" ? "▲" : "▼") : ""}</span>
      </button>
    </th>
  );
}

function Pool({ items: rows, view, setView, filter, setFilter, own, setOwn, search, setSearch, action, aside, before, queued, toggleQueue, auction, recBids, pickOf = {}, lotId }) {
  const proj = view === "proj";
  const [sort, setSort] = useState({ key: "rk", dir: "asc" });
  // Sort by any numeric column; a player without that number goes to the bottom either way. Columns that aren't in
  // this view (Total / GP in Projected) fall back to rank.
  const val = (e, i) => ({
    rk: e.v?.rank ?? i + 1, total: proj ? null : e.v?.total, max: e.v?.max, avg: e.v?.avg, gp: e.v?.gp,
    rec: recBids?.[e.id],
  })[(!proj || sort.key !== "total") ? sort.key : "rk"];
  const items = rows.map((e, i) => [e, val(e, i)])
    .sort(([, a], [, b]) => (a == null ? 1 : b == null ? -1 : sort.dir === "asc" ? a - b : b - a))
    .map(([e]) => e);
  const rank = new Map(rows.map((e, i) => [e.id, i + 1]));
  const injuries = useInjuries(); // current status: a red (out) / yellow (day-to-day) dot on the headshot, nothing else
  const f1 = v => (v == null ? "" : Number(v).toFixed(1));
  // One scale for the whole list: 0 to the biggest MAX high in it (rounded up to 10).
  const scale = Math.max(10, Math.ceil(Math.max(0, ...items.map(e => e.v?.max_high ?? 0)) / 10) * 10);
  return (
    <Panel title={<>{own === "drafted" ? "Drafted" : own === "all" ? "All players" : "Available"} <GlossaryButton terms={["PROJ MAX", "PROJ AVG", "PROJ GP", "TOTAL", "MAX", "AVG", "MAX low / high", "GP", ...(auction ? ["Rec bid"] : [])]} /></>}
      className="dr-pane dr-pane-available" aside={aside}
      extra={<><Seg options={VIEWS} value={view} onChange={setView} /><Seg options={FILTERS} value={filter} onChange={setFilter} />
        <Seg options={[["available", "Available"], ["drafted", "Drafted"], ["all", "All"]]} value={own} onChange={setOwn} />
        <input className="dr-search" placeholder="Search players and teams" value={search} onChange={e => setSearch(e.target.value)} /></>}>
      {before}
      <div className="dr-scroll">
        <table className="dr-table dr-pl">
          <thead>
            <tr>
              <SortTh k="rk" sort={sort} setSort={setSort} className="rk">Rk</SortTh><th className="hs" /><th className="who">Player</th>
              {!proj && <SortTh k="total" sort={sort} setSort={setSort} className="num w-tot" title={TIPS.total}>Total</SortTh>}
              <SortTh k="max" sort={sort} setSort={setSort} className="num w-n" title={proj ? TIPS.pmax : TIPS.max}>{proj ? "Proj max" : "Max"}</SortTh>
              <SortTh k="avg" sort={sort} setSort={setSort} className="num w-n" title={proj ? TIPS.pavg : TIPS.avg}>{proj ? "Proj avg" : "Avg"}</SortTh>
              <SortTh k="gp" sort={sort} setSort={setSort} className="num w-gp" title={proj ? TIPS.pgp : TIPS.gp}>{proj ? "Proj GP" : "GP"}</SortTh>
              <th className="w-bar" title={TIPS.range}>Max<sub>low</sub> – Max<sub>high</sub></th>
              {auction && <SortTh k="rec" sort={sort} setSort={setSort} className="num w-rec" title={TIPS.rec}>Rec bid</SortTh>}
              <th className="act" />
            </tr>
          </thead>
          <tbody>
            {items.map(e => (
              <tr key={e.id} className={e.id === lotId ? "dr-onblock" : pickOf[e.id] ? "dr-drafted" : undefined}>
                <td className="rk">{e.v?.rank ?? rank.get(e.id)}</td>
                <PoolName e={e} inj={injuries[e.id]} />
                {!proj && <td className="num">{f1(e.v?.total)}</td>}
                <td className="num">{f1(e.v?.max)}</td>
                <td className="num">{f1(e.v?.avg)}</td>
                <td className="num">{proj ? (e.v?.gp == null ? "" : Math.round(e.v.gp)) : e.v?.gp ?? ""}</td>
                <td className="bar"><RangeBar low={e.v?.max_low} mid={e.v?.max} high={e.v?.max_high} avg={e.v?.avg} width={220} scale={scale} /></td>
                {auction && <td className="num">{recBids?.[e.id] != null ? `$${recBids[e.id]}` : "—"}</td>}
                <td className="act">
                  {e.id === lotId ? <b className="dr-onblock-tag">On the block</b> : pickOf[e.id] ? (
                    <span className="dr-drafted-by">{pickOf[e.id].team_name} · {pickOf[e.id].price != null ? `$${pickOf[e.id].price}` : `#${pickOf[e.id].pick}`}</span>
                  ) : (
                  <span className="dr-act">
                    {toggleQueue && (
                      <button type="button" className={`dr-btn small dr-queue-btn${queued.has(e.id) ? " on" : ""}`} aria-pressed={queued.has(e.id)}
                        onClick={() => toggleQueue(e.id)}>{queued.has(e.id) ? "Queued" : "+ Queue"}</button>
                    )}
                    {action(e)}
                  </span>
                  )}
                </td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={9}>Nothing matches.</td></tr>}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function Board({ d, myTeamId }) {
  const n = d.order.length || 1;
  const auto = new Set(d.autopick_teams || []);
  const onClockIndex = d.status === "in_progress" ? d.picks.length : -1;
  const auction = d.draft_type === "auction";
  // Auction: rows are roster spots (G, F, C, TM, Flex, Bench…); the server seats each team's priciest buys first.
  const spots = auction ? slotList(d.roster_slots) : [];
  const bySpot = {}; // team id -> the buy in each spot row
  if (auction) {
    for (const t of d.order) {
      const left = d.picks.filter(p => p.team_id === t.id).sort((x, y) => (y.price ?? 0) - (x.price ?? 0));
      bySpot[t.id] = spots.map(slot => {
        const i = left.findIndex(p => p.slot === slot);
        return i === -1 ? null : left.splice(i, 1)[0];
      });
    }
  }
  return (
    <Panel title="Draft board" fold="board" className="dr-pane dr-pane-board" aside={auction ? "Each team's buys" : d.draft_type === "linear" ? "Same order every round" : d.draft_type === "snake_3rr" ? "Snake · round 3 repeats round 2, then alternates" : "Snake · reverses each round"}>
      <div className="dr-scroll">
        <div className="dr-board" style={{ gridTemplateColumns: `44px repeat(${n}, minmax(140px, 1fr))` }}>
          <div />
          {d.order.map(t => (
            <div key={t.id} className={`dr-board-team${t.id === myTeamId ? " mine" : ""}`}>
              <TeamIcon team={t} size={20} /><span>{t.name}</span>{auto.has(t.id) && <span className="dr-tag">Auto</span>}
            </div>
          ))}
          {Array.from({ length: auction ? spots.length : d.rounds }, (_, r) => (
            <div key={r} style={{ display: "contents" }}>
              <div className="dr-board-round">{auction ? SLOT_LABEL[spots[r]] : `R${r + 1} ${d.round_reversed?.[r] ? "←" : "→"}`}</div>
              {d.order.map((t, c) => {
                const i = r * n + (d.round_reversed?.[r] ? n - 1 - c : c);
                const p = auction ? bySpot[t.id]?.[r] : d.picks[i];
                const mine = t.id === myTeamId;
                if (p) {
                  return (
                    <div key={c} className="dr-cell filled" title={p.auto ? "Picked automatically" : undefined}>
                      <PositionBadge entry={{ kind: p.kind, position: p.position }} size={20} />
                      <span className="dr-cell-name">{shortName(p.name, p.kind)}</span>
                      <span className="dr-cell-no">{p.price != null ? `$${p.price}` : i + 1}</span>
                    </div>
                  );
                }
                if (i === onClockIndex && !auction) {
                  return <div key={c} className={`dr-cell clock${mine ? " mine" : ""}`}><b>On the clock</b><span className="dr-cell-no">{i + 1}</span></div>;
                }
                return <div key={c} className="dr-cell empty"><span className="dr-cell-no">{auction ? "" : i + 1}</span></div>;
              })}
            </div>
          ))}
        </div>
      </div>
    </Panel>
  );
}

function Roster({ team, slots, picks, entities }) {
  const mine = picks.filter(p => p.team_id === team.id);
  const left = [...mine];
  const rows = slotList(slots).map(slot => {
    const i = left.findIndex(p => p.slot === slot);
    return { slot, pick: i === -1 ? null : left.splice(i, 1)[0] };
  });
  return (
    <Panel title="Your roster" fold="roster" className="dr-pane dr-pane-roster" aside={`${mine.length} of ${rows.length} filled`} extra={<TeamIcon team={team} size={20} />} top={team.color}>
      <div className="dr-roster">
        {rows.map(({ slot, pick }, i) => pick ? (
          <div key={i} className="dr-roster-row filled"><EntityRow e={entities[pick.id] || { ...pick, nba_team: null }} />{pick.price != null && <b className="dr-price">${pick.price}</b>}</div>
        ) : (
          <div key={i} className="dr-roster-row empty"><span className="dr-slot">{SLOT_LABEL[slot]}</span><span>Open</span></div>
        ))}
      </div>
    </Panel>
  );
}

// Your draft queue: players you want, in order (draft only, private). Auto-pick takes the first
// one still available that fits your roster. Taken players drop off on their own.
const TOP_ICON = (
  <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
    <path d="M2 2h10M7 12V5M3.5 8.5 7 5l3.5 3.5" stroke="currentColor" strokeWidth="1.7" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
const X_ICON = (
  <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
    <path d="M2.5 2.5l7 7M9.5 2.5l-7 7" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
  </svg>
);

function QueueRow({ i, e, canDraft, fitsNow, onDraft, onTop, onRemove }) {
  const [first, last] = nameLines(e);
  return (
    <div className="dr-queue-row">
      <b className="dr-queue-no">{i + 1}</b>
      <PositionBadge entry={e} size={22} />
      <NbaTeamSquare tricode={e.kind === "nba_team" ? e.id : e.nba_team} size={22} />
      <EntityLink id={e.id} name={<span className="dr-name2"><span>{first}</span><b>{last}</b></span>} />
      <span className="dr-queue-actions">
        {!fitsNow && <span className="dr-tag" title="No open spot on your roster for him right now">No spot</span>}
        {canDraft && fitsNow && <button type="button" className="dr-btn primary tiny" onClick={onDraft}>Draft</button>}
        {onTop && <button type="button" className="dr-icon-btn" title="Move to top" aria-label={`Move ${e.name} to the top`} onClick={onTop}>{TOP_ICON}</button>}
        <button type="button" className="dr-icon-btn" title="Remove from queue" aria-label={`Remove ${e.name} from your queue`} onClick={onRemove}>{X_ICON}</button>
      </span>
    </div>
  );
}

// Your draft queue: players you want, in order (draft only, private). Auto-pick takes the first
// one still available that fits your roster. Taken players drop off on their own.
function Queue({ ids, entities, taken, onChange, canDraft, onDraft, fitsNow, autoNext }) {
  const rows = ids.filter(id => !taken.has(id) && entities[id]);
  const without = id => ids.filter(x => x !== id);
  return (
    <Panel title="Your queue" fold="queue" className="dr-pane dr-pane-queue" aside={rows.length ? `${rows.length} player${rows.length === 1 ? "" : "s"}` : null}>
      {autoNext && (
        <div className="dr-queue-auto">If your clock runs out: <b>{autoNext.name}</b>{rows.includes(autoNext.id) ? " (from your queue)" : " (best available)"}</div>
      )}
      <div className="dr-queue">
        {rows.length === 0 && <div className="dr-queue-empty">Add players with <b>+ Queue</b> in the list. Auto-pick takes the first one that fits your roster.</div>}
        {rows.map((id, i) => (
          <QueueRow key={id} i={i} e={entities[id]} canDraft={canDraft} fitsNow={fitsNow(entities[id])}
            onDraft={() => onDraft(entities[id])}
            onTop={i > 0 ? () => onChange([id, ...without(id)]) : null}
            onRemove={() => onChange(without(id))} />
        ))}
      </div>
    </Panel>
  );
}

// Every pick so far: number, round (auction: price), team, player, who made it, when.
function History({ d, entities, newestFirst = true, pane = true }) {
  const teams = Object.fromEntries(d.order.map(t => [t.id, t]));
  const picks = newestFirst ? [...d.picks].reverse() : d.picks;
  const auction = d.draft_type === "auction";
  return (
    <Panel title="Pick history" fold={pane ? "history" : undefined} className={pane ? "dr-pane dr-pane-history" : ""} aside={`${d.picks.length} of ${d.total_picks} picks`}>
      <div className="dr-history">
        {picks.length === 0 && <div className="dr-history-row"><span>No picks yet.</span></div>}
        {picks.map(p => {
          const t = teams[p.team_id];
          return (
            <div key={p.pick} className="dr-history-row">
              <span className="dr-history-no"><b>#{p.pick}</b><span>{auction ? `$${p.price ?? "—"}` : `R${p.round}`}</span></span>
              <span className="dr-history-team">{t && <TeamIcon team={t} size={22} />}<span>{p.team_name}</span></span>
              <EntityRow e={entities[p.id] || { ...p, nba_team: null }} />
              <span className="dr-history-meta">
                {p.by !== "owner" && <span className="dr-tag">{p.by === "auto" ? "auto" : "commissioner"}</span>}
                {p.picked_at && <span>{new Date(p.picked_at).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit", second: "2-digit" })}</span>}
              </span>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

function Facts({ rows }) {
  return <div className="dr-facts">{rows.map(([a, b]) => <div key={a}><span>{a}</span><b>{b}</b></div>)}</div>;
}

// More than a day out: days / hrs / min. Under a day: hrs / min / sec.
function Countdown({ ms }) {
  const s = Math.max(0, Math.floor(ms / 1000));
  const days = Math.floor(s / 86400);
  const parts = days > 0
    ? [[days, "days"], [Math.floor(s / 3600) % 24, "hrs"], [Math.floor(s / 60) % 60, "min"]]
    : [[Math.floor(s / 3600), "hrs"], [Math.floor(s / 60) % 60, "min"], [s % 60, "sec"]];
  return (
    <div className="dr-countdown">
      {parts.map(([v, u], i) => (
        <div key={u}><LedClock text={i === 0 && u === "days" ? String(v) : String(v).padStart(2, "0")} step={3.4} r={1.4} label={`${v} ${u}`} /><span>{u}</span></div>
      ))}
    </div>
  );
}

function StartsIn({ when, skew }) {
  const now = useNow(1000);
  return <Countdown ms={when - (now + skew)} />;
}

// "R1–3 30 sec · R4+ 1 min": the snake pick clock by round, from pick_seconds_by_round (blank rounds = pick_seconds).
function roundClocks(d) {
  const by = d.pick_seconds_by_round || [];
  if (!by.some(v => v != null)) return minutes(d.pick_seconds);
  const sec = r => by[r] ?? d.pick_seconds;
  const parts = [];
  for (let r = 0; r < d.rounds;) {
    let e = r;
    while (e + 1 < d.rounds && sec(e + 1) === sec(r)) e++;
    const label = e === d.rounds - 1 && e > r ? `R${r + 1}+` : e > r ? `R${r + 1}–${e + 1}` : `R${r + 1}`;
    parts.push(`${label} ${minutes(sec(r))}`);
    r = e + 1;
  }
  return parts.join(" · ");
}

function PreDraft({ d, isAdmin, skew, busy, post }) {
  const when = d.draft_start_at ? new Date(d.draft_start_at) : null;
  const local = when && when.toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  const zone = when && (when.toLocaleTimeString(undefined, { timeZoneName: "short" }).split(" ").pop());
  const utc = when && `${when.toLocaleString("en-US", { timeZone: "UTC", weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hourCycle: "h23" })} UTC`;
  const auction = d.draft_type === "auction";
  const details = [
    ["Type", TYPE_NAMES[d.draft_type]], ["Teams", String(d.order.length)], ["Rounds", String(d.rounds)],
    ...(auction ? [["Budget", `$${d.auction?.budget ?? "—"}`], ["Minimum bid", `$${d.auction?.min_bid ?? "—"}`], ["Bid clock", `${d.auction?.bid_seconds ?? "—"} s`]]
      : [["Pick clock", roundClocks(d)]]),
    ["Clock runs out", auction ? "Auto-nominate" : "Auto-pick"],
  ];
  const rules = SLOT_ORDER.map(k => [RULE_NAMES[k], String(d.roster_slots[k] || 0)]);
  return (
    <>
      {isAdmin && (
        <Commish text={d.start_enabled ? null : "Starting the draft is switched off for this league."}>
          <button type="button" className="dr-btn primary" disabled={busy || !d.start_enabled} onClick={() => post("/admin/draft/start")}>Start now</button>
          <button type="button" className="dr-btn" disabled={busy} onClick={() => post("/admin/draft/randomize")}>Randomize order</button>
          <Link className="dr-btn" to={`${base()}/league-settings#draft`}>Draft settings →</Link>
          {d.picks.length > 0 && <button type="button" className="dr-btn" disabled={busy} onClick={() => window.confirm("Reset the draft? Every roster in this league is cleared.") && post("/admin/draft/reset")}>Reset</button>}
        </Commish>
      )}
      <section className="dr-when" aria-label="Draft starts">
        <div className="dr-when-main">
          <span className="dr-h2">Draft starts</span>
          {when ? (
            <>
              <span className="dr-when-time">{local}</span>
              <span><b>{zone}</b> · shown in your time zone</span>
              <span>{utc}</span>
            </>
          ) : (
            <>
              <span className="dr-when-time">Not scheduled yet</span>
              <span>{isAdmin ? "Press Start now, or set a time in League settings → Draft." : "The commissioner will start the draft."}</span>
            </>
          )}
        </div>
        {when && (
          <div className="dr-when-count"><span>Starts in · same for everyone</span><StartsIn when={when} skew={skew} /></div>
        )}
      </section>
      <div className="dr-pre-grid">
        <Panel title="Draft order" aside={`${d.order.length} teams`}>
          <div className="dr-order">
            {d.order.map((t, i) => (
              <div key={t.id} className="dr-order-row">
                <b>{i + 1}</b><TeamIcon team={t} size={28} /><span>{t.name}</span>
              </div>
            ))}
            {d.order.length === 0 && <div className="dr-order-row"><span>No teams yet.</span></div>}
          </div>
        </Panel>
        <div className="dr-stack">
          <Panel title="Draft details"><Facts rows={details} /></Panel>
          <Panel title="Roster rules"><Facts rows={rules} /></Panel>
        </div>
      </div>
    </>
  );
}

// Draft complete: every team's picks (yours first), a quiet "auto" note per pick, grades to come,
// and the pick-by-pick history tucked away until someone wants it.
function Complete({ d, myTeamId, entities, isAdmin, busy, post }) {
  const [showHistory, setShowHistory] = useState(false);
  const done = d.picks.length ? d.picks[d.picks.length - 1].picked_at : null;
  const teams = [...d.order].sort((a, b) => (b.id === myTeamId) - (a.id === myTeamId));
  // Auction: rows are roster spots, each team's buys seated priciest first (as on the live board); snake: rounds.
  const auction = d.draft_type === "auction";
  const spots = auction ? slotList(d.roster_slots) : [];
  const cell = (t, r) => {
    if (!auction) return d.picks.filter(x => x.team_id === t.id)[r];
    const left = d.picks.filter(p => p.team_id === t.id).sort((x, y) => (y.price ?? 0) - (x.price ?? 0));
    const seated = spots.map(slot => { const i = left.findIndex(p => p.slot === slot); return i === -1 ? null : left.splice(i, 1)[0]; });
    return seated[r];
  };
  return (
    <>
      {/* One header row: status, the commissioner's Reset, My team. */}
      <section className="dr-done">
        <b>Draft complete</b>
        {done && <span>{new Date(done).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}</span>}
        <span className="dr-done-actions">
          {isAdmin && (
            <button type="button" className="dr-btn" disabled={busy} title="Commissioner"
              onClick={() => window.confirm("Reset the draft? Every roster in this league is cleared.") && post("/admin/draft/reset")}>Reset draft</button>
          )}
          {myTeamId && <Link className="dr-btn primary" to={`${base()}/team`}>My team →</Link>}
        </span>
      </section>
      {/* Board: round gutter on the left, one column per team (yours first, lighter), solid team-color headers. */}
      <div className="dr-results" style={{ gridTemplateColumns: `44px repeat(${teams.length}, minmax(200px, 1fr))` }}>
        <div />
        {teams.map(t => (
          <div key={t.id} className="dr-results-head" style={{ background: t.color, color: inkOn(t.color) }}>
            <span className="dr-results-icon"><TeamIcon team={t} size={28} /></span>
            <b>{t.name}</b>
          </div>
        ))}
        {Array.from({ length: auction ? spots.length : d.rounds }, (_, r) => (
          <div key={r} style={{ display: "contents" }}>
            <div className="dr-results-round">{auction ? SLOT_LABEL[spots[r]] : `R${r + 1}`}</div>
            {teams.map(t => {
              const p = cell(t, r);
              const e = p && (entities[p.id] || { ...p, nba_team: null });
              const [first, last] = e ? nameLines(e) : ["", ""];
              return (
                <div key={t.id} className={`dr-results-cell${t.id === myTeamId ? " mine" : ""}`}>
                  {e && (
                    <>
                      {e.kind === "player"
                        ? <Headshot playerId={e.id} tricode={e.nba_team} width={50} height={37} />
                        : <span className="dr-results-logo"><NbaTeamSquare tricode={e.id} size={30} /></span>}
                      <EntityLink id={e.id} name={<span className="dr-name2"><span>{first}</span><b>{last}</b></span>} />
                      <span className="dr-results-no">{e.kind === "nba_team" ? "TM" : e.position || "—"} · {p.price != null ? `$${p.price}` : `#${p.pick}`}</span>
                      {p.auto && <i className="dr-results-auto">auto</i>}
                    </>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>
      <section className="dr-uc" aria-label="Draft grades">
        <span className="dr-h2">Draft grades</span>
        <span>How every team's draft held up — graded at the end of the season.</span>
        <span className="dr-uc-tag">Under construction</span>
      </section>
      <div>
        <button type="button" className="dr-btn" onClick={() => setShowHistory(v => !v)} aria-expanded={showHistory}>
          {showHistory ? "Hide pick-by-pick" : "Show pick-by-pick"}
        </button>
      </div>
      {showHistory && <History d={d} entities={entities} newestFirst={false} pane={false} />}
    </>
  );
}

// Three pages share this component (page prop): "lobby" = /draft (before the start: info + Enter draft room),
// "room" = /draft/room (open before the start for the queue, and during the draft), "results" = /draft/results.
// Each redirects to the right one for the draft's state, so the sidebar's Draft link always lands right.
export default function DraftRoom({ page = "lobby" }) {
  const user = useCurrentUser();
  const [scenario] = useFantasyScenario();
  const players = useFantasyApi("players");
  const nbaTeams = useFantasyApi("nba-teams");
  const [d, setD] = useState(undefined);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [skew, setSkew] = useState(0);
  const [filter, setFilter] = useState("All");
  const [own, setOwn] = useState("available"); // Available / Drafted / All
  const [view, setView] = useState("proj");
  const [boardData, setBoardData] = useState({ key: null, data: null });
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState("available");
  const [actAs, setActAs] = useState("");
  const [opening, setOpening] = useState(null);
  const [custom, setCustom] = useState("");
  const [queue, setQueue] = useState([]);

  // Clocks: the server's clock is the official one. `skew` = how far the server's clock is from this browser's,
  // measured on the fastest round trip seen (least distorted by lag); every countdown is deadline − (now + skew),
  // so all screens show the same second and a slow reply never shifts it. A reply that changes nothing
  // (only server_time differs) doesn't touch the page.
  const best = useRef({ rtt: Infinity, key: null });
  const apply = useCallback((state, sentAt) => {
    const got = Date.now();
    const key = JSON.stringify({ ...state, server_time: null });
    if (key !== best.current.key) {
      best.current.key = key;
      setD(state);
    }
    const rtt = sentAt ? got - sentAt : Infinity;
    if (rtt < best.current.rtt) {
      best.current.rtt = rtt;
      setSkew(Date.parse(state.server_time) - (sentAt + rtt / 2));
    }
  }, []);
  const load = useCallback(() => {
    const sentAt = Date.now();
    return fetch(`${API}${API_BASE}/draft?scenario=${scenario}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : Promise.reject()))
      .then(state => apply(state, sentAt))
      .catch(() => setD(null));
  }, [scenario, apply]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!user) return;
    fetch(`${API}${API_BASE}/draft/queue?scenario=${scenario}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null)
      .then(q => { if (q) setQueue(q.entity_ids); });
  }, [user, scenario]);
  const saveQueue = useCallback(async ids => {
    setQueue(ids); // show it right away; the server keeps the saved copy
    const r = await fetch(`${API}${API_BASE}/draft/queue?scenario=${scenario}`, {
      method: "PUT", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ entity_ids: ids }),
    });
    const out = await r.json().catch(() => ({}));
    if (r.ok) setQueue(out.entity_ids); else setError(out.detail || "Couldn't save your queue");
  }, [scenario]);
  // Polling: during the draft every 1.5 s (auction) / 4 s (snake); before it every 3 s, so when the commissioner
  // starts it (or the scheduled time passes — the server starts it on the next read) everyone moves into the room.
  useEffect(() => {
    if (d?.status === "complete") return undefined;
    const ms = d?.status === "in_progress" ? (d?.draft_type === "auction" ? 1500 : POLL_MS) : 3000;
    const poll = setInterval(load, ms);
    return () => clearInterval(poll);
  }, [d?.status, d?.draft_type, load]);

  const post = async (path, body) => {
    setBusy(true); setError(null);
    try {
      const sentAt = Date.now();
      const r = await fetch(`${API}${API_BASE}${path}?scenario=${scenario}`, {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}),
      });
      const out = await r.json();
      if (!r.ok) setError(out.detail || "Something went wrong"); else apply(out, sentAt);
    } finally {
      setBusy(false);
    }
  };

  const entities = useMemo(() => {
    const out = {};
    for (const p of players || []) out[p.id] = { ...p, kind: "player" };
    for (const t of nbaTeams || []) out[t.id] = { ...t, kind: "nba_team", nba_team: t.id };
    return out;
  }, [players, nbaTeams]);

  // The list's numbers for the chosen view (/players/board). Projected order = the server's rank_values, i.e.
  // what auto-pick goes by (NBA teams included); a past season sorts by its MAX.
  const boardKey = `${view}|${scenario}`;
  useEffect(() => {
    let live = true;
    fetch(`${API}${API_BASE}/players/board?view=${view}&scenario=${scenario}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null)
      .then(data => { if (live) setBoardData({ key: boardKey, data }); });
    return () => { live = false; };
  }, [boardKey, view, scenario]);
  const board = boardData.key === boardKey ? boardData.data?.players || null : null;
  useEffect(() => () => setCardActions(null), []);
  const rankValues = d?.rank_values || null;
  const pool = useMemo(() => {
    const taken = new Set((d?.picks || []).map(p => p.id));
    const lotId = d?.auction?.lot?.entity_id;
    const q = search.trim().toLowerCase();
    const sortVal = e => (board ? (view === "proj" ? e.v?.max : e.v?.total) : view === "proj" && rankValues ? rankValues[e.id] : null) ?? -Infinity;
    // The player on the block stays in the list, pinned first; drafted players show with the Drafted / All filter.
    return Object.values(entities)
      .filter(e => e.in_pool !== false && (e.id === lotId || (own === "all" ? true : own === "drafted" ? taken.has(e.id) : !taken.has(e.id))))
      .filter(e => filter === "All" || (filter === "TM" ? e.kind === "nba_team" : e.kind === "player" && (e.position || "").includes(filter)))
      .filter(e => !q || e.name.toLowerCase().includes(q) || (e.nba_team || "").toLowerCase() === q)
      .map(e => ({ ...e, v: board?.[e.id] || (view === "proj" && rankValues?.[e.id] != null ? { max: rankValues[e.id] } : null) }))
      // With the server's numbers, its rank is the order (ties included); otherwise the value.
      .sort((a, b) => (b.id === lotId) - (a.id === lotId) || (board ? (a.v?.rank ?? Infinity) - (b.v?.rank ?? Infinity) : sortVal(b) - sortVal(a)))
      .slice(0, 250);
  }, [entities, d, filter, own, search, rankValues, board, view]);
  const pickOf = useMemo(() => Object.fromEntries((d?.picks || []).map(p => [p.id, p])), [d]);
  const poolProps = { items: pool, view, setView, filter, setFilter, own, setOwn, search, setSearch, queued: null, auction: d?.draft_type === "auction",
    recBids: d?.my_rec_bids, pickOf, lotId: d?.auction?.lot?.entity_id };

  if (d === undefined) return <FantasyShell title="Draft"><p style={{ fontSize: 13 }}>Loading…</p></FantasyShell>;
  if (d === null) return <FantasyShell title="Draft"><p style={{ fontSize: 13 }}>Couldn't load the draft.</p></FantasyShell>;

  const isAdmin = !!user?.isAdmin;
  const isAuction = d.draft_type === "auction";
  const n = d.order.length || 1;
  const myTeam = d.order.find(t => user && t.owner_user_id === user.discordId) || null;
  // Time left, capped at the clock's full length: network delay can make the raw value a few ms
  // over (e.g. 5:00.03), which would round up to 5:01.
  const fullClock = !d.deadline ? 0 : isAuction
    ? (d.auction?.lot ? d.auction.bid_seconds : d.auction?.nomination_seconds) * 1000
    : (d.pick_seconds_by_round?.[Math.floor(d.picks.length / n)] ?? d.pick_seconds) * 1000;
  const autoSet = new Set(d.autopick_teams || []);
  const taken = new Set(d.picks.map(p => p.id));
  const queued = new Set(queue);
  const toggleQueue = myTeam ? id => saveQueue(queued.has(id) ? queue.filter(x => x !== id) : [...queue, id]) : null;
  // Before the draft: the pick button shows but stays off; only + Queue works.
  const preAction = () => <button type="button" className="dr-btn small" disabled title="Opens when the draft starts">{isAuction ? "Nominate" : "Draft"}</button>;
  // The player card's header gets the same buttons as the row (+ Queue, then the pick button).
  const cardButtons = act => e => (
    <>
      {toggleQueue && <button type="button" className={`dr-btn small dr-queue-btn${queued.has(e.id) ? " on" : ""}`} onClick={() => toggleQueue(e.id)}>{queued.has(e.id) ? "Queued" : "+ Queue"}</button>}
      {act(e)}
    </>
  );
  const queuePanel = ({ canDraft = false, onDraft = () => {}, fitTeam = myTeam?.id } = {}) => myTeam && (
    <Queue ids={queue} entities={entities} taken={taken} onChange={saveQueue} autoNext={d.my_auto_next}
      canDraft={canDraft} onDraft={onDraft} fitsNow={e => fits(e, fitTeam, d.picks, d.roster_slots)} />
  );
  const sub = isAuction
    ? `Auction · ${d.order.length} teams · $${d.auction?.budget} budget · $${d.auction?.min_bid} minimum · ${d.auction?.bid_seconds}s bid clock`
    : `${TYPE_NAMES[d.draft_type]} · ${d.order.length} teams · ${d.rounds} rounds · pick clock ${roundClocks(d)}`;
  const testLabel = scenario === "replay" ? " · 2025-26 test league" : scenario.startsWith("test_") ? ` · sandbox ${scenario}` : "";

  const shell = body => (
    <FantasyShell title="Draft">
      <p className="dr-sub">{sub}{testLabel}</p>
      {error && <div className="dr-error" role="alert">{error}</div>}
      <div className="dr">{body}</div>
    </FantasyShell>
  );

  if (page === "results" && d.status !== "complete") return <Navigate to={`${base()}/draft`} replace />;
  if (page !== "results" && d.status === "complete") return <Navigate to={`${base()}/draft/results`} replace />;
  if (page === "lobby" && d.status === "in_progress") return <Navigate to={`${base()}/draft/room`} replace />;
  if (d.status === "not_started" && page === "lobby") {
    setCardActions(null);
    return shell(
      <>
        <PreDraft d={d} isAdmin={isAdmin} skew={skew} busy={busy} post={post} />
        <div className="dr-enter"><Link className="dr-btn primary" to={`${base()}/draft/room`}>Enter draft room →</Link></div>
      </>
    );
  }
  if (d.status === "not_started") {
    // The room before the start: browse, open player cards, build the queue. Picks stay off.
    setCardActions(cardButtons(preAction));
    const when = d.draft_start_at
      ? new Date(d.draft_start_at).toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })
      : "not scheduled yet";
    return shell(
      <>
        <section className="dr-waitbar"><b>The draft hasn't started</b><span>Starts {when}</span><Link to={`${base()}/draft`}>Draft info</Link></section>
        <Board d={d} myTeamId={myTeam?.id} />
        <div className="dr-main-grid">
          <Pool {...poolProps} action={preAction} queued={queued} toggleQueue={toggleQueue} />
          <div className="dr-stack">
            {queuePanel()}
            {myTeam && <Roster team={myTeam} slots={d.roster_slots} picks={d.picks} entities={entities} />}
          </div>
        </div>
      </>
    );
  }
  if (d.status === "complete") setCardActions(null);
  if (d.status === "complete") return shell(<Complete d={d} myTeamId={myTeam?.id} entities={entities} isAdmin={isAdmin} scenario={scenario} busy={busy} post={post} />);

  const tabs = (
    <div className="dr-tabs">
      <Seg full value={tab} onChange={setTab}
        options={[["available", "Available"], ...(myTeam ? [["queue", "Queue"]] : []), ["board", "Board"], ...(isAuction ? [["budgets", "Budgets"]] : []), ["roster", "Roster"], ["history", "History"]]} />
    </div>
  );
  const roster = myTeam && <Roster team={myTeam} slots={d.roster_slots} picks={d.picks} entities={entities} />;

  // ---------------- Snake / linear ----------------
  if (!isAuction) {
    const onClock = d.on_clock;
    const mine = !!(onClock && myTeam && onClock.id === myTeam.id);
    const round = d.pick_number ? Math.ceil(d.pick_number / n) : 1;
    const untilMine = (() => {
      if (!myTeam || mine) return null;
      for (let i = d.picks.length; i < d.total_picks; i++) {
        const r = Math.floor(i / n), pos = i % n;
        const t = d.order[d.round_reversed?.[r] ? n - 1 - pos : pos];
        if (t?.id === myTeam.id) return i - d.picks.length;
      }
      return null;
    })();
    const action = e => {
      if (onClock && !fits(e, onClock.id, d.picks, d.roster_slots)) return <button type="button" className="dr-btn small" disabled title={`No open spot for this on ${onClock.name}'s roster`}>No spot</button>;
      if (mine) return <button type="button" className="dr-btn primary small" disabled={busy} onClick={() => post("/draft/pick", { entity_id: e.id })}>Draft</button>;
      if (isAdmin && onClock) return <button type="button" className="dr-btn small" disabled={busy} onClick={() => post("/draft/pick", { entity_id: e.id })}>Pick for {onClock.name}</button>;
      return null;
    };
    setCardActions(cardButtons(action));
    return shell(
      <div className={`dr-live tab-${tab}`}>
        <UrgentGlow on={mine} deadline={d.deadline} skew={skew} />
        {onClock && (
          <ClockBar team={onClock} mine={mine} deadline={d.deadline} skew={skew} cap={fullClock}
            title={mine ? "You're up" : `${onClock.name} is up`}
            sub={`${mine ? `${onClock.name} · ` : ""}round ${round}, pick ${d.pick_number} of ${d.total_picks}${untilMine ? ` · you pick in ${untilMine}` : ""} · pick timer this round: ${minutes(fullClock / 1000)}`} />
        )}
        <MyAuto team={myTeam} autoNext={d.my_auto_next} queuedIds={queue} />
        {isAdmin && onClock && (
          <Commish>
            <button type="button" className="dr-btn" disabled={busy} onClick={() => post("/admin/draft/autopick")}>Auto-pick now</button>
            <Switch on={autoSet.has(onClock.id)} disabled={busy} label={`Autopick ${onClock.name}`}
              onChange={on => post("/admin/draft/autopick-team", { team_id: onClock.id, on })} />
            <button type="button" className="dr-btn" disabled={busy} onClick={() => window.confirm("Reset the draft? Every roster in this league is cleared.") && post("/admin/draft/reset")}>Reset</button>
          </Commish>
        )}
        {tabs}
        <Board d={d} myTeamId={myTeam?.id} />
        <div className="dr-main-grid">
          <Pool {...poolProps} action={action} queued={queued} toggleQueue={toggleQueue} />
          <div className="dr-stack">
            {queuePanel({ canDraft: mine && !busy, onDraft: e => post("/draft/pick", { entity_id: e.id }) })}
            {roster}
            <History d={d} entities={entities} />
          </div>
        </div>
      </div>
    );
  }

  // ---------------- Auction ----------------
  const a = d.auction;
  const lot = a.lot;
  const nominator = a.phase === "nominating" ? d.on_clock : null;
  const actingId = isAdmin ? (actAs || myTeam?.id || d.order[0]?.id) : myTeam?.id;
  const acting = d.order.find(t => t.id === actingId);
  const b = a.budgets.find(x => x.team_id === actingId);
  const canNominate = !!nominator && (isAdmin || nominator.owner_user_id === user?.discordId);
  const nomBudget = nominator && a.budgets.find(x => x.team_id === nominator.id);
  const openBid = Math.min(Math.max(opening ?? a.min_bid, a.min_bid), nomBudget?.max_bid ?? a.min_bid);
  const mineUp = !!(nominator && myTeam && nominator.id === myTeam.id);
  const highIsActing = lot && lot.high_team === actingId;
  const canBid = lot && b && b.can_bid && !highIsActing;
  // The smallest legal bid (high bid + the league's minimum raise, from the server), and two raises over it.
  const next = lot ? (lot.min_next ?? lot.high_bid + 1) : 0;
  const next2 = lot ? next + Math.max(1, next - lot.high_bid) : 0;
  const customAmount = Number(custom) || 0;
  const bid = amount => post("/draft/bid", { amount, team_id: actingId });
  const lotEntity = lot && (entities[lot.entity_id] || { id: lot.entity_id, kind: lot.kind, name: lot.name, position: lot.position });

  const action = e => {
    if (lot) return <button type="button" className="dr-btn small" disabled>Nominate</button>;
    if (canNominate && !fits(e, nominator.id, d.picks, d.roster_slots)) return <button type="button" className="dr-btn small" disabled title={`No open spot for this on ${nominator.name}'s roster`}>No spot</button>;
    if (canNominate) return <button type="button" className="dr-btn primary small" disabled={busy} onClick={() => post("/draft/nominate", { entity_id: e.id, amount: openBid, team_id: nominator.id })}>Nominate · ${openBid}</button>;
    return null;
  };
  const budgetSection = b && (
    <section className="dr-budget" aria-label="Budget">
      <span className="dr-h2 dr-budget-title">{acting && <TeamIcon team={acting} size={20} />}{acting && acting.id !== myTeam?.id ? `${acting.name}'s budget` : "Your budget"}</span>
      <div><span>Budget left</span><b>${b.remaining} of ${a.budget}</b></div>
      <div><span>Open spots</span><b>{b.open_spots}</b></div>
      <div><span>Safe max bid</span><b>${b.safe_max}</b></div>
      <div><span>Most you can bid</span><b>${b.max_bid}</b></div>
      <span className="dr-budget-note">Safe max keeps ${a.min_bid} for each other open spot</span>
    </section>
  );
  const budgets = (
    <Panel title="Budgets" fold="budgets" className="dr-pane dr-pane-budgets" aside={`$${a.budget} each`}>
      <table className="dr-table dr-budgets">
        <thead><tr><th /><th>Team</th><th className="num">Left</th><th className="num">Open</th><th className="num" title={`Keeps $${a.min_bid} for each other open spot`}>Safe max</th></tr></thead>
        <tbody>
          {a.budgets.map(x => {
            const t = d.order.find(o => o.id === x.team_id);
            return (
              <tr key={x.team_id} className={x.team_id === myTeam?.id ? "mine" : ""}>
                <td>{t && <TeamIcon team={t} size={22} />}</td><td><b>{x.team_name}</b></td>
                <td className="num"><b>${x.remaining}</b></td><td className="num">{x.open_spots}</td><td className="num">${x.safe_max}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Panel>
  );
  const opener = canNominate && !lot && (
    <div className="dr-opening">
      <span>Opening bid</span>
      <span className="dr-stepper">
        <button type="button" onClick={() => setOpening(Math.max(a.min_bid, openBid - 1))}>−</button>
        <b>${openBid}</b>
        <button type="button" onClick={() => setOpening(Math.min(nomBudget?.max_bid ?? openBid, openBid + 1))}>+</button>
      </span>
    </div>
  );

  setCardActions(cardButtons(action));
  return shell(
    <div className={`dr-live tab-${tab}`}>
      <UrgentGlow on={!lot && mineUp} deadline={d.deadline} skew={skew} />
      {lot ? (
        <section className="dr-lot" aria-label="On the block">
          <div className="dr-lot-who">
            <PositionBadge entry={lotEntity} size={38} />
            <NbaTeamSquare tricode={lotEntity.kind === "nba_team" ? lotEntity.id : lotEntity.nba_team} size={38} />
            <div>
              <span className="dr-small">On the block · nominated by {lot.nominated_by_name}</span>
              <EntityLink id={lotEntity.id} style={{ color: "inherit", textDecoration: "none" }}
                name={<><span className="dr-lot-first">{nameLines(lotEntity)[0]}</span><b className="dr-lot-name">{nameLines(lotEntity)[1]}</b></>} />
              {(() => {
                const v = rankValues ? rankValues[lotEntity.id] : lotEntity.fantasy_points;
                const gp = rankValues ? d.rank_games?.[lotEntity.id] : lotEntity.games_played;
                if (v == null) return null;
                return d.rank_kind === "proj"
                  ? <span className="dr-small">PROJ MAX <i>{Number(v).toFixed(1)}</i></span>
                  : <span className="dr-small">{Number(v).toFixed(1)} pts / game{gp ? ` · ${gp} GP` : ""} ({d.rank_season || "last season"})</span>;
              })()}
            </div>
          </div>
          <div className="dr-lot-high">
            <span className="dr-small">High bid</span>
            <span className="dr-lot-bid">${lot.high_bid}</span>
            <span className="dr-lot-team">{(() => { const t = d.order.find(o => o.id === lot.high_team); return t && <TeamIcon team={t} size={20} />; })()}<b>{lot.high_team_name}</b></span>
            {lot.my_rec != null && <span className="dr-lot-rec">Your Rec bid <b>${lot.my_rec}</b> · {lot.my_call === "winning" ? "you're winning" : lot.my_call}</span>}
          </div>
          <div className="dr-lot-clock"><TimeLeft deadline={d.deadline} skew={skew} cap={fullClock}>{ms => <LedClock text={mmss(ms)} urgent={ms < 60000} step={4} r={1.6} />}</TimeLeft><span className="dr-small">resets to 0:{String(a.bid_seconds).padStart(2, "0")} on a bid</span></div>
        </section>
      ) : nominator && (
        <ClockBar team={nominator} mine={mineUp} deadline={d.deadline} skew={skew} cap={fullClock}
          title={mineUp ? "Your turn to nominate" : `${nominator.name} is nominating`}
          sub={`Lot ${d.picks.length + 1} of ${d.total_picks}`} />
      )}
      {lot && b && (
        <section className="dr-bidbar" aria-label="Bid">
          {highIsActing ? <b>{acting?.id === myTeam?.id ? "You're" : `${acting?.name} is`} the high bidder</b> : (
            <>
              {/* Only bids this team can afford: anything over its max isn't offered at all. */}
              {canBid && next <= b.max_bid ? (
                <>
                  <button type="button" className="dr-btn primary" disabled={busy} onClick={() => bid(next)}>Bid ${next}</button>
                  {next2 <= b.max_bid && next2 !== b.max_bid && <button type="button" className="dr-btn" disabled={busy} onClick={() => bid(next2)}>Bid ${next2}</button>}
                  <input className="dr-amount" type="number" min={next} max={b.max_bid} placeholder="$ amount" value={custom} onChange={e => setCustom(e.target.value)} />
                  <button type="button" className="dr-btn" disabled={busy || customAmount < next || customAmount > b.max_bid} onClick={() => { bid(customAmount); setCustom(""); }}>Bid</button>
                  {b.max_bid !== next && <button type="button" className="dr-btn" disabled={busy} onClick={() => bid(b.max_bid)}>All in · ${b.max_bid}</button>}
                </>
              ) : (
                <b>{!b.open_spots ? "Roster full" : `${acting?.id === myTeam?.id ? "You have" : `${acting?.name} has`} $${b.remaining} left — can't top $${lot.high_bid}`}</b>
              )}
            </>
          )}
        </section>
      )}
      {budgetSection}
      {!lot && <MyAuto team={myTeam} autoNext={d.my_auto_next} queuedIds={queue} />}
      {isAdmin && (
        <Commish>
          <label className="dr-actas">Acting as
            <select value={actingId || ""} onChange={e => setActAs(e.target.value)}>
              {d.order.map(t => <option key={t.id} value={t.id}>{t.name}{t.id === myTeam?.id ? " (you)" : ""}</option>)}
            </select>
          </label>
          <button type="button" className="dr-btn" disabled={busy} onClick={() => post("/admin/draft/autopick")}>{lot ? "Close bidding now" : "Auto-nominate now"}</button>
          {nominator && !lot && (
            <Switch on={autoSet.has(nominator.id)} disabled={busy} label={`Autopick ${nominator.name}`}
              onChange={on => post("/admin/draft/autopick-team", { team_id: nominator.id, on })} />
          )}
          <button type="button" className="dr-btn" disabled={busy} onClick={() => window.confirm("Reset the draft? Every roster in this league is cleared.") && post("/admin/draft/reset")}>Reset</button>
        </Commish>
      )}
      {tabs}
      <Board d={d} myTeamId={myTeam?.id} />
      <div className="dr-main-grid">
        <Pool {...poolProps} action={action} before={opener} aside={lot ? `Nominating opens when this lot sells` : null} queued={queued} toggleQueue={toggleQueue} />
        <div className="dr-stack">
          {queuePanel({ canDraft: canNominate && !lot && mineUp && !busy, onDraft: e => post("/draft/nominate", { entity_id: e.id, amount: openBid, team_id: nominator.id }) })}
          {budgets}
          {roster}
          <History d={d} entities={entities} />
        </div>
      </div>
    </div>
  );
}
