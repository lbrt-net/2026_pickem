// WNBA teams for the /wnba/stats area (2026-10-19): stats.wnba.com team ids (logos from cdn.wnba.com) and team colors.
// Colors: each franchise's current official set, primary first. Source: TruColor, "WNBA official colors 1997 through
// present", https://www.trucolor.net/portfolio/womens-national-basketball-association-official-colors-1997-through-present/
export const WNBA_TEAMS = {
  ATL: { id: 1611661330, name: "Atlanta Dream", primary: "#C8102E", secondary: "#418FDE" },          // red, light blue
  CHI: { id: 1611661329, name: "Chicago Sky", primary: "#418FDE", secondary: "#FFCD00" },            // sky blue, radiant yellow
  CON: { id: 1611661323, name: "Connecticut Sun", primary: "#FC4C02", secondary: "#0C2340" },        // orange, navy
  DAL: { id: 1611661321, name: "Dallas Wings", primary: "#C4D600", secondary: "#0C2340" },           // lime green, navy
  GSV: { id: 1611661331, name: "Golden State Valkyries", primary: "#010101", secondary: "#AD96DC" }, // black, Valkyrie violet
  IND: { id: 1611661325, name: "Indiana Fever", primary: "#041E42", secondary: "#C8102E" },          // navy, red
  LAS: { id: 1611661320, name: "Los Angeles Sparks", primary: "#702F8A", secondary: "#FFC72C" },     // purple, gold
  LVA: { id: 1611661319, name: "Las Vegas Aces", primary: "#010101", secondary: "#A7A8A9" },         // black, silver
  MIN: { id: 1611661324, name: "Minnesota Lynx", primary: "#236192", secondary: "#78BE21" },         // lake blue, aurora green
  NYL: { id: 1611661313, name: "New York Liberty", primary: "#010101", secondary: "#6ECEB2" },       // black, seafoam green
  PDX: { id: 1611661327, name: "Portland Fire", primary: "#E93CAC", secondary: "#C8102E" },          // pink, red
  PHX: { id: 1611661317, name: "Phoenix Mercury", primary: "#582C83", secondary: "#FC4C02" },        // purple, orange (2026)
  SEA: { id: 1611661328, name: "Seattle Storm", primary: "#2C5234", secondary: "#FBE122" },          // storm green, lightning yellow
  TOR: { id: 1611661332, name: "Toronto Tempo", primary: "#612C51", secondary: "#B8CCEA" },          // Bordeaux, hydrogen blue
  WAS: { id: 1611661322, name: "Washington Mystics", primary: "#C8102E", secondary: "#0C2340" },     // red, navy
};
export const wnbaLogoUrl = tricode => (WNBA_TEAMS[tricode] ? `https://cdn.wnba.com/logos/wnba/${WNBA_TEAMS[tricode].id}/primary/D/logo.svg` : null);
// which league's area this page is in (read at render; the route decides)
export const inWnba = () => window.location.pathname.startsWith("/wnba/");
