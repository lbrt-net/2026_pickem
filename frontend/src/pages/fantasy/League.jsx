import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { GLYPHS, glyphStroke } from "../../components/fantasy/glyphs";
import { TEAM_COLOR_GROUPS, textOnColor } from "../../components/fantasy/teamColors";
import { BASE, SEASON } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";
import "./League.css";

// The league's front door (design: canvas board N · League — join).
// Not in yet and joining is open → the join view: just your team (name, abbreviation, picture =
// Discord avatar / upload / glyph + color, live preview) and one JOIN button. Nothing happens until
// Join is clicked; no other teams or links on the page — the sidebar is the way out.
// In (or joining closed) → status, the teams, Leave.

const KIND = { member: "", fake: "fake user", bot: "bot (commissioner controls)" };
const STATUS = { not_started: "Draft not started — joining is open", in_progress: "Drafting now", complete: "Drafted" };
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
  const [abbr, setAbbr] = useState(null); // null = follow the name
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

  const shownAbbr = abbr ?? autoAbbr(name);
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
      const r = await fetch(`${API}${BASE}/league/join?scenario=${scenario}`, {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      });
      const out = await r.json();
      if (!r.ok) { setError(out.detail || "Couldn't join"); return; }
      if (picture === "upload" && file) {
        const up = await fetch(`${API}${BASE}/teams/${encodeURIComponent(out.team_id)}/logo`, { method: "PUT", credentials: "include", body: file });
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
              <input className="lj-abbr-input" value={shownAbbr} maxLength={4}
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

export default function League() {
  const user = useCurrentUser();
  const [scenario] = useFantasyScenario();
  const [data, setData] = useState(undefined);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(() => (
    fetch(`${API}${BASE}/league/members?scenario=${scenario}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null).then(setData)
  ), [scenario]);
  useEffect(() => { load(); }, [load]);

  async function leave() {
    const before = data?.draft_status === "not_started";
    if (!window.confirm(before ? "Leave the league? Your team is removed." : "Leave the league? Your team becomes a bot the commissioner controls.")) return;
    setBusy(true); setError(null);
    const r = await fetch(`${API}${BASE}/league/leave?scenario=${scenario}`, { method: "POST", credentials: "include" });
    const out = await r.json();
    if (!r.ok) setError(out.detail || "Couldn't leave"); else setData(out);
    setBusy(false);
  }

  const title = scenario === "replay" ? "2025-26 test league" : "League";
  if (data === undefined) return <FantasyShell title={title} season={SEASON}><p style={{ fontSize: 13 }}>Loading…</p></FantasyShell>;
  if (data === null) return <FantasyShell title={title} season={SEASON}><p style={{ fontSize: 13 }}>Couldn't load the league.</p></FantasyShell>;

  if (data.can_join && user) {
    return (
      <FantasyShell title={title} season={SEASON}>
        <JoinView key={scenario} data={data} user={user} scenario={scenario} onJoined={msg => { setError(msg); load(); }} />
      </FantasyShell>
    );
  }

  return (
    <FantasyShell title={title} season={SEASON}>
      <div className="lj">
        <div className="lj-status">
          <b>{STATUS[data.draft_status]}</b>
          <span>{data.teams.length} / {data.team_limit} teams</span>
          <Link to={`${BASE}/draft`}>View the draft room &rarr;</Link>
        </div>

        {error && <div className="lj-error" role="alert">{error}</div>}
        {!data.my_team_id && data.join_closed_reason && <p style={{ fontSize: 14 }}>Can't join: {data.join_closed_reason}.</p>}

        <section className="lj-teams" aria-label="Teams">
          <div className="lj-label"><span className="lj-tick" aria-hidden="true" />Teams</div>
          {data.teams.length === 0 && <div className="lj-team">Nobody's in yet.</div>}
          {data.teams.map(t => (
            <div key={t.id} className={`lj-team${t.id === data.my_team_id ? " mine" : ""}`}>
              <TeamIcon team={t} size={28} />
              <span style={{ fontWeight: 700 }}>{t.name}</span>
              <span>{t.abbreviation}</span>
              {t.kind === "member" && t.owner_name && t.owner_name !== t.name && <span>· {t.owner_name}</span>}
              {KIND[t.kind] && <span>· {KIND[t.kind]}</span>}
              {t.id === data.my_team_id && <span className="lj-you">You</span>}
            </div>
          ))}
        </section>

        {data.can_leave && (
          <button className="lj-leave" disabled={busy} onClick={leave}>
            {data.draft_status === "not_started" ? "Leave the league" : "Leave the league (your team becomes a bot)"}
          </button>
        )}
      </div>
    </FantasyShell>
  );
}
