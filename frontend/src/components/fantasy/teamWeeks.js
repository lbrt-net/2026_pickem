import { useEffect, useState } from "react";
import { API } from "../../utils/helpers";
import { API_BASE } from "./data";

// Every listed team's week view (GET /team/:id/week), keyed by team id. undefined while loading.
export function useTeamWeeks(teamIds, week, scenario) {
  const ids = teamIds.join(",");
  const key = ids && week ? `${ids}|${week}|${scenario}` : null;
  const [state, setState] = useState({ key: null, data: undefined });
  useEffect(() => {
    if (!key) return undefined;
    let live = true;
    const q = new URLSearchParams({ scenario, week });
    Promise.all(ids.split(",").map(id => fetch(`${API}${API_BASE}/team/${encodeURIComponent(id)}/week?${q}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null)))
      .then(list => { if (live) setState({ key, data: Object.fromEntries(list.filter(Boolean).map(d => [d.team_id, d])) }); });
    return () => { live = false; };
  }, [key, ids, week, scenario]);
  return state.key === key ? state.data : undefined;
}

// Win probability for every matchup in a week (GET /week/winprob — the rest of the week played out thousands of
// times; back-tested in WINPROB.md). Returns probOf(teamA, teamB) → A's chance, or undefined while loading.
export function useWinProbs(week, scenario) {
  const key = week ? `${week}|${scenario}` : null;
  const [state, setState] = useState({ key: null, data: null });
  useEffect(() => {
    if (!key) return undefined;
    let live = true;
    fetch(`${API}${API_BASE}/week/winprob?${new URLSearchParams({ scenario, week })}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null)
      .then(d => { if (live) setState({ key, data: d }); });
    return () => { live = false; };
  }, [key, week, scenario]);
  const list = state.key === key ? state.data?.matchups || [] : [];
  return (a, b) => {
    const m = list.find(x => (x.a === a && x.b === b) || (x.a === b && x.b === a));
    return m ? (m.a === a ? m.p : 1 - m.p) : undefined;
  };
}

// Fallback while the real number loads: from the projected totals; a final week is 1 / 0 / 0.5.
export const winProb = (a, b, final) => (final ? (a.score > b.score ? 1 : b.score > a.score ? 0 : 0.5) : 1 / (1 + Math.exp(-(a.proj - b.proj) / 20)));

// Win % as text, so the two sides always pair up: exact 0 / 100 → "0%" / "100%"; above 0 but under 1% → "<1%" (the
// other side ">99%"); otherwise rounded to a whole % with the two sides adding to exactly 100 (the side at or over 50%
// rounds, the other side is the rest — so a 70.5 / 29.5 tie can't become 71 / 30). Used for win % and 1+ Game %.
export function winText(p) {
  if (p == null) return "";
  if (p <= 0) return "0%";
  if (p >= 1) return "100%";
  if (p < 0.01) return "<1%";
  if (p > 0.99) return ">99%";
  const k = p >= 0.5 ? Math.round(p * 100 + 1e-9) : 100 - Math.round((1 - p) * 100 + 1e-9);
  return `${Math.min(99, Math.max(1, k))}%`;
}
