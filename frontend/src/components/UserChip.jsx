import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { API } from "../utils/helpers";
import PhoneLogin from "./PhoneLogin";
import { deviceName } from "./deviceName";
import "./UserChip.css";

export default function UserChip({ user, next, extraLinks = [] }) {
  const [open, setOpen] = useState(false);
  const [phone, setPhone] = useState(false);
  // tell the server what device this login is really on (once per page load; the Devices list shows it)
  const loggedIn = !!user;
  useEffect(() => {
    if (!loggedIn) return;
    fetch(`${API}/auth/sessions/device`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device: deviceName() }) }).catch(() => {});
  }, [loggedIn]);
  if (!user) return <a className="login-link" href={`${API}/auth/discord${next ? `?next=${encodeURIComponent(next)}` : ""}`}>Log in</a>;
  return (
    <div className="user-menu" onClick={() => setOpen(o => !o)}>
      {user.avatarUrl && <img src={user.avatarUrl} className="user-avatar" alt="" />}
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
