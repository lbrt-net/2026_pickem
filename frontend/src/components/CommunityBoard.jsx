import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import "../App.css";
import CommunityCard from "../components/CommunityCard";
import CompressedCol from "../components/CompressedCol";
import Leaderboard from "../components/Leaderboard";
import Rules from "../components/Rules";
import {
  API, ROUNDS, COMP_W, GAP, N_COLS, ACTIVE_COLS,
  groupMatchups, computeWidths,
} from "../utils/helpers";

export default function CommunityBoard() {
  const navigate = useNavigate();
  const [round, setRound] = useState(0);
  const [renderRound, setRenderRound] = useState(0);
  const [matchups, setMatchups] = useState([]);
  const [aggregate, setAggregate] = useState({});
  const [cols, setCols] = useState(Array(N_COLS).fill([[], "west", ""]));
  const [colWidths, setColWidths] = useState(Array(N_COLS).fill(0));
  const [user, setUser] = useState(null);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showLeaderboard, setShowLeaderboard] = useState(false);
  const [showRules, setShowRules] = useState(false);

  const gridRef = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => {
    // Matchups + aggregate can load in parallel
    fetch(`${API}/matchups`)
      .then(r => r.json())
      .then(data => { setMatchups(data); setCols(groupMatchups(data)); })
      .catch(() => {});

    fetch(`${API}/matchups/aggregate`)
      .then(r => r.json())
      .then(setAggregate)
      .catch(() => {});

    // User for topbar badge (optional — community board doesn't require login)
    fetch(`${API}/me`, { credentials: "include" })
      .then(r => { if (r.status === 401) return null; return r.json(); })
      .then(data => {
        if (!data) return;
        setUser({ username: data.username, isAdmin: data.is_admin, avatarUrl: data.avatar_url });
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

  const activeSet = new Set(ACTIVE_COLS[renderRound]);

  return (
    <div className="app">
      <div className="topbar">
        <span className="site-title">The Field</span>
        <div className="topbar-right">
          {/* Nav: community (current) | my picks */}
          <span style={{ fontSize: 12, color: "#4a5568", padding: "4px 10px" }}>The Field</span>
          <button className="lb-btn" onClick={() => navigate(user ? `/picks/${user.username}` : "/picks/me")}>
            My Picks
          </button>

          {user?.isAdmin && (
            <button className="lb-btn" onClick={() => navigate("/admin")}>Admin</button>
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
            <a className="login-link" href={`${API}/auth/discord`}>Log in</a>
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
                  <CommunityCard
                    key={m.id}
                    matchup={m}
                    conf={conf}
                    aggregate={aggregate[m.id] || null}
                  />
                ))}
              </div>
            ) : (
              <CompressedCol matchups={colMatchups} conf={conf} label={label} picks={{}} />
            )}
          </div>
        ))}
      </div>

      {showRules && <Rules onClose={() => setShowRules(false)} />}
      {showLeaderboard && <Leaderboard onClose={() => setShowLeaderboard(false)} />}
    </div>
  );
}