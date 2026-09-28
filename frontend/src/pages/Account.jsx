import { useEffect } from "react";
import useCurrentUser from "../hooks/useCurrentUser";
import MainNav from "../components/shared/MainNav";
import { API } from "../utils/helpers";

export default function Account() {
  const user = useCurrentUser(); // undefined = still checking, null = confirmed logged out

  useEffect(() => {
    if (user === null) window.location.href = `${API}/auth/discord?next=%2Faccount`;
  }, [user]);

  return (
    <div className="site-ui" style={{ minHeight: "100vh", background: "var(--bg)" }}>
      <MainNav />
      <div style={{ padding: 24, fontSize: 14 }}>
        {user === undefined && "Checking…"}
        {user === null && "Redirecting to login…"}
        {user && `Signed in as ${user.username}`}
      </div>
    </div>
  );
}
