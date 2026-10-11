import { useState } from "react";
import { Link } from "react-router-dom";
import { API } from "../utils/helpers";
import PhoneLogin from "./PhoneLogin";
import Devices from "./Devices";
import "./UserChip.css";

export default function UserChip({ user, next, extraLinks = [] }) {
  const [open, setOpen] = useState(false);
  const [phone, setPhone] = useState(false);
  const [devices, setDevices] = useState(false);
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
          <button type="button" className="dropdown-item" onClick={() => setDevices(true)}>Devices</button>
          <a className="dropdown-item logout" href={`${API}/auth/logout`}>Log out</a>
        </div>
      )}
      {phone && <PhoneLogin onClose={() => setPhone(false)} />}
      {devices && <Devices onClose={() => setDevices(false)} />}
    </div>
  );
}
