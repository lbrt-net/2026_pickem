import { useState, useEffect } from "react";
import "../App.css";
import Sidebar from "../components/Sidebar";
import UserChip from "../components/UserChip";
import { API } from "../utils/helpers";

export default function RulesPage() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    fetch(`${API}/me`, { credentials: "include" })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setUser({ username: data.username, avatarUrl: data.avatar_url }); })
      .catch(() => {});
  }, []);

  return (
    <div className="app">
      <Sidebar />
      <div className="main-content">
        <div className="page-header">
          <div className="topbar">
            <span className="site-title">Rules</span>
            <div className="topbar-right">
              <UserChip user={user} />
            </div>
          </div>
        </div>

        <div className="page-container">
          <div className="rules-body">
            <p className="rules-section-title">Points per series</p>
            <table className="rules-table">
              <tbody>
                <tr><td>Correct winner</td><td className="rules-pts">2 pts</td></tr>
                <tr><td>Correct series length (exact)</td><td className="rules-pts">2 pts</td></tr>
                <tr><td>Correct series length (1 off)</td><td className="rules-pts">1 pt</td></tr>
                <tr><td>Correct stat leader</td><td className="rules-pts">1 pt</td></tr>
                <tr className="rules-max"><td>Max per series</td><td className="rules-pts">5 pts</td></tr>
              </tbody>
            </table>
            <p className="rules-note">Length points apply regardless of whether your winner was correct.</p>
            <p className="rules-section-title" style={{ marginTop: 18 }}>Round multipliers</p>
            <table className="rules-table">
              <tbody>
                <tr><td>R1</td><td className="rules-pts">1×</td></tr>
                <tr><td>R2</td><td className="rules-pts">4×</td></tr>
                <tr><td>CF</td><td className="rules-pts">8×</td></tr>
                <tr><td>Finals</td><td className="rules-pts">16×</td></tr>
              </tbody>
            </table>
            <p className="rules-note">A perfect Finals series = <span className="rules-highlight">80 pts</span>.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
