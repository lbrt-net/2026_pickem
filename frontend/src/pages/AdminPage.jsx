import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { API, getTeamStyle, STRIPE_POINTS } from "../utils/helpers";

function Pip({ filled, color }) {
  return (
    <div style={{
      width: 10, height: 10, borderRadius: "50%", flexShrink: 0,
      background: filled ? color : "rgba(255,255,255,0.08)",
      border: filled ? "none" : `1px solid ${color}44`,
    }} />
  );
}

function WinsControl({ label, wins, color, onChange, disabled }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", width: 80, flexShrink: 0 }}>{label}</span>
      <div style={{ display: "flex", gap: 4 }}>
        {[0, 1, 2, 3, 4].map(n => (
          <button key={n} onClick={() => !disabled && onChange(n === wins ? n - 1 : n)}
            style={{
              width: 28, height: 24, borderRadius: 4, cursor: disabled ? "default" : "pointer",
              border: `1px solid ${wins >= n + 1 ? color : "rgba(255,255,255,0.12)"}`,
              background: wins >= n + 1 ? `${color}22` : "transparent",
              color: wins >= n + 1 ? color : "rgba(255,255,255,0.25)",
              fontSize: 12, fontWeight: wins >= n + 1 ? 700 : 400,
            }}>{n + 1}</button>
        ))}
      </div>
      <span style={{ fontSize: 13, fontWeight: 700, color, minWidth: 16 }}>{wins}</span>
    </div>
  );
}

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
      <textarea
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder="One player per line"
        rows={6}
        style={{
          width: "100%", background: "#0d1421", border: "1px solid #2a3347",
          borderRadius: 6, color: "#e2e8f0", fontSize: 11, padding: "6px 8px",
          resize: "vertical", fontFamily: "inherit", lineHeight: 1.6,
        }}
      />
      <button onClick={handleSave} style={{
        marginTop: 4, width: "100%", padding: "5px 0", fontSize: 11,
        background: saved ? "rgba(74,222,128,0.1)" : "transparent",
        border: `1px solid ${saved ? "#4ade80" : "rgba(251,191,36,0.3)"}`,
        color: saved ? "#4ade80" : "#fbbf24", borderRadius: 4, cursor: "pointer",
      }}>{saved ? "Saved ✓" : `Save ${team}`}</button>
    </div>
  );
}

