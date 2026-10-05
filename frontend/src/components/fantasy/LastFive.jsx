// Last 5 results, oldest → newest: a colored circle with a white letter (design: canvas "Standings v2").
import "./LastFive.css";

const WORD = { W: "win", L: "loss", T: "tie" };

export default function LastFive({ results }) {
  const last = results.slice(-5);
  return (
    <span className="last5" aria-label={last.length ? `Last ${last.length}: ${last.map(r => WORD[r]).join(", ")}` : "No games yet"}>
      {last.map((r, i) => <span key={i} className={`last5-${r}`} aria-hidden="true">{r}</span>)}
    </span>
  );
}
