import { useSearchParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";

export default function Recap() {
  const [params] = useSearchParams();
  const week = params.get("week") || "12";

  return (
    <FantasyShell title={`Week ${week} Recap`} season="2026-27">
      <div style={{ fontSize: 10, color: "#999", marginBottom: 10 }}>Same template reused for the season-end recap, just a different cadence.</div>

      <div style={{ border: "1px solid #999", padding: 12, marginBottom: 12 }}>
        <div style={{ fontSize: 10, color: "#999" }}>TEAM OF THE WEEK</div>
        <div style={{ fontSize: 13, marginTop: 4 }}>Baseline Bandits — 412.5 pts &middot; top scorer: Nikola Jokic (58.4)</div>
      </div>

      <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
        <div style={{ flex: 1, border: "1px solid #999", padding: 12 }}>
          <div style={{ fontSize: 10, color: "#999" }}>BIGGEST BLOWOUT</div>
          <div style={{ fontSize: 13, marginTop: 4 }}>Baseline Bandits Jr 440.1 – 301.2 Bench Mob</div>
        </div>
        <div style={{ flex: 1, border: "1px solid #999", padding: 12 }}>
          <div style={{ fontSize: 10, color: "#999" }}>CLOSEST MATCHUP</div>
          <div style={{ fontSize: 13, marginTop: 4 }}>Rim Reapers 395.1 – 401.4 Screen Time</div>
        </div>
      </div>

      <div style={{ border: "1px solid #999", padding: 12, marginBottom: 12 }}>
        <div style={{ fontSize: 10, color: "#999", marginBottom: 6 }}>STANDINGS MOVERS</div>
        <div style={{ fontSize: 12 }}>Full Court Press moved up to 5th</div>
        <div style={{ fontSize: 12 }}>Airball Assassins dropped to 7th</div>
      </div>

      <div style={{ border: "1px solid #999", padding: 12 }}>
        <div style={{ fontSize: 10, color: "#999", marginBottom: 6 }}>STAT TICKER</div>
        <div style={{ fontSize: 12 }}>Highest single score: Baseline Bandits Jr, 440.1</div>
        <div style={{ fontSize: 12 }}>Best waiver pickup of the week: Alperen Sengun (+38.9 pts, Screen Time)</div>
      </div>
    </FantasyShell>
  );
}
