import { useState } from "react";
import { isLocked, isTBD, formatLockTime, getTeamStyle } from "../utils/helpers";

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
            <button key={g}
              className="game-btn"
              style={resultGames === g ? { background: "rgba(251,191,36,0.2)", borderColor: "#fbbf24", color: "#fbbf24", fontWeight: 600 } : {}}
              onClick={() => setResultGames(resultGames === g ? "" : g)}>
              {g}
            </button>
          ))}
        </div>
      </div>
      {players.length > 0 && (
        <select className="player-select" style={{ marginTop: 4 }} value={resultStat} onChange={e => setResultStat(e.target.value)}>
          <option value="">— stat leader —</option>
          {players.map(pl => <option key={pl} value={pl}>{pl}</option>)}
        </select>
      )}
      <div className="admin-result-row" style={{ marginTop: 4 }}>
        <button className="admin-btn confirm" onClick={() => {
          if (resultWinner && resultGames) {
            onSave(matchup.id, resultWinner, Number(resultGames), resultStat);
          }
        }}>Save</button>
        <button className="admin-btn" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

function TeamRow({ team, seed, selected, conf, onClick }) {
  const style = getTeamStyle(team, conf);
  return (
    <div className="trow"
      style={selected ? { background: style.bg, borderLeft: `2px solid ${style.border}` } : { borderLeft: "2px solid transparent" }}
      onClick={onClick}>
      {seed != null && <span className="seed">{seed}</span>}
      <span className="tname" style={selected ? { color: style.text } : {}}>{team}</span>
      {selected && <span className="checkmark" style={{ color: style.text }}>✓</span>}
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
  const styleA = getTeamStyle(teamA, conf);
  const styleB = getTeamStyle(teamB, conf);

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

  if (locked) {
    return (
      <div className="matchup locked">
        <div className="locked-badge">Locked · {lockLabel || ""}</div>
        <div className="trow" style={{
          background: aWon ? styleA.bg : "transparent",
          borderLeft: aWon ? `2px solid ${styleA.border}` : "2px solid transparent",
          opacity: bWon ? 0.4 : 1,
        }}>
          {matchup.seed_a != null && <span className="seed">{matchup.seed_a}</span>}
          <span className="tname" style={aWon ? { color: styleA.text } : { color: "#4a5568" }}>{teamA}</span>
          {readonly && tp && <span className="checkmark" style={{ color: styleA.text }}>✓</span>}
          {aWon && <span className="result-badge" style={{ background: styleA.border }}>W</span>}
        </div>
        <div className="mdiv" />
        <div className="trow" style={{
          background: bWon ? styleB.bg : "transparent",
          borderLeft: bWon ? `2px solid ${styleB.border}` : "2px solid transparent",
          opacity: aWon ? 0.4 : 1,
        }}>
          {matchup.seed_b != null && <span className="seed">{matchup.seed_b}</span>}
          <span className="tname" style={bWon ? { color: styleB.text } : { color: "#4a5568" }}>{teamB}</span>
          {readonly && bp && <span className="checkmark" style={{ color: styleB.text }}>✓</span>}
          {bWon && <span className="result-badge" style={{ background: styleB.border }}>W</span>}
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

  if (tbd) {
    return (
      <div className="matchup tbd">
        <div className="tbd-badge">Teams TBD</div>
        {lockLabel && <div className="lock-time-row">Locks {lockLabel}</div>}
        <div className="trow" style={{ borderLeft: "2px solid transparent" }}>
          {matchup.seed_a != null && <span className="seed">{matchup.seed_a}</span>}
          <span className="tname muted">{teamA}</span>
        </div>
        <div className="mdiv" />
        <div className="trow" style={{ borderLeft: "2px solid transparent" }}>
          {matchup.seed_b != null && <span className="seed">{matchup.seed_b}</span>}
          <span className="tname muted">{teamB}</span>
        </div>
      </div>
    );
  }

  if (readonly) {
    return (
      <div className="matchup readonly-pending">
        {lockLabel && <div className="lock-time-row">Locks {lockLabel}</div>}
        <div className="trow" style={{ borderLeft: "2px solid transparent" }}>
          {matchup.seed_a != null && <span className="seed">{matchup.seed_a}</span>}
          <span className="tname muted">{teamA}</span>
        </div>
        <div className="mdiv" />
        <div className="trow" style={{ borderLeft: "2px solid transparent" }}>
          {matchup.seed_b != null && <span className="seed">{matchup.seed_b}</span>}
          <span className="tname muted">{teamB}</span>
        </div>
        <div className="pick-hidden-note">Picks hidden until series locks</div>
      </div>
    );
  }

  return (
    <div className="matchup">
      {lockLabel && <div className="lock-time-row">Locks {lockLabel}</div>}
      <TeamRow team={teamA} seed={matchup.seed_a} selected={tp} conf={conf}
        onClick={() => setPick("winner", tp ? null : teamA)} />
      <div className="mdiv" />
      <TeamRow team={teamB} seed={matchup.seed_b} selected={bp} conf={conf}
        onClick={() => setPick("winner", bp ? null : teamB)} />
      <div className="pick-extras">
        <div className="pick-row">
          <span className="pick-label">How many games?</span>
          <div className="games-picker">
            {[4, 5, 6, 7].map((g) => {
              const ps = tp ? styleA : bp ? styleB : null;
              return (
                <button key={g} className="game-btn"
                  style={pick.games === g && ps ? { background: ps.bg, borderColor: ps.border, color: ps.text, fontWeight: 600 } : {}}
                  onClick={() => setPick("games", pick.games === g ? null : g)}>
                  {g}
                </button>
              );
            })}
          </div>
        </div>
        {players.length > 0 && (
          <div className="pick-col">
            <span className="pick-question">
              Who leads this series in {(matchup.stat_label || "stats").toLowerCase()}?
            </span>
            <select className="player-select"
              value={pick.statLeader || ""}
              onChange={(e) => setPick("statLeader", e.target.value || null)}>
              <option value="">— pick a player —</option>
              {players.map((pl) => <option key={pl} value={pl}>{pl}</option>)}
            </select>
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