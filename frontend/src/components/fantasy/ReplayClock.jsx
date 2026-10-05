import { useEffect, useState } from "react";
import useCurrentUser from "../../hooks/useCurrentUser";
import { API } from "../../utils/helpers";
import { API_BASE, TEST_SEASON, seasonOf } from "./data";
import "./ReplayClock.css";

// Test league only, admins only: the replay's "today". Moving it reloads the page so every
// view re-reads the league as of the new date (POST /admin/league/replay/clock).
export default function ReplayClock() {
  const user = useCurrentUser();
  const show = seasonOf() === TEST_SEASON && user?.isAdmin;
  const [info, setInfo] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!show) return;
    fetch(`${API}${API_BASE}/league/settings?scenario=replay`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null))
      .then(d => d && setInfo({ date: d.as_of, min: d.weeks[0]?.start, max: d.weeks.at(-1)?.end }))
      .catch(() => {});
  }, [show]);

  if (!show || !info) return null;

  function move(body) {
    setBusy(true);
    fetch(`${API}${API_BASE}/admin/league/replay/clock`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    })
      .then(r => (r.ok ? window.location.reload() : setBusy(false)))
      .catch(() => setBusy(false));
  }

  return (
    <div className="rc">
      <span className="rc-label">Test league date</span>
      <button className="rc-btn" disabled={busy} onClick={() => move({ days: -1 })} aria-label="Back one day">‹</button>
      <input type="date" className="rc-date" value={info.date} min={info.min} max={info.max} disabled={busy}
        onChange={e => e.target.value && move({ date: e.target.value })} />
      <button className="rc-btn" disabled={busy} onClick={() => move({ days: 1 })} aria-label="Forward one day">›</button>
      <button className="rc-btn" disabled={busy} onClick={() => move({ weeks: 1 })}>+1 week</button>
    </div>
  );
}
