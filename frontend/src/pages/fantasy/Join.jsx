import { useEffect, useMemo, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { GLYPHS, glyphStroke } from "../../components/fantasy/glyphs";
import { TEAM_COLOR_GROUPS, textOnColor } from "../../components/fantasy/teamColors";
import { API_BASE, base, SEASON } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";
import "./Join.css";

// The join page (design: canvas board N · League — join). Home's Join button opens it; it isn't in
// the sidebar. Just your team (name, abbreviation, picture = Discord avatar / upload / glyph +
// color, live preview) and one JOIN button — nothing happens until Join is clicked, and no other
// teams or links are on the page (the sidebar is the way out). Joined → Home. Already in, logged
// out, or joining closed → Home. Leaving the league lives at the bottom of Team settings.

const GLYPH_NAMES = { basketball: "Basketball", swish: "Swish", ref_jersey: "Ref jersey", whistle: "Whistle", sneaker: "Sneaker", jersey: "Jersey" };
const PALETTE = TEAM_COLOR_GROUPS.flatMap(g => g.colors);
const MAX_LOGO = 512 * 1024;
const autoAbbr = name => (name || "").replace(/[^A-Za-z0-9]/g, "").slice(0, 4).toUpperCase() || "TEAM";
const pick = list => list[Math.floor(Math.random() * list.length)];

const arrow = (
  <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
    <path d="M4 11h13M12 5l6 6-6 6" stroke="currentColor" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

function JoinView({ data, user, scenario, onJoined }) {
  const taken = useMemo(() => new Set(data.teams.map(t => (t.color || "").toLowerCase())), [data.teams]);
  const [name, setName] = useState(user.username || "");
  const [abbr, setAbbr] = useState(""); // blank = automatic from the name
  const [picture, setPicture] = useState(user.avatarUrl ? "avatar" : "glyph");
  const [glyph, setGlyph] = useState(() => pick(Object.keys(GLYPHS)));
  const [color, setColor] = useState(() => {
    const free = PALETTE.filter(([, hex]) => !taken.has(hex));
    return pick(free.length ? free : PALETTE)[1];
  });
  const [file, setFile] = useState(null);
  const [fileUrl, setFileUrl] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!file) { setFileUrl(null); return undefined; }
    const url = URL.createObjectURL(file);
    setFileUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const shownAbbr = abbr || autoAbbr(name);
  const preview = {
    color, glyph,
    logo_url: picture === "avatar" ? user.avatarUrl : picture === "upload" ? fileUrl : null,
  };
  const choices = [
    ...(user.avatarUrl ? [["avatar", "Discord avatar"]] : []),
    ["upload", "Upload image"],
    ["glyph", "Glyph + color"],
  ];

  function chooseFile(f) {
    setError(null);
    if (f && f.size > MAX_LOGO) { setError("That image is over 512 KB — pick a smaller one."); setFile(null); return; }
    setFile(f || null);
  }

  async function join() {
    setBusy(true); setError(null);
    try {
      const body = { name, abbreviation: shownAbbr, picture, glyph, ...(picture === "glyph" ? { color } : {}) };
      const r = await fetch(`${API}${API_BASE}/league/join?scenario=${scenario}`, {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      });
      const out = await r.json();
      if (!r.ok) { setError(out.detail || "Couldn't join"); return; }
      if (picture === "upload" && file) {
        const up = await fetch(`${API}${API_BASE}/teams/${encodeURIComponent(out.team_id)}/logo`, { method: "PUT", credentials: "include", body: file });
        if (!up.ok) {
          const detail = (await up.json().catch(() => ({}))).detail;
          onJoined(`You're in, but the picture didn't upload${detail ? `: ${detail}` : ""}. Try again in Team settings.`);
          return;
        }
      }
      onJoined(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="lj">
      <div className="lj-title">
        <h2>Join the league</h2>
        <span className="lj-count">{data.teams.length} / {data.team_limit} teams</span>
      </div>
      <div className="lj-note">
        <b>You haven't joined the league yet — click Join to finish.</b>
        <span>You can change your team info later in Team settings.</span>
      </div>
      {error && <div className="lj-error" role="alert">{error}</div>}

      <div className="lj-grid">
        <section className="lj-panel lj-preview" aria-label="Preview">
          <span className="lj-label"><span className="lj-tick" aria-hidden="true" />Your team</span>
          <TeamIcon team={preview} size={132} />
          <span className="lj-preview-name">{name.trim() || user.username}</span>
          <span className="lj-abbr">{shownAbbr}</span>
          <span className="lj-small"><TeamIcon team={preview} size={28} />How it shows in standings</span>
        </section>

        <section className="lj-panel" aria-label="Team details">
          <div className="lj-fields">
            <label className="lj-field">
              <span>Team name</span>
              <input value={name} maxLength={50} onChange={e => setName(e.target.value)} />
            </label>
            <label className="lj-field">
              <span>Abbreviation</span>
              <input className="lj-abbr-input" value={abbr} placeholder={autoAbbr(name)} maxLength={4}
                onChange={e => setAbbr(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""))} />
            </label>
          </div>

          <div className="lj-field">
            <span className="lj-sub">Picture</span>
            <div className="lj-choices" role="radiogroup" aria-label="Picture">
              {choices.map(([key, label]) => (
                <button key={key} type="button" role="radio" aria-checked={picture === key} className="lj-choice" onClick={() => setPicture(key)}>{label}</button>
              ))}
            </div>
            {picture === "avatar" && <div className="lj-well">Your Discord avatar is your team picture.</div>}
            {picture === "upload" && (
              <div className="lj-well">
                <span className="lj-well-label">PNG, JPEG, GIF or WebP, up to 512 KB</span>
                <input type="file" accept="image/png,image/jpeg,image/gif,image/webp" onChange={e => chooseFile(e.target.files?.[0])} />
              </div>
            )}
            {picture === "glyph" && (
              <div className="lj-well">
                <span className="lj-well-label">Glyph</span>
                <div className="lj-glyphs" role="radiogroup" aria-label="Glyph">
                  {Object.entries(GLYPHS).map(([key, d]) => (
                    <button key={key} type="button" role="radio" aria-checked={glyph === key} aria-label={GLYPH_NAMES[key]} title={GLYPH_NAMES[key]}
                      className="lj-glyph" style={glyph === key ? { background: color, color: textOnColor(color) } : undefined} onClick={() => setGlyph(key)}>
                      <svg width="32" height="32" viewBox="0 0 24 24" aria-hidden="true">
                        <path d={d} stroke="currentColor" strokeWidth={glyphStroke(44)} fill="none" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                  ))}
                </div>
                <span className="lj-well-label" style={{ marginTop: 6 }}>Color</span>
                <div className="lj-swatches" role="radiogroup" aria-label="Color">
                  {PALETTE.map(([label, hex]) => (
                    <button key={hex} type="button" role="radio" aria-checked={color === hex} aria-label={label} title={label}
                      className="lj-swatch" style={{ background: hex }} onClick={() => setColor(hex)} />
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      </div>

      <button type="button" className="lj-join" disabled={busy || (picture === "upload" && !file)} onClick={join}>
        {busy ? "Joining…" : picture === "upload" && !file ? "Choose an image to join" : "Join"}{arrow}
      </button>
    </div>
  );
}

export default function Join() {
  const user = useCurrentUser();
  const navigate = useNavigate();
  const [scenario] = useFantasyScenario();
  const [data, setData] = useState(undefined);

  useEffect(() => {
    fetch(`${API}${API_BASE}/league/members?scenario=${scenario}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null).then(setData);
  }, [scenario]);

  const title = scenario === "replay" ? "2025-26 test league" : "Join";
  if (data === undefined || user === undefined) return <FantasyShell title={title} season={SEASON}><p style={{ fontSize: 13 }}>Loading…</p></FantasyShell>;
  if (data === null) return <FantasyShell title={title} season={SEASON}><p style={{ fontSize: 13 }}>Couldn't load the league.</p></FantasyShell>;
  // Already in, logged out, full, or the draft started: nothing to do here — Home has the rest.
  if (!data.can_join || !user) return <Navigate to={base()} replace />;

  return (
    <FantasyShell title={title} season={SEASON}>
      <JoinView key={scenario} data={data} user={user} scenario={scenario} onJoined={msg => {
        if (msg) window.alert(msg);
        navigate(base());
      }} />
    </FantasyShell>
  );
}
