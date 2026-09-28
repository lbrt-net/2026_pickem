import { useState, useEffect, useRef } from "react";
import { useNavigate, useParams, Navigate } from "react-router-dom";
import "../pickem-2026.css";
import MatchupCard from "../components/MatchupCard";
import AppTopBar from "../components/AppTopBar";
import BracketGrid from "../components/BracketGrid";
import {
  API, ROUNDS, groupMatchups,
} from "../utils/helpers";

export default function PickemBoard() {
  const navigate = useNavigate();
  const [round, setRound] = useState(3);
  const [picks, setPicks] = useState({});
  const [user, setUser] = useState(null);
  const [matchups, setMatchups] = useState([]);
  const [cols, setCols] = useState([]);
  const [rosters, setRosters] = useState({});
  const { username } = useParams();
  const [loaded, setLoaded] = useState(false);
  const [statGuide, setStatGuide] = useState([]);
  const saveTimer = useRef({});

  useEffect(() => { window.scrollTo(0, 0); }, [username]);

  useEffect(() => {
    fetch(`${API}/pickem/2026/matchups`)
      .then(r => r.json())
      .then(data => { setMatchups(data); setCols(groupMatchups(data)); })
      .catch(() => {});
    fetch(`${API}/pickem/2026/rosters`).then(r => r.json()).then(setRosters).catch(() => {});
    fetch(`${API}/pickem/2026/stat-guide`).then(r => r.json()).then(setStatGuide).catch(() => {});
  }, []);

  // Adjust state during render instead of in an effect when username changes
  // (https://react.dev/learn/you-might-not-need-an-effect).
  const [prevUsername, setPrevUsername] = useState(username);
  if (username !== prevUsername) {
    setPrevUsername(username);
    setPicks({});
  }

  useEffect(() => {
    if (username === "me") return;
    fetch(`${API}/me`, { credentials: "include" })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data) { setLoaded(true); return; }
        const isOwnPage = !username || username === data.username;
        if (!isOwnPage) { navigate(`/pickem/2026/user/${username}`, { replace: true }); return; }
        setUser({ username: data.username, isAdmin: data.is_admin, avatarUrl: data.avatar_url });
        setLoaded(true);
        fetch(`${API}/pickem/2026/picks/me`, { credentials: "include" })
          .then(r => r.ok ? r.json() : null)
          .then(data => {
            if (!data) return;
            const rehydrated = {};
            (data.picks || []).forEach(p => {
              rehydrated[p.matchup_id] = { winner: p.winner, games: p.games, statLeader: p.stat_leader };
            });
            setPicks(rehydrated);
          })
          .catch(() => {});
      })
      .catch(() => setLoaded(true));
  }, [username, navigate]);

  function handlePick(id, pickData) {
    setPicks(prev => ({ ...prev, [id]: pickData }));
    clearTimeout(saveTimer.current[id]);
    saveTimer.current[id] = setTimeout(() => {
      fetch(`${API}/pickem/2026/picks`, {
        method: "POST", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ matchup_id: id, winner: pickData.winner, games: pickData.games, stat_leader: pickData.statLeader }),
      }).catch(() => {});
    }, 600);
  }

  function handleSetResult(matchupId, winner, games, statLeader) {
    fetch(`${API}/pickem/2026/admin/matchups/${matchupId}/result`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ winner, games, stat_leader: statLeader || "" }),
    }).catch(() => {});
  }

  const roundProgress = ROUNDS.map((_, i) => {
    const rm = matchups.filter(m => m.round === i + 1);
    return {
      total:    rm.length,
      complete: rm.filter(m => picks[m.id]?.winner && picks[m.id]?.games && picks[m.id]?.statLeader).length,
      winners:  rm.filter(m => picks[m.id]?.winner).length,
      games:    rm.filter(m => picks[m.id]?.games).length,
      stats:    rm.filter(m => picks[m.id]?.statLeader).length,
    };
  });

  if (!loaded) return null;

  if (loaded && !user) {
    return (
      <>
      <AppTopBar />
      <div className="app" style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: "var(--text)", marginBottom: 8 }}>NBA Pick'em</div>
          <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 28 }}>Log in to submit your picks</div>
          <a href={`${API}/auth/discord?next=%2Fpickem%2F2026%2Fpicks%2Fme`}
            style={{ display: "inline-block", padding: "10px 24px", background: "#5865F2", color: "white", borderRadius: 8, fontSize: 14, fontWeight: 600, textDecoration: "none" }}>
            Log in with Discord
          </a>
        </div>
      </div>
      </>
    );
  }

  if (loaded && user && !username) {
    return <Navigate to={`/pickem/2026/picks/${user.username}`} replace />;
  }

  const p = roundProgress[round];

  return (
    <>
    <AppTopBar />
    <div className="app">
      <div className="main-content">
        <div className="page-header">
          <div className="topbar">
            <span className="site-title">My Picks</span>
            <div className="tabs">
              {ROUNDS.map((r, i) => (
                <button key={i} className={`tab ${round === i ? "active" : ""}`}
                  onClick={() => setRound(i)}>{r}</button>
              ))}
            </div>
          </div>
          {p && p.total > 0 && (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "baseline", gap: 16, fontSize: 13, padding: "4px 0 6px" }}>
              <span style={{ color: p.complete === p.total ? "#4ade80" : "var(--text)", fontWeight: 600 }}>
                {p.complete}/{p.total} complete
              </span>
              {[["Winner", p.winners], ["Length", p.games], ["Stat", p.stats]].map(([label, count]) => (
                <span key={label} style={{ color: count === p.total ? "#4ade80" : "var(--text-2)" }}>
                  {label} {count}/{p.total}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="conf-labels">
          <span className="conf-west">Western Conference</span>
          <span className="conf-east">Eastern Conference</span>
        </div>

        <BracketGrid
          round={round}
          cols={cols}
          picks={picks}
          renderActive={(m, conf) => (
            <MatchupCard key={m.id} matchup={m} conf={conf} picks={picks}
              onPick={handlePick} isAdmin={!!user?.isAdmin}
              onSetResult={handleSetResult} rosters={rosters} statGuide={statGuide} />
          )}
        />
      </div>
    </div>
    </>
  );
}
