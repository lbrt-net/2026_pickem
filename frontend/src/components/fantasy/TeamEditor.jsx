import { useEffect, useRef, useState } from "react";
import TeamIcon from "./TeamIcon";
import { TEAM_COLOR_GROUPS } from "./teamColors";
import { GLYPHS } from "./glyphs";
import { API_BASE } from "./data";
import { API } from "../../utils/helpers";
import "./TeamEditor.css";

// Your team (top of Team Settings), in three areas that each save where you work:
//  Picture — your upload, your Discord picture, or an icon (one of the glyphs) on your color. Click to switch.
//  Name    — name + abbreviation, Save right beside them.
//  Color   — click a swatch, it's saved.
// Backend: GET / PUT /teams/:id/settings ({name, abbreviation, color, picture, glyph}), PUT / DELETE /teams/:id/logo.
export default function TeamEditor({ team, onSaved }) {
  const [s, setS] = useState(null); // the saved settings (GET /teams/:id/settings)
  const [name, setName] = useState(team.name || "");
  const [abbr, setAbbr] = useState(team.abbreviation || "");
  const [busy, setBusy] = useState(null); // which area is saving
  const [note, setNote] = useState({}); // area -> {text, error}
  const file = useRef(null);
  const url = path => `${API}${API_BASE}/teams/${encodeURIComponent(team.id)}${path}`;

  useEffect(() => {
    let live = true;
    fetch(`${API}${API_BASE}/teams/${encodeURIComponent(team.id)}/settings`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null)
      .then(out => { if (live && out) setS(out); });
    return () => { live = false; };
  }, [team.id]);

  async function call(area, path, opts) {
    setBusy(area); setNote(n => ({ ...n, [area]: null }));
    try {
      const r = await fetch(url(path), { credentials: "include", ...opts });
      const out = await r.json().catch(() => ({}));
      if (!r.ok) { setNote(n => ({ ...n, [area]: { error: true, text: out.detail || "Couldn't save" } })); return; }
      setS(out); onSaved?.(out);
      setNote(n => ({ ...n, [area]: { text: "Saved" } }));
    } catch {
      setNote(n => ({ ...n, [area]: { error: true, text: "Couldn't reach the server" } }));
    } finally {
      setBusy(null);
    }
  }
  const put = (area, body) => call(area, "/settings", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const upload = f => f && call("picture", "/logo", { method: "PUT", headers: { "Content-Type": f.type || "application/octet-stream" }, body: f });
  const noteFor = area => (note[area] ? <span className={`te-note${note[area].error ? " bad" : ""}`}>{note[area].text}</span> : null);

  if (!s) return <section className="te"><span className="te-title"><i aria-hidden="true" />Your team</span><p className="te-loading">Loading…</p></section>;

  const look = { ...team, ...s, name, abbreviation: abbr }; // the live preview
  const glyphLook = g => ({ ...look, logo_url: null, glyph: g });
  const nameDirty = name.trim() !== s.name || abbr.trim() !== s.abbreviation;

  return (
    <section className="te" aria-label="Your team">
      <div className="te-hero" style={{ "--tc": s.color }}>
        <TeamIcon team={look} size={72} />
        <span className="te-hero-n"><b>{name || "—"}</b><span>{abbr}</span></span>
      </div>

      <div className="te-areas">
        <div className="te-area">
          <span className="te-title"><i aria-hidden="true" />Name</span>
          <div className="te-name">
            <label className="te-field">Team name<input value={name} maxLength={50} onChange={e => setName(e.target.value)} /></label>
            <label className="te-field te-abbr">Short<input value={abbr} maxLength={4} onChange={e => setAbbr(e.target.value.toUpperCase())} /></label>
            <button type="button" className="te-btn primary" disabled={busy === "name" || !nameDirty || !name.trim() || !abbr.trim()}
              onClick={() => put("name", { name: name.trim(), abbreviation: abbr.trim() })}>Save</button>
          </div>
          {noteFor("name")}
        </div>

        <div className="te-area">
          <span className="te-title"><i aria-hidden="true" />Picture</span>
          <div className="te-pics" role="radiogroup" aria-label="Picture">
            <button type="button" role="radio" aria-checked={s.picture_mode === "upload"} className="te-pick" disabled={busy === "picture"}
              onClick={() => (s.upload_url ? put("picture", { picture: "upload" }) : file.current?.click())}>
              {s.upload_url ? <img src={s.upload_url} alt="" /> : <span className="te-pick-empty">+</span>}
              <span>{s.upload_url ? "Your upload" : "Upload"}</span>
            </button>
            <button type="button" role="radio" aria-checked={s.picture_mode === "discord"} className="te-pick" disabled={!s.discord_url || busy === "picture"}
              onClick={() => put("picture", { picture: "discord" })}>
              {s.discord_url ? <img src={s.discord_url} alt="" /> : <span className="te-pick-empty">—</span>}
              <span>Discord</span>
            </button>
            <button type="button" role="radio" aria-checked={s.picture_mode === "glyph"} className="te-pick" disabled={busy === "picture"}
              onClick={() => put("picture", { picture: "glyph" })}>
              <TeamIcon team={glyphLook(s.glyph)} size={56} />
              <span>Icon</span>
            </button>
          </div>
          {s.picture_mode === "glyph" && (
            <div className="te-glyphs" role="radiogroup" aria-label="Icon">
              {Object.keys(GLYPHS).map(g => (
                <button key={g} type="button" role="radio" aria-checked={s.glyph === g} className="te-glyph" title={g.replace("_", " ")}
                  onClick={() => put("picture", { glyph: g })}><TeamIcon team={glyphLook(g)} size={36} /></button>
              ))}
            </div>
          )}
          {s.upload_url && (
            <span className="te-links">
              <button type="button" className="te-link" onClick={() => file.current?.click()}>Replace upload</button>
              <button type="button" className="te-link" onClick={() => call("picture", "/logo", { method: "DELETE" })}>Delete upload</button>
            </span>
          )}
          <input ref={file} type="file" accept="image/png,image/jpeg,image/gif,image/webp" hidden onChange={e => { upload(e.target.files?.[0]); e.target.value = ""; }} />
          {noteFor("picture")}
        </div>

        <div className="te-area">
          <span className="te-title"><i aria-hidden="true" />Color</span>
          <div className="te-colors" role="radiogroup" aria-label="Team color">
            {TEAM_COLOR_GROUPS.flatMap(g => g.colors).map(([label, hex]) => (
              <button key={hex} type="button" role="radio" aria-checked={s.color === hex} aria-label={label} title={label}
                className="te-swatch" style={{ background: hex }} disabled={busy === "color"} onClick={() => put("color", { color: hex })} />
            ))}
          </div>
          {noteFor("color")}
        </div>
      </div>
    </section>
  );
}
