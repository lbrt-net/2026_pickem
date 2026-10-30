import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import StatsNav from "./StatsNav";
import { useLeague, statsRoot, leagueQ, seasonLabel } from "./statsLeague";
import "./Rebounding.css";
import "./StatsIndex.css";

// /stats/nba and /stats/wnba — the directory of the stats pages. Public NBA analysis from the play-by-play; nothing here links into fantasy.
// same order as the stats nav (StatsNav.jsx)
const PAGES = [
  { to: "/stats/games", title: "Games", route: "standings", nbaOnly: true,
    what: "Today's games: who should win and by how much, from the same player ratings and minutes as the standings, with every earlier day's calls against the final scores." },
  { to: "/stats/standings", title: "Standings", route: "standings", nbaOnly: true,
    what: "The season so far and where it's headed: games back through any date on the slider, and the projected finish from player ratings, projected minutes and 10,000 simulations." },
  { to: "/stats/shooting", title: "Shooting", route: "shot-value",
    what: "Points over what the league scores from the same shots in the same situations, per 75 possessions. The 300 biggest shot-takers, expected and actual points per shot, shot diet, and a shot chart for every row." },
  { to: "/stats/rebounding", title: "Rebounding", route: "rebounding",
    what: "Every live miss a player was on the floor for: his share and his team's rate, expected from the shot alone, expected from the other nine plus a man of his size, and actual. Defense and offense, with what he takes off teammates." },
  { to: "/stats/playmaking", title: "Playmaking", route: "playmaking",
    what: "Box Creation, Ben Taylor's box-score estimate of the open shots a player creates for teammates per 100 possessions, with the formula's pieces for every player." },
  // no route: its data is static files, so the card doesn't fetch just to show the season
  { to: "/stats/gravity", title: "Gravity", route: null, season: "2025-26",
    what: "Every rotation player on vs off: where his teammates shoot from (offense) or where opponents shoot from against his team (defense), and how well they make them, in points per 75 of their shots. A 3D court of the shift for every row." },
  { to: "/stats/lineups", title: "Lineups", route: null, season: null,
    what: "Rotation patterns: every player on the game clock, how often he was on the floor at each moment — narrowed to the games when someone played, played his normal minutes, or missed, over any date range." },
];

export default function StatsIndex() {
  // /stats/nba and /stats/wnba: the same directory, each on its own league's data. Each card shows the season
  // its data is on (the nightly refresh moves them to 2026-27 as the season starts)
  const league = useLeague(), root = statsRoot(league);
  const [meta, setMeta] = useState({});
  useEffect(() => {  // every page's meta in one small request (GET /nba/stats/meta), not each page's whole dataset
    fetch(`${API}/nba/stats/meta${leagueQ(league)}`, { credentials: "include" }).then(r => r.json())
      .then(d => setMeta(m => ({ ...m, ...Object.fromEntries(Object.entries(d || {}).map(([k, v]) => [`${league}:${k}`, v || {}])) }))).catch(() => {});
  }, [league]);
  return (
    <div className="site-ui stats-ui" style={{ minHeight: "100vh" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1100, boxSizing: "border-box", minWidth: 0 }}>
        <StatsNav />
        <div className="rb-head">
          <h1 className="rb-title">{league === "wnba" ? "WNBA Stats" : "Stats"}</h1>
          <span className="rb-meta">from the play-by-play</span>
        </div>
        <div className="si-grid">
          {PAGES.filter(p => !(p.nbaOnly && league === "wnba")).map(p => (
            <Link key={p.to} to={p.to.replace(/^\/stats/, root)} className="si-card">
              <div className="si-top"><b>{p.title}</b><span>{p.route ? seasonLabel(meta[`${league}:${p.route}`], league) : (league === "wnba" ? "WNBA 2026" : p.season || "")}{meta[`${league}:${p.route}`]?.built ? ` · built ${meta[`${league}:${p.route}`].built}` : ""}</span></div>
              <p>{p.what}</p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
