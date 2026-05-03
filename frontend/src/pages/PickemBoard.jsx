import { useState, useEffect, useRef } from "react";
import { useNavigate, useParams, Navigate } from "react-router-dom";
import "../App.css";
import MatchupCard from "../components/MatchupCard";
import CompressedCol from "../components/CompressedCol";
import Leaderboard from "../components/Leaderboard";
import Rules from "../components/Rules";
import {
  API, ROUNDS, COMP_W, GAP, N_COLS, ACTIVE_COLS,
  groupMatchups, computeWidths, isLocked,
} from "../utils/helpers";

export default function PickemBoard() {
  const navigate = useNavigate();
  const [round, setRound] = useState(1);
  const [renderRound, setRenderRound] = useState(1);
  const [picks, setPicks] = useState({});
  const [colWidths, setColWidths] = useState(Array(N_COLS).fill(0));
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [pickStatus, setPickStatus] = useState({});
  const [user, setUser] = useState(null);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showLeaderboard, setShowLeaderboard] = useState(false);
  const [showRules, setShowRules] = useState(false);
  const [matchups, setMatchups] = useState([]);
  const [cols, setCols] = useState(Array(N_COLS).fill([[], "west", ""]));
  const [rosters, setRosters] = useState({});
  const { username } = useParams(); // undefined on /picks/me route
  const [loaded, setLoaded] = useState(false);

  const gridRef = useRef(null);
  const topbarRef = useRef(null);
  const timerRef = useRef(null);
  const saveTimer = useRef({});
  const [tabsTop, setTabsTop] = useState(49);

  useEffect(() => { window.scrollTo(0, 0); }, [username]);

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
    if (username === "me") return; // Navigate will redirect, avoid double-fetch
    setPicks({});
    setPickStatus({});
    fetch(`${API}/me`, { credentials: "include" })
      .then(r => { if (r.status === 401) return null; return r.json(); })
      .then(data => {
        if (!data) { setLoaded(true); return; }
        setUser({ username: data.username, isAdmin: data.is_admin, avatarUrl: data.avatar_url });
        setLoaded(true);
  
        // Determine whose picks to load:
        // - /picks/me → load own picks
        // - /picks/:username where username matches → load own picks (editable)
        // - /picks/:username where different → load that user's picks (readonly)
        const targetUser = username || data.username;
        const isOwnPage = !username || username === data.username;
  
        if (isOwnPage) {
          fetch(`${API}/picks/me`, { credentials: "include" })
            .then(r => { if (r.status === 401) return null; return r.json(); })
            .then(data => {
              if (!data) return;
              const rehydrated = {};
              (data.picks || []).forEach(p => {
                rehydrated[p.matchup_id] = { winner: p.winner, games: p.games, statLeader: p.stat_leader };
              });
              setPicks(rehydrated);
            })
            .catch(() => {});
        } else {
          fetch(`${API}/picks/user/${encodeURIComponent(targetUser)}`)
            .then(r => r.ok ? r.json() : null)
            .then(data => {
              if (!data) return;
              const rehydrated = {};
              (data.picks || []).forEach(p => {
                if (p.winner != null || p.games != null || p.stat_leader != null) {
                  rehydrated[p.matchup_id] = { winner: p.winner, games: p.games, statLeader: p.stat_leader };
                }
              });
              setPicks(rehydrated);
            })
            .catch(() => {});
          fetch(`${API}/picks/user/${encodeURIComponent(targetUser)}/status`)
            .then(r => r.ok ? r.json() : null)
            .then(data => {
              if (!data) return;
              setPickStatus(data.status || {});
            })
            .catch(() => {});
        }
      })
      .catch(() => setLoaded(true));
  }, [username]);

  useEffect(() => {
    function updateWidths() {
      setIsMobile(window.innerWidth < 768);
      if (!gridRef.current) return;
      setColWidths(computeWidths(round, gridRef.current.offsetWidth));
    }
    updateWidths();
    window.addEventListener("resize", updateWidths);
    return () => window.removeEventListener("resize", updateWidths);
  }, [round, loaded]);

  useEffect(() => {
    function measureTopbar() {
      if (!topbarRef.current) return;
      setTabsTop(topbarRef.current.offsetHeight);
    }
    measureTopbar();
    window.addEventListener("resize", measureTopbar);
    return () => window.removeEventListener("resize", measureTopbar);
  }, [loaded, username]);

  const isOwnPage = !username || username === user?.username;
  const readonly = !isOwnPage;

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

  // picks has real data for own page (all) and other pages (locked only)
  // pickStatus fills in unlocked matchups for other users' pages
  const hasWinner = (id) => id in picks ? !!picks[id]?.winner     : !!pickStatus[id]?.has_winner;
  const hasGames  = (id) => id in picks ? !!picks[id]?.games      : !!pickStatus[id]?.has_games;
  const hasStat   = (id) => id in picks ? !!picks[id]?.statLeader : !!pickStatus[id]?.has_stat_leader;

  const roundProgress = ROUNDS.map((_, i) => {
    const rm = matchups.filter(m => m.round === i + 1);
    const settled = rm.length > 0 && rm.every(m => isLocked(m));
    return {
      total:    rm.length,
      complete: rm.filter(m => hasWinner(m.id) && hasGames(m.id) && hasStat(m.id)).length,
      winners:  rm.filter(m => hasWinner(m.id)).length,
      games:    rm.filter(m => hasGames(m.id)).length,
      stats:    rm.filter(m => hasStat(m.id)).length,
      settled,
    };
  });


  if (!loaded) return null;

  if (loaded && !user) {
    return (
      <div className="app" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: "#e2e8f0", marginBottom: 8 }}>NBA Pick'em</div>
          <div style={{ fontSize: 13, color: "#4a5568", marginBottom: 28 }}>Log in to submit your picks</div>
          <a href={`${API}/auth/discord`}
            style={{ display: "inline-block", padding: "10px 24px", background: "#5865F2", color: "white", borderRadius: 8, fontSize: 14, fontWeight: 600, textDecoration: "none" }}>
            Log in with Discord
          </a>
        </div>
      </div>
    );
  }

  if (loaded && user && !username) {
    return <Navigate to={`/picks/${user.username}`} replace />;
  }

  return (
    <div className="app">
      <div className="topbar" ref={topbarRef}>
        <span className="site-title">NBA Pick'em</span>
        <div className="topbar-right">
          <button className="lb-btn" onClick={() => navigate("/")}>The Field</button>
          <span style={{ fontSize: 12, color: "#4a5568", padding: "4px 10px" }}>
            {readonly ? `${username}'s Picks` : "My Picks"}
          </span>

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
            <a className="login-link" href={`${API}/auth/discord`}>Log in with Discord</a>
          )}
        </div>
      </div>

      <div className="tabs" style={{ top: tabsTop }}>
        {ROUNDS.map((r, i) => (
          <button key={i} className={`tab ${round === i ? "active" : ""}`}
            onClick={() => handleRoundChange(i)}>{r}</button>
        ))}
      </div>

      {(() => {
        const p = roundProgress[round];
        const show = p.total > 0;
        if (!show) return null;
        const allDone = p.complete === p.total;
        return (
          <div style={{ display: "flex", justifyContent: "center", alignItems: "baseline", gap: 16, fontSize: 13, marginBottom: 8 }}>
            <span style={{ color: allDone ? "#4ade80" : "#fff", fontWeight: 600 }}>
              {p.complete}/{p.total} complete
            </span>
            {[["Winner", p.winners], ["Length", p.games], ["Stat", p.stats]].map(([label, count]) => (
              <span key={label} style={{ color: count === p.total ? "#4ade80" : "#fff" }}>
                {label} {count}/{p.total}
              </span>
            ))}
          </div>
        );
      })()}

      {!isMobile && (
        <div className="conf-labels">
          <span className="conf-west">Western Conference</span>
          <span className="conf-east">Eastern Conference</span>
        </div>
      )}

      {isMobile ? (
        <div className="mobile-cards">
          {cols
            .filter((_, i) => activeSet.has(i))
            .flatMap(([colMatchups, conf]) =>
              colMatchups.map(m => (
                <MatchupCard key={m.id} matchup={m} conf={conf} picks={picks}
                  onPick={handlePick} isAdmin={!readonly && !!user?.isAdmin} readonly={readonly}
                  onSetResult={handleSetResult} rosters={rosters} />
              ))
            )}
        </div>
      ) : (
        <div className="grid" ref={gridRef}>
          {cols.map(([colMatchups, conf, label], i) => (
            <div key={i} className="col" style={{ width: colWidths[i] || COMP_W }}>
              {activeSet.has(i) ? (
                <div className="col-active">
                  {colMatchups.map(m => (
                    <MatchupCard key={m.id} matchup={m} conf={conf} picks={picks}
                      onPick={handlePick} isAdmin={!readonly && !!user?.isAdmin} readonly={readonly}
                      onSetResult={handleSetResult} rosters={rosters} />
                  ))}
                </div>
              ) : (
                <CompressedCol matchups={colMatchups} conf={conf} label={label} picks={picks} />
              )}
            </div>
          ))}
        </div>
      )}

      {showRules && <Rules onClose={() => setShowRules(false)} />}
      {showLeaderboard && <Leaderboard onClose={() => setShowLeaderboard(false)} />}
    </div>
  );
}