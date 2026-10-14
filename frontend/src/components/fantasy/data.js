import { useEffect, useState } from "react";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";

export const SEASON = "2026_27";
// Server routes for both leagues; ?scenario= picks which one.
export const API_BASE = `/fantasy/${SEASON}`;
// The 2025-26 test league reuses every 2026-27 page under its own URL (/fantasy/2025_26/...);
// the URL decides the league. (2027-28 is a separate placeholder.)
export const TEST_SEASON = "2025_26";
export const seasonOf = (path = window.location.pathname) => (path.startsWith(`/fantasy/${TEST_SEASON}`) ? TEST_SEASON : SEASON);
// Page links for the league being viewed.
export const base = () => `/fantasy/${seasonOf()}`;
// Placeholders until league rules are set.
export const REGULAR_SEASON_WEEKS = 19;
export const PLAYOFF_TEAMS = 6;
// Fallback roster layout; the real one is per league (each team from GET /teams has `slot_list`).
export const SLOT_ORDER = ["G", "F", "C", "TEAM"];

export const teamPath = ownerId => `${base()}/team/${ownerId}`;
export const entityPath = id => `${base()}/players/${id}`;

// Fetch one /fantasy/2026_27/<name> endpoint for the league being viewed.
// Returns undefined while loading, null if the request failed.
export function useFantasyApi(name) {
  const [scenario] = useFantasyScenario();
  const key = `${name}?scenario=${scenario}`;
  const [state, setState] = useState({ key: null, data: undefined });

  useEffect(() => {
    let current = true;
    fetch(`${API}${API_BASE}/${key}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null))
      .catch(() => null)
      .then(data => { if (current) setState({ key, data }); });
    return () => { current = false; };
  }, [key]);

  return state.key === key ? state.data : undefined;
}

// Roster entries in display order (G, G, F, F, ...), with empty slots as null.
export function rosterBySlot(roster, order = SLOT_ORDER) {
  const left = [...roster];
  return order.map(slot => {
    const i = left.findIndex(e => e.slot === slot);
    return { slot, entry: i === -1 ? null : left.splice(i, 1)[0] };
  });
}

// Round-robin (circle method): every team plays every other team once per cycle.
export function weekPairings(teams, week) {
  const ids = [...teams].sort((a, b) => a.name.localeCompare(b.name));
  if (ids.length % 2) ids.push(null);
  const n = ids.length;
  if (n < 2) return [];
  const rest = ids.slice(1);
  const r = (week - 1) % (n - 1);
  const rot = [ids[0], ...rest.map((_, i) => rest[(i + r) % rest.length])];
  const pairs = [];
  for (let i = 0; i < n / 2; i++) {
    const a = rot[i], b = rot[n - 1 - i];
    if (a && b) pairs.push([a, b]);
  }
  return pairs;
}

// Weekly score is projected from per-game averages until real box scores exist,
// so a team scores the same every week; only the opponent changes.
export const weekScore = team => team.total_fantasy_points;

// Records, points for/against through a given week, sorted into standings order.
// `results` is each team's week-by-week "W"/"L"/"T", oldest first.
export function standingsThrough(teams, week) {
  const rows = new Map(teams.map(t => [t.id, { team: t, w: 0, l: 0, t: 0, pf: 0, pa: 0, results: [] }]));
  for (let wk = 1; wk <= week; wk++) {
    for (const [a, b] of weekPairings(teams, wk)) {
      const ra = rows.get(a.id), rb = rows.get(b.id);
      const sa = weekScore(a), sb = weekScore(b);
      ra.pf += sa; ra.pa += sb; rb.pf += sb; rb.pa += sa;
      if (sa > sb) { ra.w++; rb.l++; ra.results.push("W"); rb.results.push("L"); }
      else if (sb > sa) { rb.w++; ra.l++; rb.results.push("W"); ra.results.push("L"); }
      else { ra.t++; rb.t++; ra.results.push("T"); rb.results.push("T"); }
    }
  }
  return [...rows.values()]
    .map(r => ({ ...r, pf: Math.round(r.pf * 10) / 10, pa: Math.round(r.pa * 10) / 10 }))
    .sort((x, y) => (y.w + y.t / 2) - (x.w + x.t / 2) || y.pf - x.pf);
}

export const record = r => (r.t ? `${r.w}-${r.l}-${r.t}` : `${r.w}-${r.l}`);
