import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { API, getTeamStyle } from "../utils/helpers";

/* ── Pip ───────────────────────────────────────────────────────────────── */
function Pip({ filled, color }) {
  return (
    <div style={{
      width: 10, height: 10, borderRadius: "50%", flexShrink: 0,
      background: filled ? color : "rgba(255,255,255,0.08)",
      border: filled ? "none" : `1px solid ${color}44`,
    }} />
  );
}

/* ── WinsControl ───────────────────────────────────────────────────────── */
function WinsControl({ label, wins, color, onChange }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", width: 80, flexShrink: 0 }}>{label}</span>
      <div style={{ display: "flex", gap: 4 }}>
        {[0, 1, 2, 3, 4].map(n => (
          <button key={n} onClick={() => onChange(n)}
            style={{
              width: 28, height: 24, borderRadius: 4, cursor: "pointer",
              border: `1px solid ${wins === n ? color : "rgba(255,255,255,0.12)"}`,
              background: wins === n ? `${color}22` : "transparent",
              color: wins === n ? color : "rgba(255,255,255,0.25)",
              fontSize: 12, fontWeight: wins === n ? 700 : 400,
            }}>{n}</button>
        ))}
      </div>
    </div>
  );
}

/* ── MatchupEditor ─────────────────────────────────────────────────────── */
function MatchupEditor({ matchup, onSaved }) {
  const [open, setOpen] = useState(false);
  const [teamA, setTeamA] = useState(matchup.team_a || "");
  const [teamB, setTeamB] = useState(matchup.team_b || "");
  const [seedA, setSeedA] = useState(matchup.seed_a ?? "");
  const [seedB, setSeedB] = useState(matchup.seed_b ?? "");
  const [gameTime, setGameTime] = useState(matchup.game_time || "");
  const [statLabel, setStatLabel] = useState(matchup.stat_label || "");
  // home_net_rating: team_a's net rating differential at home vs this opponent.
  // Positive = team_a favored at home. Drives the series probability chart on The Field.
  const [homeNetRating, setHomeNetRating] = useState(
    matchup.home_net_rating != null ? String(matchup.home_net_rating) : ""
  );
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState("");

  async function save() {
    setErr("");
    const res = await fetch(`${API}/admin/matchups`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id: matchup.id,
        label: matchup.label,
        team_a: teamA || null,
        team_b: teamB || null,
        seed_a: seedA !== "" ? Number(seedA) : null,
        seed_b: seedB !== "" ? Number(seedB) : null,
        conference: matchup.conference,
        round: matchup.round,
        stat_label: statLabel || null,
        game_time: gameTime || null,
        home_net_rating: homeNetRating !== "" ? parseFloat(homeNetRating) : null,
      }),
    });
    if (res.ok) {
      setSaved(true);
      setTimeout(() => { setSaved(false); onSaved?.(); }, 1200);
    } else {
      const body = await res.json().catch(() => ({}));
      setErr(body.detail || "Save failed");
    }
  }

  const Row = ({ label: lbl, children }) => (
    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
      <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", width: 76, flexShrink: 0 }}>{lbl}</span>
      {children}
    </div>
  );

  const inputStyle = { background: "#111827", border: "1px solid #2a3347", borderRadius: 4, color: "#e2e8f0", fontSize: 12, padding: "4px 6px" };

  return (
    <div style={{ background: "#0d1421", borderRadius: 6, overflow: "hidden" }}>
      <button onClick={() => setOpen(o => !o)} style={{
        width: "100%", padding: "7px 12px", background: "transparent", border: "none",
        borderBottom: open ? "1px solid #1f2937" : "none",
        color: "rgba(255,255,255,0.3)", fontSize: 10, textTransform: "uppercase",
        letterSpacing: "0.08em", cursor: "pointer", textAlign: "left",
        display: "flex", justifyContent: "space-between",
      }}>
        <span>Edit matchup</span><span>{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div style={{ padding: "10px 12px", display: "flex", flexDirection: "column", gap: 8 }}>
          <Row label="Team A">
            <input value={teamA} onChange={e => setTeamA(e.target.value)}
              placeholder="e.g. Boston" style={{ ...inputStyle, flex: 1 }} />
          </Row>
          <Row label="Team B">
            <input value={teamB} onChange={e => setTeamB(e.target.value)}
              placeholder="e.g. Philadelphia" style={{ ...inputStyle, flex: 1 }} />
          </Row>
          <div style={{ display: "flex", gap: 8 }}>
            {[["Seed A", seedA, setSeedA], ["Seed B", seedB, setSeedB]].map(([lbl, val, set]) => (
              <Row key={lbl} label={lbl}>
                <input type="number" min={1} max={8} value={val} onChange={e => set(e.target.value)}
                  style={{ ...inputStyle, flex: 1, width: 0 }} />
              </Row>
            ))}
          </div>
          <Row label="Tip-off (CT)">
            <input type="datetime-local" value={gameTime} onChange={e => setGameTime(e.target.value)}
              style={{ ...inputStyle, flex: 1 }} />
          </Row>
          <Row label="Stat label">
            <input value={statLabel} onChange={e => setStatLabel(e.target.value)}
              placeholder="e.g. Drives" style={{ ...inputStyle, flex: 1 }} />
          </Row>
          <Row label="Home NR">
            <input type="number" step="0.1" value={homeNetRating}
              onChange={e => setHomeNetRating(e.target.value)}
              placeholder="e.g. 8.5 or -3.2"
              style={{ ...inputStyle, flex: 1 }} />
          </Row>
          <div style={{ fontSize: 10, color: "rgba(255,255,255,0.2)", marginLeft: 84 }}>
            Team A net rating at home (pos = A favored). Drives series probability chart.
          </div>
          {err && <div style={{ fontSize: 11, color: "#f87171" }}>{err}</div>}
          <button onClick={save} style={{
            width: "100%", padding: "6px 0", fontSize: 12, borderRadius: 4, cursor: "pointer",
            background: saved ? "rgba(74,222,128,0.1)" : "transparent",
            border: `1px solid ${saved ? "#4ade80" : "rgba(251,191,36,0.3)"}`,
            color: saved ? "#4ade80" : "#fbbf24",
          }}>{saved ? "Saved ✓" : "Save matchup"}</button>
        </div>
      )}
    </div>
  );
}

