import { useEffect, useMemo } from "react";
import { load, useCached } from "./cache";
import { API } from "../../utils/helpers";
import { API_BASE } from "./data";

// Every listed team's week view, keyed by team id — one request for all of them (GET /week/all: built in parallel and
// kept warm on the server), shared by Home / Matchup through the visit's store (cache.js). undefined while loading.
export const teamWeeksUrl = (week, scenario) => `${API}${API_BASE}/week/all?${new URLSearchParams({ scenario, week })}`;
// fetch every team's week again now (a live game's 30-second refresh)
export const refreshTeamWeeks = (week, scenario) => { if (week) load(teamWeeksUrl(week, scenario), true); };

export function useTeamWeeks(teamIds, week, scenario) {
  const ids = teamIds.join(",");
  const all = useCached(ids && week ? teamWeeksUrl(week, scenario) : null);
  return useMemo(() => {
    if (all === undefined) return undefined;
    const want = new Set(ids.split(","));
    return Object.fromEntries(Object.entries(all || {}).filter(([id]) => want.has(id)));
  }, [all, ids]);
}

// Win probability for every matchup in a week (GET /week/winprob — the rest of the week played out thousands of
// times; back-tested in WINPROB.md). Returns probOf(teamA, teamB) → A's chance, or undefined while loading.
export function useWinProbs(week, scenario, tick = 0) {
  // through the visit's store (cache.js; the page bundle can pre-fill it); tick: bump it to refetch (Matchup does every
  // 30 s while a game is live) — the last numbers stay up while it loads
  const url = week ? `${API}${API_BASE}/week/winprob?${new URLSearchParams({ scenario, week })}` : null;
  const data = useCached(url);
  useEffect(() => { if (url && tick) load(url, true); }, [url, tick]);
  const list = data?.matchups || [];
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
