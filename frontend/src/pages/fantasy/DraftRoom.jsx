import { useCallback, useEffect, useMemo, useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { EntityLink } from "../../components/fantasy/links";
import { API_BASE, SEASON, useFantasyApi } from "../../components/fantasy/data";
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
  const [actAs, setActAs] = useState("");      // auction: commissioner bids/nominates as this team
  const [opening, setOpening] = useState(null); // auction: opening bid for a nomination
  const [bidAmount, setBidAmount] = useState(null);

  const apply = useCallback(state => {
    setD(state);
    setSkew(Date.parse(state.server_time) - Date.now());
  }, []);

  const load = useCallback(() => (
    fetch(`${API}${API_BASE}/draft?scenario=${scenario}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : Promise.reject()))
      .then(apply)
      .catch(() => setD(null))
  ), [scenario, apply]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (d?.status !== "in_progress") return undefined;
    // Auction bid clocks are short, so poll faster there.
    const poll = setInterval(load, d?.draft_type === "auction" ? 1500 : POLL_MS);
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => { clearInterval(poll); clearInterval(tick); };
  }, [d?.status, d?.draft_type, load]);

  const post = async (path, body) => {
    setBusy(true); setError(null);
    try {
      const r = await fetch(`${API}${API_BASE}${path}?scenario=${scenario}`, {
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
  // Board cell (round r, team column c) → the pick, following each round's direction from the server.
  const board = Array.from({ length: d.rounds }, (_, r) => d.order.map((_, c) => d.picks[r * n + (d.round_reversed?.[r] ? n - 1 - c : c)]));
  const typeName = { snake: "Snake draft", snake_3rr: "Snake draft with 3rd-round reversal", linear: "Normal draft (same order every round)", auction: "Auction draft" }[d.draft_type];
  const isAuction = d.draft_type === "auction";
  const auction = d.auction;
  const clockText = isAuction
    ? `$${auction.budget} budget, $${auction.min_bid} minimum bid, ${auction.nomination_seconds}s to nominate, bid clock resets to ${auction.bid_seconds}s on every bid`
    : d.pick_seconds_by_round?.length
      ? `per-round clocks (${d.pick_seconds_by_round.map(s => `${Math.round(s / 6) / 10}m`).join(", ")}, then ${Math.round(d.pick_seconds / 60)}m)`
      : `${Math.round(d.pick_seconds / 60 * 10) / 10} minutes per pick`;

  // Auction: who's acting. Owners act as their own team; the commissioner picks any team.
  const myTeam = d.order.find(t => user && t.owner_user_id === user.discordId);
  const actingId = isAdmin ? (actAs || myTeam?.id || d.order[0]?.id) : myTeam?.id;
  const lot = auction?.lot;
  const nominator = isAuction && auction?.phase === "nominating" ? d.on_clock : null;
  const canNominate = running && !!nominator && (isAdmin || nominator.owner_user_id === user?.discordId);
  const openBid = opening ?? auction?.min_bid ?? 1;
  const nextBid = lot ? Math.max(bidAmount ?? 0, lot.high_bid + 1) : 0;
  const myBudget = auction?.budgets.find(b => b.team_id === actingId);
  const rosterOf = id => d.picks.filter(p => p.team_id === id);

  return (
    <FantasyShell title="Draft" season={SEASON}>
      <p style={{ fontSize: 14, marginBottom: 12 }}>
        {typeName} · {d.order.length} teams · {d.rounds} rounds ({slotsText}, no bench) · {clockText} —
        if the clock runs out, the best available player is picked automatically.
        {scenario === "replay" && <b> 2025-26 test league.</b>}
        {scenario.startsWith("test_") && <b> Sandbox: {scenario}.</b>}
      </p>
      {d.status === "not_started" && d.draft_start_at && (
        <p style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>
          Starts {new Date(d.draft_start_at).toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}
          {isAdmin ? " — or press Start now." : "."}
        </p>
      )}

      {isAdmin && (
        <div style={{ ...box, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <span style={{ ...heading, marginBottom: 0 }}>Commissioner</span>
          {!running && <button disabled={busy} onClick={() => post("/admin/draft/start")}>{d.status === "not_started" ? "Start the draft" : "Restart the draft (clears rosters)"}</button>}
          {running && <button disabled={busy} onClick={() => post("/admin/draft/autopick")}>{!isAuction ? "Auto-pick this pick" : lot ? "Close bidding now" : "Auto-nominate now"}</button>}
          {running && <button disabled={busy} onClick={() => post("/admin/draft/autodraft")}>{isAuction ? "Finish the auction (each player to its nominator at the minimum)" : "Auto-draft the rest"}</button>}
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

      {running && isAuction && (
        <div style={{ border: "2px solid var(--text)", padding: 12, marginBottom: 14, fontSize: 15 }}>
          <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
            {lot ? (
              <span>Up for bid: <b><EntityLink id={lot.entity_id} name={lot.name} /></b> ({lot.position}) · high bid <b>${lot.high_bid}</b> by <b>{lot.high_team_name}</b> · nominated by {lot.nominated_by_name}</span>
            ) : (
              <span><b>{nominator?.name}</b> to nominate{nominator?.owner_user_id === user?.discordId ? " (you)" : isAdmin ? " (you can nominate for them)" : ""} — pick a player below</span>
            )}
            <span style={{ fontWeight: 700, fontSize: 20, color: left < 5000 ? "var(--accent-red)" : "var(--text)" }}>{clock(left)}</span>
          </div>
          {(isAdmin || myTeam) && (
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginTop: 10, fontSize: 14 }}>
              {isAdmin ? (
                <label>Act as{" "}
                  <select value={actingId || ""} onChange={e => setActAs(e.target.value)} style={{ fontSize: 14 }}>
                    {d.order.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                  </select>
                </label>
              ) : <span>You: <b>{myTeam.name}</b></span>}
              {myBudget && <span>${myBudget.remaining} left · max bid ${myBudget.max_bid} · {myBudget.open_spots} open spot{myBudget.open_spots === 1 ? "" : "s"}</span>}
              {lot && (
                <>
                  <input type="number" min={lot.high_bid + 1} value={nextBid} onChange={e => setBidAmount(Number(e.target.value) || 0)} style={{ width: 80, fontSize: 14 }} />
                  <button disabled={busy} onClick={() => post("/draft/bid", { amount: nextBid, team_id: actingId })}>Bid ${nextBid}</button>
                  <button disabled={busy} onClick={() => post("/draft/bid", { amount: lot.high_bid + 1, team_id: actingId })}>+1</button>
                  <button disabled={busy} onClick={() => post("/draft/bid", { amount: lot.high_bid + 5, team_id: actingId })}>+5</button>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {running && !isAuction && d.on_clock && (
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
          {canNominate && (
            <label style={{ display: "block", fontSize: 13, marginBottom: 8 }}>Opening bid ${" "}
              <input type="number" min={auction.min_bid} value={openBid} onChange={e => setOpening(Number(e.target.value) || 0)} style={{ width: 70, fontSize: 13 }} />
            </label>
          )}
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
                  <td style={cell}>
                    {!isAuction && canPick && <button disabled={busy} onClick={() => post("/draft/pick", { entity_id: e.id })}>Draft</button>}
                    {canNominate && <button disabled={busy} onClick={() => post("/draft/nominate", { entity_id: e.id, amount: openBid, team_id: nominator.id })}>Nominate ${openBid}</button>}
                  </td>
                </tr>
              ))}
              {pool.length === 0 && <tr><td colSpan={4} style={cell}>Nothing available.</td></tr>}
            </tbody>
          </table>
        </div>

        {isAuction ? (
          <div style={{ ...box, flex: 1, minWidth: 320, overflowX: "auto" }}>
            <div style={heading}>Teams</div>
            <table style={{ fontSize: 13, borderCollapse: "collapse", width: "100%" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {auction.budgets.map(b => <th key={b.team_id} style={cell}>{b.team_name}</th>)}
                </tr>
              </thead>
              <tbody>
                <tr>
                  {auction.budgets.map(b => <td key={b.team_id} style={cell}>${b.remaining} left · max ${b.max_bid}</td>)}
                </tr>
                {Array.from({ length: d.rounds }, (_, r) => (
                  <tr key={r} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                    {auction.budgets.map(b => {
                      const p = rosterOf(b.team_id)[r];
                      return <td key={b.team_id} style={cell}>{p ? <><EntityLink id={p.id} name={p.name} /> ${p.price}</> : ""}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
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
        )}
      </div>
    </FantasyShell>
  );
}
