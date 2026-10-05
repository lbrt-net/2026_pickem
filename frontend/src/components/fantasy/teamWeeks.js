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

// Win probability from the projected totals (a 20-point projected lead ≈ 73%); a final week is 1 / 0 / 0.5.
export const winProb = (a, b, final) => (final ? (a.score > b.score ? 1 : b.score > a.score ? 0 : 0.5) : 1 / (1 + Math.exp(-(a.proj - b.proj) / 20)));
