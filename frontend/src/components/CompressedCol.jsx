import { dotClass } from "../utils/helpers";

export default function CompressedCol({ matchups, conf, label, picks }) {
  return (
    <div className="cinner">
      <span className="vlabel">{label}</span>
      {matchups.map((m) => (
        <div key={m.id} className={`dot ${picks[m.id]?.winner ? dotClass(conf) : ""}`} />
      ))}
    </div>
  );
}