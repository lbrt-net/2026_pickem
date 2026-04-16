import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import MatchupCard from "../components/MatchupCard";
import CompressedCol from "../components/CompressedCol";
import {
  API, ROUNDS, COMP_W, N_COLS, ACTIVE_COLS,
  groupMatchups, computeWidths,
} from "../utils/helpers";

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
    ]).then(([matchupData, rosterData, pickData]) => {
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
      setLoading(false);
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
      <div className="topbar">
        <button className="lb-btn" onClick={() => navigate("/")}>← Back</button>
        <span className="site-title">{username}'s picks</span>
        <div style={{ width: 60 }} />
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
                    rosters={rosters} readonly={true} />
                ))}
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