function MatchupAdmin({ matchup, rosters, onSaveRoster }) {
  const [winsA, setWinsA] = useState(matchup.wins_a || 0);
  const [winsB, setWinsB] = useState(matchup.wins_b || 0);
  const [winner, setWinner] = useState(matchup.winner_result || "");
  const [games, setGames] = useState(matchup.games_result || "");
  const [statLeader, setStatLeader] = useState(matchup.stat_leader_result || "");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  const teamA = matchup.team_a || "TBD";
  const teamB = matchup.team_b || "TBD";
  const sA = getTeamStyle(teamA, matchup.conference?.toLowerCase());
  const sB = getTeamStyle(teamB, matchup.conference?.toLowerCase());
  const players = [...(rosters[teamA] || []), ...(rosters[teamB] || [])].filter((p, i, a) => a.indexOf(p) === i).sort();

  async function saveWins(wa, wb) {
    setWinsA(wa); setWinsB(wb);
    await fetch(`${API}/admin/matchups/${matchup.id}/wins`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ wins_a: wa, wins_b: wb }),
    });
  }

  async function saveResult() {
    if (!winner) { setMsg("Pick a winner first"); return; }
    setSaving(true);
    await fetch(`${API}/admin/matchups/${matchup.id}/result`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ winner, games: Number(games) || 0, stat_leader: statLeader }),
    });
    setSaving(false);
    setMsg("Result saved ✓");
    setTimeout(() => setMsg(""), 2000);
  }

  async function clearResult() {
    await fetch(`${API}/admin/matchups/${matchup.id}/result`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ winner: "", games: 0, stat_leader: "" }),
    });
    setWinner(""); setGames(""); setStatLeader("");
    setMsg("Result cleared");
    setTimeout(() => setMsg(""), 2000);
  }

  const hasResult = !!matchup.winner_result;

  return (
    <div style={{
      background: "#111827", border: "1px solid #1f2937", borderRadius: 10,
      overflow: "hidden", marginBottom: 12,
    }}>
      {/* Header */}
      <div style={{ padding: "8px 14px", background: "#0d1421", borderBottom: "1px solid #1f2937", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: "#e2e8f0" }}>{matchup.label}</span>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          {hasResult && <span style={{ fontSize: 10, color: "#4ade80", background: "rgba(74,222,128,0.1)", border: "1px solid rgba(74,222,128,0.3)", borderRadius: 3, padding: "1px 6px" }}>Result set</span>}
          <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)" }}>{matchup.conference} · R{matchup.round}</span>
        </div>
      </div>

      <div style={{ padding: "12px 14px", display: "flex", flexDirection: "column", gap: 12 }}>

        {/* Team rows with pips */}
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 32, height: 32, background: sA.seedBg, borderRadius: 4, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <span style={{ fontSize: 14, fontWeight: 700, color: "#fff" }}>{matchup.seed_a}</span>
            </div>
            <span style={{ fontSize: 13, fontWeight: 600, color: "#fff", flex: 1 }}>{teamA}</span>
            <div style={{ display: "flex", gap: 3 }}>
              {[0,1,2,3].map(i => <Pip key={i} filled={i < winsA} color={sA.pipFill} />)}
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 32, height: 32, background: sB.seedBg, borderRadius: 4, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <span style={{ fontSize: 14, fontWeight: 700, color: "#fff" }}>{matchup.seed_b}</span>
            </div>
            <span style={{ fontSize: 13, fontWeight: 600, color: "#fff", flex: 1 }}>{teamB}</span>
            <div style={{ display: "flex", gap: 3 }}>
              {[0,1,2,3].map(i => <Pip key={i} filled={i < winsB} color={sB.pipFill} />)}
            </div>
          </div>
        </div>

        {/* Wins controls */}
        <div style={{ background: "#0d1421", borderRadius: 6, padding: "10px 12px", display: "flex", flexDirection: "column", gap: 8 }}>
          <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Series score</span>
          <WinsControl label={teamA} wins={winsA} color={sA.pipFill} onChange={wa => saveWins(wa < 0 ? 0 : wa, winsB)} />
          <WinsControl label={teamB} wins={winsB} color={sB.pipFill} onChange={wb => saveWins(winsA, wb < 0 ? 0 : wb)} />
        </div>

        {/* Result section */}
        <div style={{ background: "#0d1421", borderRadius: 6, padding: "10px 12px", display: "flex", flexDirection: "column", gap: 8 }}>
          <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Official result</span>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", width: 50, flexShrink: 0 }}>Winner</span>
            <select value={winner} onChange={e => setWinner(e.target.value)}
              style={{ flex: 1, background: "#111827", border: "1px solid #2a3347", borderRadius: 4, color: "#e2e8f0", fontSize: 12, padding: "4px 6px" }}>
              <option value="">— select —</option>
              {matchup.team_a && <option value={matchup.team_a}>{teamA}</option>}
              {matchup.team_b && <option value={matchup.team_b}>{teamB}</option>}
            </select>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", width: 50, flexShrink: 0 }}>Games</span>
            <div style={{ display: "flex", gap: 3 }}>
              {[4,5,6,7].map(g => (
                <button key={g} onClick={() => setGames(games === g ? "" : g)}
                  style={{ width: 28, height: 24, borderRadius: 4, border: `1px solid ${games === g ? "#fbbf24" : "rgba(255,255,255,0.12)"}`, background: games === g ? "rgba(251,191,36,0.15)" : "transparent", color: games === g ? "#fbbf24" : "rgba(255,255,255,0.35)", fontSize: 12, fontWeight: games === g ? 700 : 400, cursor: "pointer" }}>{g}</button>
              ))}
            </div>
          </div>
          {players.length > 0 && (
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", width: 50, flexShrink: 0 }}>{matchup.stat_label || "Stat"}</span>
              <select value={statLeader} onChange={e => setStatLeader(e.target.value)}
                style={{ flex: 1, background: "#111827", border: "1px solid #2a3347", borderRadius: 4, color: "#e2e8f0", fontSize: 12, padding: "4px 6px" }}>
                <option value="">— select —</option>
                {players.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
          )}
          <div style={{ display: "flex", gap: 6, marginTop: 2 }}>
            <button onClick={saveResult} disabled={saving}
              style={{ flex: 1, padding: "6px 0", fontSize: 12, borderRadius: 4, cursor: "pointer", background: "rgba(74,222,128,0.1)", border: "1px solid rgba(74,222,128,0.3)", color: "#4ade80" }}>
              {saving ? "Saving..." : "Save result"}
            </button>
            {hasResult && (
              <button onClick={clearResult}
                style={{ padding: "6px 12px", fontSize: 12, borderRadius: 4, cursor: "pointer", background: "transparent", border: "1px solid rgba(248,113,113,0.3)", color: "#f87171" }}>
                Clear
              </button>
            )}
          </div>
          {msg && <span style={{ fontSize: 11, color: "#4ade80" }}>{msg}</span>}
        </div>

        {/* Rosters */}
        {(matchup.team_a || matchup.team_b) && (
          <div style={{ background: "#0d1421", borderRadius: 6, padding: "10px 12px" }}>
            <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", marginBottom: 8 }}>Rosters</span>
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

export default function AdminPage() {
  const navigate = useNavigate();
  const [matchups, setMatchups] = useState([]);
  const [rosters, setRosters] = useState({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    Promise.all([
      fetch(`${API}/admin/matchups`, { credentials: "include" }).then(r => {
        if (r.status === 403) { navigate("/"); return []; }
        return r.json();
      }),
      fetch(`${API}/rosters`).then(r => r.json()),
    ]).then(([m, r]) => {
      setMatchups(m);
      setRosters(r);
      setLoading(false);
    });
  }, []);

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
        ) : (
          filtered.map(m => (
            <MatchupAdmin key={m.id} matchup={m} rosters={rosters} onSaveRoster={handleSaveRoster} />
          ))
        )}
      </div>
    </div>
  );
}