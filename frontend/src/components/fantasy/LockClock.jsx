import { useEffect, useState } from "react";
import LedClock from "./LedClock";
import "./LockClock.css";

export function LockIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" aria-label="Locked this week">
      <rect x="2.2" y="5.2" width="7.6" height="5.6" rx="1" stroke="currentColor" strokeWidth="1.4" fill="none" />
      <path d="M4 5.2V3.8a2 2 0 0 1 4 0v1.4" stroke="currentColor" strokeWidth="1.4" fill="none" />
    </svg>
  );
}

export function UnlockIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" aria-label="Not locked yet">
      <rect x="2.2" y="5.2" width="7.6" height="5.6" rx="1" stroke="currentColor" strokeWidth="1.4" fill="none" />
      <path d="M4 5.2V3.8a2 2 0 0 1 3.9-.6" stroke="currentColor" strokeWidth="1.4" fill="none" strokeLinecap="round" />
    </svg>
  );
}

const UNIT = { D: "day", H: "hour", M: "minute", S: "second" };

// "Week N rosters start locking in 2 days" (Roster, Home): counts to 5 min before the week's first game
// of any NBA team (each player then locks with his own team's first game); once that has passed, it
// counts to week N+1's. `lock` / `next` = the week view's week_lock / next_lock. One unit, spelled out;
// the replay (whole days) counts days.
export default function LockClock({ lock, next, asOf }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t); }, []);
  const left = l => (l.at ? Date.parse(l.at) - now : Date.parse(`${l.date}T00:00:00`) - Date.parse(`${asOf}T00:00:00`));
  const target = lock && left(lock) > 0 ? lock : next && left(next) > 0 ? next : null;
  if (!target) return null;
  const s = Math.floor(left(target) / 1000);
  const [v, u] = s >= 86400 ? [Math.floor(s / 86400), "D"] : s >= 3600 ? [Math.floor(s / 3600), "H"] : s >= 60 ? [Math.floor(s / 60), "M"] : [s, "S"];
  const unit = `${UNIT[u]}${v === 1 ? "" : "s"}`;
  return (
    <span className="lockclock" title={target.at ? `First lock ${new Date(target.at).toLocaleString()}` : `First game ${target.date}`}>
      <span className="lbl">Week {target.week} rosters start locking in</span>
      <LedClock text={String(v)} step={1.7} r={0.75} label={`${v} ${unit}`} />
      <span className="unit">{unit}</span>
    </span>
  );
}
