import { useLocation } from "react-router-dom";

// NBA and WNBA stats are separate areas (2026-10-19): /stats/… is the NBA, /wnba/stats/… the WNBA, each with its own
// directory page. The pages are shared; the area picks the data. Stats never link into fantasy.
export function useLeague() {
  return useLocation().pathname.startsWith("/wnba/") ? "wnba" : "nba";
}
export const statsRoot = league => (league === "wnba" ? "/wnba/stats" : "/stats");
// the data request's league (the API stays under /nba/stats/…)
export const leagueQ = league => (league === "wnba" ? "?league=wnba" : "");

// "2025-26", or for a season in progress / the WNBA: "WNBA 2026 · 49 games so far"; "not built yet" when the page has no data
export function seasonLabel(meta, league) {
  if (!meta) return "";
  if (meta.empty) return league === "wnba" ? "WNBA · not built yet" : "not built yet";
  const s = `${league === "wnba" ? "WNBA " : ""}${meta.season || ""}`;
  return meta.games ? `${s} · ${meta.games.toLocaleString()} games so far` : s;
}
