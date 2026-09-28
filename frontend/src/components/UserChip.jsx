import { useState } from "react";
import { Link } from "react-router-dom";
import { API } from "../utils/helpers";
import "./UserChip.css";

export default function UserChip({ user, next, extraLinks = [] }) {
  const [open, setOpen] = useState(false);
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
          <a className="dropdown-item logout" href={`${API}/auth/logout`}>Log out</a>
        </div>
      )}
    </div>
  );
}
