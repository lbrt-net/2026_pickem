import { useState, useEffect } from "react";
import { API } from "../utils/helpers";

export default function RosterEditor({ matchups, rosters, onSave, onClose }) {
  const teams = [...new Set(
    matchups.flatMap(m => [m.team_a, m.team_b].filter(Boolean))
  )].sort();

  const [selectedTeam, setSelectedTeam] = useState(teams[0] || "");
  const [text, setText] = useState("");

  useEffect(() => {
    if (!selectedTeam) return;
    setText((rosters[selectedTeam] || []).join("\n"));
  }, [selectedTeam, rosters]);

  function handleSave() {
    const players = text.split("\n").map(s => s.trim()).filter(Boolean);
    onSave(selectedTeam, players);
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Edit Rosters</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="rules-body">
          <p className="rules-note" style={{ marginBottom: 10 }}>
            One player name per line. Saved per team — carries through all rounds.
          </p>
          <select className="player-select"
            style={{ width: "100%", marginBottom: 10, fontSize: 13, padding: "6px 8px" }}
            value={selectedTeam}
            onChange={e => setSelectedTeam(e.target.value)}>
            {teams.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <textarea className="roster-textarea"
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder={"Jayson Tatum\nJaylen Brown\nJrue Holiday"}
            rows={8}
          />
          <button className="admin-btn confirm"
            style={{ marginTop: 8, width: "100%", padding: "7px 0", fontSize: 12 }}
            onClick={handleSave}>
            Save {selectedTeam} roster
          </button>
        </div>
      </div>
    </div>
  );
}