/* ── RosterPanel ───────────────────────────────────────────────────────── */
function RosterPanel({ team, rosters, onSave }) {
  const [text, setText] = useState((rosters[team] || []).join("\n"));
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setText((rosters[team] || []).join("\n"));
  }, [team, rosters]);

  function handleSave() {
    const players = text.split("\n").map(s => s.trim()).filter(Boolean);
    onSave(team, players);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  }

  return (
    <div style={{ flex: 1 }}>
      <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", marginBottom: 4 }}>{team}</div>
      <textarea value={text} onChange={e => setText(e.target.value)}
        placeholder="One player per line" rows={6}
        style={{ width: "100%", background: "#111827", border: "1px solid #2a3347", borderRadius: 6, color: "#e2e8f0", fontSize: 11, padding: "6px 8px", resize: "vertical", fontFamily: "inherit", lineHeight: 1.6, boxSizing: "border-box" }} />
      <button onClick={handleSave} style={{
        marginTop: 4, width: "100%", padding: "5px 0", fontSize: 11, cursor: "pointer",
        background: saved ? "rgba(74,222,128,0.1)" : "transparent",
        border: `1px solid ${saved ? "#4ade80" : "rgba(251,191,36,0.3)"}`,
        color: saved ? "#4ade80" : "#fbbf24", borderRadius: 4,
      }}>{saved ? "Saved ✓" : `Save ${team}`}</button>
    </div>
  );
}

