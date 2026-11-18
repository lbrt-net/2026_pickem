import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { API } from "../utils/helpers";
import PhoneLogin from "./PhoneLogin";
import { deviceNameDetailed } from "./deviceName";
import "./UserChip.css";

export default function UserChip({ user, next, extraLinks = [] }) {
  const [open, setOpen] = useState(false);
  const [phone, setPhone] = useState(false);
  const [badAvatar, setBadAvatar] = useState(false);
  // tell the server what device this login is really on (once per page load; the Devices list shows it)
  const loggedIn = !!user;
  useEffect(() => {
    if (!loggedIn) return;
    deviceNameDetailed().then(device => fetch(`${API}/auth/sessions/device`, { method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ device }) })).catch(() => {});
  }, [loggedIn]);
  if (!user) return <a className="login-link" href={`${API}/auth/discord${next ? `?next=${encodeURIComponent(next)}` : ""}`}>Log in</a>;
  return (
    <div className="user-menu" onClick={() => setOpen(o => !o)}>
      {/* the saved Discord picture goes dead when they change it on Discord (it refreshes on their next Discord
          login); show their first letter in the ring instead of an empty circle (2026-11-18) */}
      {user.avatarUrl && !badAvatar
        ? <img src={user.avatarUrl} className="user-avatar" alt="" onError={() => setBadAvatar(true)} />
        : <span className="user-avatar user-avatar-letter" aria-hidden="true">{(user.username || "?")[0]}</span>}
      <span className="user-name">{user.username}</span>
      {open && (
        <div className="user-dropdown">
          {extraLinks.map(({ label, to }) => (
            <Link key={to} className="dropdown-item" to={to}>{label}</Link>
          ))}
          <button type="button" className="dropdown-item" onClick={() => setPhone(true)}>Log in on your phone</button>
          <a className="dropdown-item logout" href={`${API}/auth/logout`}>Log out</a>
        </div>
      )}
      {phone && <PhoneLogin onClose={() => setPhone(false)} />}
    </div>
  );
}
