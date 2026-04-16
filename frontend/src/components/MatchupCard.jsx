import { useState } from "react";
import { isLocked, isTBD, formatLockTime, pickClass } from "../utils/helpers";

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
              className={`game-btn ${resultGames === g ? "selected wp" : ""}`}
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

export default function MatchupCard({ matchup, conf, picks, onPick, isAdmin, onSetResult, rosters, readonly }) {
  const p = pickClass(conf);
  const pick = picks[matchup.id] || {};
  const locked = isLocked(matchup);
  const tbd = isTBD(matchup);
  const lockLabel = formatLockTime(matchup.lock_time);

  const teamA = matchup.team_a || "TBD";
  const teamB = matchup.team_b || "TBD";
  const tp = pick.winner === teamA;
  const bp = pick.winner === teamB;

  const players = [
    ...(rosters[teamA] || []),
    ...(rosters[teamB] || []),
  ].filter((pl, i, arr) => arr.indexOf(pl) === i).sort();

  const [showResult, setShowResult] = useState(false);

  function setPick(field, value) {
    if (locked || tbd || readonly) return;
    onPick && onPick(matchup.id, { ...pick, [field]: value });
  }

  // Locked card — picks visible if readonly (viewing another user), hidden if own view pre-lock
  if (locked) {
    return (
      <div className="matchup locked">
        <div className="locked-badge">Locked · {lockLabel || ""}</div>
        <div className={`trow ${readonly && tp ? p : ""}`}>
          {matchup.seed_a != null && <span className="seed">{matchup.seed_a}</span>}
          <span className={`tname ${readonly && tp ? p : "muted"}`}>{teamA}</span>
          {readonly && tp && <span className="checkmark">✓</span>}
        </div>
        <div className="mdiv" />
        <div className={`trow ${readonly && bp ? p : ""}`}>
          {matchup.seed_b != null && <span className="seed">{matchup.seed_b}</span>}
          <span className={`tname ${readonly && bp ? p : "muted"}`}>{teamB}</span>
          {readonly && bp && <span className="checkmark">✓</span>}
        </div>
        {readonly && (pick.games || pick.statLeader) && (
          <div className="pick-extras">
            {pick.games && (
              <div className="pick-row">
                <span className="pick-label">Games</span>
                <span className="pick-value">{pick.games}</span>
              </div>
            )}
            {pick.statLeader && (
              <div className="pick-row">
                <span className="pick-label">{matchup.stat_label || "Stat leader"}</span>
                <span className="pick-value">{pick.statLeader}</span>
              </div>
            )}
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

  // TBD card
  if (tbd) {
    return (
      <div className="matchup tbd">
        <div className="tbd-badge">Teams TBD</div>
        {lockLabel && <div className="lock-time-row">Locks {lockLabel}</div>}
        <div className="trow">
          {matchup.seed_a != null && <span className="seed">{matchup.seed_a}</span>}
          <span className="tname muted">{teamA}</span>
        </div>
        <div className="mdiv" />
        <div className="trow">
          {matchup.seed_b != null && <span className="seed">{matchup.seed_b}</span>}
          <span className="tname muted">{teamB}</span>
        </div>
      </div>
    );
  }

  // Readonly active card — picks not yet revealed (series not started)
  if (readonly) {
    return (
      <div className="matchup readonly-pending">
        <div className="lock-time-row">Locks {lockLabel}</div>
        <div className="trow">
          {matchup.seed_a != null && <span className="seed">{matchup.seed_a}</span>}
          <span className="tname muted">{teamA}</span>
        </div>
        <div className="mdiv" />
        <div className="trow">
          {matchup.seed_b != null && <span className="seed">{matchup.seed_b}</span>}
          <span className="tname muted">{teamB}</span>
        </div>
        <div className="pick-hidden-note">Picks hidden until series locks</div>
      </div>
    );
  }

  // Active / pickable
  return (
    <div className="matchup">
      {lockLabel && <div className="lock-time-row">Locks {lockLabel}</div>}
      <div className={`trow ${tp ? p : ""}`} onClick={() => setPick("winner", tp ? null : teamA)}>
        {matchup.seed_a != null && <span className="seed">{matchup.seed_a}</span>}
        <span className={`tname ${tp ? p : ""}`}>{teamA}</span>
        {tp && <span className="checkmark">✓</span>}
      </div>
      <div className="mdiv" />
      <div className={`trow ${bp ? p : ""}`} onClick={() => setPick("winner", bp ? null : teamB)}>
        {matchup.seed_b != null && <span className="seed">{matchup.seed_b}</span>}
        <span className={`tname ${bp ? p : ""}`}>{teamB}</span>
        {bp && <span className="checkmark">✓</span>}
      </div>

      <div className="pick-extras">
        <div className="pick-row">
          <span className="pick-label">How many games?</span>
          <div className="games-picker">
            {[4, 5, 6, 7].map((g) => (
              <button key={g}
                className={`game-btn ${pick.games === g ? "selected " + p : ""}`}
                onClick={() => setPick("games", pick.games === g ? null : g)}>
                {g}
              </button>
            ))}
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