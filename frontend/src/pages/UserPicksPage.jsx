import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import "../App.css";
import MatchupCard from "../components/MatchupCard";
import Sidebar from "../components/Sidebar";
import BracketGrid from "../components/BracketGrid";
import UserChip from "../components/UserChip";
import {
  API, ROUNDS, groupMatchups,
} from "../utils/helpers";

function pickPoints(pick, matchup) {
  let pts = 0;
  const winnerCorrect = pick.winner && pick.winner === matchup.winner_result;
  if (winnerCorrect) pts += 2;
  if (pick.games != null && matchup.games_result != null) {
    if (winnerCorrect) {
      const dist = Math.abs(pick.games - matchup.games_result);
      if (dist === 0) pts += 2;
      else if (dist === 1) pts += 1;
    } else {
      const dist = Math.abs(15 - pick.games - matchup.games_result);
      if (dist <= 2) pts += 1;
    }
  }
  if (pick.stat_leader && matchup.stat_leader_result) {
    const leaders = matchup.stat_leader_result.split(",").map(s => s.trim().toLowerCase());
    if (leaders.includes(pick.stat_leader.trim().toLowerCase())) pts += 1;
  }
  return Math.min(pts, 5);
}

export default function UserPicksPage() {
  const { username } = useParams();
  const [picks, setPicks] = useState({});
  const [cols, setCols] = useState([]);
  const [matchups, setMatchups] = useState([]);
  const [rosters, setRosters] = useState({});
  const [round, setRound] = useState(2);
  const [pickStatus, setPickStatus] = useState({});
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [user, setUser] = useState(null);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/matchups`).then(r => r.json()),
      fetch(`${API}/rosters`).then(r => r.json()),
      fetch(`${API}/picks/user/${encodeURIComponent(username)}`).then(r => {
        if (r.status === 404) { setNotFound(true); return null; }
        return r.json();
      }),
      fetch(`${API}/picks/user/${encodeURIComponent(username)}/status`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/me`, { credentials: "include" }).then(r => r.ok ? r.json() : null),
    ]).then(([matchupData, rosterData, pickData, statusData, meData]) => {
      setCols(groupMatchups(matchupData));
      setMatchups(matchupData);
      setRosters(rosterData);
      if (pickData) {
        const rehydrated = {};
        (pickData.picks || []).forEach(p => {
          rehydrated[p.matchup_id] = { winner: p.winner, games: p.games, statLeader: p.stat_leader };
        });
        setPicks(rehydrated);
      }
      if (statusData) setPickStatus(statusData.status || {});
      if (meData) setUser({ username: meData.username, avatarUrl: meData.avatar_url });
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [username]);

  const hasWinner = (id) => picks[id]?.winner || pickStatus[id]?.has_winner;
  const hasGames  = (id) => picks[id]?.games  || pickStatus[id]?.has_games;
  const hasStat   = (id) => picks[id]?.statLeader || pickStatus[id]?.has_stat_leader;

  const roundProgress = ROUNDS.map((_, i) => {
    const rm = matchups.filter(m => m.round === i + 1);
    return {
      total:    rm.length,
      complete: rm.filter(m => hasWinner(m.id) && hasGames(m.id) && hasStat(m.id)).length,
      winners:  rm.filter(m => hasWinner(m.id)).length,
      games:    rm.filter(m => hasGames(m.id)).length,
      stats:    rm.filter(m => hasStat(m.id)).length,
    };
  });

  if (loading) return (
    <div className="app">
      <Sidebar />
      <div className="main-content"><div className="modal-loading">Loading...</div></div>
    </div>
  );

  if (notFound) return (
    <div className="app">
      <Sidebar />
      <div className="main-content">
        <div className="page-header">
          <div className="topbar"><span className="site-title">Not found</span></div>
        </div>
        <div className="modal-loading">User not found.</div>
      </div>
    </div>
  );

  const p = roundProgress[round];

  return (
    <div className="app">
      <Sidebar />
      <div className="main-content">
        <div className="page-header">
          <div className="topbar">
            <span className="site-title">{username}'s picks</span>
            <div className="tabs">
              {ROUNDS.map((r, i) => (
                <button key={i} className={`tab ${round === i ? "active" : ""}`}
                  onClick={() => setRound(i)}>{r}</button>
              ))}
            </div>
            <div className="topbar-right">
              <UserChip user={user} />
            </div>
          </div>
          {p && p.total > 0 && (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "baseline", gap: 16, fontSize: 13, padding: "4px 0 6px" }}>
              <span style={{ color: p.complete === p.total ? "var(--accent-blue)" : "var(--text)", fontWeight: 600 }}>
                {p.complete}/{p.total} complete
              </span>
              {[["Winner", p.winners], ["Length", p.games], ["Stat", p.stats]].map(([label, count]) => (
                <span key={label} style={{ color: count === p.total ? "var(--accent-blue)" : "var(--text-2)" }}>
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

        <div className="scroll-vert">
          <BracketGrid
            round={round}
            cols={cols}
            picks={picks}
            renderActive={(m, conf) => {
              const pick = picks[m.id];
              const pts = m.winner_result && pick ? pickPoints(pick, m) : null;
              return (
                <div key={m.id}>
                  <MatchupCard matchup={m} conf={conf} picks={picks} rosters={rosters} readonly={true} />
                  {pts !== null && (
                    <div style={{ textAlign: "center", fontSize: 12, fontWeight: 700, marginTop: 4, marginBottom: 8, color: pts >= 4 ? "var(--accent-blue)" : pts >= 2 ? "var(--accent-gold)" : "var(--accent-red)" }}>
                      {pts} / 5 pts
                    </div>
                  )}
                </div>
              );
            }}
          />
        </div>
      </div>
    </div>
  );
}
