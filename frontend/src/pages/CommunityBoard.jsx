import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import "../App.css";
import CommunityCard from "../components/CommunityCard";
import CompressedCol from "../components/CompressedCol";
import Sidebar from "../components/Sidebar";
import {
  API, ROUNDS, COMP_W, GAP, N_COLS, ACTIVE_COLS,
  groupMatchups, computeWidths,
} from "../utils/helpers";

export default function CommunityBoard() {
  const navigate = useNavigate();
  const [round, setRound] = useState(2);
  const [renderRound, setRenderRound] = useState(2);
  const [matchups, setMatchups] = useState([]);
  const [aggregate, setAggregate] = useState({});
  const [cols, setCols] = useState(Array(N_COLS).fill([[], "west", ""]));
  const [colWidths, setColWidths] = useState(Array(N_COLS).fill(0));
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [user, setUser] = useState(null);
  const [showUserMenu, setShowUserMenu] = useState(false);

  const gridRef = useRef(null);
  const timerRef = useRef(null);
  const topbarRef = useRef(null);
  const [tabsTop, setTabsTop] = useState(49);

  useEffect(() => {
    fetch(`${API}/matchups`)
      .then(r => r.json())
      .then(data => { setMatchups(data); setCols(groupMatchups(data)); })
      .catch(() => {});

    fetch(`${API}/matchups/aggregate`)
      .then(r => r.json())
      .then(setAggregate)
      .catch(() => {});

    fetch(`${API}/me`, { credentials: "include" })
      .then(r => { if (r.status === 401) return null; return r.json(); })
      .then(data => {
        if (!data) return;
        setUser({ username: data.username, isAdmin: data.is_admin, avatarUrl: data.avatar_url });
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (topbarRef.current) setTabsTop(topbarRef.current.offsetHeight);
  }, [user]);

  useEffect(() => {
    function updateWidths() {
      setIsMobile(window.innerWidth < 768);
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
      <Sidebar />
      <div className="main-content">
        <div className="topbar" ref={topbarRef}>
          <span className="site-title">Bracket</span>
          <div className="topbar-right">
            {user ? (
              <div className="user-menu" onClick={() => setShowUserMenu(m => !m)}>
                {user.avatarUrl && <img src={user.avatarUrl} className="user-avatar" alt="" />}
                <span className="user-name">{user.username}</span>
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

        <div className="tabs" style={{ top: tabsTop }}>
          {ROUNDS.map((r, i) => (
            <button key={i} className={`tab ${round === i ? "active" : ""}`}
              onClick={() => handleRoundChange(i)}>{r}</button>
          ))}
        </div>

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
                  <CommunityCard key={m.id} matchup={m} conf={conf} aggregate={aggregate[m.id] || null} />
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
                      <CommunityCard key={m.id} matchup={m} conf={conf} aggregate={aggregate[m.id] || null} />
                    ))}
                  </div>
                ) : (
                  <CompressedCol matchups={colMatchups} conf={conf} label={label} picks={{}} />
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