/* ── StatGameLog ───────────────────────────────────────────────────────── */
// rosters prop threads through both team rosters so every player is pre-populated
// at 0 for each game tab. Saved values override 0. Dimmed text = default/unsaved.
function StatGameLog({ matchup, winsA, winsB, rosters }) {
  const totalGames = winsA + winsB;
  const numGames = Math.max(totalGames, 1);

  const [selectedGame, setSelectedGame] = useState(numGames);
  const [log, setLog] = useState(() => {
    try { return JSON.parse(matchup.stat_game_log || "{}"); } catch { return {}; }
  });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setSelectedGame(Math.max(winsA + winsB, 1));
  }, [winsA, winsB]);

  // All players from both rosters, deduped and sorted alphabetically
  const teamA = matchup.team_a || "";
  const teamB = matchup.team_b || "";
  const allPlayers = [...(rosters[teamA] || []), ...(rosters[teamB] || [])]
    .filter((p, i, a) => a.indexOf(p) === i)
    .sort();

  // Saved rows for this game
  const savedRows = log[String(selectedGame)] || [];
  const savedNames = new Set(savedRows.map(r => r.name?.trim()).filter(Boolean));

  // Default rows: roster players not yet in saved rows, shown at 0 (dimmed)
  const defaultRows = allPlayers
    .filter(p => !savedNames.has(p))
    .map(p => ({ name: p, value: 0 }));

  // Merged: saved rows first (editable, full opacity), then defaults (dimmed)
  const gameRows = [...savedRows, ...defaultRows];

  function updateRow(idx, field, value) {
    setLog(prev => {
      const saved = [...(prev[String(selectedGame)] || [])];
      if (idx < saved.length) {
        // Already a saved row — update in place
        saved[idx] = { ...saved[idx], [field]: value };
        return { ...prev, [String(selectedGame)]: saved };
      } else {
        // Default row being edited — promote into saved rows
        const defaultIdx = idx - saved.length;
        const playerName = allPlayers.filter(p => !new Set(saved.map(r => r.name?.trim())).has(p))[defaultIdx];
        const promoted = { name: playerName, value: 0, [field]: value };
        return { ...prev, [String(selectedGame)]: [...saved, promoted] };
      }
    });
  }

  function removeRow(idx) {
    setLog(prev => {
      const rows = [...(prev[String(selectedGame)] || [])];
      if (idx < rows.length) {
        rows.splice(idx, 1);
        return { ...prev, [String(selectedGame)]: rows };
      }
      // Clicking × on a default row is a no-op — it'll reappear from roster
      return prev;
    });
  }

  async function saveLog() {
    await fetch(`${API}/admin/matchups/${matchup.id}/stat-log`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ log }),
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  }

  return (
    <div style={{ background: "#0d1421", borderRadius: 6, padding: "10px 12px" }}>
      <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: 8 }}>
        Stat Log{matchup.stat_label ? ` — ${matchup.stat_label}` : ""}
      </span>

      {/* Game tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 10, flexWrap: "wrap" }}>
        {Array.from({ length: numGames }, (_, i) => i + 1).map(g => (
          <button key={g} onClick={() => setSelectedGame(g)} style={{
            padding: "3px 10px", fontSize: 11, borderRadius: 4, cursor: "pointer",
            border: `1px solid ${selectedGame === g ? "#fbbf24" : "rgba(255,255,255,0.12)"}`,
            background: selectedGame === g ? "rgba(251,191,36,0.12)" : "transparent",
            color: selectedGame === g ? "#fbbf24" : "rgba(255,255,255,0.35)",
          }}>G{g}</button>
        ))}
      </div>

      {/* Rows */}
      <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 8 }}>
        {gameRows.length === 0 && (
          <div style={{ fontSize: 11, color: "rgba(255,255,255,0.2)", textAlign: "center", padding: "8px 0" }}>
            No roster loaded — add players in Rosters section first.
          </div>
        )}
        {gameRows.map((row, idx) => {
          const isDefault = idx >= savedRows.length;
          return (
            <div key={`${row.name}-${idx}`} style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <input value={row.name} onChange={e => updateRow(idx, "name", e.target.value)}
                placeholder="Player name"
                style={{ flex: 1, background: "#111827", border: "1px solid #2a3347", borderRadius: 4, color: isDefault ? "rgba(255,255,255,0.35)" : "#e2e8f0", fontSize: 11, padding: "4px 6px" }} />
              <input value={row.value} onChange={e => updateRow(idx, "value", e.target.value)}
                placeholder="0" type="number"
                style={{ width: 64, background: "#111827", border: "1px solid #2a3347", borderRadius: 4, color: isDefault ? "rgba(255,255,255,0.3)" : "#e2e8f0", fontSize: 11, padding: "4px 6px", textAlign: "right" }} />
              <button onClick={() => removeRow(idx)} style={{
                background: "transparent", border: "none", color: "rgba(248,113,113,0.5)",
                cursor: "pointer", fontSize: 16, lineHeight: 1, padding: "0 2px", flexShrink: 0,
              }}>×</button>
            </div>
          );
        })}
      </div>

      <div style={{ display: "flex", gap: 6 }}>
        <button onClick={saveLog} style={{
          flex: 1, padding: "5px 0", fontSize: 11,
          background: saved ? "rgba(74,222,128,0.1)" : "transparent",
          border: `1px solid ${saved ? "#4ade80" : "rgba(251,191,36,0.3)"}`,
          color: saved ? "#4ade80" : "#fbbf24", borderRadius: 4, cursor: "pointer",
        }}>{saved ? "Saved ✓" : "Save log"}</button>
      </div>
    </div>
  );
}

