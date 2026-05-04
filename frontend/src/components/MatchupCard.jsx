import { useState, useRef, useEffect } from "react";
import { isLocked, isTBD, formatLockTime, getTeamStyle, STRIPE_POINTS } from "../utils/helpers";

const GRAY = {
  field:   "#1a1a1a",
  seedBg:  "#4a4a4a",
  stripe1: "#555555",
  stripe2: "#333333",
  pipFill: "#555555",
};

function Stripes({ s, height = 60 }) {
  // Both parallelograms: 16px wide, 20px angle offset, full row height
  // s1: "0,0 16,0 36,h 20,h"   s2: "16,0 32,0 52,h 36,h"
  const h = height;
  return (
    <svg width="60" height={h} viewBox={`0 0 60 ${h}`} xmlns="http://www.w3.org/2000/svg" style={{ flexShrink: 0, display: "block" }}>
      <rect width="60" height={h} fill={s.field} />
      <polygon points={`0,0 16,0 36,${h} 20,${h}`} fill={s.stripe1} />
      <polygon points={`16,0 32,0 52,${h} 36,${h}`} fill={s.stripe2} />
    </svg>
  );
}

function TeamRow({ team, seed, style, picked, eliminated, children }) {
  const s = eliminated ? GRAY : style;
  return (
    <div style={{ display: "flex", height: 60, alignItems: "stretch", opacity: eliminated ? 0.75 : 1 }}>
      {/* seed block */}
      <div style={{ width: 44, flexShrink: 0, background: s.seedBg, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontSize: 22, fontWeight: 700, color: "#fff", fontFamily: "-apple-system,sans-serif" }}>{seed}</span>
      </div>
      {/* field */}
      <div style={{ flex: 1, background: s.field, display: "flex", alignItems: "center", padding: "0 12px", gap: 6 }}>
        <span style={{ fontSize: 14, fontWeight: 600, color: eliminated ? "#888" : "#fff", flex: 1, fontFamily: "-apple-system,sans-serif" }}>
          {team}{picked ? " ✓" : ""}
        </span>
        {children}
      </div>
      {/* stripes */}
      <Stripes s={s} height={60} />
      {/* dots zone */}
      {null}
    </div>
  );
}

function PipsRow({ wins, total = 4, pipFill, field }) {
  return (
    <div style={{ width: 72, flexShrink: 0, background: field, display: "flex", alignItems: "center", justifyContent: "center", gap: 4 }}>
      {Array.from({ length: total }).map((_, i) => (
        <div key={i} style={{
          width: 10, height: 10, borderRadius: "50%",
          background: i < wins ? pipFill : "rgba(255,255,255,0.08)",
          border: i < wins ? "none" : `1px solid ${pipFill}44`,
          flexShrink: 0,
        }} />
      ))}
    </div>
  );
}

