// NBA teams: city / nickname split and official current colors (primary, secondary), from
// trucolor.net's NBA franchise records (2025-26 era), pulled 2026-10-03. Used for the NBA team
// abbreviation squares (primary fill, secondary stripe). Keyed by the tricode the data layer uses.
export const NBA_TEAMS = {
  ATL: { city: "Atlanta", nickname: "Hawks", primary: "#c8102e", secondary: "#ffc72c" },
  BOS: { city: "Boston", nickname: "Celtics", primary: "#007a33", secondary: "#ffffff" },
  BKN: { city: "Brooklyn", nickname: "Nets", primary: "#010101", secondary: "#ffffff" },
  CHA: { city: "Charlotte", nickname: "Hornets", primary: "#00778b", secondary: "#211747" },
  CHI: { city: "Chicago", nickname: "Bulls", primary: "#ba0c2f", secondary: "#010101" },
  CLE: { city: "Cleveland", nickname: "Cavaliers", primary: "#6f263d", secondary: "#b9975b" },
  DAL: { city: "Dallas", nickname: "Mavericks", primary: "#0050b5", secondary: "#0c2340" },
  DEN: { city: "Denver", nickname: "Nuggets", primary: "#0c2340", secondary: "#862633" },
  DET: { city: "Detroit", nickname: "Pistons", primary: "#1d4289", secondary: "#c8102e" },
  GSW: { city: "Golden State", nickname: "Warriors", primary: "#1d4289", secondary: "#ffc72c" },
  HOU: { city: "Houston", nickname: "Rockets", primary: "#c8102e", secondary: "#ffcd00" },
  IND: { city: "Indiana", nickname: "Pacers", primary: "#0c2340", secondary: "#ffcd00" },
  LAC: { city: "LA", nickname: "Clippers", primary: "#0c2340", secondary: "#c8102e" },
  LAL: { city: "Los Angeles", nickname: "Lakers", primary: "#330072", secondary: "#ffc72c" },
  MEM: { city: "Memphis", nickname: "Grizzlies", primary: "#0c2340", secondary: "#7d9cc0" },
  MIA: { city: "Miami", nickname: "Heat", primary: "#010101", secondary: "#862633" },
  MIL: { city: "Milwaukee", nickname: "Bucks", primary: "#2c5234", secondary: "#ddcba4" },
  MIN: { city: "Minnesota", nickname: "Timberwolves", primary: "#1d4289", secondary: "#009a44" },
  NOP: { city: "New Orleans", nickname: "Pelicans", primary: "#0c2340", secondary: "#b9975b" },
  NYK: { city: "New York", nickname: "Knicks", primary: "#1d4289", secondary: "#ff8200" },
  OKC: { city: "Oklahoma City", nickname: "Thunder", primary: "#0072ce", secondary: "#041e42" },
  ORL: { city: "Orlando", nickname: "Magic", primary: "#0050b5", secondary: "#010101" },
  PHI: { city: "Philadelphia", nickname: "76ers", primary: "#1d4289", secondary: "#c8102e" },
  PHX: { city: "Phoenix", nickname: "Suns", primary: "#211747", secondary: "#a9431e" },
  POR: { city: "Portland", nickname: "Trail Blazers", primary: "#010101", secondary: "#c8102e" },
  SAC: { city: "Sacramento", nickname: "Kings", primary: "#010101", secondary: "#582c83" },
  SAS: { city: "San Antonio", nickname: "Spurs", primary: "#010101", secondary: "#9ea2a2" },
  TOR: { city: "Toronto", nickname: "Raptors", primary: "#ba0c2f", secondary: "#010101" },
  UTA: { city: "Utah", nickname: "Jazz", primary: "#330072", secondary: "#010101" },
  WAS: { city: "Washington", nickname: "Wizards", primary: "#c8102e", secondary: "#0c2340" },
};

// Two lines: first / last for players (split at the first space until the NBA's own first/last
// names are stored — ROADMAP), city / nickname for NBA teams.
export function nameLines(entry) {
  if (entry?.kind === "nba_team") {
    const t = NBA_TEAMS[entry.id];
    return t ? [t.city, t.nickname] : ["", entry.name];
  }
  const name = entry?.name || "";
  const i = name.indexOf(" ");
  return i === -1 ? ["", name] : [name.slice(0, i), name.slice(i + 1)];
}