/* ── MatchupAdmin ──────────────────────────────────────────────────────── */
function MatchupAdmin({ matchup, rosters, onSaveRoster, onRefresh }) {
  const [winsA, setWinsA] = useState(matchup.wins_a ?? 0);
  const [winsB, setWinsB] = useState(matchup.wins_b ?? 0);
  const [winsSaving, setWinsSaving] = useState(false);
  const [winsSaved, setWinsSaved] = useState(false);

  const [winner, setWinner] = useState(matchup.winner_result || "");
  const [games, setGames] = useState(matchup.games_result || "");
  const [statLeaders, setStatLeaders] = useState(
    matchup.stat_leader_result
      ? matchup.stat_leader_result.split(",").map(s => s.trim()).join("\n")
      : ""
  );
  const [resultSaving, setResultSaving] = useState(false);
  const [resultMsg, setResultMsg] = useState("");

  const teamA = matchup.team_a || "TBD";
  const teamB = matchup.team_b || "TBD";
  const sA = getTeamStyle(teamA, matchup.conference?.toLowerCase());
  const sB = getTeamStyle(teamB, matchup.conference?.toLowerCase());
  const hasResult = !!matchup.winner_result;

  async function saveWins() {
    setWinsSaving(true);
    await fetch(`${API}/admin/matchups/${matchup.id}/wins`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ wins_a: winsA, wins_b: winsB }),
    });
    setWinsSaving(false);
    setWinsSaved(true);
    setTimeout(() => setWinsSaved(false), 1500);
  }

  async function saveResult() {
    if (!winner) { setResultMsg("Pick a winner first"); return; }
    setResultSaving(true);
    const statLeaderValue = statLeaders.split("\n").map(s => s.trim()).filter(Boolean).join(",");
    const res = await fetch(`${API}/admin/matchups/${matchup.id}/result`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ winner, games: Number(games) || 0, stat_leader: statLeaderValue }),
    });
    setResultSaving(false);
    if (res.ok) {
      setResultMsg("Result saved ✓");
    } else {
      const body = await res.json().catch(() => ({}));
      setResultMsg(body.detail || "Save failed");
    }
    setTimeout(() => setResultMsg(""), 2500);
  }

  async function clearResult() {
    await fetch(`${API}/admin/matchups/${matchup.id}/result`, {
      method: "DELETE", credentials: "include",
    });
    setWinner(""); setGames(""); setStatLeaders("");
    setResultMsg("Result cleared");
    setTimeout(() => setResultMsg(""), 2000);
  }

  return (
    <div style={{ background: "#111827", border: "1px solid #1f2937", borderRadius: 10, overflow: "hidden", marginBottom: 12 }}>

      <div style={{ padding: "8px 14px", background: "#0d1421", borderBottom: "1px solid #1f2937", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: "#e2e8f0" }}>{matchup.label}</span>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          {hasResult && (
            <span style={{ fontSize: 10, color: "#4ade80", background: "rgba(74,222,128,0.1)", border: "1px solid rgba(74,222,128,0.3)", borderRadius: 3, padding: "1px 6px" }}>
              Result set
            </span>
          )}
          <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)" }}>
            {matchup.conference} · R{matchup.round}
          </span>
        </div>
      </div>

      <div style={{ padding: "12px 14px", display: "flex", flexDirection: "column", gap: 10 }}>

        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {[
            { team: teamA, seed: matchup.seed_a, wins: winsA, s: sA },
            { team: teamB, seed: matchup.seed_b, wins: winsB, s: sB },
          ].map(({ team, seed, wins, s }) => (
            <div key={team} style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 32, height: 32, background: s.seedBg, borderRadius: 4, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <span style={{ fontSize: 14, fontWeight: 700, color: "#fff" }}>{seed}</span>
              </div>
              <span style={{ fontSize: 13, fontWeight: 600, color: "#fff", flex: 1 }}>{team}</span>
              <div style={{ display: "flex", gap: 3 }}>
                {[0, 1, 2, 3].map(i => <Pip key={i} filled={i < wins} color={s.pipFill} />)}
              </div>
            </div>
          ))}
        </div>

        <div style={{ background: "#0d1421", borderRadius: 6, padding: "10px 12px", display: "flex", flexDirection: "column", gap: 8 }}>
          <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Series score</span>
          <WinsControl label={teamA} wins={winsA} color={sA.pipFill} onChange={setWinsA} />
          <WinsControl label={teamB} wins={winsB} color={sB.pipFill} onChange={setWinsB} />
          <button onClick={saveWins} disabled={winsSaving} style={{
            width: "100%", padding: "5px 0", fontSize: 11, borderRadius: 4, cursor: "pointer",
            background: winsSaved ? "rgba(74,222,128,0.1)" : "transparent",
            border: `1px solid ${winsSaved ? "#4ade80" : "rgba(255,255,255,0.15)"}`,
            color: winsSaved ? "#4ade80" : "rgba(255,255,255,0.4)",
          }}>{winsSaving ? "Saving..." : winsSaved ? "Saved ✓" : "Save series score"}</button>
        </div>

        <MatchupEditor matchup={matchup} onSaved={onRefresh} />

        <div style={{ background: "#0d1421", borderRadius: 6, padding: "10px 12px", display: "flex", flexDirection: "column", gap: 8 }}>
          <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Official result</span>

          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", width: 56, flexShrink: 0 }}>Winner</span>
            <select value={winner} onChange={e => setWinner(e.target.value)}
              style={{ flex: 1, background: "#111827", border: "1px solid #2a3347", borderRadius: 4, color: "#e2e8f0", fontSize: 12, padding: "4px 6px" }}>
              <option value="">— select —</option>
              {matchup.team_a && <option value={matchup.team_a}>{teamA}</option>}
              {matchup.team_b && <option value={matchup.team_b}>{teamB}</option>}
            </select>
          </div>

          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", width: 56, flexShrink: 0 }}>Games</span>
            <div style={{ display: "flex", gap: 3 }}>
              {[4, 5, 6, 7].map(g => (
                <button key={g} onClick={() => setGames(games === g ? "" : g)} style={{
                  width: 28, height: 24, borderRadius: 4, cursor: "pointer",
                  border: `1px solid ${games === g ? "#fbbf24" : "rgba(255,255,255,0.12)"}`,
                  background: games === g ? "rgba(251,191,36,0.15)" : "transparent",
                  color: games === g ? "#fbbf24" : "rgba(255,255,255,0.35)",
                  fontSize: 12, fontWeight: games === g ? 700 : 400,
                }}>{g}</button>
              ))}
            </div>
          </div>

          <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
            <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", width: 56, flexShrink: 0, paddingTop: 4 }}>
              {matchup.stat_label || "Stat"}
            </span>
            <div style={{ flex: 1 }}>
              <textarea
                value={statLeaders}
                onChange={e => setStatLeaders(e.target.value)}
                placeholder={"One name per line\n(multiple = tied)"}
                rows={3}
                style={{ width: "100%", background: "#111827", border: "1px solid #2a3347", borderRadius: 4, color: "#e2e8f0", fontSize: 11, padding: "4px 6px", resize: "vertical", fontFamily: "inherit", lineHeight: 1.7, boxSizing: "border-box" }}
              />
              <div style={{ fontSize: 10, color: "rgba(255,255,255,0.2)", marginTop: 2 }}>
                Multiple names = tied (any counts as correct). Case insensitive.
              </div>
            </div>
          </div>

          <div style={{ display: "flex", gap: 6 }}>
            <button onClick={saveResult} disabled={resultSaving} style={{
              flex: 1, padding: "6px 0", fontSize: 12, borderRadius: 4, cursor: "pointer",
              background: "rgba(74,222,128,0.1)", border: "1px solid rgba(74,222,128,0.3)", color: "#4ade80",
            }}>{resultSaving ? "Saving..." : "Save result"}</button>
            {hasResult && (
              <button onClick={clearResult} style={{
                padding: "6px 12px", fontSize: 12, borderRadius: 4, cursor: "pointer",
                background: "transparent", border: "1px solid rgba(248,113,113,0.3)", color: "#f87171",
              }}>Clear</button>
            )}
          </div>
          {resultMsg && (
            <span style={{ fontSize: 11, color: resultMsg.includes("✓") || resultMsg.includes("cleared") ? "#4ade80" : "#f87171" }}>
              {resultMsg}
            </span>
          )}
        </div>

        {/* rosters threaded through so StatGameLog can pre-populate all players */}
        <StatGameLog matchup={matchup} winsA={winsA} winsB={winsB} rosters={rosters} />

        {(matchup.team_a || matchup.team_b) && (
          <div style={{ background: "#0d1421", borderRadius: 6, padding: "10px 12px" }}>
            <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: 8 }}>
              Rosters
            </span>
            <div style={{ display: "flex", gap: 10 }}>
              {matchup.team_a && <RosterPanel team={matchup.team_a} rosters={rosters} onSave={onSaveRoster} />}
              {matchup.team_b && <RosterPanel team={matchup.team_b} rosters={rosters} onSave={onSaveRoster} />}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