function PlayerSearch({ players, value, onChange }) {
  const [query, setQuery] = useState(value || "");
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  const filtered = (() => {
    if (!open) return [];
    if (query.length === 0) return players.slice(0, 5);
    if (query.length < 2) return [];
    return players.filter(p => p.toLowerCase().includes(query.toLowerCase())).slice(0, 10);
  })();

  useEffect(() => {
    function handleClick(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false); }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  useEffect(() => { setQuery(value || ""); }, [value]);

  function select(player) { setQuery(player); onChange(player); setOpen(false); }

  return (
    <div className="player-search" ref={ref}>
      <input className="player-search-input" type="text"
        placeholder="Click to pick, or type to search..."
        value={query}
        onChange={e => { setQuery(e.target.value); setOpen(true); if (!e.target.value) onChange(null); }}
        onFocus={() => setOpen(true)} />
      {open && filtered.length > 0 && (
        <div className="player-search-dropdown">
          {filtered.map(p => <div key={p} className="player-search-option" onMouseDown={() => select(p)}>{p}</div>)}
        </div>
      )}
    </div>
  );
}

function AdminResultForm({ matchup, rosters, onSave, onCancel }) {
  const [resultWinner, setResultWinner] = useState("");
  const [resultGames, setResultGames] = useState("");
  const [resultStat, setResultStat] = useState("");
  const teamA = matchup.team_a || "TBD";
  const teamB = matchup.team_b || "TBD";
  const players = [...(rosters[teamA] || []), ...(rosters[teamB] || [])].filter((p, i, a) => a.indexOf(p) === i).sort();

  return (
    <div className="admin-result-form">
      <div className="admin-result-row">
        <select className="player-select" value={resultWinner} onChange={e => setResultWinner(e.target.value)}>
          <option value="">— winner —</option>
          {matchup.team_a && <option value={matchup.team_a}>{teamA}</option>}
          {matchup.team_b && <option value={matchup.team_b}>{teamB}</option>}
        </select>
        <div className="games-picker">
          {[4, 5, 6, 7].map(g => (
            <button key={g} className="game-btn"
              style={resultGames === g ? { background: "rgba(251,191,36,0.2)", borderColor: "#fbbf24", color: "#fbbf24", fontWeight: 600 } : {}}
              onClick={() => setResultGames(resultGames === g ? "" : g)}>{g}</button>
          ))}
        </div>
      </div>
      {players.length > 0 && <PlayerSearch players={players} value={resultStat} onChange={v => setResultStat(v || "")} />}
      <div className="admin-result-row" style={{ marginTop: 4 }}>
        <button className="admin-btn confirm" onClick={() => { if (resultWinner && resultGames) onSave(matchup.id, resultWinner, Number(resultGames), resultStat); }}>Save</button>
        <button className="admin-btn" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

export default function MatchupCard({ matchup, conf, picks, onPick, isAdmin, onSetResult, rosters, readonly, statGuide = [] }) {
  const pick = picks[matchup.id] || {};
  const locked = isLocked(matchup);
  const tbd = isTBD(matchup);
  const lockLabel = formatLockTime(matchup.lock_time);

  const teamA = matchup.team_a || "TBD";
  const teamB = matchup.team_b || "TBD";
  const tp = pick.winner === teamA;
  const bp = pick.winner === teamB;
  const sA = getTeamStyle(teamA, conf);
  const sB = getTeamStyle(teamB, conf);
  const ps = tp ? sA : bp ? sB : null;

  const players = [...(rosters[teamA] || []), ...(rosters[teamB] || [])].filter((p, i, a) => a.indexOf(p) === i).sort();
  const [showResult, setShowResult] = useState(false);
  const [showGuide, setShowGuide] = useState(false);
  const guide = statGuide.find(g => g.teams.includes(teamA) && g.teams.includes(teamB)) || null;

  const aWon = matchup.winner_result === teamA;
  const bWon = matchup.winner_result === teamB;
  const aWins = matchup.games_a || 0; 
  const bWins = matchup.games_b || 0; 

  function setPick(field, value) {
    if (locked || tbd || readonly) return;
    onPick && onPick(matchup.id, { ...pick, [field]: value });
  }

  const LockBar = () => (
    <div style={{ height: 22, display: "flex", alignItems: "center", padding: "0 12px", background: "#0a0e18", borderBottom: "1px solid rgba(255,255,255,0.06)", justifyContent: "space-between" }}>
      <span style={{ fontSize: 10, color: "rgba(255,255,255,0.35)", fontFamily: "-apple-system,sans-serif" }}>
        {locked ? `Locked` : lockLabel ? `Locks ${lockLabel}` : ""}
      </span>
    </div>
  );

  // ── TBD ───────────────────────────────────────────────────────────────────
  if (tbd) {
    return (
      <div className="matchup tbd">
        <LockBar />
        {[{ s: sA, seed: matchup.seed_a, name: teamA, known: !!matchup.team_a },
          { s: sB, seed: matchup.seed_b, name: teamB, known: !!matchup.team_b }].map((t, i) => (
          <div key={i}>
            {i > 0 && <div style={{ height: 2, background: "#fff" }} />}
            <div style={{ display: "flex", height: 60, alignItems: "stretch", opacity: t.known ? 0.7 : 0.4 }}>
              <div style={{ width: 44, flexShrink: 0, background: t.known ? t.s.seedBg : "#333", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ fontSize: 22, fontWeight: 700, color: t.known ? "#fff" : "#888" }}>{t.seed}</span>
              </div>
              <div style={{ flex: 1, background: t.known ? t.s.field : "#111", display: "flex", alignItems: "center", padding: "0 12px" }}>
                <span style={{ fontSize: 14, fontWeight: 500, color: t.known ? "#fff" : "#555" }}>{t.name}</span>
              </div>
              <Stripes s={t.known ? t.s : { field: "#111", stripe1: "#333", stripe2: "#222" }} />
              <div style={{ width: 72, background: t.known ? t.s.field : "#111" }} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  // ── Readonly pending ───────────────────────────────────────────────────────
  if (readonly && !locked) {
    return (
      <div className="matchup readonly-pending">
        <LockBar />
        {[{ s: sA, seed: matchup.seed_a, name: teamA }, { s: sB, seed: matchup.seed_b, name: teamB }].map((t, i) => (
          <div key={i}>
            {i > 0 && <div style={{ height: 2, background: "#fff" }} />}
            <div style={{ display: "flex", height: 60, alignItems: "stretch", opacity: 0.5 }}>
              <div style={{ width: 44, flexShrink: 0, background: t.s.seedBg, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ fontSize: 22, fontWeight: 700, color: "#fff" }}>{t.seed}</span>
              </div>
              <div style={{ flex: 1, background: t.s.field, display: "flex", alignItems: "center", padding: "0 12px" }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: "#fff", flex: 1 }}>{t.name}</span>
              </div>
              <Stripes s={t.s} />
              <div style={{ width: 72, background: t.s.field, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)" }}>hidden</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  // ── Locked ────────────────────────────────────────────────────────────────
  if (locked) {
    return (
      <div className="matchup locked">
        <LockBar />
        {/* Team A — full color always; checkmark shows user's pick */}
        <div style={{ display: "flex", height: 60, alignItems: "stretch" }}>
          <div style={{ width: 44, flexShrink: 0, background: sA.seedBg, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <span style={{ fontSize: 22, fontWeight: 700, color: "#fff" }}>{matchup.seed_a}</span>
          </div>
          <div style={{ flex: 1, background: sA.field, display: "flex", alignItems: "center", padding: "0 12px", gap: 6 }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "#fff", flex: 1 }}>
              {teamA}{tp && " ✓"}
            </span>
          </div>
          <Stripes s={sA} />
          <PipsRow wins={aWins} pipFill={sA.pipFill} field={sA.field} />
        </div>
        <div style={{ height: 2, background: "#fff" }} />
        {/* Team B — full color always; checkmark shows user's pick */}
        <div style={{ display: "flex", height: 60, alignItems: "stretch" }}>
          <div style={{ width: 44, flexShrink: 0, background: sB.seedBg, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <span style={{ fontSize: 22, fontWeight: 700, color: "#fff" }}>{matchup.seed_b}</span>
          </div>
          <div style={{ flex: 1, background: sB.field, display: "flex", alignItems: "center", padding: "0 12px", gap: 6 }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "#fff", flex: 1 }}>
              {teamB}{bp && " ✓"}
            </span>
          </div>
          <Stripes s={sB} />
          <PipsRow wins={bWins} pipFill={sB.pipFill} field={sB.field} />
        </div>
        {/* Readonly picks summary */}
        {(pick.games || pick.statLeader) && (
          <div className="pick-extras">
            {pick.games && <div className="pick-row"><span className="pick-label">Games</span><span className="pick-value">{pick.games}</span></div>}
            {pick.statLeader && <div className="pick-row"><span className="pick-label">{matchup.stat_label || "Stat"}</span><span className="pick-value">{pick.statLeader}</span></div>}
          </div>
        )}
        {isAdmin && !readonly && (
          <div className="admin-bar">
            {!showResult
              ? <button className="admin-btn" onClick={() => setShowResult(true)}>Set result</button>
              : <AdminResultForm matchup={matchup} rosters={rosters}
                  onSave={(id, w, g, s) => { onSetResult(id, w, g, s); setShowResult(false); }}
                  onCancel={() => setShowResult(false)} />}
          </div>
        )}
      </div>
    );
  }

  // ── Active / pickable ─────────────────────────────────────────────────────
  return (
    <div className="matchup">
      <LockBar />
      {/* Team A */}
      <div style={{ display: "flex", height: 60, alignItems: "stretch", cursor: "pointer" }}
        onClick={() => setPick("winner", tp ? null : teamA)}>
        <div style={{ width: 44, flexShrink: 0, background: sA.seedBg, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <span style={{ fontSize: 22, fontWeight: 700, color: "#fff" }}>{matchup.seed_a}</span>
        </div>
        <div style={{ flex: 1, background: sA.field, display: "flex", alignItems: "center", padding: "0 12px" }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "#fff", flex: 1 }}>{teamA}{tp ? " ✓" : ""}</span>
        </div>
        <Stripes s={sA} />
        <PipsRow wins={0} pipFill={sA.pipFill} field={sA.field} />
      </div>
      <div style={{ height: 2, background: "#fff" }} />
      {/* Team B */}
      <div style={{ display: "flex", height: 60, alignItems: "stretch", cursor: "pointer" }}
        onClick={() => setPick("winner", bp ? null : teamB)}>
        <div style={{ width: 44, flexShrink: 0, background: sB.seedBg, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <span style={{ fontSize: 22, fontWeight: 700, color: "#fff" }}>{matchup.seed_b}</span>
        </div>
        <div style={{ flex: 1, background: sB.field, display: "flex", alignItems: "center", padding: "0 12px" }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "#fff", flex: 1 }}>{teamB}{bp ? " ✓" : ""}</span>
        </div>
        <Stripes s={sB} />
        <PipsRow wins={0} pipFill={sB.pipFill} field={sB.field} />
      </div>
      {/* Picks */}
      <div className="pick-extras">
        <div className="pick-row">
          <span className="pick-label" style={ps ? { color: ps.accent } : {}}>How many games?</span>
          <div className="games-picker">
            {[4, 5, 6, 7].map(g => (
              <button key={g} className="game-btn"
                style={pick.games === g && ps ? { background: `${ps.accent}22`, borderColor: ps.accent, color: ps.accent, fontWeight: 700 } : {}}
                onClick={() => setPick("games", pick.games === g ? null : g)}>{g}</button>
            ))}
          </div>
        </div>
        {players.length > 0 && (
          <div className="pick-col">
            <span className="pick-question" style={ps ? { color: ps.accent } : {}}>
              Who leads this series in {(matchup.stat_label || "stats").toLowerCase()}?
            </span>
            <PlayerSearch players={players} value={pick.statLeader || ""} onChange={v => setPick("statLeader", v)} />
            {guide && (
              <div style={{ marginTop: 6 }}>
                <button
                  onClick={() => setShowGuide(v => !v)}
                  style={{ background: "none", border: "none", cursor: "pointer", fontSize: 11, color: "rgba(255,255,255,0.4)", padding: 0, letterSpacing: "0.04em" }}>
                  {showGuide ? "▴" : "▾"} stat guide ({guide.stat})
                </button>
                {showGuide && (() => {
                  const roundCols = [
                    { key: "r1", label: "R1" },
                    { key: "r2", label: "R2" },
                    { key: "cf", label: "CF" },
                  ].filter(({ key }) => guide.players.some(p => p[key] != null));
                  const lastKey = roundCols.length ? roundCols[roundCols.length - 1].key : null;
                  return (
                    <table style={{ width: "100%", fontSize: 11, borderCollapse: "collapse", marginTop: 4, color: "#e2e8f0" }}>
                      <thead>
                        <tr style={{ color: "rgba(255,255,255,0.4)", textAlign: "left" }}>
                          <th style={{ paddingBottom: 2, fontWeight: 400 }}>Player</th>
                          <th style={{ paddingBottom: 2, fontWeight: 400, width: 32, textAlign: "center" }}>Tm</th>
                          <th style={{ paddingBottom: 2, fontWeight: 400, width: 36, textAlign: "right" }}>RS</th>
                          <th style={{ paddingBottom: 2, fontWeight: 400, width: 42, textAlign: "right" }}>Post-ASB</th>
                          {roundCols.map(({ key, label }) => (
                            <th key={key} style={{ paddingBottom: 2, fontWeight: 400, width: 36, textAlign: "right" }}>{label}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {guide.players.map(p => (
                          <tr key={p.name} style={{ borderTop: "1px solid rgba(255,255,255,0.05)", cursor: "pointer" }}
                            onClick={() => setPick("statLeader", p.name)}>
                            <td style={{ padding: "3px 0", color: pick.statLeader === p.name ? "#fbbf24" : "#e2e8f0" }}>{p.name}</td>
                            <td style={{ textAlign: "center", color: "rgba(255,255,255,0.4)" }}>{p.team}</td>
                            <td style={{ textAlign: "right", color: "rgba(255,255,255,0.5)" }}>{p.rs.toFixed(1)}</td>
                            <td style={{ textAlign: "right", color: "rgba(255,255,255,0.5)" }}>{p.post.toFixed(1)}</td>
                            {roundCols.map(({ key }) => (
                              <td key={key} style={{ textAlign: "right", fontWeight: key === lastKey ? 600 : 400, color: key === lastKey ? "#e2e8f0" : "rgba(255,255,255,0.5)" }}>
                                {p[key] != null ? p[key].toFixed(1) : "—"}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  );
                })()}
              </div>
            )}
          </div>
        )}
      </div>
      {isAdmin && (
        <div className="admin-bar">
          {!showResult
            ? <button className="admin-btn" onClick={() => setShowResult(true)}>Set result</button>
            : <AdminResultForm matchup={matchup} rosters={rosters}
                onSave={(id, w, g, s) => { onSetResult(id, w, g, s); setShowResult(false); }}
                onCancel={() => setShowResult(false)} />}
        </div>
      )}
    </div>
  );
}