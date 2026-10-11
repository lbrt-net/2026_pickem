import { useCallback, useEffect, useState } from "react";
import { API } from "../utils/helpers";
import "./Account.css";

// Account page → Devices: every device you're logged in on (GET /auth/sessions) — which device, how you logged in,
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

export default function Devices() {
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
  const end = d => {
    if (d.current) window.location.href = `${API}/auth/logout`;
    else call(`/auth/sessions/${encodeURIComponent(d.id)}/end`, "POST");
  };
  const others = (list || []).filter(d => !d.current).length;
  return (
    <section className="ac-panel" aria-label="Devices">
      <div className="ac-head">Devices</div>
      {error && <p className="ac-p">{error}</p>}
      <div className="dv-list">
        {(list || []).map(d => (
          <div key={d.id} className="dv-row">
            <div className="dv-who">
              <b>{d.device}{d.current && <span className="dv-this">This device</span>}</b>
              <span>{HOW[d.method] || d.method} · {day(d.created_at)} · {ago(d.last_seen)}</span>
            </div>
            <button type="button" className="ac-btn out" onClick={() => end(d)}>Log out</button>
          </div>
        ))}
      </div>
      {others > 0 && <div className="ac-foot"><button type="button" className="ac-btn primary" onClick={() => call("/auth/sessions/end-others", "POST")}>Log out everywhere else</button></div>}
    </section>
  );
}
