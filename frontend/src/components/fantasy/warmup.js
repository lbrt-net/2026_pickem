import { API } from "../../utils/helpers";
import { API_BASE } from "./data";
import { bundleFirst, load, prefetch, seed } from "./cache";

// Once per visit, when the browser is idle after the first page (2026-10-21): load what the site keeps needing into
// the shared store (cache.js) so the next page opens at once — the league basics, this week's matchups (all teams'
// weeks), the Players lists (~60 KB) and every rostered pop-up's history in one request (GET /players/histories,
// 2026-10-25 — it used to be ~200 requests per visitor, which swamped the server). Player pages load when opened.
const done = new Set();
const idle = f => (window.requestIdleCallback ? window.requestIdleCallback(f, { timeout: 3000 }) : setTimeout(f, 1500));

export function warmUp(scenario) {
  if (!scenario || done.has(scenario)) return;
  done.add(scenario);
  idle(() => {
    const u = n => `${API}${API_BASE}/${n}${n.includes("?") ? "&" : "?"}scenario=${scenario}`;
    for (const n of ["teams", "results", "league/members", "league/settings", "scoring", "nba-teams", "players",
      "players/board?view=proj", "players/actual?window=season"]) prefetch(u(n));
    load(u("results")).then(r => {
      const week = r?.current_week || r?.home_week;
      if (week) prefetch(`${API}${API_BASE}/week/all?${new URLSearchParams({ scenario, week })}`);
    });
    // every rostered player's / team's pop-up history in ONE request (built once on the server), seeded into the store
    load(u("players/histories")).then(all => {
      for (const [id, h] of Object.entries(all || {})) seed(`${API}${API_BASE}/players/${encodeURIComponent(id)}/history?scenario=${scenario}`, h);
    });
  });
}

// The first page of a visit asks for everything it needs in one request (GET /bundle, 2026-10-22) — started before the
// page draws, so the page's own requests find their data in the store instead of making ~10 trips.
export function startBundle() {
  const path = window.location.pathname;
  const m = /^\/fantasy\/(2026_27|2025_26)(\/[^?#]*)?/.exec(path);
  if (!m) return;
  let scenario = "live";
  if (m[1] === "2025_26") scenario = "replay";
  else {
    try { const s = localStorage.getItem("fantasyScenario"); if (s === "test_pre" || s === "test_post") scenario = s; } catch { /* storage unavailable */ }
  }
  const rest = (m[2] || "").replace(/\/$/, "");
  const page = rest === "" ? "home" : rest === "/matchup" ? "matchup" : rest.startsWith("/team") ? "roster" : rest === "/players" ? "players" : "basics";
  const week = new URLSearchParams(window.location.search).get("week");
  const q = new URLSearchParams({ page, scenario, ...(week ? { week } : {}) });
  bundleFirst(fetch(`${API}${API_BASE}/bundle?${q}`, { credentials: "include" })
    .then(r => (r.ok ? r.json() : null))
    .then(b => { for (const [k, v] of Object.entries(b?.items || {})) seed(`${API}${API_BASE}/${k}`, v); }));
}
