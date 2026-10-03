import { useCallback, useEffect, useMemo, useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { EntityLink } from "../../components/fantasy/links";
import { BASE, SEASON, useFantasyApi } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";

// Live snake draft. Server owns everything (GET /draft): order, picks, who's on the clock,
// the deadline, and auto-picks when a clock runs out. This page polls every few seconds and
// ticks the countdown locally. The commissioner (admin) can pick for whichever team is on
// the clock, auto-pick, and start/reset the draft.

const box = { border: "1px solid var(--border)", padding: 12, marginBottom: 14 };
const heading = { fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 8 };
const cell = { padding: "5px 8px", textAlign: "left", whiteSpace: "nowrap" };
const POLL_MS = 4000;

// Team ids in order with the one at `i` moved by `delta` (−1 up, +1 down).
const moved = (order, i, delta) => {
  const ids = order.map(t => t.id);
  [ids[i], ids[i + delta]] = [ids[i + delta], ids[i]];
  return ids;
};

const clock = ms => {
  const s = Math.max(0, Math.round(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};

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
  const [kind, setKind] = useState("player");
  const [search, setSearch] = useState("");

  const apply = useCallback(state => {
    setD(state);
    setSkew(Date.parse(state.server_time) - Date.now());
  }, []);

  const load = useCallback(() => (
    fetch(`${API}${BASE}/draft?scenario=${scenario}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : Promise.reject()))
      .then(apply)
      .catch(() => setD(null))
  ), [scenario, apply]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (d?.status !== "in_progress") return undefined;
    const poll = setInterval(load, POLL_MS);
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => { clearInterval(poll); clearInterval(tick); };
  }, [d?.status, load]);

  const post = async (path, body) => {
    setBusy(true); setError(null);
    try {
      const r = await fetch(`${API}${BASE}${path}?scenario=${scenario}`, {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}),
      });
      const out = await r.json();
      if (!r.ok) setError(out.detail || "Something went wrong"); else apply(out);
    } finally {
      setBusy(false);
    }
  };

  const taken = useMemo(() => new Set((d?.picks || []).map(p => p.id)), [d]);
  const pool = useMemo(() => {
    const list = kind === "player" ? players || [] : (nbaTeams || []).map(t => ({ ...t, position: "TEAM" }));
    const q = search.trim().toLowerCase();
    return list.filter(e => !taken.has(e.id) && (!q || e.name.toLowerCase().includes(q)))
      .sort((a, b) => b.fantasy_points - a.fantasy_points).slice(0, 60);
  }, [kind, players, nbaTeams, taken, search]);

  if (d === undefined) return <FantasyShell title="Draft" season={SEASON}><p style={{ fontSize: 13 }}>Loading…</p></FantasyShell>;
  if (d === null) return <FantasyShell title="Draft" season={SEASON}><p style={{ fontSize: 13 }}>Couldn't load the draft.</p></FantasyShell>;

  const isAdmin = !!user?.isAdmin;
  const running = d.status === "in_progress";
  const myTurn = running && user && d.on_clock?.owner_user_id === user.discordId;
  const canPick = running && (isAdmin || myTurn);
  const left = running ? Date.parse(d.deadline) - (now + skew) : 0;
  const slotsText = Object.entries(d.roster_slots).map(([k, v]) => `${v} ${k === "PLAYER" ? "player" : k === "TEAM" ? "NBA team" : k}${v > 1 ? "s" : ""}`).join(" + ");
  const n = d.order.length || 1;
  const board = Array.from({ length: d.rounds }, (_, r) => d.order.map((_, c) => d.picks[r * n + (r % 2 === 0 ? c : n - 1 - c)]));

  return (
    <FantasyShell title="Draft" season={SEASON}>
      <p style={{ fontSize: 14, marginBottom: 12 }}>
        Snake draft · {d.order.length} teams · {d.rounds} rounds ({slotsText}, no bench) · {Math.round(d.pick_seconds / 60)} minutes per pick —
        if the clock runs out, the best available player is picked automatically.
        {scenario !== "live" && <b> Sandbox: {scenario}.</b>}
      </p>

      {isAdmin && (
        <div style={{ ...box, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <span style={{ ...heading, marginBottom: 0 }}>Commissioner</span>
          {!running && <button disabled={busy} onClick={() => post("/admin/draft/start")}>{d.status === "not_started" ? "Start the draft" : "Restart the draft (clears rosters)"}</button>}
          {running && <button disabled={busy} onClick={() => post("/admin/draft/autopick")}>Auto-pick this pick</button>}
          {running && <button disabled={busy} onClick={() => post("/admin/draft/autodraft")}>Auto-draft the rest</button>}
          {scenario !== "live" && d.status !== "not_started" && <button disabled={busy} onClick={() => post("/admin/draft/reset")}>Reset (empty rosters)</button>}
        </div>
      )}

      {error && <p style={{ fontSize: 14, color: "var(--accent-red)", marginBottom: 12 }}>{error}</p>}

      {!running && (
        <div style={box}>
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8, flexWrap: "wrap" }}>
            <span style={{ ...heading, marginBottom: 0 }}>Draft order (round 1 — reverses every round)</span>
            {isAdmin && <button disabled={busy} onClick={() => post("/admin/draft/randomize")}>Randomize</button>}
          </div>
          <ol style={{ fontSize: 14, paddingLeft: 22, margin: 0 }}>
            {d.order.map((t, i) => (
              <li key={t.id} style={{ padding: "3px 0" }}>
                <span style={{ display: "inline-flex", gap: 8, alignItems: "center" }}>
                  <span style={{ minWidth: 150 }}>{t.name}</span>
                  {isAdmin && (
                    <>
                      <button disabled={busy || i === 0} aria-label={`Move ${t.name} up`}
                        onClick={() => post("/admin/draft/order", { team_ids: moved(d.order, i, -1) })}>↑</button>
                      <button disabled={busy || i === d.order.length - 1} aria-label={`Move ${t.name} down`}
                        onClick={() => post("/admin/draft/order", { team_ids: moved(d.order, i, 1) })}>↓</button>
                    </>
                  )}
                </span>
              </li>
            ))}
          </ol>
          {isAdmin && <p style={{ fontSize: 13, marginTop: 8 }}>Changes save immediately. Start uses this order; Reset keeps it.</p>}
        </div>
      )}

      {d.status === "not_started" && <p style={{ fontSize: 14, marginBottom: 14 }}>The draft hasn't started{isAdmin ? "." : " — the commissioner starts it."}</p>}
      {d.status === "complete" && <p style={{ fontSize: 14, marginBottom: 14 }}><b>The draft is complete.</b></p>}

      {running && d.on_clock && (
        <div style={{ border: "2px solid var(--text)", padding: 12, marginBottom: 14, display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 10, fontSize: 15 }}>
          <span>Pick {d.pick_number} of {d.total_picks} · Round {Math.ceil(d.pick_number / n)}</span>
          <span>On the clock: <b>{d.on_clock.name}</b>{myTurn ? " (you)" : isAdmin && !d.on_clock.owner_user_id ? " (you pick for this bot)" : ""}</span>
          <span style={{ fontWeight: 700, fontSize: 20, color: left < 60000 ? "var(--accent-red)" : "var(--text)" }}>{clock(left)}</span>
        </div>
      )}

      <div style={{ display: "flex", gap: 14, flexWrap: "wrap", alignItems: "flex-start" }}>
        <div style={{ ...box, flex: 1.2, minWidth: 320 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8, flexWrap: "wrap" }}>
            <span style={{ ...heading, marginBottom: 0 }}>Available</span>
            <button onClick={() => setKind("player")} style={{ fontWeight: kind === "player" ? 700 : 400, borderColor: kind === "player" ? "var(--text)" : "var(--border)" }}>Players</button>
            <button onClick={() => setKind("team")} style={{ fontWeight: kind === "team" ? 700 : 400, borderColor: kind === "team" ? "var(--text)" : "var(--border)" }}>NBA teams</button>
            <input placeholder="Search" value={search} onChange={e => setSearch(e.target.value)} style={{ marginLeft: "auto", fontSize: 13 }} />
          </div>
          <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <th style={cell}>Name</th><th style={cell}>{kind === "player" ? "Pos · NBA" : ""}</th>
                <th style={{ ...cell, textAlign: "right" }} title={kind === "player" ? "Fantasy points per game" : "Average point margin"}>{kind === "player" ? "Fantasy Pts" : "Margin"}</th>
                <th style={cell} />
              </tr>
            </thead>
            <tbody>
              {pool.map(e => (
                <tr key={e.id} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                  <td style={cell}><EntityLink id={e.id} name={e.name} /></td>
                  <td style={cell}>{kind === "player" ? `${e.position || "—"} · ${e.nba_team}` : ""}</td>
                  <td style={{ ...cell, textAlign: "right" }}>{e.fantasy_points}</td>
                  <td style={cell}>{canPick && <button disabled={busy} onClick={() => post("/draft/pick", { entity_id: e.id })}>Draft</button>}</td>
                </tr>
              ))}
              {pool.length === 0 && <tr><td colSpan={4} style={cell}>Nothing available.</td></tr>}
            </tbody>
          </table>
        </div>

        <div style={{ ...box, flex: 1, minWidth: 320, overflowX: "auto" }}>
          <div style={heading}>Draft board</div>
          <table style={{ fontSize: 13, borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <th style={cell}>Rd</th>
                {d.order.map(t => <th key={t.id} style={cell}>{t.name}</th>)}
              </tr>
            </thead>
            <tbody>
              {board.map((row, r) => (
                <tr key={r} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                  <td style={{ ...cell, fontWeight: 700 }}>{r + 1}</td>
                  {row.map((p, c) => (
                    <td key={c} style={cell}>{p ? <><EntityLink id={p.id} name={p.name} />{p.auto ? " (auto)" : ""}</> : ""}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </FantasyShell>
  );
}
