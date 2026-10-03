import { useCallback, useEffect, useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { BASE, SEASON } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import { API } from "../../utils/helpers";

// Commissioner (admin) settings per league/sandbox: playoff size and rounds, when the fantasy
// season ends, All-Star break fusing, matchup schedule. The server validates against the
// league's real NBA schedule and returns the resulting week layout, shown as a preview.

const SANDBOXES = [
  { value: "live", label: "2026-27 league" },
  { value: "replay", label: "2025-26 test league" },
  { value: "test_pre", label: "Sandbox: pre-draft" },
  { value: "test_post", label: "Sandbox: post-draft" },
];
const SLOT_NAMES = { PLAYER: "Players (any)", TEAM: "NBA teams", G: "Guards", F: "Forwards", C: "Centers", FLEX: "Flex (player or team)" };

// ISO (UTC) → the "YYYY-MM-DDTHH:MM" local value a datetime-local input wants.
const toLocalInput = iso => {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = n => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};
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
  const [roundText, setRoundText] = useState("");

  const adopt = useCallback(d => {
    setData(d);
    setDraft(d ? structuredClone(d.settings) : null);
    setRoundText(d ? d.settings.pick_seconds_by_round.join(", ") : "");
  }, []);

  const load = useCallback(sc => {
    fetch(`${API}${BASE}/league/settings?scenario=${sc}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null)
      .then(adopt);
  }, [adopt]);

  useEffect(() => { if (user?.isAdmin) load(scenario); }, [user, scenario, load]);

  async function save() {
    setStatus("Saving…");
    const r = await fetch(`${API}${BASE}/admin/league/settings?scenario=${scenario}`, {
      method: "PUT", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(draft),
    });
    const body = await r.json();
    if (!r.ok) { setStatus(body.detail || "Couldn't save"); return; }
    adopt(body); setStatus("Saved.");
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
            <div style={heading}>Teams &amp; roster</div>
            <div style={row}>
              <label>Team limit{" "}
                <input type="number" min={2} max={16} value={draft.team_count}
                  onChange={e => set("team_count", Number(e.target.value) || 2)} style={{ width: 64, fontSize: 14 }} />
              </label>
              <span>(2–16; joining closes when the league is full or the draft starts)</span>
            </div>
            <div style={row}>
              <span>Roster spots</span>
              {["PLAYER", "TEAM", "G", "F", "C", "FLEX"].map(k => (
                <label key={k}>
                  {SLOT_NAMES[k]}{" "}
                  <input type="number" min={0} max={10} value={draft.roster_slots[k] || 0}
                    onChange={e => set("roster_slots", { ...draft.roster_slots, [k]: Math.max(0, Number(e.target.value) || 0) })}
                    style={{ width: 52, fontSize: 14 }} />
                </label>
              ))}
            </div>
          </div>

          <div style={box}>
            <div style={heading}>Draft</div>
            <div style={row}>
              <span>Type</span>
              <select value={draft.draft_type} onChange={e => set("draft_type", e.target.value)} style={{ fontSize: 14 }}>
                <option value="snake">Snake (order reverses every round)</option>
                <option value="snake_3rr">Snake with 3rd-round reversal (round 3 repeats round 2's order)</option>
                <option value="linear">Normal (same order every round)</option>
                <option value="auction">Auction (bidding)</option>
              </select>
            </div>
            <div style={row}>
              <label>Pick clock{" "}
                <input type="number" min={10} max={86400} value={draft.pick_seconds}
                  onChange={e => set("pick_seconds", Number(e.target.value) || 10)} style={{ width: 80, fontSize: 14 }} /> seconds
              </label>
              <span>({Math.round(draft.pick_seconds / 60 * 10) / 10} min)</span>
            </div>
            <div style={row}>
              <label>Per-round clocks (optional){" "}
                <input value={roundText} placeholder="e.g. 120, 120, 60"
                  onChange={e => setRoundText(e.target.value)}
                  onBlur={() => set("pick_seconds_by_round", roundText.split(/[,\s]+/).filter(Boolean).map(Number).filter(n => n > 0))}
                  style={{ width: 200, fontSize: 14 }} />
              </label>
              <span>seconds for round 1, 2, …; later rounds use the pick clock</span>
            </div>
            <div style={row}>
              <span>If a pick's clock runs out</span>
              <select value={draft.missed_pick} onChange={e => set("missed_pick", e.target.value)} style={{ fontSize: 14 }}>
                <option value="autopick">Auto-pick the best available player that fits</option>
              </select>
            </div>
            <div style={row}>
              <label>Scheduled start{" "}
                <input type="datetime-local" value={toLocalInput(draft.draft_start_at)}
                  onChange={e => set("draft_start_at", e.target.value ? new Date(e.target.value).toISOString() : null)} style={{ fontSize: 14 }} />
              </label>
              {draft.draft_start_at && <button onClick={() => set("draft_start_at", null)}>Clear</button>}
              <span>(your local time; blank = starts when you press Start in the Draft Room)</span>
            </div>
            {draft.draft_type === "auction" && (
              <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 10 }}>
                <div style={row}>
                  <label>Budget per team <input type="number" min={1} value={draft.auction_budget} onChange={e => set("auction_budget", Number(e.target.value) || 1)} style={{ width: 80, fontSize: 14 }} /></label>
                  <label>Minimum bid <input type="number" min={0} value={draft.auction_min_bid} onChange={e => set("auction_min_bid", Number(e.target.value) || 0)} style={{ width: 64, fontSize: 14 }} /></label>
                </div>
                <div style={row}>
                  <label>Nomination time <input type="number" min={5} max={600} value={draft.nomination_seconds} onChange={e => set("nomination_seconds", Number(e.target.value) || 5)} style={{ width: 64, fontSize: 14 }} /> s</label>
                  <label>Bid clock (resets on each bid) <input type="number" min={3} max={120} value={draft.bid_seconds} onChange={e => set("bid_seconds", Number(e.target.value) || 3)} style={{ width: 64, fontSize: 14 }} /> s</label>
                </div>
                <p style={{ fontSize: 13, color: "var(--accent-gold)" }}>Auction settings save, but the auction draft room itself isn't built yet — Start won't run an auction.</p>
              </div>
            )}
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
