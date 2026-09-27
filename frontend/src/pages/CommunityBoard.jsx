import { useState, useEffect } from "react";
import "../pickem-2026.css";
import CommunityCard from "../components/CommunityCard";
import AppTopBar from "../components/AppTopBar";
import Sidebar from "../components/Sidebar";
import ChampionsBanner from "../components/ChampionsBanner";
import BracketGrid from "../components/BracketGrid";
import BracketOverview from "../components/BracketOverview";
import {
  API, ROUNDS, groupMatchups,
} from "../utils/helpers";

export default function CommunityBoard() {
  const [round, setRound] = useState(window.innerWidth < 768 ? 3 : null);
  const [matchups, setMatchups] = useState([]);
  const [aggregate, setAggregate] = useState({});
  const [cols, setCols] = useState([]);
  const [userCount, setUserCount] = useState(null);

  useEffect(() => {
    fetch(`${API}/pickem/2026/stats`)
      .then(r => r.json())
      .then(data => setUserCount(data.user_count))
      .catch(() => {});

    fetch(`${API}/pickem/2026/matchups`)
      .then(r => r.json())
      .then(data => { setMatchups(data); setCols(groupMatchups(data)); })
      .catch(() => {});

    fetch(`${API}/pickem/2026/matchups/aggregate`)
      .then(r => r.json())
      .then(setAggregate)
      .catch(() => {});
  }, []);

  function handleTab(i) {
    setRound(prev => prev === i ? null : i);
  }

  return (
    <>
    <AppTopBar />
    <div className="app">
      <ChampionsBanner />
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
          </div>
        </div>

        {userCount !== null && (
          <div className="tagline">There are currently {userCount.toLocaleString()} {userCount === 1 ? "person" : "people"} playing!</div>
        )}

        <div className="conf-labels">
          <span className="conf-west">Western Conference</span>
          <span className="conf-east">Eastern Conference</span>
        </div>

        {round === null ? (
          <div className="scroll-horiz">
            <BracketOverview cols={cols} onZoom={setRound} />
          </div>
        ) : (
          <div className="scroll-vert">
            <BracketGrid
              round={round}
              cols={cols}
              renderActive={(m, conf) => (
                <CommunityCard key={m.id} matchup={m} conf={conf} aggregate={aggregate[m.id] || null} />
              )}
            />
          </div>
        )}
      </div>
    </div>
    </>
  );
}
