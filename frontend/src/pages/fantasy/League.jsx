import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { BASE, SEASON } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";

// The league's front door: who's in it, Join (until the draft starts), Leave, and the draft room.
// Joining asks for a team name, abbreviation, and picture; "Skip" uses your Discord name, an
// automatic abbreviation, and your Discord avatar.

const box = { border: "1px solid var(--border)", padding: 14, marginBottom: 14 };
const heading = { fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 8 };
const KIND = { member: "", fake: "fake user", bot: "bot (commissioner controls)" };
const STATUS = { not_started: "Draft not started — joining is open", in_progress: "Drafting now", complete: "Drafted" };

export default function League() {
  const user = useCurrentUser();
  const [scenario] = useFantasyScenario();
  const [data, setData] = useState(undefined);
  const [joining, setJoining] = useState(false);
  const [form, setForm] = useState({ name: "", abbreviation: "" });
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(() => (
    fetch(`${API}${BASE}/league/members?scenario=${scenario}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null).then(setData)
  ), [scenario]);
  useEffect(() => { load(); }, [load]);

  async function join(useDefaults) {
    setBusy(true); setError(null);
    try {
      const r = await fetch(`${API}${BASE}/league/join?scenario=${scenario}`, {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(useDefaults ? {} : form),
      });
      const out = await r.json();
      if (!r.ok) { setError(out.detail || "Couldn't join"); return; }
      if (!useDefaults && file) {
        const up = await fetch(`${API}${BASE}/teams/${encodeURIComponent(out.team_id)}/logo`, {
          method: "PUT", credentials: "include", body: file,
        });
        if (!up.ok) setError(`Joined, but the picture didn't upload: ${(await up.json()).detail}`);
      }
      setJoining(false);
      await load();
    } finally {
      setBusy(false);
    }
  }

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

  return (
    <FantasyShell title={title} season={SEASON}>
      <div style={{ ...box, display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <span style={{ fontSize: 15, fontWeight: 700 }}>{STATUS[data.draft_status]}</span>
        <span>{data.teams.length} / {data.team_limit} teams</span>
        <Link to={`${BASE}/draft`} style={{ marginLeft: "auto", fontWeight: 600 }}>View the draft room &rarr;</Link>
      </div>

      {error && <p style={{ fontSize: 14, color: "var(--accent-red)", marginBottom: 12 }}>{error}</p>}

      {data.can_join && !joining && (
        <div style={box}>
          <button onClick={() => { setJoining(true); setForm({ name: user?.username || "", abbreviation: "" }); }} style={{ fontSize: 15, padding: "8px 18px" }}>
            Join this league
          </button>
        </div>
      )}

      {data.can_join && joining && (
        <div style={box}>
          <div style={heading}>Your team</div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end", marginBottom: 12 }}>
            <label style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 4 }}>
              Team name
              <input value={form.name} maxLength={50} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} style={{ fontSize: 14, width: 240 }} />
            </label>
            <label style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 4 }}>
              Abbreviation (1–4)
              <input value={form.abbreviation} maxLength={4} placeholder="auto"
                onChange={e => setForm(f => ({ ...f, abbreviation: e.target.value.toUpperCase() }))} style={{ fontSize: 14, width: 80 }} />
            </label>
            <label style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 4 }}>
              Picture (PNG/JPEG/GIF/WebP, ≤ 512 KB)
              <input type="file" accept="image/png,image/jpeg,image/gif,image/webp" onChange={e => setFile(e.target.files?.[0] || null)} />
            </label>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button disabled={busy} onClick={() => join(false)}>Join</button>
            <button disabled={busy} onClick={() => join(true)}>Skip — use my Discord name, initials &amp; avatar</button>
            <button disabled={busy} onClick={() => setJoining(false)}>Cancel</button>
          </div>
        </div>
      )}

      {!data.can_join && !data.my_team_id && data.join_closed_reason && (
        <p style={{ fontSize: 14, marginBottom: 14 }}>Can't join: {data.join_closed_reason}.</p>
      )}

      <div style={box}>
        <div style={heading}>Teams</div>
        {data.teams.length === 0 && <p style={{ fontSize: 14 }}>Nobody's in yet.</p>}
        {data.teams.map(t => (
          <div key={t.id} style={{ display: "flex", gap: 10, alignItems: "center", padding: "6px 0", borderTop: "1px solid var(--border-subtle)", fontSize: 14 }}>
            <TeamIcon team={t} size={28} />
            <span style={{ fontWeight: 600 }}>{t.name}</span>
            <span>{t.abbreviation}</span>
            {t.kind === "member" && t.owner_name && t.owner_name !== t.name && <span>· {t.owner_name}</span>}
            {KIND[t.kind] && <span>· {KIND[t.kind]}</span>}
            {t.id === data.my_team_id && <span style={{ fontWeight: 700 }}>· you</span>}
          </div>
        ))}
      </div>

      {data.can_leave && (
        <button disabled={busy} onClick={leave}>
          {data.draft_status === "not_started" ? "Leave the league" : "Leave the league (your team becomes a bot)"}
        </button>
      )}
    </FantasyShell>
  );
}
