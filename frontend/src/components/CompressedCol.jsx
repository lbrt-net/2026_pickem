import { dotClass } from "../utils/helpers";

export default function CompressedCol({ matchups, conf, label, picks }) {
  return (
    <div className="cinner">
      {matchups.map((m) => (
        <div key={m.id} className={`dot ${(picks[m.id]?.winner || m.winner_result) ? dotClass(conf) : ""}`} />
      ))}
    </div>
  );
}