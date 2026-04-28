import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { API } from "../utils/helpers";

export default function Leaderboard({ onClose }) {
  const [board, setBoard] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetch(`${API}/leaderboard`, { credentials: "include" })
      .then(r => r.json())
      .then(data => { setBoard(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  function handleUserClick(username) {
    onClose();
    navigate(`/user/${encodeURIComponent(username)}`);
  }

  const rounds = [
    { key: "r1", label: "R1" },
    { key: "r2", label: "R2" },
    { key: "r3", label: "CF" },
    { key: "r4", label: "Fin" },
  ].filter(r => board.some(row => row[r.key] > 0));

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Leaderboard</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        {loading ? (
          <div className="modal-loading">Loading...</div>
        ) : (
          <table className="lb-table">
            <thead>
              <tr>
                <th>#</th><th>User</th>
                {rounds.map(r => <th key={r.key} style={{ color: "rgba(255,255,255,0.4)", fontWeight: 500 }}>{r.label}</th>)}
                <th>Pts</th>
              </tr>
            </thead>
            <tbody>
              {board.map((row, i) => (
                <tr key={row.username} className="lb-row" onClick={() => handleUserClick(row.username)}>
                  <td className="lb-rank">{i + 1}</td>
                  <td className="lb-name">
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      {row.avatar_url && <img src={row.avatar_url} style={{ width: 22, height: 22, borderRadius: "50%", outline: "1.5px solid rgba(255,255,255,0.2)" }} alt="" />}
                      {row.username}
                    </div>
                  </td>
                  {rounds.map(r => (
                    <td key={r.key} style={{ color: "rgba(255,255,255,0.45)", fontSize: 12 }}>{row[r.key] || 0}</td>
                  ))}
                  <td className="lb-score">{row.points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
