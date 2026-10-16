import { Link } from "react-router-dom";
import MainNav from "../../components/shared/MainNav";
import StatsNav from "./StatsNav";
import "./Rebounding.css";
import "./StatsIndex.css";

// /stats — the directory of the stats pages. Public NBA analysis from the play-by-play; nothing here links into fantasy.
const PAGES = [
  { to: "/stats/shooting", title: "Shooting", season: "2025-26",
    what: "Points over what the league scores from the same shots in the same situations, per 75 possessions. The 300 biggest shot-takers, expected and actual points per shot, shot diet, and a shot chart for every row." },
  { to: "/stats/rebounding", title: "Rebounding", season: "2024-25",
    what: "Every live miss a player was on the floor for: his share and his team's rate, expected from the shot alone, expected from the other nine plus a man of his size, and actual. Defense and offense, with what he takes off teammates." },
  { to: "/stats/playmaking", title: "Playmaking", season: "2025-26",
    what: "Box Creation, Ben Taylor's box-score estimate of the open shots a player creates for teammates per 100 possessions, with the formula's pieces for every player." },
];

export default function StatsIndex() {
  return (
    <div className="site-ui" style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1100, boxSizing: "border-box", minWidth: 0 }}>
        <StatsNav />
        <div className="rb-head">
          <h1 className="rb-title">Stats</h1>
          <span className="rb-meta">NBA analysis built from the play-by-play · one page per question</span>
        </div>
        <div className="si-grid">
          {PAGES.map(p => (
            <Link key={p.to} to={p.to} className="si-card">
              <div className="si-top"><b>{p.title}</b><span>{p.season}</span></div>
              <p>{p.what}</p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
