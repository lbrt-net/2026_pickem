import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";

const snake = ["BB", "RR", "BJ", "ST", "FC", "BZ", "AA", "TD", "BM", "ZD"]; // round 1 order; reverses each round

const available = [
  [1, "Bam Adebayo", "C", "44.0", "39.2"],
  [2, "Herbert Jones", "SF", "23.1", "21.4"],
  [3, "Jalen Williams", "SF", "41.5", "34.0"],
  [4, "Coby White", "PG", "33.8", "27.1"],
  [5, "Alperen Sengun", "C", "39.9", "31.0"],
];

const queue = ["Bam Adebayo", "Jalen Williams", "Coby White"];

const recentPicks = [
  [43, "Rim Reapers", "Franz Wagner", "SF"],
  [42, "Screen Time", "Scottie Barnes", "PF"],
  [41, "Full Court Press", "Devin Vassell", "SG"],
];

export default function DraftRoom() {
  const season = "2026-27";
  return (
    <FantasyShell title="Draft Room" season={season}>
      <div style={{ fontSize: 10, color: "#999", marginBottom: 6 }}>
        Live during the draft only — after it ends this becomes{" "}
        <Link to={`/fantasy/${season}/draft/recap`} style={{ textDecoration: "underline" }}>Draft Recap</Link>.
        No ADP yet — using projected points + historical average instead. Possible move to a bidding/auction format later, not decided.
      </div>

      <div style={{ border: "1px solid #999", padding: 8, marginBottom: 10, display: "flex", gap: 6, overflowX: "auto" }}>
        <span style={{ fontSize: 10, color: "#999", alignSelf: "center" }}>SNAKE ORDER (Rd 1):</span>
        {snake.map((t, i) => (
          <span key={t} style={{ fontSize: 11, border: i === 6 ? "2px solid #111" : "1px solid #ccc", padding: "3px 7px" }}>{i + 1}. {t}</span>
        ))}
      </div>

      <div style={{ border: "2px solid #111", padding: 10, display: "flex", justifyContent: "space-between", marginBottom: 14, fontSize: 13 }}>
        <span style={{ fontWeight: 700 }}>Round 4, Pick 7</span>
        <span>On the clock: <b>Baseline Bandits (You)</b></span>
        <span style={{ fontWeight: 700 }}>0:47</span>
      </div>

      <div style={{ display: "flex", gap: 20 }}>
        <div style={{ flex: 1.4, border: "1px solid #999", padding: 12 }}>
          <div style={{ fontSize: 10, color: "#999", marginBottom: 6 }}>AVAILABLE PLAYERS</div>
          <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ fontSize: 10, color: "#999", textAlign: "left" }}>
                <th>#</th><th>Name</th><th>Pos</th><th style={{ textAlign: "right" }}>Proj</th><th style={{ textAlign: "right" }}>Hist Avg</th><th></th>
              </tr>
            </thead>
            <tbody>
              {available.map(([rank, name, pos, proj, hist]) => (
                <tr key={name} style={{ borderTop: "1px solid #eee" }}>
                  <td style={{ padding: "5px 0" }}>{rank}</td><td>{name}</td><td>{pos}</td>
                  <td style={{ textAlign: "right" }}>{proj}</td><td style={{ textAlign: "right" }}>{hist}</td>
                  <td><span style={{ border: "1px solid #333", padding: "2px 8px", fontSize: 11 }}>Draft</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ border: "1px solid #999", padding: 12 }}>
            <div style={{ fontSize: 10, color: "#999", marginBottom: 6 }}>YOUR QUEUE</div>
            {queue.map((n, i) => <div key={n} style={{ fontSize: 12, padding: "3px 0" }}>{i + 1}. {n}</div>)}
          </div>
          <div style={{ border: "1px solid #999", padding: 12 }}>
            <div style={{ fontSize: 10, color: "#999", marginBottom: 6 }}>RECENT PICKS</div>
            {recentPicks.map(([pick, team, name, pos]) => (
              <div key={pick} style={{ fontSize: 11, padding: "3px 0", borderBottom: "1px solid #eee" }}>Pick {pick} — {team} take {name} ({pos})</div>
            ))}
            <div style={{ fontSize: 11, marginTop: 6, textDecoration: "underline" }}>View full draft history &rarr;</div>
          </div>
        </div>
      </div>
    </FantasyShell>
  );
}
