import { useCallback, useEffect, useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { BASE, SEASON } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import { API } from "../../utils/helpers";

// Commissioner (admin) settings per league/sandbox: playoff size and rounds, when the fantasy
// season ends, All-Star break fusing, matchup schedule. The server validates against the
// league's real NBA schedule and returns the resulting week layout, shown as a preview.

const SANDBOXES = [
  { value: "live", label: "Live league" },
  { value: "replay", label: "Replay 2025-26" },
  { value: "test_pre", label: "Test: pre-draft" },
  { value: "test_post", label: "Test: post-draft" },
];
const box = { border: "1px solid var(--border)", padding: 14, marginBottom: 14 };
const heading = { fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 8 };
const row = { display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", fontSize: 14, marginBottom: 10 };
const fmt = iso => new Date(`${iso}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });

export default function LeagueSettings() {
  const user = useCurrentUser();
  const [scenario, setScenario] = useState("live");
  const [data, setData] = useState(undefined);
  const [draft, setDraft] = useState(null);
  const [status, setStatus] = useState(null);

  const load = useCallback(sc => {
    fetch(`${API}${BASE}/league/settings?scenario=${sc}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null)
      .then(d => { setData(d); setDraft(d ? structuredClone(d.settings) : null); });
  }, []);

  useEffect(() => { if (user?.isAdmin) load(scenario); }, [user, scenario, load]);

  async function save() {
    setStatus("Saving…");
    const r = await fetch(`${API}${BASE}/admin/league/settings?scenario=${scenario}`, {
      method: "PUT", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(draft),
    });
    const body = await r.json();
    if (!r.ok) { setStatus(body.detail || "Couldn't save"); return; }
    setData(body); setDraft(structuredClone(body.settings)); setStatus("Saved.");
  }

  if (user === undefined) return <FantasyShell title="League settings" season={SEASON}><p style={{ fontSize: 13 }}>Checking…</p></FantasyShell>;
  if (!user?.isAdmin) return <FantasyShell title="League settings" season={SEASON}><p style={{ fontSize: 13 }}>Commissioner only.</p></FantasyShell>;

  const set = (k, v) => setDraft(d => ({ ...d, [k]: v }));
  const setRound = (i, k, v) => setDraft(d => ({ ...d, playoff_rounds: d.playoff_rounds.map((r, j) => (j === i ? { ...r, [k]: v } : r)) }));
  const byes = draft ? 2 ** draft.playoff_rounds.length - draft.playoff_teams : 0;

  return (
    <FantasyShell title="League settings" season={SEASON}>
      <div style={row}>
        <span>League</span>
        <select value={scenario} onChange={e => { setStatus(null); setScenario(e.target.value); }} style={{ fontSize: 14 }}>
          {SANDBOXES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
        {data && <span>NBA season {data.season}</span>}
      </div>

      {data === undefined && <p style={{ fontSize: 13 }}>Loading…</p>}
      {data === null && <p style={{ fontSize: 13 }}>Couldn't load settings.</p>}

      {draft && (
        <>
          <div style={box}>
            <div style={heading}>Playoffs</div>
            <div style={row}>
              <label>Teams in the playoffs{" "}
                <input type="number" min={2} max={32} value={draft.playoff_teams}
                  onChange={e => set("playoff_teams", Number(e.target.value) || 2)} style={{ width: 64, fontSize: 14 }} />
              </label>
              <span>{byes > 0 ? `Top ${byes} seed${byes > 1 ? "s" : ""} get a first-round bye` : "No byes"}</span>
            </div>
            {draft.playoff_rounds.map((r, i) => (
              <div key={i} style={row}>
                <span style={{ width: 60 }}>Round {i + 1}</span>
                <input value={r.name} onChange={e => setRound(i, "name", e.target.value)} style={{ fontSize: 14, width: 170 }} />
                <label>
                  <input type="number" min={1} max={4} value={r.weeks}
                    onChange={e => setRound(i, "weeks", Number(e.target.value) || 1)} style={{ width: 52, fontSize: 14 }} />{" "}
                  week{r.weeks > 1 ? "s" : ""}
                </label>
                {draft.playoff_rounds.length > 1 && (
                  <button onClick={() => set("playoff_rounds", draft.playoff_rounds.filter((_, j) => j !== i))}>Remove</button>
                )}
              </div>
            ))}
            <button onClick={() => set("playoff_rounds", [{ name: "Round", weeks: 1 }, ...draft.playoff_rounds])}>+ Add an earlier round</button>
          </div>

          <div style={box}>
            <div style={heading}>Season</div>
            <div style={row}>
              <label>End the fantasy season{" "}
                <input type="number" min={0} max={60} value={draft.cutoff_days}
                  onChange={e => set("cutoff_days", Math.max(0, Number(e.target.value) || 0))} style={{ width: 64, fontSize: 14 }} />{" "}
                days before the NBA's last regular-season game
              </label>
              <span>(0 = play through the NBA's last week)</span>
            </div>
            <label style={row}>
              <input type="checkbox" checked={draft.fuse_all_star} onChange={e => set("fuse_all_star", e.target.checked)} />
              Fuse the All-Star break and the week after it into one 2-week period
            </label>
            <div style={row}>
              <span>Regular-season matchups</span>
              <select value={draft.matchup_schedule} onChange={e => set("matchup_schedule", e.target.value)} style={{ fontSize: 14 }}>
                <option value="round_robin">Round robin (everyone plays everyone, repeating)</option>
              </select>
            </div>
          </div>

          <div style={row}>
            <button onClick={save}>Save settings</button>
            <button onClick={() => { setDraft(structuredClone(data.defaults)); setStatus("Defaults loaded — Save to apply."); }}>Load defaults</button>
            {status && <span>{status}</span>}
          </div>

          <div style={box}>
            <div style={heading}>Week layout (saved settings)</div>
            <table style={{ fontSize: 14, borderCollapse: "collapse" }}>
              <tbody>
                {data.weeks.map(w => (
                  <tr key={w.week} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                    <td style={{ padding: "4px 10px 4px 0", fontWeight: w.kind === "playoffs" ? 700 : 400 }}>{w.label}</td>
                    <td style={{ padding: "4px 0" }}>{fmt(w.start)} – {fmt(w.end)}</td>
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
