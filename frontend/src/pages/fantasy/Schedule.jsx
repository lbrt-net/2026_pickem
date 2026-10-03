import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { EntityLink } from "../../components/fantasy/links";
import { API_BASE, SEASON, TEST_SEASON, seasonOf } from "../../components/fantasy/data";
import { API } from "../../utils/helpers";
import { featureOn } from "../../components/fantasy/features";

// Real NBA schedule by fantasy week (Mon–Sun; All-Star break fused into 2 weeks;
// Championship is 2 weeks). ?season=2025-26&week=12 — state lives in the URL.
const SEASONS = featureOn("pastSeasons") ? ["2026-27", "2025-26", "2024-25", "2023-24", "2022-23"] : ["2026-27"];
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const card = { border: "1px solid var(--border)", background: "var(--surface)", padding: 10 };
const heading = { fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 8 };

const fmtDate = iso => new Date(`${iso}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });
const tipoff = g => g.time_tbd || !g.tipoff_utc
  ? "Time TBD"
  : new Date(g.tipoff_utc).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit", timeZone: "America/Chicago" }) + " CT";

function addDays(iso, n) {
  const d = new Date(`${iso}T12:00:00`);
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

function Game({ g }) {
  const team = t => (t ? <EntityLink id={t} name={t} /> : "TBD");
  let right;
  if (g.status === "final") right = `${g.away_score}–${g.home_score} Final`;
  else if (g.status === "postponed" || g.status === "cancelled") right = g.status === "postponed" ? "Postponed" : "Cancelled";
  else if (g.status === "live") right = g.status_text || "Live";
  else right = tipoff(g);
  return (
    <div style={{ fontSize: 13, padding: "5px 0", borderTop: "1px solid var(--border-subtle)" }}>
      <div style={{ fontWeight: 600 }}>{team(g.away_team)} @ {team(g.home_team)}</div>
      <div style={{ fontSize: 12 }}>{right}{g.game_type === "cup_final" ? " · NBA Cup final (doesn't count)" : ""}</div>
    </div>
  );
}

export default function Schedule() {
  const [params, setParams] = useSearchParams();
  // The 2025-26 test league shows the 2025-26 NBA schedule.
  const seasons = seasonOf() === TEST_SEASON ? ["2025-26"] : SEASONS;
  const season = seasons.includes(params.get("season")) ? params.get("season") : seasons[0];
  const week = params.get("week");
  const [data, setData] = useState({ key: null, value: undefined });
  const key = `${season}|${week ?? ""}`;

  useEffect(() => {
    let current = true;
    const q = new URLSearchParams({ season, ...(week ? { week } : {}) });
    fetch(`${API}${API_BASE}/schedule?${q}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null)
      .then(v => { if (current) setData({ key, value: v }); });
    return () => { current = false; };
  }, [key, season, week]);

  const d = data.key === key ? data.value : undefined;
  const set = changes => setParams(p => {
    Object.entries(changes).forEach(([k, v]) => (v == null ? p.delete(k) : p.set(k, v)));
    return p;
  }, { replace: true });

  const w = d?.week;
  const idx = w ? d.weeks.findIndex(x => x.week === w.week) : -1;
  const days = [];
  if (w) for (let i = 0; addDays(w.start, i) <= w.end; i++) days.push(addDays(w.start, i));
  const counts = Object.entries(d?.team_counts || {}).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));

  return (
    <FantasyShell title="Schedule" season={SEASON}>
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 14, fontSize: 13 }}>
        {seasons.length > 1 && (
          <select value={season} onChange={e => set({ season: e.target.value, week: null })} style={{ fontSize: 13 }}>
            {seasons.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        )}
        {d?.weeks?.length > 0 && (
          <>
            <button disabled={idx <= 0} onClick={() => set({ week: d.weeks[idx - 1].week })}>&larr;</button>
            <select value={w?.week ?? ""} onChange={e => set({ week: e.target.value })} style={{ fontSize: 13 }}>
              {d.weeks.map(x => <option key={x.week} value={x.week}>{x.label} · {fmtDate(x.start)}–{fmtDate(x.end)}</option>)}
            </select>
            <button disabled={idx >= d.weeks.length - 1} onClick={() => set({ week: d.weeks[idx + 1].week })}>&rarr;</button>
          </>
        )}
      </div>

      {d === undefined && <p style={{ fontSize: 13 }}>Loading…</p>}
      {d === null && <p style={{ fontSize: 13 }}>Couldn't load the schedule.</p>}
      {d && !w && <p style={{ fontSize: 13 }}>No schedule loaded for {season} yet.</p>}

      {w && (
        <>
          <p style={{ fontSize: 13, marginBottom: 12 }}>
            <b>{w.label}</b>, {fmtDate(w.start)} – {fmtDate(w.end)}
            {w.kind === "playoffs" ? " · fantasy playoffs" : ""} · {d.games.filter(g => g.game_type === "regular").length} games.
            Weeks run Monday–Sunday; the All-Star break and the Championship are 2 weeks each.
          </p>

          <div style={heading}>Games per NBA team this week</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 18 }}>
            {counts.map(([t, n]) => (
              <span key={t} style={{ ...card, padding: "4px 8px", fontSize: 13 }}>
                <EntityLink id={t} name={t} /> <b>{n}</b>
              </span>
            ))}
            {counts.length === 0 && <span style={{ fontSize: 13 }}>No games.</span>}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))", gap: 8 }}>
            {days.map(day => {
              const games = d.games.filter(g => g.game_date === day);
              return (
                <div key={day} style={card}>
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>
                    {DAYS[(new Date(`${day}T12:00:00`).getDay() + 6) % 7]} {fmtDate(day)}
                  </div>
                  {games.length === 0 && <div style={{ fontSize: 12 }}>No games</div>}
                  {games.map(g => <Game key={g.game_id} g={g} />)}
                </div>
              );
            })}
          </div>
        </>
      )}
    </FantasyShell>
  );
}
