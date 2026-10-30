import { useCallback, useEffect, useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { textOnColor } from "../../components/fantasy/teamColors";
import { API_BASE } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";
import "./LeagueSettings.css";

// Commissioner (admin) settings for the league being viewed (design: canvas board P).
// Sections: General (league name), Teams (limit + Remove), Roster, Draft, Playoffs, Season, and
// the week layout the saved settings produce. The server validates everything on Save.

const SECTIONS = [["general", "General"], ["teams", "Teams"], ["roster", "Roster"], ["draft", "Draft"], ["playoffs", "Playoffs"], ["season", "Season"], ["weeks", "Week layout"], ["matchups", "Matchups"], ["history", "Past seasons"]];
const SLOT_NAMES = { G: "G", F: "F", C: "C", TEAM: "TM", FLEX: "FLX", BENCH: "Bench" };
const DRAFT_TYPES = [
  ["snake", "Snake", "Order reverses every round"],
  ["snake_3rr", "Snake, 3rd-round reversal", "Round 3 repeats round 2's order"],
  ["linear", "Normal", "Same order every round"],
  ["auction", "Auction", "Teams bid on nominated players"],
];
const CLOCKS = [[60, "1 min"], [120, "2 min"], [300, "5 min"], [600, "10 min"]];
const KIND = { member: "Member", fake: "Fake user", bot: "Bot (you run it)" };
const LEAGUE_LABEL = { live: "2026-27 league", replay: "2025-26 test league", test_pre: "Sandbox: pre-draft", test_post: "Sandbox: post-draft", livetest: "Test: live game" };

// ISO (UTC) → the "YYYY-MM-DDTHH:MM" local value a datetime-local input wants.
const toLocalInput = iso => {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = n => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};
const fmt = iso => new Date(`${iso}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });

function Stepper({ value, min, max, onChange, unit }) {
  return (
    <span className="ls-line">
      <span className="ls-stepper">
        <button type="button" aria-label="Less" onClick={() => onChange(Math.max(min, value - 1))}>−</button>
        <span>{value}</span>
        <button type="button" aria-label="More" onClick={() => onChange(Math.min(max, value + 1))}>+</button>
      </span>
      {unit && <span>{unit}</span>}
    </span>
  );
}

function Section({ id, title, desc, children }) {
  return (
    <section id={id} className="ls-section" aria-label={title}>
      <div className="ls-section-head">
        <span className="ls-label"><span className="ls-tick" aria-hidden="true" />{title}</span>
        {desc && <span className="ls-desc">{desc}</span>}
      </div>
      {children}
    </section>
  );
}

function Row({ name, help, children }) {
  return (
    <div className="ls-row">
      <div className="ls-name">{name}</div>
      <div className="ls-control">
        <div className="ls-line">{children}</div>
        {help && <span className="ls-help">{help}</span>}
      </div>
    </div>
  );
}

// Draft order: Randomize, or "Set order" — click teams in pick order (no typing, no dragging);
// the last team fills in by itself. Saves right away. Locked once the draft starts.
function DraftOrder({ scenario }) {
  const [d, setD] = useState(undefined);
  const [placed, setPlaced] = useState(null); // team ids clicked so far, or null when not editing
  const [error, setError] = useState(null);
  const load = useCallback(() => (
    fetch(`${API}${API_BASE}/draft?scenario=${scenario}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null).then(setD)
  ), [scenario]);
  useEffect(() => { load(); }, [load]);

  async function send(path, body) {
    setError(null);
    const r = await fetch(`${API}${API_BASE}${path}?scenario=${scenario}`, {
      method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}),
    });
    const out = await r.json().catch(() => ({}));
    if (!r.ok) { setError(out.detail || "Couldn't save the order"); return; }
    setD(out);
    setPlaced(null);
  }

  if (!d) return <span className="ls-help">{d === null ? "Couldn't load the draft order." : "Loading…"}</span>;
  const locked = d.status !== "not_started";
  const byId = Object.fromEntries(d.order.map(t => [t.id, t]));
  function click(id) {
    const next = [...placed, id];
    const rest = d.order.filter(t => !next.includes(t.id));
    if (rest.length <= 1) send("/admin/draft/order", { team_ids: [...next, ...rest.map(t => t.id)] });
    else setPlaced(next);
  }

  if (placed) {
    const waiting = d.order.filter(t => !placed.includes(t.id));
    return (
      <div className="ls-order-edit">
        <div className="ls-line">
          <button type="button" className="ls-btn primary" disabled>Setting order… ({placed.length} of {d.order.length})</button>
          <button type="button" className="ls-btn" onClick={() => setPlaced([])}>Start over</button>
          <button type="button" className="ls-btn" onClick={() => setPlaced(null)}>Cancel</button>
        </div>
        <div className="ls-order-cols">
          <div className="ls-order-list">
            <div className="ls-order-head">New order</div>
            {d.order.map((_, i) => {
              const t = byId[placed[i]];
              return (
                <div key={i} className={`ls-order-row${i === placed.length ? " next" : ""}`}>
                  <b>{i + 1}</b>{t ? <><TeamIcon team={t} size={24} /><span>{t.name}</span></> : <span>{i === placed.length ? `← click a team for pick ${i + 1}` : ""}</span>}
                </div>
              );
            })}
          </div>
          <div className="ls-order-pick">
            <div className="ls-order-head">Click teams in pick order</div>
            {waiting.map(t => (
              <button key={t.id} type="button" className="ls-order-team" onClick={() => click(t.id)}><TeamIcon team={t} size={24} />{t.name}</button>
            ))}
            <span className="ls-help">The last team fills in by itself.</span>
          </div>
        </div>
        {error && <span className="ls-error-text" role="alert">{error}</span>}
      </div>
    );
  }
  return (
    <div className="ls-order-edit">
      <div className="ls-order-list ls-order-scroll">
        {d.order.map((t, i) => <div key={t.id} className="ls-order-row"><b>{i + 1}</b><TeamIcon team={t} size={24} /><span>{t.name}</span></div>)}
        {d.order.length === 0 && <div className="ls-order-row"><span>No teams yet.</span></div>}
      </div>
      {locked ? <span className="ls-help">Locked — the draft has started.</span> : (
        <div className="ls-line">
          <button type="button" className="ls-btn" onClick={() => send("/admin/draft/randomize")}>Randomize</button>
          <button type="button" className="ls-btn" disabled={d.order.length < 2} onClick={() => setPlaced([])}>Set order</button>
          <span className="ls-help">Saves right away.</span>
        </div>
      )}
      {error && <span className="ls-error-text" role="alert">{error}</span>}
    </div>
  );
}

