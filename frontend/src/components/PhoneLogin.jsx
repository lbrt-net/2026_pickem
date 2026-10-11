import { useCallback, useEffect, useState } from "react";
import QRCode from "qrcode";
import { API } from "../utils/helpers";
import "./PhoneLogin.css";

// "Log in on your phone": a QR code of a one-time login link (POST /auth/phone-link — 10 minutes, one use). The
// phone's camera opens it; a confirm page there logs the phone in. A new code replaces the old one when time's up.
export default function PhoneLogin({ onClose }) {
  const [qr, setQr] = useState(null);
  const [until, setUntil] = useState(0);
  const [now, setNow] = useState(() => Date.now());
  const [error, setError] = useState(null);

  const make = useCallback(async () => {
    setError(null); setQr(null);
    try {
      const r = await fetch(`${API}/auth/phone-link`, { method: "POST", credentials: "include" });
      if (!r.ok) throw new Error();
      const { url, minutes } = await r.json();
      // dark modules on white so any phone camera reads it
      setQr(await QRCode.toDataURL(url, { margin: 1, width: 260, color: { dark: "#000000", light: "#ffffff" } }));
      setUntil(Date.now() + minutes * 60000);
    } catch {
      setError("Couldn't make a code — try again.");
    }
  }, []);

  useEffect(() => { make(); }, [make]);
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    const esc = e => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", esc);
    return () => { clearInterval(t); window.removeEventListener("keydown", esc); };
  }, [onClose]);

  const left = Math.max(0, Math.round((until - now) / 1000));
  const expired = qr && left === 0;
  return (
    <div className="pl-modal" role="dialog" aria-modal="true" aria-label="Log in on your phone" onClick={e => { e.stopPropagation(); if (e.target === e.currentTarget) onClose(); }}>
      <div className="pl-box">
        <b className="pl-h">Log in on your phone</b>
        <div className="pl-qr">
          {qr && !expired && <img src={qr} alt="QR code to log in on your phone" width={260} height={260} />}
          {(!qr || expired) && !error && <span className="pl-wait">{expired ? "Code expired" : "Making a code…"}</span>}
          {error && <span className="pl-wait">{error}</span>}
        </div>
        <p className="pl-p">Point your phone's camera at the code{qr && !expired ? ` · ${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}` : ""}</p>
        <div className="pl-f">
          {(expired || error) && <button type="button" className="pl-btn primary" onClick={make}>New code</button>}
          <button type="button" className="pl-btn" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
