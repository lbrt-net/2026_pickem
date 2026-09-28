import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";

const box = { border: "1px solid var(--border)", padding: 14, marginBottom: 14 };
const label = { fontSize: 10, color: "var(--text)", marginBottom: 6 };
const link = { fontSize: 12, textDecoration: "underline" };

export default function FantasyHome() {
  const season = "2026_27";
  return (
    <FantasyShell title="Fantasy Home" season={season}>
      <div style={box}>
        <div style={label}>LEAGUE STANDINGS (top 5 + your rank)</div>
        <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
          <tbody>
            {[
              [1, "Baseline Bandits (you)", "10-2"],
              [2, "Rim Reapers", "9-3"],
              [3, "Baseline Bandits Jr", "8-4"],
              [4, "Screen Time", "8-4"],
              [5, "Full Court Press", "7-5"],
            ].map(([rank, name, rec]) => (
              <tr key={rank} style={{ fontWeight: name.includes("(you)") ? 700 : 400 }}>
                <td style={{ padding: "3px 6px" }}>{rank}</td>
                <td style={{ padding: "3px 6px" }}>{name}</td>
                <td style={{ padding: "3px 6px", textAlign: "right" }}>{rec}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <Link to={`/fantasy/${season}/standings`} style={link}>View full standings &rarr;</Link>
      </div>

      <div style={{ display: "flex", gap: 14 }}>
        <div style={{ ...box, flex: 1 }}>
          <div style={label}>THIS WEEK'S MATCHUP</div>
          <div style={{ fontSize: 13 }}>Baseline Bandits 412.5 &ndash; 388.2 Dunk or Be Dunked</div>
          <Link to={`/fantasy/${season}/matchup`} style={link}>View matchup &rarr;</Link>
        </div>
        <div style={{ ...box, flex: 1 }}>
          <div style={label}>NEXT WEEK — WEEK 13</div>
          <div style={{ fontSize: 13 }}>vs Screen Time (8-4)</div>
        </div>
      </div>

      <div style={box}>
        <div style={label}>SUGGESTED PICKUPS (moved here from Players)</div>
        {[
          ["Jalen Williams", "OKC", "Trending up · 3 straight 25+ games"],
          ["Alperen Sengun", "HOU", "Favorable schedule next 2 weeks"],
        ].map(([name, team, reason]) => (
          <div key={name} style={{ fontSize: 12, display: "flex", justifyContent: "space-between", padding: "3px 0" }}>
            <span>{name} — {team}</span><span style={{ color: "var(--text)" }}>{reason}</span>
          </div>
        ))}
        <Link to={`/fantasy/${season}/players`} style={link}>Browse all players &rarr;</Link>
      </div>

      <div style={box}>
        <div style={label}>YOUR TEAM</div>
        <div style={{ fontSize: 12, fontWeight: 700, margin: "4px 0" }}>Starters</div>
        {["Tyrese Haliburton (PG)", "Anthony Edwards (SG)", "Jayson Tatum (SF)", "Giannis Antetokounmpo (PF)", "Nikola Jokic (C)"].map(p => (
          <div key={p} style={{ fontSize: 12, padding: "2px 0" }}>{p}</div>
        ))}
        <div style={{ fontSize: 12, fontWeight: 700, margin: "8px 0 4px" }}>Bench</div>
        {["Devin Booker", "Domantas Sabonis", "Jaylen Brown", "Bam Adebayo (IL)"].map(p => (
          <div key={p} style={{ fontSize: 12, color: "var(--text)", padding: "2px 0" }}>{p}</div>
        ))}
        <Link to={`/fantasy/${season}/team`} style={{ ...link, display: "inline-block", marginTop: 10, border: "1px solid var(--border)", padding: "6px 12px", textDecoration: "none" }}>
          Manage Team &rarr;
        </Link>
      </div>
    </FantasyShell>
  );
}
