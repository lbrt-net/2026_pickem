import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "../pickem-2026.css";
import AppTopBar from "../components/AppTopBar";
import ChampionsBanner from "../components/ChampionsBanner";
import { API } from "../utils/helpers";

export default function LeaderboardPage() {
  const navigate = useNavigate();
  const [board, setBoard] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/pickem/2026/scores`, { credentials: "include" })
      .then(r => r.json())
      .then(data => { setBoard(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const rounds = [
    { key: "r1", label: "R1" },
    { key: "r2", label: "R2" },
    { key: "r3", label: "CF" },
    { key: "r4", label: "Finals" },
  ].filter(r => board.some(row => row[r.key] > 0));

  return (
    <>
    <AppTopBar />
    <div className="app">
      <ChampionsBanner />
      <div className="main-content">
        <div className="page-header">
          <div className="topbar">
            <span className="site-title">Leaderboard</span>
          </div>
        </div>

        <div className="page-container">
          {loading ? (
            <div className="modal-loading">Loading...</div>
          ) : (
            <div className="scroll-vert">
            <table className="lb-table lb-table-scroll">
              <thead>
                <tr>
                  <th>#</th><th>User</th>
                  {rounds.map(r => <th key={r.key}>{r.label}</th>)}
                  <th>Pts</th>
                </tr>
              </thead>
              <tbody>
                {board.map((row, i) => (
                  <tr key={row.username} className="lb-row" onClick={() => navigate(`/pickem/2026/user/${encodeURIComponent(row.username)}`)}>
                    <td className="lb-rank">{i + 1}</td>
                    <td className="lb-name">
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        {row.avatar_url && <img src={row.avatar_url} style={{ width: 22, height: 22, borderRadius: "50%", outline: "1.5px solid rgba(60,40,10,0.4)" }} alt="" />}
                        {row.username}
                      </div>
                    </td>
                    {rounds.map(r => (
                      <td key={r.key} style={{ fontSize: 12 }}>{row[r.key] || 0}</td>
                    ))}
                    <td className="lb-score">{row.points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )}
        </div>
      </div>
    </div>
    </>
  );
}
