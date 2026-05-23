import { useState, useEffect } from "react";
import "../App.css";
import CommunityCard from "../components/CommunityCard";
import Sidebar from "../components/Sidebar";
import BracketGrid from "../components/BracketGrid";
import BracketOverview from "../components/BracketOverview";
import UserChip from "../components/UserChip";
import {
  API, ROUNDS, groupMatchups,
} from "../utils/helpers";

export default function CommunityBoard() {
  const [round, setRound] = useState(null); // null = overview
  const [matchups, setMatchups] = useState([]);
  const [aggregate, setAggregate] = useState({});
  const [cols, setCols] = useState([]);
  const [user, setUser] = useState(null);

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
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data) setUser({ username: data.username, isAdmin: data.is_admin, avatarUrl: data.avatar_url });
      })
      .catch(() => {});
  }, []);

  function handleTab(i) {
    setRound(prev => prev === i ? null : i);
  }

  return (
    <div className="app">
      <Sidebar />
      <div className="main-content">
        <div className="page-header">
          <div className="topbar">
            <span className="site-title">Bracket</span>
            <div className="tabs">
              {ROUNDS.map((r, i) => (
                <button key={i} className={`tab ${round === i ? "active" : ""}`}
                  onClick={() => handleTab(i)}>{r}</button>
              ))}
            </div>
            <div className="topbar-right">
              <UserChip user={user} />
            </div>
          </div>
        </div>

        <div className="conf-labels">
          <span className="conf-west">Western Conference</span>
          <span className="conf-east">Eastern Conference</span>
        </div>

        {round === null ? (
          <BracketOverview cols={cols} onZoom={setRound} />
        ) : (
          <BracketGrid
            round={round}
            cols={cols}
            renderActive={(m, conf) => (
              <CommunityCard key={m.id} matchup={m} conf={conf} aggregate={aggregate[m.id] || null} />
            )}
          />
        )}
      </div>
    </div>
  );
}