// The start time in UTC, so everyone can line it up (the input itself is in your time zone).
const utcText = iso => `${new Date(iso).toLocaleString("en-US", { timeZone: "UTC", weekday: "short", month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit", hourCycle: "h23" })} UTC`;
const zoneText = () => {
  const name = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const abbr = new Date().toLocaleTimeString(undefined, { timeZoneName: "short" }).split(" ").pop();
  return `${abbr} · ${name.replace(/_/g, " ")} (your time zone)`;
};

// Matchups: each regular-season week's pairs (round robin by default). The commissioner can set any week by
// hand — pick both sides of each game — or put it back on the round robin. Saves right away (PUT /admin/league/matchups).
function Matchups({ scenario }) {
  const [data, setData] = useState(undefined);
  const [week, setWeek] = useState(null);
  const [edit, setEdit] = useState(null); // pairs being edited, or null
  const [error, setError] = useState(null);
  const [report, setReport] = useState(null); // the last "Balance now" result: each team's strength and opponents' average
  const load = useCallback(() => {
    fetch(`${API}${API_BASE}/league/matchups?scenario=${scenario}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null).then(setData);
  }, [scenario]);
  useEffect(() => { load(); }, [load]);
  if (!data) return <span className="ls-help">{data === null ? "Couldn't load the matchups." : "Loading…"}</span>;
  const w = data.weeks.find(x => x.week === week) || data.weeks[0];
  if (!w) return <span className="ls-help">No regular-season weeks.</span>;
  const byId = Object.fromEntries(data.teams.map(t => [t.id, t]));
  const fmtD = d => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });

  async function save(pairs) {
    setError(null);
    const r = await fetch(`${API}${API_BASE}/admin/league/matchups?scenario=${scenario}`, {
      method: "PUT", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ week: w.week, pairs }),
    });
    const out = await r.json().catch(() => ({}));
    if (!r.ok) { setError(out.detail || "Couldn't save"); return; }
    setData(out); setEdit(null);
  }
  async function balance() {
    setError(null);
    const r = await fetch(`${API}${API_BASE}/admin/league/balance-schedule?scenario=${scenario}`, { method: "POST", credentials: "include" });
    const out = await r.json().catch(() => ({}));
    if (!r.ok || !out.ok) { setError(out.detail || out.reason || "Couldn't balance"); return; }
    setReport(out); load();
  }
  const pairs = edit || w.pairs;
  // Picking a team that's in another game swaps the two, so every team still plays once.
  const pickTeam = (i, j, id) => {
    const old = pairs[i][j];
    setEdit(pairs.map((p, k) => p.map((x, m) => ((k === i && m === j) ? id : x === id ? old : x))));
  };

  // The whole schedule at once: a row per team, a column per week, each cell that week's opponent (or Bye).
  // Weeks set by hand are marked; clicking a week opens it in the editor below.
  const opp = (wk, id) => {
    const p = wk.pairs.find(x => x.includes(id));
    return p ? p.find(x => x !== id) : null;
  };
  const pick = wk => { setWeek(wk.week); setEdit(null); setError(null); };
  // How many times each pair meets over the regular season, plus each team's byes.
  const meets = {}, byes = {};
  for (const x of data.weeks) {
    const playing = new Set();
    for (const [a, b] of x.pairs) { meets[`${a}|${b}`] = (meets[`${a}|${b}`] || 0) + 1; meets[`${b}|${a}`] = (meets[`${b}|${a}`] || 0) + 1; playing.add(a); playing.add(b); }
    for (const t of data.teams) if (!playing.has(t.id)) byes[t.id] = (byes[t.id] || 0) + 1;
  }
  const anyBye = Object.keys(byes).length > 0;
  // Heat fill: each cell's strength follows its count within its kind (meetings / byes) — fewest faint, most strong.
  const heat = (n, all) => {
    const lo = Math.min(...all), hi = Math.max(...all);
    return { "--heat": `${hi === lo ? 30 : Math.round(12 + ((n - lo) / (hi - lo)) * 48)}%` };
  };
  const meetAll = data.teams.flatMap(a => data.teams.filter(b => b.id !== a.id).map(b => meets[`${a.id}|${b.id}`] || 0));
  const byeAll = data.teams.map(t => byes[t.id] || 0);
  const games = id => data.teams.reduce((n, o) => n + (meets[`${id}|${o.id}`] || 0), 0);
  const totalGames = data.teams.reduce((n, t) => n + games(t.id), 0) / 2;

  return (
    <div className="ls-mu">
      <div className="ls-grid-wrap ls-matrix-wrap">
        <table className="ls-grid ls-matrix">
          <thead>
            <tr>
              <th className="ls-grid-team" />
              {data.teams.map(t => <th key={t.id} title={t.name}><TeamIcon team={t} size={22} /></th>)}
              <th className="tot">Total</th>
              {anyBye && <th className="bye"><span className="ls-grid-bye">BYE</span></th>}
            </tr>
          </thead>
          <tbody>
            {data.teams.map(t => (
              <tr key={t.id}>
                <th className="ls-grid-team" style={{ "--tc": t.color }}><span><TeamIcon team={t} size={20} />{t.name}</span></th>
                {data.teams.map(o => {
                  const n = meets[`${t.id}|${o.id}`] || 0;
                  return o.id === t.id ? <td key={o.id} className="self" /> : <td key={o.id} style={heat(n, meetAll)}>{n}</td>;
                })}
                <td className="tot">{games(t.id)}</td>
                {anyBye && <td className="bye" style={heat(byes[t.id] || 0, byeAll)}>{byes[t.id] || 0}</td>}
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th className="ls-grid-team">Total</th>
              {data.teams.map(o => <td key={o.id} className="tot">{games(o.id)}</td>)}
              <td className="tot">{totalGames}</td>
              {anyBye && <td className="tot bye">{byeAll.reduce((a, b) => a + b, 0)}</td>}
            </tr>
          </tfoot>
        </table>
      </div>
      <div className="ls-grid-wrap">
        <table className="ls-grid ls-wkgrid">
          <thead>
            <tr>
              <th className="ls-grid-team" />
              {data.weeks.map(x => (
                <th key={x.week} className={`${x.week === w.week ? "on" : ""}${x.custom ? " custom" : ""}`}>
                  <button type="button" onClick={() => pick(x)} title={`${x.label} · ${fmtD(x.start)} – ${fmtD(x.end)}${x.custom ? " · set by hand" : ""}`}>{x.week}</button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.teams.map(t => (
              <tr key={t.id}>
                <th className="ls-grid-team" style={{ "--tc": t.color }}><span><TeamIcon team={t} size={20} />{t.name}</span></th>
                {data.weeks.map(x => {
                  const o = byId[opp(x, t.id)];
                  return (
                    <td key={x.week} className={x.week === w.week ? "on" : ""} onClick={() => pick(x)}>
                      {o ? <span className="ls-grid-opp" style={{ background: o.color, color: textOnColor(o.color) }} title={o.name}>{o.abbreviation || o.name.slice(0, 4)}</span> : <span className="ls-grid-bye">BYE</span>}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="ls-line">
        <select value={w.week} onChange={e => { setWeek(Number(e.target.value)); setEdit(null); setError(null); }}>
          {data.weeks.map(x => <option key={x.week} value={x.week}>{x.label} · {fmtD(x.start)} – {fmtD(x.end)}{x.custom ? " · set by hand" : ""}</option>)}
        </select>
        <span className="ls-help">{w.custom ? "Set by hand." : "Round robin."}</span>
      </div>
      <div className="ls-mu-list">
        {pairs.map((p, i) => (
          <div key={i} className="ls-mu-row">
            {p.map((id, j) => (
              <span key={j} className="ls-mu-side" style={{ "--tc": byId[id]?.color }}>
                {byId[id] && <TeamIcon team={byId[id]} size={22} />}
                {edit ? (
                  <select value={id} onChange={e => pickTeam(i, j, e.target.value)}>
                    {data.teams.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                  </select>
                ) : <span>{byId[id]?.name || id}</span>}
                {j === 0 && <b className="ls-mu-vs">vs</b>}
              </span>
            ))}
          </div>
        ))}
        {!edit && data.teams.filter(t => !pairs.some(p => p.includes(t.id))).map(t => (
          <div key={t.id} className="ls-mu-row">
            <span className="ls-mu-side" style={{ "--tc": t.color }}><TeamIcon team={t} size={22} /><span>{t.name}</span><b className="ls-mu-vs">vs</b></span>
            <span className="ls-mu-side bye"><span className="ls-grid-bye">BYE</span></span>
          </div>
        ))}
        {pairs.length === 0 && <div className="ls-mu-row"><span>No games this week.</span></div>}
      </div>
      <div className="ls-line">
        {edit ? (
          <>
            <button type="button" className="ls-btn primary" onClick={() => save(edit)}>Save {w.label}</button>
            <button type="button" className="ls-btn" onClick={() => setEdit(null)}>Cancel</button>
          </>
        ) : (
          <>
            <button type="button" className="ls-btn" onClick={() => setEdit(w.pairs.map(p => [...p]))}>Change matchups</button>
            {w.custom && <button type="button" className="ls-btn" onClick={() => save(null)}>Back to round robin</button>}
            <button type="button" className="ls-btn" onClick={balance}>Balance every week by 3-season win %</button>
          </>
        )}
      </div>
      {error && <span className="ls-error-text" role="alert">{error}</span>}
      {report && (
        <div className="ls-grid-wrap" style={{ marginTop: 12 }}>
          <table className="ls-grid ls-bal">
            <thead><tr><th className="ls-grid-team">Team</th><th>Manager</th><th>Strength</th><th>Opponents' average</th><th>Games</th><th>Byes</th></tr></thead>
            <tbody>
              {Object.entries(report.teams).sort((a, b) => b[1].strength - a[1].strength).map(([name, r]) => (
                <tr key={name}><td className="ls-grid-team">{name}</td><td>{r.manager || "new (.400)"}</td><td>{r.strength.toFixed(3)}</td>
                  <td>{r.opp_avg != null ? r.opp_avg.toFixed(3) : "—"}</td><td>{r.games}</td><td>{r.byes}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// Past seasons: each manager's win-loss in the fantasy seasons on record. The balanced schedule's strength is the
// average win % over the last 3 seasons (a season he missed counts .400); a team is matched to its manager by Discord
// account, else by name / aliases in the owner's username or team name. Saved with the button (PUT /admin/league/manager-history).
function PastSeasons() {
  const [data, setData] = useState(undefined);
  const [rows, setRows] = useState(null);
  const [seasons, setSeasons] = useState([]);
  const [status, setStatus] = useState(null);
  const [newSeason, setNewSeason] = useState("");
  const load = useCallback(() => {
    fetch(`${API}${API_BASE}/league/manager-history`, { credentials: "include" }).then(r => (r.ok ? r.json() : null)).catch(() => null)
      .then(d => { setData(d); if (d) { setRows(d.managers.map(m => ({ ...m, records: { ...m.records } }))); setSeasons(d.seasons); } });
  }, []);
  useEffect(() => { load(); }, [load]);
  if (!data || !rows) return <span className="ls-help">{data === null ? "Couldn't load past seasons." : "Loading…"}</span>;
  const set = (i, k, v) => setRows(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  const setWL = (i, s, side, v) => setRows(rows.map((r, j) => {
    if (j !== i) return r;
    const wl = [...(r.records[s] || ["", ""])]; wl[side] = v === "" ? "" : Number(v);
    return { ...r, records: { ...r.records, [s]: wl } };
  }));
  const strength = r => {
    const pct = seasons.slice(0, 3).map(s => { const [w, l] = r.records[s] || []; return w === "" || l === "" || w == null || l == null || w + l === 0 ? 0.4 : w / (w + l); });
    return pct.length ? pct.reduce((a, b) => a + b, 0) / pct.length : 0.4;
  };
  async function save() {
    setStatus("Saving…");
    const r = await fetch(`${API}${API_BASE}/admin/league/manager-history`, {
      method: "PUT", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ managers: rows }),
    });
    const out = await r.json().catch(() => ({}));
    if (!r.ok) { setStatus(out.detail || "Couldn't save"); return; }
    setData(out); setRows(out.managers.map(m => ({ ...m, records: { ...m.records } }))); setSeasons(out.seasons); setStatus("Saved.");
  }
  return (
    <div>
      <div className="ls-grid-wrap">
        <table className="ls-grid ls-hist">
          <thead><tr><th className="ls-grid-team">Manager</th><th>Also known as</th><th>Discord id</th>
            {seasons.map(s => <th key={s}>{s}</th>)}<th>Strength</th></tr></thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td className="ls-grid-team"><input type="text" value={r.manager} onChange={e => set(i, "manager", e.target.value)} style={{ width: 130 }} /></td>
                <td><input type="text" value={r.aliases || ""} onChange={e => set(i, "aliases", e.target.value)} style={{ width: 150 }} /></td>
                <td><input type="text" value={r.discord_id || ""} onChange={e => set(i, "discord_id", e.target.value)} style={{ width: 150 }} /></td>
                {seasons.map(s => (
                  <td key={s} className="ls-wl">
                    <input type="number" min={0} value={(r.records[s] || [""])[0] ?? ""} onChange={e => setWL(i, s, 0, e.target.value)} aria-label={`${r.manager} ${s} wins`} />
                    <span>–</span>
                    <input type="number" min={0} value={(r.records[s] || ["", ""])[1] ?? ""} onChange={e => setWL(i, s, 1, e.target.value)} aria-label={`${r.manager} ${s} losses`} />
                  </td>
                ))}
                <td>{strength(r).toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="ls-line">
        <button type="button" className="ls-btn" onClick={() => setRows([...rows, { manager: "", aliases: "", discord_id: "", records: {} }])}>Add manager</button>
        <input type="text" placeholder="2026-27" value={newSeason} onChange={e => setNewSeason(e.target.value)} style={{ width: 100 }} />
        <button type="button" className="ls-btn" disabled={!newSeason.trim() || seasons.includes(newSeason.trim())}
          onClick={() => { setSeasons([newSeason.trim(), ...seasons].sort().reverse()); setNewSeason(""); }}>Add season</button>
        <button type="button" className="ls-btn primary" onClick={save}>Save past seasons</button>
        {status && <span>{status}</span>}
      </div>
    </div>
  );
}

export default function LeagueSettings() {
  const user = useCurrentUser();
  const [scenario] = useFantasyScenario();
  const [data, setData] = useState(undefined);
  const [draft, setDraft] = useState(null);
  const [members, setMembers] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [roundText, setRoundText] = useState("");
  const [customClock, setCustomClock] = useState(false);

  const adopt = useCallback(d => {
    setData(d);
    setDraft(d ? structuredClone(d.settings) : null);
    setRoundText(d ? d.settings.pick_seconds_by_round.join(", ") : "");
    setCustomClock(d ? !CLOCKS.some(([s]) => s === d.settings.pick_seconds) : false);
  }, []);

  const loadMembers = useCallback(() => (
    fetch(`${API}${API_BASE}/league/members?scenario=${scenario}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null).then(setMembers)
  ), [scenario]);

  useEffect(() => {
    if (!user?.isAdmin) return;
    fetch(`${API}${API_BASE}/league/settings?scenario=${scenario}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null).then(adopt);
    loadMembers();
  }, [user, scenario, adopt, loadMembers]);

  async function save() {
    setStatus("Saving…"); setError(null);
    const r = await fetch(`${API}${API_BASE}/admin/league/settings?scenario=${scenario}`, {
      method: "PUT", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(draft),
    });
    const body = await r.json();
    if (!r.ok) { setStatus(null); setError(body.detail || "Couldn't save"); return; }
    adopt(body); setStatus("Saved.");
    loadMembers();
  }

  async function remove(team) {
    const before = members.draft_status === "not_started";
    if (!window.confirm(before ? `Remove ${team.name} from the league?` : `Remove ${team.name}? The draft has started, so the team stays as a bot you run.`)) return;
    setError(null);
    const r = await fetch(`${API}${API_BASE}/admin/league/teams/${encodeURIComponent(team.id)}/remove?scenario=${scenario}`, { method: "POST", credentials: "include" });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) setError(body.detail || "Couldn't remove the team"); else setMembers(body);
  }

  if (user === undefined) return <FantasyShell title="League settings"><p style={{ fontSize: 13 }}>Checking…</p></FantasyShell>;
  if (!user?.isAdmin) return <FantasyShell title="League settings"><p style={{ fontSize: 13 }}>Commissioner only.</p></FantasyShell>;
  if (data === undefined) return <FantasyShell title="League settings"><p style={{ fontSize: 13 }}>Loading…</p></FantasyShell>;
  if (data === null || !draft) return <FantasyShell title="League settings"><p style={{ fontSize: 13 }}>Couldn't load settings.</p></FantasyShell>;

  const set = (k, v) => { setStatus(null); setDraft(d => ({ ...d, [k]: v })); };
  const setRound = (i, k, v) => set("playoff_rounds", draft.playoff_rounds.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  const dirty = JSON.stringify(draft) !== JSON.stringify(data.settings);
  const byes = 2 ** draft.playoff_rounds.length - draft.playoff_teams;
  const spots = Object.values(draft.roster_slots).reduce((a, n) => a + (n || 0), 0);
  const isAuction = draft.draft_type === "auction";
  const locked = !!data.draft_locked; // draft started: roster / team limit / draft settings are read-only

  return (
    <FantasyShell title="League settings">
      <div className="ls">
        <div className="ls-title">
          <span className="ls-tag">Commissioner</span>
          <span>{[draft.league_name || data.settings.league_name, LEAGUE_LABEL[scenario], `NBA season ${data.season}`].filter(Boolean).join(" · ")}</span>
        </div>

        <div className="ls-layout">
          <nav className="ls-index" aria-label="Sections">
            {SECTIONS.map(([id, label]) => <a key={id} href={`#${id}`}>{label}</a>)}
          </nav>

          <div className="ls-main">
            <Section id="general" title="General" desc="The basics everyone sees.">
              <Row name="League name" help="Shows at the top of Home. Up to 40 characters.">
                <input type="text" value={draft.league_name} maxLength={40} placeholder="Name your league" style={{ width: 340, maxWidth: "100%" }}
                  onChange={e => set("league_name", e.target.value)} />
              </Row>
            </Section>

            <Section id="teams" title="Teams"
              desc={members ? `${members.teams.length} of ${draft.team_count} spots filled · ${members.draft_status === "not_started" ? "joining is open until the draft starts" : "joining closed when the draft started"}.` : null}>
              <fieldset className="ls-fieldset" disabled={locked}>
                <Row name="Team limit" help={locked ? "Locked — the draft has started. Reset the draft to change it." : "Joining closes when the league is full or the draft starts."}>
                  <Stepper value={draft.team_count} min={2} max={16} onChange={v => set("team_count", v)} unit="teams (2–16)" />
                </Row>
              </fieldset>
              {members && (
                <>
                  <div className="ls-scroll">
                    <table className="ls-teams">
                      <thead>
                        <tr><th /><th>Team</th><th>Owner</th><th>Type</th><th className="act">Commissioner</th></tr>
                      </thead>
                      <tbody>
                        {members.teams.length === 0 && <tr><td /><td colSpan={3}>Nobody's in yet.</td><td className="act" /></tr>}
                        {members.teams.map(t => {
                          const mine = t.id === members.my_team_id;
                          return (
                            <tr key={t.id}>
                              <td><TeamIcon team={t} size={36} /></td>
                              <td><b>{t.name}</b><span className="abbr">{t.abbreviation}</span></td>
                              <td>{t.owner_name || "—"}</td>
                              <td>{KIND[t.kind]}</td>
                              <td className="act">
                                {mine ? <span style={{ fontSize: 13 }}>Leave is in your Team settings</span>
                                  : <button type="button" className="ls-btn small danger" onClick={() => remove(t)}>Remove</button>}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                  <div className="ls-note">
                    Before the draft, <b>Remove</b> takes the team out of the league. Once the draft starts, the team stays as a bot you run.
                  </div>
                </>
              )}
            </Section>

            <Section id="roster" title="Roster" desc={locked ? "Locked — the draft has started. Reset the draft (Draft room → Commissioner → Reset) to change these." : "Spots per team, bench included. Each spot is one draft round, so the draft always fills the whole roster."}>
              <fieldset className="ls-fieldset" disabled={locked}>
              <Row name="Spots" help={<><b>{spots} spot{spots === 1 ? "" : "s"} → {spots} draft round{spots === 1 ? "" : "s"}.</b> G / F / C take players listed at that position, TM an NBA team, FLX any player or NBA team, Bench anyone (doesn't score).</>}>
                <div className="ls-slots" style={{ width: "100%" }}>
                  {Object.keys(SLOT_NAMES).map(k => (
                    <div key={k} className="ls-slot">
                      <span>{SLOT_NAMES[k]}</span>
                      <Stepper value={draft.roster_slots[k] || 0} min={0} max={10} onChange={v => set("roster_slots", { ...draft.roster_slots, [k]: v })} />
                    </div>
                  ))}
                </div>
              </Row>
              <Row name="IR spots" help="Emergency slots to stash an injured player (red or yellow dot). A player moved there is locked in for the next 4 weeks. Doesn't score.">
                <Stepper value={draft.ir_slots ?? 1} min={0} max={3} onChange={v => set("ir_slots", v)} />
              </Row>
              </fieldset>
            </Section>

            <Section id="draft" title="Draft" desc={locked ? "Locked — the draft has started. Reset the draft to change these. (The draft order below still shows.)" : "How and when the draft runs."}>
              <fieldset className="ls-fieldset" disabled={locked}>
              <Row name="Type">
                <div className="ls-cards" role="radiogroup" aria-label="Draft type" style={{ width: "100%" }}>
                  {DRAFT_TYPES.map(([key, name, desc]) => (
                    <button key={key} type="button" role="radio" aria-checked={draft.draft_type === key} className="ls-card" onClick={() => set("draft_type", key)}>
                      <b><span className="ls-dot" aria-hidden="true" />{name}</b><small>{desc}</small>
                    </button>
                  ))}
                </div>
              </Row>
              {!isAuction && (
                <>
                  <Row name="Pick clock" help="Per pick.">
                    <span className="ls-seg" role="radiogroup" aria-label="Pick clock">
                      {CLOCKS.map(([s, label]) => (
                        <button key={s} type="button" role="radio" aria-checked={!customClock && draft.pick_seconds === s}
                          onClick={() => { setCustomClock(false); set("pick_seconds", s); }}>{label}</button>
                      ))}
                      <button type="button" role="radio" aria-checked={customClock} onClick={() => setCustomClock(true)}>Custom</button>
                    </span>
                    {customClock && (
                      <span className="ls-line">
                        <input type="number" min={10} max={86400} value={draft.pick_seconds} style={{ width: 100 }}
                          onChange={e => set("pick_seconds", Number(e.target.value) || 10)} /> seconds
                      </span>
                    )}
                  </Row>
                  <Row name="Per-round clocks" help="Optional, in seconds for round 1, 2, …; rounds past the list use the pick clock.">
                    <input type="text" value={roundText} placeholder="e.g. 120, 120, 60" style={{ width: 260 }}
                      onChange={e => setRoundText(e.target.value)}
                      onBlur={() => set("pick_seconds_by_round", roundText.split(/[,\s]+/).filter(Boolean).map(Number).filter(n => n > 0))} />
                    {draft.pick_seconds_by_round.length > 0 && (
                      <button type="button" className="ls-btn small" onClick={() => { setRoundText(""); set("pick_seconds_by_round", []); }}>Clear</button>
                    )}
                  </Row>
                  <Row name="Clock runs out" help="The only option for now — skipping isn't allowed.">
                    <select value={draft.missed_pick} onChange={e => set("missed_pick", e.target.value)} style={{ width: 360, maxWidth: "100%" }}>
                      <option value="autopick">Auto-pick the best available that fits</option>
                    </select>
                  </Row>
                </>
              )}
              {isAuction && (
                <>
                  <Row name="Budget per team">
                    <input type="number" min={1} max={10000} value={draft.auction_budget} style={{ width: 110 }} onChange={e => set("auction_budget", Number(e.target.value) || 1)} /> dollars
                  </Row>
                  <Row name="Minimum bid">
                    <input type="number" min={0} value={draft.auction_min_bid} style={{ width: 110 }} onChange={e => set("auction_min_bid", Number(e.target.value) || 0)} /> dollars
                  </Row>
                  <Row name="Minimum raise" help="Each new bid must beat the high bid by at least this much of it, rounded up — never less than $1.">
                    <input type="number" min={0} max={50} value={draft.auction_min_raise_pct ?? 4} style={{ width: 110 }} onChange={e => set("auction_min_raise_pct", Math.max(0, Math.min(50, Number(e.target.value) || 0)))} /> % of the high bid
                  </Row>
                  <Row name="Bidding opens in order" help="After a nomination, the next team in the draft order can bid right away, then each team after waits this much more. The head start rotates with the nominator. 0 = everyone at once.">
                    <input type="number" min={0} max={1} step={0.05} value={(draft.auction_open_step_ms ?? 250) / 1000} style={{ width: 110 }}
                      onChange={e => set("auction_open_step_ms", Math.round(Math.max(0, Math.min(1, Number(e.target.value) || 0)) * 1000))} /> seconds per team
                  </Row>
                  <Row name="Nomination time" help="Time runs out → the best available is nominated at the minimum bid.">
                    <input type="number" min={5} max={600} value={draft.nomination_seconds} style={{ width: 110 }} onChange={e => set("nomination_seconds", Number(e.target.value) || 5)} /> seconds
                  </Row>
                  <Row name="End-of-draft nomination time" help="Once no team still drafting has more than 25% of the budget left, nominations use this clock instead.">
                    <input type="number" min={5} max={600} value={draft.late_nomination_seconds ?? 15} style={{ width: 110 }} onChange={e => set("late_nomination_seconds", Number(e.target.value) || 5)} /> seconds
                  </Row>
                  <Row name="Bid clock" help="Each player starts with this much; the high bidder wins when it runs out.">
                    <input type="number" min={3} max={120} value={draft.bid_seconds} style={{ width: 110 }} onChange={e => set("bid_seconds", Number(e.target.value) || 3)} /> seconds
                  </Row>
                  <Row name="Time added per bid" help="Chess clock: every bid adds this much to what's left, never past the full bid clock.">
                    <input type="number" min={1} max={120} value={draft.bid_increment_seconds ?? 3} style={{ width: 110 }} onChange={e => set("bid_increment_seconds", Number(e.target.value) || 1)} /> seconds
                  </Row>
                </>
              )}
              <Row name="Scheduled start" help="Set in your time zone. Everyone sees it in their own time zone; the countdown is the same for all. Blank = starts when you press Start in the Draft Room.">
                <input type="datetime-local" value={toLocalInput(draft.draft_start_at)}
                  onChange={e => set("draft_start_at", e.target.value ? new Date(e.target.value).toISOString() : null)} />
                <span className="ls-zone">{zoneText()}</span>
                {draft.draft_start_at && <button type="button" className="ls-btn small" onClick={() => set("draft_start_at", null)}>Clear</button>}
              </Row>
              {draft.draft_start_at && (
                <div className="ls-row" style={{ borderTop: 0, paddingTop: 0 }}>
                  <div />
                  <div className="ls-utc"><b>= {utcText(draft.draft_start_at)}</b></div>
                </div>
              )}
              </fieldset>
              <Row name="Draft order">
                <DraftOrder scenario={scenario} />
              </Row>
            </Section>

            <Section id="playoffs" title="Playoffs" desc="Bracket size and how long each round lasts.">
              <Row name="Automatic" help="Fewer than 4 teams: a 1-week final. 4–6 teams: top 4. 7 or more: top 6, top 2 seeds skip the first round.">
                <button type="button" role="switch" aria-checked={draft.playoff_auto !== false} aria-label="Automatic playoffs" className="ls-toggle"
                  onClick={() => set("playoff_auto", draft.playoff_auto === false)} />
                <span>Follow the number of teams</span>
              </Row>
              <fieldset className="ls-fieldset" disabled={draft.playoff_auto !== false}>
              <Row name="Playoff teams">
                <Stepper value={draft.playoff_teams} min={2} max={32} onChange={v => set("playoff_teams", v)} unit="teams" />
                <span>{byes > 0 ? `Top ${byes} seed${byes > 1 ? "s" : ""} get a first-round bye` : "No byes"}</span>
              </Row>
              <Row name="Rounds">
                <div className="ls-rounds" style={{ width: "100%" }}>
                  {draft.playoff_rounds.map((r, i) => (
                    <div key={i} className="ls-round">
                      <b>Round {i + 1}</b>
                      <input type="text" value={r.name} maxLength={40} style={{ width: 220 }} onChange={e => setRound(i, "name", e.target.value)} />
                      <Stepper value={r.weeks} min={1} max={4} onChange={v => setRound(i, "weeks", v)} unit={r.weeks > 1 ? "weeks" : "week"} />
                      {draft.playoff_rounds.length > 1 && (
                        <button type="button" className="ls-btn small" style={{ marginLeft: "auto" }}
                          onClick={() => set("playoff_rounds", draft.playoff_rounds.filter((_, j) => j !== i))}>Remove</button>
                      )}
                    </div>
                  ))}
                  <div>
                    <button type="button" className="ls-btn small" onClick={() => set("playoff_rounds", [{ name: "Round", weeks: 1 }, ...draft.playoff_rounds])}>+ Add an earlier round</button>
                  </div>
                </div>
              </Row>
              </fieldset>
            </Section>

            <Section id="season" title="Season" desc="When the fantasy season starts, breaks and ends.">
              <Row name="Season ends" help="0 = play through the NBA's last week.">
                <Stepper value={draft.cutoff_days} min={0} max={60} onChange={v => set("cutoff_days", v)} unit="days before the NBA's last regular-season game" />
              </Row>
              <Row name="All-Star break">
                <button type="button" role="switch" aria-checked={draft.fuse_all_star} aria-label="Fuse the All-Star break" className="ls-toggle"
                  onClick={() => set("fuse_all_star", !draft.fuse_all_star)} />
                <span>Fuse the All-Star break and the week after into one 2-week period</span>
              </Row>
              <Row name="Matchups" help="Balanced: set when the draft completes so every team's opponents average the same 3-season win % (Past seasons).">
                <select value={draft.matchup_schedule} onChange={e => set("matchup_schedule", e.target.value)} style={{ width: 360, maxWidth: "100%" }}>
                  <option value="balanced">Balanced by 3-season win %</option>
                  <option value="round_robin">Round robin (everyone plays everyone)</option>
                </select>
              </Row>
            </Section>

            <Section id="weeks" title="Week layout"
              desc={`From the saved settings: ${data.weeks.filter(w => w.kind !== "playoffs").length} regular-season periods, then ${data.weeks.filter(w => w.kind === "playoffs").length} playoff periods.`}>
              <div className="ls-weeks">
                {data.weeks.map(w => (
                  <div key={w.week}>{w.kind === "playoffs" ? <b>{w.label}</b> : <span>{w.label}</span>}<span>{fmt(w.start)} – {fmt(w.end)}</span></div>
                ))}
              </div>
            </Section>

            <Section id="matchups" title="Matchups" desc="Who plays whom each regular-season week. Round robin unless you set a week by hand.">
              <Matchups scenario={scenario} />
            </Section>

            <Section id="history" title="Past seasons" desc="Each manager's record in earlier seasons. The balanced schedule uses the average win % over the last 3 (a missed season counts .400).">
              <PastSeasons />
            </Section>

            <div className={`ls-save${dirty ? " dirty" : ""}`}>
              {dirty ? <b>Unsaved changes</b> : <span style={{ fontSize: 14 }}>{status || "All changes saved."}</span>}
              {error && <span className="ls-error" role="alert">{error}</span>}
              <span>
                <button type="button" className="ls-btn" onClick={() => {
                  const keep = { league_name: draft.league_name };
                  if (locked) for (const k of data.draft_locked_keys || []) keep[k] = draft[k]; // locked ones stay as they are
                  setDraft({ ...structuredClone(data.defaults), ...keep }); setStatus(null);
                }}>Load defaults</button>
                <button type="button" className="ls-btn" disabled={!dirty} onClick={() => adopt(data)}>Discard</button>
                <button type="button" className="ls-btn primary" disabled={!dirty} onClick={save}>Save settings</button>
              </span>
            </div>
          </div>
        </div>
      </div>
    </FantasyShell>
  );
}
