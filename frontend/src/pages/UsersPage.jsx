import { useState, useEffect } from "react";
import "../pickem-2026.css";
import AppTopBar from "../components/AppTopBar";
import { API } from "../utils/helpers";

function ToggleBtn({ active, activeLabel, inactiveLabel, color, onClick, disabled }) {
  return (
    <button onClick={disabled ? undefined : onClick} style={{
      fontSize: 11, padding: "3px 8px", borderRadius: 4,
      cursor: disabled ? "default" : "pointer",
      border: `1px solid ${active ? color : "var(--border)"}`,
      background: active ? `${color}22` : "transparent",
      color: active ? color : "var(--text-muted)",
      fontWeight: active ? 600 : 400,
      opacity: disabled ? 0.5 : 1,
      transition: "all 0.15s",
    }}>
      {active ? activeLabel : inactiveLabel}
    </button>
  );
}

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/admin/users`, { credentials: "include" })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { setUsers(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  async function toggle(discordId, field) {
    const res = await fetch(`${API}/admin/users/${discordId}/${field}`, {
      method: "POST", credentials: "include",
    });
    if (!res.ok) return;
    const data = await res.json();
    setUsers(prev => prev.map(u =>
      u.discord_id === discordId ? { ...u, [`is_${field}`]: data[`is_${field}`] } : u
    ));
  }

  function confirmToggle(u, field) {
    const username = u.username;
    let msg;
    if (field === "ban") {
      msg = u.is_banned
        ? `Unban ${username}?`
        : `Ban ${username}? They will be blocked from logging in.`;
    } else if (field === "admin") {
      msg = u.is_admin
        ? `Remove admin from ${username}?`
        : `Make ${username} an admin? They will be able to edit bracket results and manage users.`;
    }
    if (window.confirm(msg)) toggle(u.discord_id, field);
  }

  return (
    <>
    <AppTopBar />
    <div className="app">
      <div className="main-content">
        <div className="page-header">
          <div className="topbar">
            <span className="site-title">Users</span>
          </div>
        </div>

        {loading ? (
          <div className="modal-loading">Loading...</div>
        ) : (
          <table className="lb-table">
            <thead>
              <tr>
                <th>#</th>
                <th>User</th>
                <th>Admin</th>
                <th>Hidden</th>
                <th>Banned</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u, i) => (
                <tr key={u.discord_id} className="lb-row" style={{ cursor: "default" }}>
                  <td className="lb-rank">{i + 1}</td>
                  <td className="lb-name">
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      {u.avatar_url && (
                        <img src={u.avatar_url} style={{ width: 22, height: 22, borderRadius: "50%", outline: "1.5px solid rgba(255,255,255,0.15)" }} alt="" />
                      )}
                      <span style={{ color: u.is_banned ? "var(--text-muted)" : u.is_hidden ? "var(--text-2)" : "var(--text)" }}>
                        {u.username}
                      </span>
                    </div>
                  </td>
                  <td>
                    {u.is_owner ? (
                      <span style={{ fontSize: 11, padding: "3px 8px", borderRadius: 4, border: "1px solid var(--border)", color: "var(--text-muted)" }}>Owner</span>
                    ) : (
                      <ToggleBtn
                        active={u.is_admin}
                        activeLabel="Admin"
                        inactiveLabel="User"
                        color="var(--accent-blue)"
                        onClick={() => confirmToggle(u, "admin")}
                      />
                    )}
                  </td>
                  <td>
                    <ToggleBtn
                      active={u.is_hidden}
                      activeLabel="Hidden"
                      inactiveLabel="Visible"
                      color="var(--accent-gold)"
                      onClick={() => toggle(u.discord_id, "hidden")}
                      disabled={u.is_owner}
                    />
                  </td>
                  <td>
                    <ToggleBtn
                      active={u.is_banned}
                      activeLabel="Banned"
                      inactiveLabel="Active"
                      color="var(--accent-red)"
                      onClick={() => confirmToggle(u, "ban")}
                      disabled={u.is_owner}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
    </>
  );
}
