import { useCallback, useEffect, useState } from "react";
import { API } from "../utils/helpers";
import "./PhoneLogin.css";

// Account menu → Devices: every device you're logged in on (GET /auth/sessions) — which device, how you logged in,
// last active — with Log out on each and Log out everywhere else. Logging this device out sends you to the home page.
const ago = iso => {
  const m = Math.round((Date.now() - Date.parse(iso)) / 60000);
  if (m < 5) return "active now";
  if (m < 60) return `active ${m} min ago`;
  if (m < 60 * 24) return `active ${Math.round(m / 60)} h ago`;
  return `active ${Math.round(m / 1440)} d ago`;
};
const day = iso => new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
const HOW = { discord: "Discord", phone: "phone code" };

export default function Devices({ onClose }) {
  const [list, setList] = useState(null);
  const [error, setError] = useState(null);
  const call = useCallback(async (path, method = "GET") => {
    setError(null);
    try {
      const r = await fetch(`${API}${path}`, { method, credentials: "include" });
      if (!r.ok) throw new Error();
      setList(await r.json());
    } catch {
      setError("Couldn't load your devices.");
    }
  }, []);
  useEffect(() => { call("/auth/sessions"); }, [call]);
  useEffect(() => {
    const esc = e => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onClose]);

  const end = d => {
    if (d.current) window.location.href = `${API}/auth/logout`;
    else call(`/auth/sessions/${encodeURIComponent(d.id)}/end`, "POST");
  };
  const others = (list || []).filter(d => !d.current).length;
  return (
    <div className="pl-modal" role="dialog" aria-modal="true" aria-label="Devices" onClick={e => { e.stopPropagation(); if (e.target === e.currentTarget) onClose(); }}>
      <div className="pl-box dv-box">
        <b className="pl-h">Devices</b>
        {error && <p className="pl-p">{error}</p>}
        <div className="dv-list">
          {(list || []).map(d => (
            <div key={d.id} className="dv-row">
              <div className="dv-who">
                <b>{d.device}{d.current && <span className="dv-this">This device</span>}</b>
                <span>{HOW[d.method] || d.method} · {day(d.created_at)} · {ago(d.last_seen)}</span>
              </div>
              <button type="button" className="pl-btn out" onClick={() => end(d)}>Log out</button>
            </div>
          ))}
        </div>
        <div className="pl-f">
          {others > 0 && <button type="button" className="pl-btn primary" onClick={() => call("/auth/sessions/end-others", "POST")}>Log out everywhere else</button>}
          <button type="button" className="pl-btn" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
