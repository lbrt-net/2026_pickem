import { useState, useEffect, useRef } from "react";
import "./App.css";

const API = "";

const ROUNDS = ["First round", "Conf semis", "Conf finals", "NBA Finals"];
const COMP_W = 54;
const GAP = 6;
const N_COLS = 7;

const ACTIVE_COLS = [[0, 6], [1, 5], [2, 4], [3]];

// ---------------------------------------------------------------------------
// Static player rosters keyed by matchup id — update each round as needed
// ---------------------------------------------------------------------------
const PLAYER_ROSTERS = {
  "e1": ["Cade Cunningham", "Jaden Ivey", "Ausar Thompson", "Tobias Harris"],
  "e4": ["Donovan Mitchell", "Darius Garland", "Evan Mobley", "Scottie Barnes", "RJ Barrett"],
  "e3": ["Jalen Brunson", "Karl-Anthony Towns", "OG Anunoby", "Trae Young", "Dyson Daniels"],
  "e2": ["Jayson Tatum", "Jaylen Brown", "Jrue Holiday", "Tyrese Maxey", "Paul George"],
  "w1": ["Shai Gilgeous-Alexander", "Jalen Williams", "Chet Holmgren", "Isaiah Hartenstein"],
  "w4": ["LeBron James", "Anthony Davis", "Austin Reaves", "Alperen Sengun", "Jalen Green"],
  "w3": ["Nikola Jokic", "Jamal Murray", "Michael Porter Jr.", "Anthony Edwards", "Julius Randle"],
  "w2": ["Victor Wembanyama", "Devin Vassell", "Scoot Henderson", "Anfernee Simons", "Jerami Grant"],
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function isLocked(matchup) {
  if (!matchup.lock_time) return false;
  return new Date(matchup.lock_time) <= new Date();
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
function MatchupCard({ matchup, conf, picks, onPick, isAdmin, onSetResult }) {
  const p = pickClass(conf);
  const pick = picks[matchup.id] || {};
  const locked = isLocked(matchup);
  const tbd = isTBD(matchup);
  const players = PLAYER_ROSTERS[matchup.id] || [];

  const teamA = matchup.team_a || "TBD";
  const teamB = matchup.team_b || "TBD";
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

  // Locked
  if (locked) {
    return (
      <div className="matchup locked">
        <div className="locked-badge">Locked</div>
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
            <span className="pick-label">Stat leader</span>
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
              <tr><th>#</th><th>User</th><th>Correct</th></tr>
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
                  <td className="lb-score">{row.correct}</td>
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
  const [matchups, setMatchups] = useState([]);
  const [cols, setCols] = useState(Array(N_COLS).fill([[], "west", ""]));
  const gridRef = useRef(null);
  const timerRef = useRef(null);
  const saveTimer = useRef({});

  // Load matchups
  useEffect(() => {
    fetch(`${API}/matchups`)
      .then(r => r.json())
      .then(data => {
        setMatchups(data);
        setCols(groupMatchups(data));
      })
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
                  />
                ))}
              </div>
            ) : (
              <CompressedCol matchups={colMatchups} conf={conf} label={label} picks={picks} />
            )}
          </div>
        ))}
      </div>

      {showLeaderboard && <Leaderboard onClose={() => setShowLeaderboard(false)} />}
    </div>
  );
}