import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import MatchupCard from "../components/MatchupCard";
import CompressedCol from "../components/CompressedCol";
import Leaderboard from "../components/Leaderboard";
import Rules from "../components/Rules";
import {
  API, ROUNDS, COMP_W, GAP, N_COLS, ACTIVE_COLS,
  groupMatchups, computeWidths,
} from "../utils/helpers";

export default function PickemBoard() {
  const navigate = useNavigate();
  const [round, setRound] = useState(0);
  const [renderRound, setRenderRound] = useState(0);
  const [picks, setPicks] = useState({});
  const [colWidths, setColWidths] = useState(Array(N_COLS).fill(0));
  const [user, setUser] = useState(null);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showLeaderboard, setShowLeaderboard] = useState(false);
  const [showRules, setShowRules] = useState(false);
  const [matchups, setMatchups] = useState([]);
  const [cols, setCols] = useState(Array(N_COLS).fill([[], "west", ""]));
  const [rosters, setRosters] = useState({});

  const gridRef = useRef(null);
  const timerRef = useRef(null);
  const saveTimer = useRef({});

  // Load matchups + rosters
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
      .then(r => { if (r.status === 401) return null; return r.json(); })
      .then(data => {
        if (!data) return;
        setUser({ username: data.username, isAdmin: data.is_admin, avatarUrl: data.avatar_url });
        const rehydrated = {};
        (data.picks || []).forEach(p => {
          rehydrated[p.matchup_id] = { winner: p.winner, games: p.games, statLeader: p.stat_leader };
        });
        setPicks(rehydrated);
      })
      .catch(() => {});
  }, []);

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
    setPicks(prev => ({ ...prev, [id]: pickData }));
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
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ winner, games, stat_leader: statLeader || "" }),
    }).catch(() => {});
  }

  const activeSet = new Set(ACTIVE_COLS[renderRound]);

  return (
    <div className="app">
      <div className="topbar">
        <span className="site-title">NBA Pick'em</span>
        <div className="topbar-right">
          {user?.isAdmin && (
            <button className="lb-btn" onClick={() => navigate("/admin")}>Admin</button>
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
          <button key={i} className={`tab ${round === i ? "active" : ""}`}
            onClick={() => handleRoundChange(i)}>{r}</button>
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
                {colMatchups.map(m => (
                  <MatchupCard key={m.id} matchup={m} conf={conf} picks={picks}
                    onPick={handlePick} isAdmin={false} onSetResult={handleSetResult}
                    rosters={rosters} />
                ))}
              </div>
            ) : (
              <CompressedCol matchups={colMatchups} conf={conf} label={label} picks={picks} />
            )}
          </div>
        ))}
      </div>

      {showRules && <Rules onClose={() => setShowRules(false)} />}
      {showLeaderboard && <Leaderboard onClose={() => setShowLeaderboard(false)} />}
    </div>
  );
}