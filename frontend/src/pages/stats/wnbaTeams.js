// WNBA teams for the /wnba/stats area (2026-10-19): stats.wnba.com team ids (logos from cdn.wnba.com) and team colors.
// The colors are close approximations of each team's brand; primary first.
export const WNBA_TEAMS = {
  ATL: { id: 1611661330, name: "Atlanta Dream", primary: "#E31837", secondary: "#5091CD" },
  CHI: { id: 1611661329, name: "Chicago Sky", primary: "#418FDE", secondary: "#FFCD00" },
  CON: { id: 1611661323, name: "Connecticut Sun", primary: "#F05023", secondary: "#0A2240" },
  DAL: { id: 1611661321, name: "Dallas Wings", primary: "#C4D600", secondary: "#002B5C" },
  GSV: { id: 1611661331, name: "Golden State Valkyries", primary: "#7B57A6", secondary: "#000000" },
  IND: { id: 1611661325, name: "Indiana Fever", primary: "#E03A3E", secondary: "#FFD520" },
  LAS: { id: 1611661320, name: "Los Angeles Sparks", primary: "#702F8A", secondary: "#FDB927" },
  LVA: { id: 1611661319, name: "Las Vegas Aces", primary: "#BA0C2F", secondary: "#A7A8AA" },
  MIN: { id: 1611661324, name: "Minnesota Lynx", primary: "#266092", secondary: "#79BC43" },
  NYL: { id: 1611661313, name: "New York Liberty", primary: "#6ECEB2", secondary: "#000000" },
  PDX: { id: 1611661327, name: "Portland Fire", primary: "#E03C31", secondary: "#000000" },
  PHX: { id: 1611661317, name: "Phoenix Mercury", primary: "#CB6015", secondary: "#3C286E" },
  SEA: { id: 1611661328, name: "Seattle Storm", primary: "#2C5234", secondary: "#FBE122" },
  TOR: { id: 1611661332, name: "Toronto Tempo", primary: "#A6192E", secondary: "#000000" },
  WAS: { id: 1611661322, name: "Washington Mystics", primary: "#C8102E", secondary: "#002B5C" },
};
export const wnbaLogoUrl = tricode => (WNBA_TEAMS[tricode] ? `https://cdn.wnba.com/logos/wnba/${WNBA_TEAMS[tricode].id}/primary/D/logo.svg` : null);
// which league's area this page is in (read at render; the route decides)
export const inWnba = () => window.location.pathname.startsWith("/wnba/");
