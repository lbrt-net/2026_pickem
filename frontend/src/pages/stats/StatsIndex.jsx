import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import StatsNav from "./StatsNav";
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
  { to: "/stats/lineups", title: "Lineups", route: "lineups",
    what: "The best and worst players, pairs, trios and five-man units by net rating: points scored minus points allowed per 100 possessions together, with on/off for single players." },
  // no route: its data is large, so the card doesn't fetch it just to show the season
  { to: "/stats/defense", title: "Defense", route: null, season: "2025-26",
    what: "Every team's defenders: DRtg raw and adjusted for opponents, on/off, how often they faced top scorers and third-string units, lift and stability across teammates, and every pair and trio together." },
];

export default function StatsIndex() {
  // each card shows the season its data is on (the nightly refresh moves them to 2026-27 as the season starts)
  const [meta, setMeta] = useState({});
  useEffect(() => {
    PAGES.filter(p => p.route).forEach(p => {
      fetch(`${API}/nba/stats/${p.route}`, { credentials: "include" }).then(r => r.json())
        .then(d => setMeta(m => ({ ...m, [p.route]: d?.meta || {} }))).catch(() => {});
    });
  }, []);
  return (
    <div className="site-ui stats-ui" style={{ minHeight: "100vh" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1100, boxSizing: "border-box", minWidth: 0 }}>
        <StatsNav />
        <div className="rb-head">
          <h1 className="rb-title">Stats</h1>
          <span className="rb-meta">from the play-by-play</span>
        </div>
        <div className="si-grid">
          {PAGES.map(p => (
            <Link key={p.to} to={p.to} className="si-card">
              <div className="si-top"><b>{p.title}</b><span>{meta[p.route]?.season || p.season || ""}{meta[p.route]?.built ? ` · built ${meta[p.route].built}` : ""}</span></div>
              <p>{p.what}</p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
