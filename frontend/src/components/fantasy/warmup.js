import { API } from "../../utils/helpers";
import { API_BASE } from "./data";
import { load, prefetch } from "./cache";

// Once per visit, when the browser is idle after the first page (2026-10-21): load what the site keeps needing into
// the shared store (cache.js) so the next page opens at once — the league basics, this week's matchups (all teams'
// weeks), the Players lists (~60 KB) and every rostered player's / team's pop-up data (~1.4 KB each, 4 at a time so
// the server isn't swamped). Player pages are not preloaded (~17 KB each — loaded when opened).
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
    load(u("teams")).then(teams => {
      const ids = (teams || []).flatMap(t => (t.roster || []).map(e => e.id));
      let i = 0;
      const next = () => {
        if (i >= ids.length) return;
        const id = ids[i++];
        load(`${API}${API_BASE}/players/${encodeURIComponent(id)}/history?scenario=${scenario}`).then(next);
      };
      for (let k = 0; k < 4; k++) next();
    });
  });
}
