import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import LedClock from "../../components/fantasy/LedClock";
import { NbaTeamSquare, PositionBadge } from "../../components/fantasy/RosterBits";
import { nameLines } from "../../components/fantasy/nbaTeams";
import { EntityLink } from "../../components/fantasy/links";
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

const mmss = ms => {
  const s = Math.max(0, Math.ceil(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};
const minutes = s => (s % 60 ? `${Math.round(s / 6) / 10} min` : `${s / 60} min`);
const shortName = (name, kind) => {
  if (kind === "nba_team") return nameLines({ kind, id: "", name })[1] || name;
  const i = (name || "").indexOf(" ");
  return i === -1 ? name : `${name[0]}. ${name.slice(i + 1)}`;
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

function Panel({ title, aside, extra, top, className = "", children }) {
  return (
    <section className={`dr-panel ${className}`} aria-label={title} style={top ? { borderTop: `3px solid ${top}` } : undefined}>
      <div className="dr-panel-head"><span className="dr-h2">{title}</span>{extra}{aside != null && <span className="dr-aside">{aside}</span>}</div>
      {children}
    </section>
  );
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

function ClockBar({ team, mine, title, sub, ms }) {
  return (
    <section className={`dr-clockbar${mine ? " mine" : ""}`} aria-label="On the clock">
      <div className="dr-clockbar-who">
        {team && <TeamIcon team={team} size={48} />}
        <div><b>{title}</b><span>{sub}</span></div>
      </div>
      <div className="dr-clockbar-led"><LedClock text={mmss(ms)} urgent={ms < 60000} /></div>
    </section>
  );
}

function EntityRow({ e }) {
  const [first, last] = nameLines(e);
  return (
    <span className="dr-entity">
      <PositionBadge entry={e} size={30} />
      <NbaTeamSquare tricode={e.kind === "nba_team" ? e.id : e.nba_team} size={30} />
      <EntityLink id={e.id} name={<span className="dr-name2"><span>{first}</span><b>{last}</b></span>} />
    </span>
  );
}

function Pool({ items, filter, setFilter, search, setSearch, action, aside, before, valueSeason }) {
  return (
    <Panel title="Available" className="dr-pane dr-pane-available" aside={aside}
      extra={<><Seg options={FILTERS} value={filter} onChange={setFilter} /><input className="dr-search" placeholder="Search players and teams" value={search} onChange={e => setSearch(e.target.value)} /></>}>
      {before}
      <div className="dr-scroll">
        <table className="dr-table">
          <thead><tr><th className="rk">Rk</th><th>Player / team</th><th className="num" title={`${valueSeason} per game; NBA teams: average point margin. Auto-pick ranks by this.`}>Pts / game ({valueSeason})</th><th className="num gp" title={`Games played in ${valueSeason}`}>GP</th><th className="act" /></tr></thead>
          <tbody>
            {items.map((e, i) => (
              <tr key={e.id}>
                <td className="rk">{i + 1}</td>
                <td><EntityRow e={e} /></td>
                <td className="num pts">{e.value == null ? "—" : `${e.kind === "nba_team" && e.value > 0 ? "+" : ""}${Number(e.value).toFixed(1)}`}</td>
                <td className="num gp">{e.gp ?? "—"}</td>
                <td className="act">{action(e)}</td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={5}>Nothing matches.</td></tr>}
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
  const byTeam = {}; // auction: each team's buys in order (no pick order to follow)
  for (const p of d.picks) (byTeam[p.team_id] ||= []).push(p);
  return (
    <Panel title="Draft board" className="dr-pane dr-pane-board" aside={auction ? "Each team's buys" : d.draft_type === "linear" ? "Same order every round" : "Snake · reverses each round"}>
      <div className="dr-scroll">
        <div className="dr-board" style={{ gridTemplateColumns: `44px repeat(${n}, minmax(140px, 1fr))` }}>
          <div />
          {d.order.map(t => (
            <div key={t.id} className={`dr-board-team${t.id === myTeamId ? " mine" : ""}`}>
              <TeamIcon team={t} size={20} /><span>{t.name}</span>{auto.has(t.id) && <span className="dr-tag">Auto</span>}
            </div>
          ))}
          {Array.from({ length: d.rounds }, (_, r) => (
            <div key={r} style={{ display: "contents" }}>
              <div className="dr-board-round">{auction ? r + 1 : `R${r + 1} ${d.round_reversed?.[r] ? "←" : "→"}`}</div>
              {d.order.map((t, c) => {
                const i = r * n + (d.round_reversed?.[r] ? n - 1 - c : c);
                const p = auction ? (byTeam[t.id] || [])[r] : d.picks[i];
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
    <Panel title="Your roster" className="dr-pane dr-pane-roster" aside={`${mine.length} of ${rows.length} filled`} extra={<TeamIcon team={team} size={20} />} top={team.color}>
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

// Every pick so far: number, round (auction: price), team, player, who made it, when.
function History({ d, entities, newestFirst = true, pane = true }) {
  const teams = Object.fromEntries(d.order.map(t => [t.id, t]));
  const picks = newestFirst ? [...d.picks].reverse() : d.picks;
  const auction = d.draft_type === "auction";
  return (
    <Panel title="Pick history" className={pane ? "dr-pane dr-pane-history" : ""} aside={`${d.picks.length} of ${d.total_picks} picks`}>
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

function PreDraft({ d, isAdmin, myTeamId, now, busy, post, scenario }) {
  const when = d.draft_start_at ? new Date(d.draft_start_at) : null;
  const local = when && when.toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  const zone = when && (when.toLocaleTimeString(undefined, { timeZoneName: "short" }).split(" ").pop());
  const utc = when && `${when.toLocaleString("en-US", { timeZone: "UTC", weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hourCycle: "h23" })} UTC`;
  const auction = d.draft_type === "auction";
  const details = [
    ["Type", TYPE_NAMES[d.draft_type]], ["Teams", String(d.order.length)], ["Rounds", String(d.rounds)],
    ...(auction ? [["Budget", `$${d.auction?.budget ?? "—"}`], ["Minimum bid", `$${d.auction?.min_bid ?? "—"}`], ["Bid clock", `${d.auction?.bid_seconds ?? "—"} s`]]
      : [["Pick clock", minutes(d.pick_seconds)]]),
    ["Clock runs out", auction ? "Auto-nominate" : "Auto-pick"],
  ];
  const rules = SLOT_ORDER.map(k => [RULE_NAMES[k], String(d.roster_slots[k] || 0)]);
  return (
    <>
      {isAdmin && (
        <Commish text={d.start_enabled ? "Start time, draft order and clocks are in League settings → Draft." : "Starting the draft is switched off for now. Start time, draft order and clocks are in League settings → Draft."}>
          <button type="button" className="dr-btn primary" disabled={busy || !d.start_enabled} onClick={() => post("/admin/draft/start")}>Start now</button>
          <button type="button" className="dr-btn" disabled={busy} onClick={() => post("/admin/draft/randomize")}>Randomize order</button>
          <Link className="dr-btn" to={`${base()}/league-settings#draft`}>Draft settings →</Link>
          {scenario !== "live" && d.picks.length > 0 && <button type="button" className="dr-btn" disabled={busy} onClick={() => post("/admin/draft/reset")}>Reset</button>}
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
          <div className="dr-when-count"><span>Starts in · same for everyone</span><Countdown ms={when - now} /></div>
        )}
      </section>
      <div className="dr-pre-grid">
        <Panel title="Draft order" aside={`${d.order.length} teams`}>
          <div className="dr-order">
            {d.order.map((t, i) => (
              <div key={t.id} className={`dr-order-row${t.id === myTeamId ? " mine" : ""}`}>
                <b>{i + 1}</b><TeamIcon team={t} size={28} /><span>{t.name}</span>{t.id === myTeamId && <span className="dr-you">You</span>}
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

function Complete({ d, myTeamId, entities }) {
  const history = <History d={d} entities={entities} newestFirst={false} pane={false} />;
  return (
    <>
      <section className="dr-done">
        <b>Draft complete</b>
        <span>{d.picks.length} picks · {d.picks.filter(p => p.auto).length} made automatically</span>
        <Link className="dr-btn primary" to={`${base()}/team`}>My team →</Link>
      </section>
      <div className="dr-done-grid">
        {d.order.map(t => (
          <Panel key={t.id} title={t.name} aside={t.id === myTeamId ? "You" : ""} extra={<TeamIcon team={t} size={22} />} top={t.color}>
            {d.picks.filter(p => p.team_id === t.id).map(p => (
              <div key={p.pick} className="dr-done-row">
                <EntityRow e={entities[p.id] || { ...p, nba_team: null }} />
                <span className="dr-done-no"><b>{p.price != null ? `$${p.price}` : `#${p.pick}`}</b>{p.auto && <span>auto</span>}</span>
              </div>
            ))}
          </Panel>
        ))}
      </div>
      {history}
    </>
  );
}

export default function DraftRoom() {
  const user = useCurrentUser();
  const [scenario] = useFantasyScenario();
  const players = useFantasyApi("players");
  const nbaTeams = useFantasyApi("nba-teams");
  const [d, setD] = useState(undefined);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const [skew, setSkew] = useState(0);
  const [filter, setFilter] = useState("All");
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState("available");
  const [actAs, setActAs] = useState("");
  const [opening, setOpening] = useState(null);
  const [custom, setCustom] = useState("");

  // Clocks: when a new deadline arrives, pin it once as a local end time
  // (arrival time + how long the server said was left) and count down from that alone. Polling
  // never re-adjusts a deadline it has already pinned, so the countdown only ever ticks down.
  // `skew` (server − local clock, from the fastest round trip) is only used for the start-time
  // countdown before the draft.
  const best = useRef({ rtt: Infinity });
  const apply = useCallback((state, sentAt) => {
    const got = Date.now();
    setD(prev => ({
      ...state,
      _localEnd: state.deadline
        ? (prev && prev.deadline === state.deadline && prev._localEnd
          ? prev._localEnd
          : got + (Date.parse(state.deadline) - Date.parse(state.server_time)))
        : null,
    }));
    const rtt = sentAt ? got - sentAt : Infinity;
    if (rtt <= best.current.rtt || best.current.rtt === Infinity) {
      best.current.rtt = rtt;
      setSkew(Date.parse(state.server_time) - (sentAt ? sentAt + rtt / 2 : got));
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
    const tick = setInterval(() => setNow(Date.now()), 250); // 4×/s so no second gets skipped
    if (d?.status !== "in_progress") return () => clearInterval(tick);
    const poll = setInterval(load, d?.draft_type === "auction" ? 1500 : POLL_MS);
    return () => { clearInterval(poll); clearInterval(tick); };
  }, [d?.status, d?.draft_type, load]);
  // Before the draft the page doesn't poll — except once a scheduled start time has passed, so the
  // room switches to the live draft without a reload (the server starts it on the next read).
  const startDue = d?.status === "not_started" && d?.start_enabled && d?.draft_start_at && now + skew >= Date.parse(d.draft_start_at);
  useEffect(() => {
    if (!startDue) return undefined;
    load();
    const poll = setInterval(load, 3000);
    return () => clearInterval(poll);
  }, [startDue, load]);

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

  // Test league: auto-pick ranks on the season before the replayed one, so the list shows (and
  // sorts by) those same numbers — what you see is what auto-pick goes by.
  const rankValues = d?.rank_values || null;
  const statsSeason = d?.rank_season || (players && players[0]?.stats_season) || "last season";
  const pool = useMemo(() => {
    const taken = new Set((d?.picks || []).map(p => p.id));
    const lotId = d?.auction?.lot?.entity_id;
    const q = search.trim().toLowerCase();
    return Object.values(entities)
      .filter(e => !taken.has(e.id) && e.id !== lotId)
      .filter(e => filter === "All" || (filter === "TM" ? e.kind === "nba_team" : e.kind === "player" && (e.position || "").includes(filter)))
      .filter(e => !q || e.name.toLowerCase().includes(q) || (e.nba_team || "").toLowerCase() === q)
      .map(e => (rankValues
        ? { ...e, value: rankValues[e.id] ?? null, gp: d.rank_games?.[e.id] ?? null }
        : { ...e, value: e.fantasy_points, gp: e.games_played ?? null }))
      .sort((a, b) => (b.value ?? -Infinity) - (a.value ?? -Infinity))
      .slice(0, 60);
  }, [entities, d, filter, search, rankValues]);

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
  const left = d._localEnd ? Math.max(0, Math.min(d._localEnd - now, fullClock)) : 0;
  const autoSet = new Set(d.autopick_teams || []);
  const sub = isAuction
    ? `Auction · ${d.order.length} teams · $${d.auction?.budget} budget · $${d.auction?.min_bid} minimum · ${d.auction?.bid_seconds}s bid clock`
    : `${TYPE_NAMES[d.draft_type]} · ${d.order.length} teams · ${d.rounds} rounds · ${minutes(d.pick_seconds)} per pick`;
  const testLabel = scenario === "replay" ? " · 2025-26 test league" : scenario.startsWith("test_") ? ` · sandbox ${scenario}` : "";

  const shell = body => (
    <FantasyShell title="Draft">
      <p className="dr-sub">{sub}{testLabel}</p>
      {error && <div className="dr-error" role="alert">{error}</div>}
      <div className="dr">{body}</div>
    </FantasyShell>
  );

  if (d.status === "not_started") {
    return shell(<PreDraft d={d} isAdmin={isAdmin} myTeamId={myTeam?.id} now={now + skew} busy={busy} post={post} scenario={scenario} />);
  }
  if (d.status === "complete") return shell(<Complete d={d} myTeamId={myTeam?.id} entities={entities} />);

  const tabs = (
    <div className="dr-tabs">
      <Seg full value={tab} onChange={setTab}
        options={[["available", "Available"], ["board", "Board"], ...(isAuction ? [["budgets", "Budgets"]] : []), ["roster", "Roster"], ["history", "History"]]} />
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
    return shell(
      <div className={`dr-live tab-${tab}`}>
        {onClock && (
          <ClockBar team={onClock} mine={mine} ms={left}
            title={mine ? "You're up" : `${onClock.name} is up`}
            sub={`${mine ? `${onClock.name} · ` : ""}round ${round}, pick ${d.pick_number} of ${d.total_picks}${untilMine ? ` · you pick in ${untilMine}` : ""}${d.auto_next ? ` · auto-pick: ${d.auto_next.name}` : ""}`} />
        )}
        {isAdmin && onClock && (
          <Commish text={`${onClock.name} is on the clock${d.auto_next ? ` — auto-pick would take ${d.auto_next.name}` : ""}. Pick for them from the list, or:`}>
            <button type="button" className="dr-btn" disabled={busy} onClick={() => post("/admin/draft/autopick")}>Auto-pick now</button>
            <Switch on={autoSet.has(onClock.id)} disabled={busy} label={`Autopick ${onClock.name}`}
              onChange={on => post("/admin/draft/autopick-team", { team_id: onClock.id, on })} />
            {scenario !== "live" && <button type="button" className="dr-btn" disabled={busy} onClick={() => post("/admin/draft/reset")}>Reset</button>}
          </Commish>
        )}
        {tabs}
        <Board d={d} myTeamId={myTeam?.id} />
        <div className="dr-main-grid">
          <Pool items={pool} filter={filter} setFilter={setFilter} search={search} setSearch={setSearch} action={action} valueSeason={statsSeason} />
          {roster}
        </div>
        <History d={d} entities={entities} />
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
  const next = lot ? lot.high_bid + 1 : 0;
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
    <Panel title="Budgets" className="dr-pane dr-pane-budgets" aside={`$${a.budget} each`}>
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

  return shell(
    <div className={`dr-live tab-${tab}`}>
      {lot ? (
        <section className="dr-lot" aria-label="On the block">
          <div className="dr-lot-who">
            <PositionBadge entry={lotEntity} size={44} />
            <NbaTeamSquare tricode={lotEntity.kind === "nba_team" ? lotEntity.id : lotEntity.nba_team} size={44} />
            <div>
              <span className="dr-small">On the block · nominated by {lot.nominated_by_name}</span>
              <span>{nameLines(lotEntity)[0]}</span>
              <b className="dr-lot-name">{nameLines(lotEntity)[1]}</b>
              {(() => {
                const v = rankValues ? rankValues[lotEntity.id] : lotEntity.fantasy_points;
                const gp = rankValues ? d.rank_games?.[lotEntity.id] : lotEntity.games_played;
                return v != null && <span className="dr-small">{Number(v).toFixed(1)} pts / game{gp ? ` · ${gp} GP` : ""} ({statsSeason})</span>;
              })()}
            </div>
          </div>
          <div className="dr-lot-high">
            <span className="dr-small">High bid</span>
            <span className="dr-lot-bid">${lot.high_bid}</span>
            <span className="dr-lot-team">{(() => { const t = d.order.find(o => o.id === lot.high_team); return t && <TeamIcon team={t} size={20} />; })()}<b>{lot.high_team_name}</b></span>
          </div>
          <div className="dr-lot-clock"><LedClock text={mmss(left)} urgent={left < 60000} step={4} r={1.6} /><span className="dr-small">resets to 0:{String(a.bid_seconds).padStart(2, "0")} on a bid</span></div>
        </section>
      ) : nominator && (
        <ClockBar team={nominator} mine={mineUp} ms={left}
          title={mineUp ? "Your turn to nominate" : `${nominator.name} is nominating`}
          sub={`Lot ${d.picks.length + 1} of ${d.total_picks} · out of time → ${d.auto_next ? d.auto_next.name : "best available"} at $${a.min_bid}`} />
      )}
      {lot && b && (
        <section className="dr-bidbar" aria-label="Bid">
          {highIsActing ? <b>{acting?.id === myTeam?.id ? "You're" : `${acting?.name} is`} the high bidder</b> : (
            <>
              <button type="button" className="dr-btn primary" disabled={busy || !canBid || next > b.max_bid} onClick={() => bid(next)}>Bid ${next}</button>
              <button type="button" className="dr-btn" disabled={busy || !canBid || lot.high_bid + 5 > b.max_bid} onClick={() => bid(lot.high_bid + 5)}>Bid ${lot.high_bid + 5}</button>
              <input className="dr-amount" type="number" min={next} max={b.max_bid} placeholder="$ amount" value={custom} onChange={e => setCustom(e.target.value)} />
              <button type="button" className="dr-btn" disabled={busy || !canBid || customAmount < next || customAmount > b.max_bid} onClick={() => { bid(customAmount); setCustom(""); }}>Bid</button>
              <button type="button" className="dr-btn" disabled={busy || !canBid || b.max_bid < next} onClick={() => bid(b.max_bid)}>All in · ${b.max_bid}</button>
              {!b.can_bid && <span className="dr-small">{b.open_spots ? "Out of money" : "Roster full"}</span>}
            </>
          )}
        </section>
      )}
      {budgetSection}
      {isAdmin && (
        <Commish text={lot ? "Bid or nominate for any team." : nominator ? `${nominator.name} is nominating. Nominate for them from the list, or:` : null}>
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
          {scenario !== "live" && <button type="button" className="dr-btn" disabled={busy} onClick={() => post("/admin/draft/reset")}>Reset</button>}
        </Commish>
      )}
      {tabs}
      <div className="dr-main-grid">
        <Pool items={pool} filter={filter} setFilter={setFilter} search={search} setSearch={setSearch} action={action} before={opener} valueSeason={statsSeason}
          aside={lot ? `Nominating opens when this lot sells` : null} />
        <div className="dr-stack">
          {budgets}
          {roster}
        </div>
      </div>
      <Board d={d} myTeamId={myTeam?.id} />
      <History d={d} entities={entities} />
    </div>
  );
}
