import { useEffect, useState } from "react";
import { API } from "../utils/helpers";

// Returns undefined while the /me request is in flight, null once it's
// confirmed there's no session, or the user object once logged in — callers
// that need to tell "still checking" apart from "confirmed logged out"
// (e.g. before redirecting to login) can rely on the undefined/null split.
export default function useCurrentUser() {
  const [user, setUser] = useState(undefined);

  useEffect(() => {
    fetch(`${API}/me`, { credentials: "include" })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        setUser(data ? { discordId: data.discord_id, username: data.username, handle: data.handle || data.username, isAdmin: data.is_admin, avatarUrl: data.avatar_url } : null);
      })
      .catch(() => setUser(null));
  }, []);

  return user;
}
