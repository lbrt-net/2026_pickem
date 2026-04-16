import { useState, useEffect, useRef } from "react";
import "./App.css";

const API = "";

const ROUNDS = ["First round", "Conf semis", "Conf finals", "NBA Finals"];
const COMP_W = 54;
const GAP = 6;
const N_COLS = 7;

const ACTIVE_COLS = [[0, 6], [1, 5], [2, 4], [3]];

// Player rosters are now loaded from /rosters and stored in state (team-keyed)

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function isLocked(matchup) {
  if (!matchup.lock_time) return false;
  return new Date(matchup.lock_time) <= new Date();
}

function formatLockTime(lock_time) {
  if (!lock_time) return null;
  return new Date(lock_time).toLocaleString("en-US", {
    timeZone: "America/Chicago",
    month: "short", day: "numeric",
    hour: "numeric", minute: "2-digit",
    hour12: true,
  }) + " CT";
}

function isTBD(matchup) {
  return !matchup.team_a || !matchup.team_b;
}

function groupMatchups(matchups) {
  const buckets = {
    "west-1": [], "west-2": [], "west-3": [],
    "finals-4": [],
    "east-3": [], "east-2": [], "east-1": [],
  };
  for (const m of matchups) {
    const conf = (m.conference || "").toLowerCase();
    const round = m.round || 1;
    let key;
    if (conf === "finals" || round === 4) key = "finals-4";
    else if (conf === "west") key = `west-${round}`;
    else if (conf === "east") key = `east-${round}`;
    if (key && buckets[key]) buckets[key].push(m);
  }
  return [
    [buckets["west-1"], "west",   "West · R1"],
    [buckets["west-2"], "west",   "West · R2"],
    [buckets["west-3"], "west",   "West CF"],
    [buckets["finals-4"], "finals", "Finals"],
    [buckets["east-3"], "east",   "East CF"],
    [buckets["east-2"], "east",   "East · R2"],
    [buckets["east-1"], "east",   "East · R1"],
  ];
}

function pickClass(conf) {
  return conf === "west" ? "wp" : conf === "east" ? "ep" : "fp";
}
function dotClass(conf) {
  return conf === "west" ? "dw" : conf === "east" ? "de" : "df";
}

