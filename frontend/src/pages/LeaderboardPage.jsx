import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "../App.css";
import Sidebar from "../components/Sidebar";
import { API } from "../utils/helpers";

export default function LeaderboardPage() {
  const navigate = useNavigate();
  const [board, setBoard] = useState([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [showUserMenu, setShowUserMenu] = useState(false);

  useEffect(() => {
    fetch(`${API}/me`, { credentials: "include" })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setUser({ username: data.username, avatarUrl: data.avatar_url }); })
      .catch(() => {});

    fetch(`${API}/leaderboard`, { credentials: "include" })
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
    <div className="app">
      <Sidebar />
      <div className="main-content">
        <div className="topbar">
          <span className="site-title">Leaderboard</span>
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

        <div className="page-container">
          {loading ? (
            <div className="modal-loading">Loading...</div>
          ) : (
            <table className="lb-table">
              <thead>
                <tr>
                  <th>#</th><th>User</th>
                  {rounds.map(r => <th key={r.key}>{r.label}</th>)}
                  <th>Pts</th>
                </tr>
              </thead>
              <tbody>
                {board.map((row, i) => (
                  <tr key={row.username} className="lb-row" onClick={() => navigate(`/user/${encodeURIComponent(row.username)}`)}>
                    <td className="lb-rank">{i + 1}</td>
                    <td className="lb-name">
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        {row.avatar_url && <img src={row.avatar_url} style={{ width: 22, height: 22, borderRadius: "50%", outline: "1.5px solid rgba(255,255,255,0.15)" }} alt="" />}
                        {row.username}
                      </div>
                    </td>
                    {rounds.map(r => (
                      <td key={r.key} style={{ color: "var(--text-2)", fontSize: 12 }}>{row[r.key] || 0}</td>
                    ))}
                    <td className="lb-score">{row.points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
