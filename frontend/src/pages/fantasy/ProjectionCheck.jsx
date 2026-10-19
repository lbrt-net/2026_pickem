import { useEffect, useMemo, useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { EntityLink } from "../../components/fantasy/links";
import { API_BASE, SEASON } from "../../components/fantasy/data";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";

// Projection check (2026-10-19): every player's weekly projection and 1+ Game %, saved on the server before the
// week's first game (projection_log.py, the 3 AM job), next to what actually happened once the week is over.
const cell = { padding: "6px 8px", textAlign: "right", whiteSpace: "nowrap" };
const left = { ...cell, textAlign: "left" };
const f1 = v => (v == null ? "" : v.toFixed(1));
const pct = v => (v == null ? "" : `${Math.round(v * 100)}%`);

export default function ProjectionCheck() {
  const [scenario] = useFantasyScenario();
  const [week, setWeek] = useState(null);
  const [who, setWho] = useState("rostered");
  const [data, setData] = useState(undefined);
  useEffect(() => {
    let on = true;
    fetch(`${API}${API_BASE}/projection-check?scenario=${scenario}${week ? `&week=${week}` : ""}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null).then(d => { if (on) setData(d); });
    return () => { on = false; };
  }, [scenario, week]);

  const rows = useMemo(() => (data?.rows || []).filter(r => (who === "all" ? true : who === "rostered" ? r.team_id : !r.team_id)),
    [data, who]);
  const s = data?.summary;

  return (
    <FantasyShell title="Projection Check" season={SEASON}>
      <p style={{ fontSize: 13, marginBottom: 10 }}>
        Each player's projection for the week, saved before its first game, and what he actually did.
      </p>
      {data === undefined ? <p style={{ fontSize: 13 }}>Loading…</p> : !data?.weeks?.length ? <p style={{ fontSize: 13 }}>Nothing saved yet.</p> : (
        <>
          <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 14, fontSize: 13, flexWrap: "wrap" }}>
            <span>Week</span>
            <select value={data.week} onChange={e => setWeek(Number(e.target.value))} style={{ fontSize: 13 }}>
              {data.weeks.map(w => <option key={w} value={w}>{w}</option>)}
            </select>
            <select value={who} onChange={e => setWho(e.target.value)} style={{ fontSize: 13 }}>
              <option value="rostered">On a team</option>
              <option value="free">Free agents</option>
              <option value="all">Everyone</option>
            </select>
          </div>
          {s ? (
            <table style={{ fontSize: 13, borderCollapse: "collapse", marginBottom: 18 }}>
              <tbody>
                <tr><td style={left}>Players checked</td><td style={cell}>{s.n}</td></tr>
                <tr><td style={left}>Average miss (actual − projected)</td><td style={cell}>{f1(s.avg_miss)}</td></tr>
                <tr><td style={left}>Typical miss, either way</td><td style={cell}>{f1(s.avg_abs_miss)}</td></tr>
                <tr><td style={left}>How wide misses ran (standard deviation)</td><td style={cell}>{f1(s.miss_spread)}</td></tr>
                <tr><td style={left}>How wide the projections said they would run</td><td style={cell}>{f1(s.said_spread)}</td></tr>
                {s.play_bins.map(b => (
                  <tr key={b.from}><td style={left}>1+ Game % {Math.round(b.from * 100)}–{Math.round(b.to * 100)}% ({b.n} players)</td>
                    <td style={cell}>said {pct(b.said)} · played {pct(b.played)}</td></tr>
                ))}
              </tbody>
            </table>
          ) : <p style={{ fontSize: 13, marginBottom: 14 }}>Results fill in once the week is over.</p>}
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.04em", borderBottom: "1px solid var(--border)" }}>
                  <th style={left}>Player</th><th style={left}>Team</th><th style={cell}>Games</th><th style={cell}>Projected</th>
                  <th style={cell}>1+ Game %</th><th style={cell}>Actual</th><th style={cell}>Played</th><th style={cell}>Miss</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(r => (
                  <tr key={r.entity_id} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                    <td style={left}><EntityLink id={r.entity_id} name={r.name} /></td>
                    <td style={left}>{r.team_name || "Free agent"}</td>
                    <td style={cell}>{r.games}</td>
                    <td style={cell}><i>{f1(r.projected)}</i></td>
                    <td style={cell}>{pct(r.play_prob)}</td>
                    <td style={cell}>{r.filled_at ? (r.actual == null ? "—" : f1(r.actual)) : ""}</td>
                    <td style={cell}>{r.filled_at ? r.actual_games : ""}</td>
                    <td style={cell}>{r.filled_at && r.projected != null ? f1((r.actual || 0) - r.projected) : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </FantasyShell>
  );
}
