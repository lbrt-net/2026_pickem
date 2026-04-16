import { useState, useRef, useEffect } from "react";
import { isLocked, isTBD, formatLockTime, getTeamStyle } from "../utils/helpers";

function PlayerSearch({ players, value, onChange }) {
  const [query, setQuery] = useState(value || "");
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  const filtered = (() => {
    if (!open) return [];
    if (query.length === 0) return players.slice(0, 5);
    return players.filter(p => p.toLowerCase().includes(query.toLowerCase())).slice(0, 10);
  })();

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  useEffect(() => { setQuery(value || ""); }, [value]);

  function select(player) {
    setQuery(player);
    onChange(player);
    setOpen(false);
  }

  function handleChange(e) {
    setQuery(e.target.value);
    setOpen(true);
    if (!e.target.value) onChange(null);
  }

  return (
    <div className="player-search" ref={ref}>
      <input
        className="player-search-input"
        type="text"
        placeholder="Click to pick, or type to search..."
        value={query}
        onChange={handleChange}
        onFocus={() => setOpen(true)}
      />
      {open && filtered.length > 0 && (
        <div className="player-search-dropdown">
          {filtered.map(p => (
            <div key={p} className="player-search-option" onMouseDown={() => select(p)}>{p}</div>
          ))}
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
  const players = [
    ...(rosters[teamA] || []),
    ...(rosters[teamB] || []),
  ].filter((p, i, arr) => arr.indexOf(p) === i).sort();

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
              onClick={() => setResultGames(resultGames === g ? "" : g)}>
              {g}
            </button>
          ))}
        </div>
      </div>
      {players.length > 0 && (
        <PlayerSearch players={players} value={resultStat} onChange={v => setResultStat(v || "")} />
      )}
      <div className="admin-result-row" style={{ marginTop: 4 }}>
        <button className="admin-btn confirm" onClick={() => {
          if (resultWinner && resultGames) onSave(matchup.id, resultWinner, Number(resultGames), resultStat);
        }}>Save</button>
        <button className="admin-btn" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

export default function MatchupCard({ matchup, conf, picks, onPick, isAdmin, onSetResult, rosters, readonly }) {
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
  // Active pick style — whichever team is picked
  const ps = tp ? sA : bp ? sB : null;

  const players = [
    ...(rosters[teamA] || []),
    ...(rosters[teamB] || []),
  ].filter((pl, i, arr) => arr.indexOf(pl) === i).sort();

  const [showResult, setShowResult] = useState(false);

  function setPick(field, value) {
    if (locked || tbd || readonly) return;
    onPick && onPick(matchup.id, { ...pick, [field]: value });
  }

  const aWon = matchup.winner_result === teamA;
  const bWon = matchup.winner_result === teamB;

  // ── Locked ────────────────────────────────────────────────────────────────
  if (locked) {
    return (
      <div className="matchup locked">
        {/* Lock bar with winner's color if result is set */}
        <div className="locked-badge" style={aWon ? { background: sA.lockBar, borderBottom: `1px solid ${sA.border}` } : bWon ? { background: sB.lockBar, borderBottom: `1px solid ${sB.border}` } : {}}>
          Locked · {lockLabel || ""}
        </div>

        {/* Team A */}
        <div className="trow" style={{
          background: aWon ? sA.bg : "transparent",
          borderLeft: aWon ? `3px solid ${sA.border}` : "3px solid transparent",
          opacity: bWon ? 0.38 : 1,
        }}>
          <span className="seed" style={aWon ? { color: sA.seed } : {}}>{matchup.seed_a ?? ""}</span>
          <span className="tname" style={aWon ? { color: sA.text } : { color: "#4a5568" }}>{teamA}</span>
          {readonly && tp && <span className="checkmark" style={{ color: sA.accent }}>✓</span>}
          {aWon && <span className="result-badge" style={{ background: sA.border, color: "#fff" }}>W</span>}
        </div>

        <div className="mdiv" style={aWon ? { background: sA.divider, opacity: 0.4 } : bWon ? { background: sB.divider, opacity: 0.4 } : {}} />

        {/* Team B */}
        <div className="trow" style={{
          background: bWon ? sB.bg : "transparent",
          borderLeft: bWon ? `3px solid ${sB.border}` : "3px solid transparent",
          opacity: aWon ? 0.38 : 1,
        }}>
          <span className="seed" style={bWon ? { color: sB.seed } : {}}>{matchup.seed_b ?? ""}</span>
          <span className="tname" style={bWon ? { color: sB.text } : { color: "#4a5568" }}>{teamB}</span>
          {readonly && bp && <span className="checkmark" style={{ color: sB.accent }}>✓</span>}
          {bWon && <span className="result-badge" style={{ background: sB.border, color: "#fff" }}>W</span>}
        </div>

        {readonly && (pick.games || pick.statLeader) && (
          <div className="pick-extras">
            {pick.games && <div className="pick-row"><span className="pick-label">Games</span><span className="pick-value">{pick.games}</span></div>}
            {pick.statLeader && <div className="pick-row"><span className="pick-label">{matchup.stat_label || "Stat leader"}</span><span className="pick-value">{pick.statLeader}</span></div>}
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

  // ── TBD ───────────────────────────────────────────────────────────────────
  if (tbd) {
    return (
      <div className="matchup tbd">
        <div className="tbd-badge">Teams TBD</div>
        {lockLabel && <div className="lock-time-row">Locks {lockLabel}</div>}
        <div className="trow" style={{ borderLeft: "3px solid transparent" }}>
          {matchup.seed_a != null && <span className="seed">{matchup.seed_a}</span>}
          <span className="tname muted">{teamA}</span>
        </div>
        <div className="mdiv" />
        <div className="trow" style={{ borderLeft: "3px solid transparent" }}>
          {matchup.seed_b != null && <span className="seed">{matchup.seed_b}</span>}
          <span className="tname muted">{teamB}</span>
        </div>
      </div>
    );
  }

  // ── Readonly pending ───────────────────────────────────────────────────────
  if (readonly) {
    return (
      <div className="matchup readonly-pending">
        {lockLabel && <div className="lock-time-row">Locks {lockLabel}</div>}
        <div className="trow" style={{ borderLeft: "3px solid transparent" }}>
          {matchup.seed_a != null && <span className="seed">{matchup.seed_a}</span>}
          <span className="tname muted">{teamA}</span>
        </div>
        <div className="mdiv" />
        <div className="trow" style={{ borderLeft: "3px solid transparent" }}>
          {matchup.seed_b != null && <span className="seed">{matchup.seed_b}</span>}
          <span className="tname muted">{teamB}</span>
        </div>
        <div className="pick-hidden-note">Picks hidden until series locks</div>
      </div>
    );
  }

  // ── Active / pickable ─────────────────────────────────────────────────────
  return (
    <div className="matchup">
      {/* Lock time bar — tinted with picked team's lockBar color */}
      {lockLabel && (
        <div className="lock-time-row" style={ps ? { background: ps.lockBar, color: "#cbd5e1" } : {}}>
          Locks {lockLabel}
        </div>
      )}

      {/* Team A row */}
      <div className="trow"
        style={tp ? { background: sA.bg, borderLeft: `3px solid ${sA.border}` } : { borderLeft: "3px solid transparent" }}
        onClick={() => setPick("winner", tp ? null : teamA)}>
        <span className="seed" style={tp ? { color: sA.seed, fontWeight: 700 } : {}}>{matchup.seed_a ?? ""}</span>
        <span className="tname" style={tp ? { color: sA.text } : {}}>{teamA}</span>
        {tp && <span className="checkmark" style={{ color: sA.accent }}>✓</span>}
      </div>

      {/* Divider — tints with picked team */}
      <div className="mdiv" style={ps ? { background: ps.divider, opacity: 0.35 } : {}} />

      {/* Team B row */}
      <div className="trow"
        style={bp ? { background: sB.bg, borderLeft: `3px solid ${sB.border}` } : { borderLeft: "3px solid transparent" }}
        onClick={() => setPick("winner", bp ? null : teamB)}>
        <span className="seed" style={bp ? { color: sB.seed, fontWeight: 700 } : {}}>{matchup.seed_b ?? ""}</span>
        <span className="tname" style={bp ? { color: sB.text } : {}}>{teamB}</span>
        {bp && <span className="checkmark" style={{ color: sB.accent }}>✓</span>}
      </div>

      <div className="pick-extras">
        <div className="pick-row">
          <span className="pick-label" style={ps ? { color: ps.accent } : {}}>How many games?</span>
          <div className="games-picker">
            {[4, 5, 6, 7].map(g => (
              <button key={g} className="game-btn"
                style={pick.games === g && ps ? {
                  background: ps.bg,
                  borderColor: ps.accent,
                  color: ps.accent,
                  fontWeight: 700,
                } : {}}
                onClick={() => setPick("games", pick.games === g ? null : g)}>
                {g}
              </button>
            ))}
          </div>
        </div>
        {players.length > 0 && (
          <div className="pick-col">
            <span className="pick-question" style={ps ? { color: ps.accent } : {}}>
              Who leads this series in {(matchup.stat_label || "stats").toLowerCase()}?
            </span>
            <PlayerSearch
              players={players}
              value={pick.statLeader || ""}
              onChange={v => setPick("statLeader", v)}
            />
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