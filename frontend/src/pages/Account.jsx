import { useEffect, useState } from "react";
import useCurrentUser from "../hooks/useCurrentUser";
import MainNav from "../components/shared/MainNav";
import Devices from "../components/Devices";
import PhoneLogin from "../components/PhoneLogin";
import { API } from "../utils/helpers";
import "../components/Account.css";

// Account (/account, account menu → Account): who you are, the devices you're logged in on, and a QR code to log in
// on your phone.
export default function Account() {
  const user = useCurrentUser(); // undefined = still checking, null = confirmed logged out
  const [qr, setQr] = useState(false);

  useEffect(() => {
    if (user === null) window.location.href = `${API}/auth/discord?next=%2Faccount`;
  }, [user]);

  return (
    <div className="site-ui ac-page">
      <MainNav />
      <main className="ac-main">
        <h1 className="ac-title">Account</h1>
        {user === undefined && <p className="ac-p">Loading…</p>}
        {user && (
          <>
            <section className="ac-me">
              {user.avatarUrl && <img src={user.avatarUrl} alt="" className="ac-avatar" />}
              <b>{user.username}</b>
            </section>
            <Devices />
            <section className="ac-panel" aria-label="Log in on your phone">
              <div className="ac-head">Log in on your phone</div>
              <div className="ac-foot"><button type="button" className="ac-btn primary" onClick={() => setQr(true)}>Show code</button></div>
            </section>
            {qr && <PhoneLogin onClose={() => setQr(false)} />}
          </>
        )}
      </main>
    </div>
  );
}
