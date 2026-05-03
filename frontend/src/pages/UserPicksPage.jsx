import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import "../App.css";
import MatchupCard from "../components/MatchupCard";
import CompressedCol from "../components/CompressedCol";
import {
  API, ROUNDS, COMP_W, N_COLS, ACTIVE_COLS,
  groupMatchups, computeWidths,
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
  const navigate = useNavigate();
  const [picks, setPicks] = useState({});
  const [matchups, setMatchups] = useState([]);
  const [cols, setCols] = useState(Array(N_COLS).fill([[], "west", ""]));
  const [rosters, setRosters] = useState({});
  const [round, setRound] = useState(0);
  const [renderRound, setRenderRound] = useState(0);
  const [colWidths, setColWidths] = useState(Array(N_COLS).fill(0));
  const [pickStatus, setPickStatus] = useState({});
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const gridRef = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/matchups`).then(r => r.json()),
      fetch(`${API}/rosters`).then(r => r.json()),
      fetch(`${API}/picks/user/${encodeURIComponent(username)}`).then(r => {
        if (r.status === 404) { setNotFound(true); return null; }
        return r.json();
      }),
      fetch(`${API}/picks/user/${encodeURIComponent(username)}/status`).then(r => r.ok ? r.json() : null),
    ]).then(([matchupData, rosterData, pickData, statusData]) => {
      setMatchups(matchupData);
      setCols(groupMatchups(matchupData));
      setRosters(rosterData);
      if (pickData) {
        const rehydrated = {};
        (pickData.picks || []).forEach(p => {
          rehydrated[p.matchup_id] = { winner: p.winner, games: p.games, statLeader: p.stat_leader };
        });
        setPicks(rehydrated);
      }
      if (statusData) setPickStatus(statusData.status || {});
      setLoading(false);
      setTimeout(() => {
        if (gridRef.current) {
          setColWidths(computeWidths(0, gridRef.current.offsetWidth));
        }
      }, 50);
    }).catch(() => setLoading(false));
  }, [username]);

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

  if (loading) return <div className="app"><div className="modal-loading">Loading...</div></div>;
  if (notFound) return (
    <div className="app">
      <div className="topbar">
        <button className="lb-btn" onClick={() => navigate("/")}>← Back</button>
      </div>
      <div className="modal-loading">User not found.</div>
    </div>
  );

  return (
    <div className="app">
      <div style={{ position: "sticky", top: 0, zIndex: 20, background: "#0a0f1e" }}>
        <div className="topbar" style={{ position: "relative", zIndex: "auto", marginBottom: 0 }}>
          <button className="lb-btn" onClick={() => navigate("/")}>← Back</button>
          <span className="site-title">{username}'s picks</span>
          <div style={{ width: 60 }} />
        </div>
        <div className="tabs" style={{ position: "relative", top: "auto", zIndex: "auto", marginTop: 0 }}>
          {ROUNDS.map((r, i) => (
            <button key={i} className={`tab ${round === i ? "active" : ""}`}
              onClick={() => handleRoundChange(i)}>{r}</button>
          ))}
        </div>
      </div>

      {(() => {
        const p = roundProgress[round];
        if (!p || p.total === 0) return null;
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

      <div className="conf-labels">
        <span className="conf-west">Western Conference</span>
        <span className="conf-east">Eastern Conference</span>
      </div>

      <div className="grid" ref={gridRef}>
        {cols.map(([colMatchups, conf, label], i) => (
          <div key={i} className="col" style={{ width: colWidths[i] || COMP_W }}>
            {activeSet.has(i) ? (
              <div className="col-active">
                {colMatchups.map(m => {
                  const pick = picks[m.id];
                  const pts = m.winner_result && pick ? pickPoints(pick, m) : null;
                  return (
                    <div key={m.id}>
                      <MatchupCard matchup={m} conf={conf} picks={picks} rosters={rosters} readonly={true} />
                      {pts !== null && (
                        <div style={{
                          textAlign: "center", fontSize: 12, fontWeight: 700,
                          marginTop: 4, marginBottom: 8,
                          color: pts >= 4 ? "#4ade80" : pts >= 2 ? "#fbbf24" : "#f87171",
                        }}>
                          {pts} / 5 pts
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <CompressedCol matchups={colMatchups} conf={conf} label={label} picks={picks} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
