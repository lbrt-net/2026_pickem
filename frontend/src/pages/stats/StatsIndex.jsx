import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import StatsNav from "./StatsNav";
import { useLeague, statsRoot, leagueQ, seasonLabel } from "./statsLeague";
import "./Rebounding.css";
import "./StatsIndex.css";

// /stats — the directory of the stats pages. Public NBA analysis from the play-by-play; nothing here links into fantasy.
const PAGES = [
  { to: "/stats/shooting", title: "Shooting", route: "shot-value",
    what: "Points over what the league scores from the same shots in the same situations, per 75 possessions. The 300 biggest shot-takers, expected and actual points per shot, shot diet, and a shot chart for every row." },
  { to: "/stats/rebounding", title: "Rebounding", route: "rebounding",
    what: "Every live miss a player was on the floor for: his share and his team's rate, expected from the shot alone, expected from the other nine plus a man of his size, and actual. Defense and offense, with what he takes off teammates." },
  { to: "/stats/playmaking", title: "Playmaking", route: "playmaking",
    what: "Box Creation, Ben Taylor's box-score estimate of the open shots a player creates for teammates per 100 possessions, with the formula's pieces for every player." },
  // no route: its data is static files, so the card doesn't fetch just to show the season
  { to: "/stats/gravity", title: "Gravity", route: null, season: "2025-26",
    what: "Every rotation player on vs off: where his teammates shoot from (offense) or where opponents shoot from against his team (defense), and how well they make them, in points per 75 of their shots. A 3D court of the shift for every row." },
];

export default function StatsIndex() {
  // /stats (NBA) and /wnba/stats (WNBA): the same directory, each on its own league's data. Each card shows the season
  // its data is on (the nightly refresh moves them to 2026-27 as the season starts)
  const league = useLeague(), root = statsRoot(league);
  const [meta, setMeta] = useState({});
  useEffect(() => {
    PAGES.filter(p => p.route).forEach(p => {
      fetch(`${API}/nba/stats/${p.route}${leagueQ(league)}`, { credentials: "include" }).then(r => r.json())
        .then(d => setMeta(m => ({ ...m, [`${league}:${p.route}`]: d?.meta || {} }))).catch(() => {});
    });
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
          {PAGES.map(p => (
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