/* ── AdminPage ─────────────────────────────────────────────────────────── */
export default function AdminPage() {
  const navigate = useNavigate();
  const [matchups, setMatchups] = useState([]);
  const [rosters, setRosters] = useState({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  const load = useCallback(() => {
    Promise.all([
      fetch(`${API}/admin/matchups`, { credentials: "include" }).then(r => {
        if (r.status === 403) { navigate("/"); return []; }
        return r.json();
      }),
      fetch(`${API}/rosters`).then(r => r.json()),
    ]).then(([m, r]) => {
      setMatchups(Array.isArray(m) ? m : []);
      setRosters(r);
      setLoading(false);
    });
  }, [navigate]);

  useEffect(() => { load(); }, [load]);

  function handleSaveRoster(team, players) {
    fetch(`${API}/admin/rosters`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ team_name: team, players }),
    }).then(() => setRosters(prev => ({ ...prev, [team]: players })));
  }

  const rounds = ["all", "1", "2", "3", "4"];
  const filtered = filter === "all" ? matchups : matchups.filter(m => String(m.round) === filter);

  return (
    <div className="app">
      <div className="topbar">
        <button className="lb-btn" onClick={() => navigate("/")}>← Back</button>
        <span className="site-title">Admin</span>
        <div style={{ display: "flex", gap: 6 }}>
          {rounds.map(r => (
            <button key={r} className={`tab ${filter === r ? "active" : ""}`}
              style={{ padding: "4px 10px", fontSize: 11 }}
              onClick={() => setFilter(r)}>
              {r === "all" ? "All" : `R${r}`}
            </button>
          ))}
        </div>
      </div>

      <div style={{ padding: "12px", maxWidth: 800, margin: "0 auto" }}>
        {loading ? (
          <div style={{ color: "rgba(255,255,255,0.4)", textAlign: "center", padding: 40 }}>Loading...</div>
        ) : filtered.length === 0 ? (
          <div style={{ color: "rgba(255,255,255,0.25)", textAlign: "center", padding: 40 }}>No matchups for this round.</div>
        ) : (
          filtered.map(m => (
            <MatchupAdmin
              key={m.id}
              matchup={m}
              rosters={rosters}
              onSaveRoster={handleSaveRoster}
              onRefresh={load}
            />
          ))
        )}
      </div>
    </div>
  );
}