import { useEffect, useState } from "react";
import { API } from "../../utils/helpers";

// Current injuries (GET /nba/injuries: Out / Day-To-Day, injury, return date). Present only — no history.
// Loaded once per page load and shared: { player_id: row }.
let cache = null;
let pending = null;
function load() {
  if (!pending) {
    pending = fetch(`${API}/nba/injuries`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : []))
      .catch(() => [])
      .then(rows => { cache = Object.fromEntries((rows || []).map(r => [String(r.player_id), r])); return cache; });
  }
  return pending;
}

export function useInjuries() {
  const [map, setMap] = useState(cache);
  useEffect(() => { if (!cache) load().then(setMap); }, []);
  return map || {};
}

// Out = red, Day-To-Day = yellow; anything else shows nothing.
export const injuryKind = inj => (!inj ? null : inj.status === "Out" || inj.status === "Out For Season" ? "out" : inj.status === "Day-To-Day" ? "dtd" : null);
export const injuryWord = inj => (injuryKind(inj) === "out" ? "Out" : injuryKind(inj) === "dtd" ? "Day-to-day" : "");
export const backText = inj => (inj?.return_date
  ? new Date(`${inj.return_date}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })
  : null);


// Health filter for player lists (Players, draft list): All / Healthy / out or day-to-day (red + yellow dots) / out only
// (red). Labels are the dots themselves.
export const HEALTH_OPTS = [["all", "All"], ["healthy", "Healthy"],
  ["hurt", <span className="hf-dots" title="Out or day-to-day"><i className="out" /><i className="dtd" /></span>],
  ["out", <span className="hf-dots" title="Out"><i className="out" /></span>]];
export const healthMatch = (health, inj) => {
  const k = injuryKind(inj);
  return health === "all" || (health === "healthy" ? !k : health === "hurt" ? !!k : k === "out");
};
