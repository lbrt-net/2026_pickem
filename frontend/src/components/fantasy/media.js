// NBA imagery from the NBA's CDN: player headshots (transparent cutouts, by NBA person id — the
// same ids our player pool uses) and team logos (dark-background version, by NBA team id).
// Fine for a private league; check licensing before going public.
export const NBA_TEAM_IDS = {
  ATL: 1610612737, BOS: 1610612738, CLE: 1610612739, NOP: 1610612740, CHI: 1610612741, DAL: 1610612742,
  DEN: 1610612743, GSW: 1610612744, HOU: 1610612745, LAC: 1610612746, LAL: 1610612747, MIA: 1610612748,
  MIL: 1610612749, MIN: 1610612750, BKN: 1610612751, NYK: 1610612752, ORL: 1610612753, IND: 1610612754,
  PHI: 1610612755, PHX: 1610612756, POR: 1610612757, SAC: 1610612758, SAS: 1610612759, OKC: 1610612760,
  TOR: 1610612761, UTA: 1610612762, MEM: 1610612763, WAS: 1610612764, DET: 1610612765, CHA: 1610612766,
};
export const headshotUrl = playerId => `https://cdn.nba.com/headshots/nba/latest/260x190/${playerId}.png`;
export const logoUrl = tricode => (NBA_TEAM_IDS[tricode] ? `https://cdn.nba.com/logos/nba/${NBA_TEAM_IDS[tricode]}/primary/D/logo.svg` : null);