// ---------------------------------------------------------------------------
// MatchupCard
// ---------------------------------------------------------------------------
function MatchupCard({ matchup, conf, picks, onPick, isAdmin, onSetResult, rosters }) {
  const p = pickClass(conf);
  const pick = picks[matchup.id] || {};
  const locked = isLocked(matchup);
  const tbd = isTBD(matchup);
  const statLabel = matchup.stat_label || "Stat leader";

  const teamA = matchup.team_a || "TBD";
  const teamB = matchup.team_b || "TBD";

  // Combine players from both teams, deduplicated
  const players = [
    ...(rosters[teamA] || []),
    ...(rosters[teamB] || []),
  ].filter((p, i, arr) => arr.indexOf(p) === i);
  const tp = pick.winner === teamA;
  const bp = pick.winner === teamB;

  const [showResult, setShowResult] = useState(false);
  const [resultWinner, setResultWinner] = useState("");
  const [resultGames, setResultGames] = useState("");
  const [resultStat, setResultStat] = useState("");

  function setPick(field, value) {
    if (locked || tbd) return;
    onPick(matchup.id, { ...pick, [field]: value });
  }

  const AdminResultForm = () => (
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
            onSetResult(matchup.id, resultWinner, Number(resultGames), resultStat);
            setShowResult(false);
            setResultWinner(""); setResultGames(""); setResultStat("");
          }
        }}>Save</button>
        <button className="admin-btn" onClick={() => setShowResult(false)}>Cancel</button>
      </div>
    </div>
  );

  const lockLabel = formatLockTime(matchup.lock_time);

  // Locked
  if (locked) {
    return (
      <div className="matchup locked">
        <div className="locked-badge">Locked · {lockLabel || ""}</div>
        <div className="trow">
          {matchup.seed_a != null && <span className="seed">{matchup.seed_a}</span>}
          <span className="tname muted">{teamA}</span>
        </div>
        <div className="mdiv" />
        <div className="trow">
          {matchup.seed_b != null && <span className="seed">{matchup.seed_b}</span>}
          <span className="tname muted">{teamB}</span>
        </div>
        {isAdmin && (
          <div className="admin-bar">
            {!showResult
              ? <button className="admin-btn" onClick={() => setShowResult(true)}>Set result</button>
              : <AdminResultForm />}
          </div>
        )}
      </div>
    );
  }

  // TBD — known lock time but unknown teams
  if (tbd) {
    return (
      <div className="matchup tbd">
        <div className="tbd-badge">Teams TBD</div>
        {lockLabel && <div className="lock-time-row">{lockLabel}</div>}
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
          <span className="pick-label">Games</span>
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
          <div className="pick-row">
            <span className="pick-label">{statLabel}</span>
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
            : <AdminResultForm />}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// CompressedCol
// ---------------------------------------------------------------------------
function CompressedCol({ matchups, conf, label, picks }) {
  return (
    <div className="cinner">
      <span className="vlabel">{label}</span>
      {matchups.map((m) => (
        <div key={m.id} className={`dot ${picks[m.id]?.winner ? dotClass(conf) : ""}`} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Roster Editor (admin only)
// ---------------------------------------------------------------------------
function RosterEditor({ matchups, rosters, onSave, onClose }) {
  // Collect all known teams from current matchups
  const teams = [...new Set(
    matchups.flatMap(m => [m.team_a, m.team_b].filter(Boolean))
  )].sort();

  const [selectedTeam, setSelectedTeam] = useState(teams[0] || "");
  const [text, setText] = useState("");

  useEffect(() => {
    if (!selectedTeam) return;
    setText((rosters[selectedTeam] || []).join("\n"));
  }, [selectedTeam]);

  function handleSave() {
    const players = text.split("\n").map(s => s.trim()).filter(Boolean);
    onSave(selectedTeam, players);
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Edit Rosters</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="rules-body">
          <p className="rules-note" style={{marginBottom: 10}}>One player name per line. Saved per team — carries through all rounds.</p>
          <select className="player-select" style={{width: "100%", marginBottom: 10, fontSize: 13, padding: "6px 8px"}}
            value={selectedTeam} onChange={e => setSelectedTeam(e.target.value)}>
            {teams.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <textarea className="roster-textarea"
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder={"Jayson Tatum\nJaylen Brown\nJrue Holiday"}
            rows={8}
          />
          <button className="admin-btn confirm" style={{marginTop: 8, width: "100%", padding: "7px 0", fontSize: 12}}
            onClick={handleSave}>
            Save {selectedTeam} roster
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Rules Modal
// ---------------------------------------------------------------------------
function Rules({ onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Scoring Rules</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="rules-body">
          <p className="rules-section-title">Points per series</p>
          <table className="rules-table">
            <tbody>
              <tr><td>Correct winner</td><td className="rules-pts">2 pts</td></tr>
              <tr><td>Correct games (exact)</td><td className="rules-pts">2 pts</td></tr>
              <tr><td>Correct games (1 off)</td><td className="rules-pts">1 pt</td></tr>
              <tr><td>Correct stat leader</td><td className="rules-pts">1 pt</td></tr>
              <tr className="rules-max"><td>Max per series</td><td className="rules-pts">5 pts</td></tr>
            </tbody>
          </table>
          <p className="rules-note">Games points apply regardless of whether your winner was correct.</p>

          <p className="rules-section-title" style={{marginTop: 18}}>Round multipliers</p>
          <table className="rules-table">
            <tbody>
              <tr><td>First round</td><td className="rules-pts">1×</td></tr>
              <tr><td>Conference semifinals</td><td className="rules-pts">2×</td></tr>
              <tr><td>Conference finals</td><td className="rules-pts">4×</td></tr>
              <tr><td>NBA Finals</td><td className="rules-pts">8×</td></tr>
            </tbody>
          </table>
          <p className="rules-note">A perfect Finals series = <span className="rules-highlight">40 pts</span>.</p>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Leaderboard
// ---------------------------------------------------------------------------
function Leaderboard({ onClose }) {
  const [board, setBoard] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/leaderboard`, { credentials: "include" })
      .then((r) => r.json())
      .then((data) => { setBoard(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Leaderboard</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        {loading ? (
          <div className="modal-loading">Loading...</div>
        ) : (
          <table className="lb-table">
            <thead>
              <tr><th>#</th><th>User</th><th>Pts</th></tr>
            </thead>
            <tbody>
              {board.map((row, i) => (
                <tr key={row.username}>
                  <td className="lb-rank">{i + 1}</td>
                  <td className="lb-name">
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      {row.avatar_url && <img src={row.avatar_url} style={{ width: 22, height: 22, borderRadius: "50%" }} alt="" />}
                      {row.username}
                    </div>
                  </td>
                  <td className="lb-score">{row.points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------
export default function App() {
  const [round, setRound] = useState(0);
  const [picks, setPicks] = useState({});
  const [colWidths, setColWidths] = useState(Array(N_COLS).fill(0));
  const [renderRound, setRenderRound] = useState(0);
  const [user, setUser] = useState(null);
  const [adminMode, setAdminMode] = useState(true);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showLeaderboard, setShowLeaderboard] = useState(false);
  const [showRules, setShowRules] = useState(false);
  const [matchups, setMatchups] = useState([]);
  const [cols, setCols] = useState(Array(N_COLS).fill([[], "west", ""]));
  const [rosters, setRosters] = useState({});
  const [showRosterEditor, setShowRosterEditor] = useState(false);
  const gridRef = useRef(null);
  const timerRef = useRef(null);
  const saveTimer = useRef({});

  // Load matchups
  useEffect(() => {
    fetch(`${API}/matchups`)
      .then(r => r.json())
      .then(data => { setMatchups(data); setCols(groupMatchups(data)); })
      .catch(() => {});
    fetch(`${API}/rosters`)
      .then(r => r.json())
      .then(setRosters)
      .catch(() => {});
  }, []);

  // Load user + picks
  useEffect(() => {
    fetch(`${API}/picks/me`, { credentials: "include" })
      .then((r) => {
        if (r.status === 401) return null;
        return r.json();
      })
      .then((data) => {
        if (!data) return;
        setUser({ username: data.username, isAdmin: data.is_admin, avatarUrl: data.avatar_url });
        const rehydrated = {};
        (data.picks || []).forEach((p) => {
          rehydrated[p.matchup_id] = {
            winner: p.winner,
            games: p.games,
            statLeader: p.stat_leader,
          };
        });
        setPicks(rehydrated);
      })
      .catch(() => {});
  }, []);

  function computeWidths(activeRound, containerWidth) {
    const active = new Set(ACTIVE_COLS[activeRound]);
    const nActive = ACTIVE_COLS[activeRound].length;
    const nComp = N_COLS - nActive;
    const totalGaps = (N_COLS - 1) * GAP;
    const compTotal = nComp * COMP_W;
    const activeW = (containerWidth - totalGaps - compTotal) / nActive;
    return Array.from({ length: N_COLS }, (_, i) => (active.has(i) ? activeW : COMP_W));
  }

  useEffect(() => {
    function updateWidths() {
      if (!gridRef.current) return;
      setColWidths(computeWidths(round, gridRef.current.offsetWidth));
    }
    updateWidths();
    window.addEventListener("resize", updateWidths);
    return () => window.removeEventListener("resize", updateWidths);
  }, [round]);

  function handleRoundChange(r) {
    setRound(r);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setRenderRound(r), 220);
  }

  function handlePick(id, pickData) {
    setPicks((prev) => ({ ...prev, [id]: pickData }));
    clearTimeout(saveTimer.current[id]);
    saveTimer.current[id] = setTimeout(() => {
      fetch(`${API}/picks`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          matchup_id: id,
          winner: pickData.winner,
          games: pickData.games,
          stat_leader: pickData.statLeader,
        }),
      }).catch(() => {});
    }, 600);
  }

  function handleSetResult(matchupId, winner, games, statLeader) {
    fetch(`${API}/admin/matchups/${matchupId}/result`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ winner, games, stat_leader: statLeader || "" }),
    }).catch(() => {});
  }

  function handleSaveRoster(teamName, players) {
    fetch(`${API}/admin/rosters`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ team_name: teamName, players }),
    })
      .then(r => r.json())
      .then(() => setRosters(prev => ({ ...prev, [teamName]: players })))
      .catch(() => {});
  }

  const activeSet = new Set(ACTIVE_COLS[renderRound]);
  const showAdmin = user?.isAdmin && adminMode;

  return (
    <div className="app">
      <div className="topbar">
        <span className="site-title">NBA Pick'em</span>
        <div className="topbar-right">
          {user?.isAdmin && (
            <button className={`mode-toggle ${adminMode ? "mode-admin" : "mode-user"}`}
              onClick={() => setAdminMode(m => !m)}>
              {adminMode ? "⚙ Admin view" : "👤 User view"}
            </button>
          )}
          {user?.isAdmin && adminMode && (
            <button className="lb-btn" onClick={() => setShowRosterEditor(true)}>Rosters</button>
          )}
          <button className="lb-btn" onClick={() => setShowRules(true)}>Rules</button>
          <button className="lb-btn" onClick={() => setShowLeaderboard(true)}>Leaderboard</button>
          {user ? (
            <div className="user-menu" onClick={() => setShowUserMenu(m => !m)}>
              {user.avatarUrl && <img src={user.avatarUrl} className="user-avatar" alt="" />}
              <span className="user-name">{user.username}</span>
              {user.isAdmin && <span className="admin-tag">admin</span>}
              {showUserMenu && (
                <div className="user-dropdown">
                  <a className="dropdown-item logout" href={`${API}/auth/logout`}>Log out</a>
                </div>
              )}
            </div>
          ) : (
            <a className="login-link" href={`${API}/auth/discord`}>Log in with Discord</a>
          )}
        </div>
      </div>

      <div className="tabs">
        {ROUNDS.map((r, i) => (
          <button key={i}
            className={`tab ${round === i ? "active" : ""}`}
            onClick={() => handleRoundChange(i)}>
            {r}
          </button>
        ))}
      </div>

      <div className="conf-labels">
        <span className="conf-west">Western Conference</span>
        <span className="conf-east">Eastern Conference</span>
      </div>

      <div className="grid" ref={gridRef}>
        {cols.map(([colMatchups, conf, label], i) => (
          <div key={i} className="col" style={{ width: colWidths[i] || COMP_W }}>
            {activeSet.has(i) ? (
              <div className="col-active">
                {colMatchups.map((m) => (
                  <MatchupCard
                    key={m.id}
                    matchup={m}
                    conf={conf}
                    picks={picks}
                    onPick={handlePick}
                    isAdmin={showAdmin}
                    onSetResult={handleSetResult}
                    rosters={rosters}
                  />
                ))}
              </div>
            ) : (
              <CompressedCol matchups={colMatchups} conf={conf} label={label} picks={picks} />
            )}
          </div>
        ))}
      </div>

      {showRosterEditor && (
        <RosterEditor
          matchups={matchups}
          rosters={rosters}
          onSave={handleSaveRoster}
          onClose={() => setShowRosterEditor(false)}
        />
      )}
      {showRules && <Rules onClose={() => setShowRules(false)} />}
      {showLeaderboard && <Leaderboard onClose={() => setShowLeaderboard(false)} />}
    </div>
  );
}