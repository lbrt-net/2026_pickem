import { useState } from "react";
import { API } from "../utils/helpers";

export default function UserChip({ user }) {
  const [open, setOpen] = useState(false);
  if (!user) return <a className="login-link" href={`${API}/auth/discord`}>Log in</a>;
  return (
    <div className="user-menu" onClick={() => setOpen(o => !o)}>
      {user.avatarUrl && <img src={user.avatarUrl} className="user-avatar" alt="" />}
      <span className="user-name">{user.username}</span>
      {open && (
        <div className="user-dropdown">
          <a className="dropdown-item logout" href={`${API}/auth/logout`}>Log out</a>
        </div>
      )}
    </div>
  );
}
