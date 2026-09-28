import { useCallback, useEffect, useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { EntityLink } from "../../components/fantasy/links";
import { BASE, SEASON } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import { API } from "../../utils/helpers";

// Admin-only control panel for the replay sandbox: a 2025-26 league with a movable clock.
// Everything shown is computed by the server (GET /results?scenario=replay) from real box
// scores up to the clock date — best game per player, point margin per NBA team slot.

const box = { border: "1px solid var(--border)", padding: 14, marginBottom: 14 };
const heading = { fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 8 };
const cell = { padding: "4px 8px", textAlign: "left" };
const num = { ...cell, textAlign: "right" };
const fmtDate = iso => new Date(`${iso}T12:00:00`).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric", year: "numeric" });

function Side({ side, align }) {
  return (
    <div style={{ flex: 1, minWidth: 240 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700, fontSize: 15, marginBottom: 6, flexDirection: align === "right" ? "row-reverse" : "row" }}>
        <span>{side.team.name}</span><span>{side.score}</span>
      </div>
      <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
        <tbody>
          {side.slots.map((s, i) => (
            <tr key={i} style={{ borderTop: "1px solid var(--border-subtle)" }}>
              <td style={{ ...cell, fontWeight: 700, width: 48 }}>{s.slot}</td>
              <td style={cell}><EntityLink id={s.id} name={s.name} /></td>
              <td style={cell}>{s.kind === "player" ? (s.best_game_date ? `best ${s.best_game_date.slice(5)}` : "no game") : `${s.games} games`}</td>
              <td style={num}>{s.score}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Replay() {
  const user = useCurrentUser();
  const [data, setData] = useState(undefined);
  const [week, setWeek] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    return fetch(`${API}${BASE}/results?scenario=replay`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : r.json().then(e => Promise.reject(e.detail))))
      .then(d => { setData(d); setWeek(null); setError(null); })
      .catch(e => { setData(null); setError(String(e || "Couldn't load")); });
  }, []);

  useEffect(() => { if (user?.isAdmin) load(); }, [user, load]);

  const post = async (path, body) => {
    setBusy(true);
    try {
      const r = await fetch(`${API}${BASE}/admin/league/replay/${path}`, {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}),
      });
      if (!r.ok) setError((await r.json()).detail);
      await load();
    } finally {
      setBusy(false);
    }
  };

  if (user === undefined) return <FantasyShell title="Replay" season={SEASON}><p style={{ fontSize: 13 }}>Checking…</p></FantasyShell>;
  if (!user?.isAdmin) return <FantasyShell title="Replay" season={SEASON}><p style={{ fontSize: 13 }}>Admins only.</p></FantasyShell>;

  const shown = data?.weeks?.find(w => w.week === (week ?? data.current_week)) ?? data?.weeks?.[data.weeks.length - 1];

  return (
    <FantasyShell title="Replay sandbox" season={SEASON}>
      <p style={{ fontSize: 14, marginBottom: 12 }}>
        A test league replaying the {data?.season ?? "2025-26"} NBA season with real box scores. Only games on or before the clock
        date count. Rosters come from a draft ranked on the season before, so nothing peeks ahead.
        Pick "Replay 2025-26" in the sidebar sandbox menu to see the other pages with this league.
      </p>

      <div style={{ ...box, display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <span style={{ fontSize: 16, fontWeight: 700, marginRight: 8 }}>
          {data ? fmtDate(data.as_of) : "…"}{data?.current_week ? ` · week ${data.current_week}` : ""}
        </span>
        <button disabled={busy} onClick={() => post("clock", { days: 1 })}>+1 day</button>
        <button disabled={busy} onClick={() => post("clock", { weeks: 1 })}>+1 week</button>
        <button disabled={busy} onClick={() => post("clock", { days: -1 })}>−1 day</button>
        <button disabled={busy} onClick={() => post("clock", { weeks: -1 })}>−1 week</button>
        <input type="date" disabled={busy} min={data?.season_start} max={data?.season_end}
          onChange={e => e.target.value && post("clock", { date: e.target.value })} />
        <button disabled={busy} onClick={() => post("reset")} style={{ marginLeft: "auto" }}>Reset: re-draft + back to opening week</button>
      </div>

      {error && <p style={{ fontSize: 14, color: "var(--accent-red)", marginBottom: 12 }}>{error}</p>}
      {data === undefined && <p style={{ fontSize: 13 }}>Loading…</p>}

      {data && data.weeks.length === 0 && <p style={{ fontSize: 14 }}>The clock is before opening week. Press "+1 day" or Reset.</p>}

      {shown && (
        <div style={box}>
          <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 10, flexWrap: "wrap" }}>
            <span style={heading}>Matchups</span>
            <select value={shown.week} onChange={e => setWeek(Number(e.target.value))} style={{ fontSize: 13 }}>
              {data.weeks.map(w => <option key={w.week} value={w.week}>{w.label} ({w.status === "final" ? "final" : "in progress"})</option>)}
            </select>
          </div>
          {shown.kind !== "regular" && <p style={{ fontSize: 14 }}>Playoff matchups aren't built yet.</p>}
          {shown.matchups.map((m, i) => (
            <div key={i} style={{ display: "flex", gap: 20, flexWrap: "wrap", padding: "10px 0", borderTop: i ? "1px solid var(--border)" : 0 }}>
              <Side side={m.home} />
              <Side side={m.away} align="right" />
            </div>
          ))}
        </div>
      )}

      {data && (
        <div style={box}>
          <div style={heading}>Standings (final weeks only)</div>
          <table style={{ width: "100%", fontSize: 14, borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <th style={cell}>#</th><th style={cell}>Team</th><th style={num}>Record</th>
                <th style={num} title="Total points scored">Pts For</th><th style={num} title="Total points scored against">Pts Against</th>
              </tr>
            </thead>
            <tbody>
              {data.standings.map((r, i) => (
                <tr key={r.team.id} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                  <td style={cell}>{i + 1}</td><td style={{ ...cell, fontWeight: 600 }}>{r.team.name}</td>
                  <td style={num}>{r.w}-{r.l}{r.t ? `-${r.t}` : ""}</td><td style={num}>{r.pf}</td><td style={num}>{r.pa}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </FantasyShell>
  );
}
