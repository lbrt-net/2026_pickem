import { useState } from "react";
import TeamIcon from "./TeamIcon";
import { TEAM_COLOR_GROUPS } from "./teamColors";
import { API_BASE } from "./data";
import { API } from "../../utils/helpers";
import "./TeamEditor.css";

// Edit your team where its name lives (the Roster page's team header): name, abbreviation, picture, color.
// Saves through PUT /teams/:id/settings and PUT / DELETE /teams/:id/logo (backend settings.py).
export default function TeamEditor({ team, onSaved, onClose }) {
  const [name, setName] = useState(team.name || "");
  const [abbr, setAbbr] = useState(team.abbreviation || "");
  const [color, setColor] = useState(team.color || null);
  const [logo, setLogo] = useState(team.logo_url || null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [note, setNote] = useState(null);
  const url = path => `${API}${API_BASE}/teams/${encodeURIComponent(team.id)}${path}`;

  async function call(path, opts) {
    setBusy(true); setError(null); setNote(null);
    try {
      const r = await fetch(url(path), { credentials: "include", ...opts });
      const out = await r.json().catch(() => ({}));
      if (!r.ok) { setError(out.detail || "Couldn't save"); return null; }
      return out;
    } catch {
      setError("Couldn't reach the server — try again");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function pickPicture(file) {
    if (!file) return;
    const out = await call("/logo", { method: "PUT", headers: { "Content-Type": file.type || "application/octet-stream" }, body: file });
    if (out) { setLogo(out.logo_url); onSaved(out); }
  }
  async function removePicture() {
    const out = await call("/logo", { method: "DELETE" });
    if (out) { setLogo(out.logo_url); onSaved(out); }
  }
  async function save() {
    const out = await call("/settings", {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name.trim(), abbreviation: abbr.trim(), color }),
    });
    if (out) { onSaved(out); setNote("Saved."); onClose?.(); }
  }

  const preview = { ...team, name, abbreviation: abbr, color, logo_url: logo };
  return (
    <section className="te" aria-label="Your team">
      <span className="te-title"><i aria-hidden="true" />Your team</span>
      <div className="te-row">
        <span className="te-pic">
          <TeamIcon team={preview} size={64} />
          <span className="te-pic-btns">
            <label className="te-btn small">Upload picture<input type="file" accept="image/png,image/jpeg,image/gif,image/webp" hidden
              onChange={e => pickPicture(e.target.files?.[0])} /></label>
            {logo && <button type="button" className="te-btn small" disabled={busy} onClick={removePicture}>Remove picture</button>}
          </span>
        </span>
        <label className="te-field">Name<input value={name} maxLength={50} onChange={e => setName(e.target.value)} /></label>
        <label className="te-field te-abbr">Abbreviation<input value={abbr} maxLength={4} onChange={e => setAbbr(e.target.value.toUpperCase())} /></label>
      </div>
      <div className="te-colors" role="radiogroup" aria-label="Team color">
        {TEAM_COLOR_GROUPS.flatMap(g => g.colors).map(([label, hex]) => (
          <button key={hex} type="button" role="radio" aria-checked={color === hex} aria-label={label} title={label}
            className="te-swatch" style={{ background: hex }} onClick={() => setColor(hex)} />
        ))}
      </div>
      {error && <div className="te-error" role="alert">{error}</div>}
      <div className="te-actions">
        {note && <span className="te-note">{note}</span>}
        {onClose && <button type="button" className="te-btn" onClick={onClose}>Cancel</button>}
        <button type="button" className="te-btn primary" disabled={busy || !name.trim()} onClick={save}>Save</button>
      </div>
    </section>
  );
}
