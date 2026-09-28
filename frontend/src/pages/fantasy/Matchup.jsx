import { useSearchParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { REGULAR_SEASON_WEEKS, SEASON, rosterBySlot, weekPairings, weekScore, useFantasyApi } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";

const tab = active => ({ fontSize: 13, padding: "6px 12px", fontWeight: active ? 700 : 400, borderColor: active ? "var(--text)" : "var(--border)" });
const cell = { padding: "5px 8px" };

// ?week=N&team=<ownerId>&view=leaderboard — all state lives in the URL so other pages can link straight in.
export default function Matchup() {
  const user = useCurrentUser();
  const teams = useFantasyApi("teams");
  const [params, setParams] = useSearchParams();
  const week = Math.min(Math.max(Number(params.get("week")) || 1, 1), REGULAR_SEASON_WEEKS);
  const view = params.get("view") || "matchup";
  const set = changes => setParams(p => { Object.entries(changes).forEach(([k, v]) => p.set(k, v)); return p; }, { replace: true });

  const all = teams || [];
  const pairs = weekPairings(all, week);
  const focus = params.get("team") || user?.discordId;
  const pair = pairs.find(p => p.some(t => t.owner_user_id === focus)) || pairs[0];
  const [a, b] = pair || [];

  const weeklyLeaders = all
    .flatMap(t => t.roster.map(e => ({ ...e, team: t })))
    .sort((x, y) => y.fantasy_points - x.fantasy_points)
    .slice(0, 10);

  return (
    <FantasyShell title="Matchup" season={SEASON}>
      <div style={{ display: "flex", gap: 10, marginBottom: 10, flexWrap: "wrap" }}>
        <select value={week} onChange={e => set({ week: e.target.value })} style={{ fontSize: 13 }}>
          {Array.from({ length: REGULAR_SEASON_WEEKS }, (_, i) => i + 1).map(w => <option key={w} value={w}>Week {w}</option>)}
        </select>
        <select value={a?.owner_user_id ?? ""} onChange={e => set({ team: e.target.value })} style={{ fontSize: 13 }}>
          {pairs.map(([x, y]) => <option key={x.id} value={x.owner_user_id}>{x.name} vs {y.name}</option>)}
        </select>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
        <button onClick={() => set({ view: "matchup" })} style={tab(view === "matchup")}>Matchup View</button>
        <button onClick={() => set({ view: "leaderboard" })} style={tab(view === "leaderboard")}>Weekly Leaderboard (top scorer wins a prize)</button>
      </div>

      {teams === undefined && <p style={{ fontSize: 13 }}>Loading…</p>}
      {teams && !pair && <p style={{ fontSize: 13 }}>Need at least two teams for a matchup.</p>}

      {pair && (
        <div style={{ border: "1px solid var(--border)", padding: 14, marginBottom: 14 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700, fontSize: 15 }}>
            <TeamLink ownerId={a.owner_user_id} name={a.name} /><span>Week {week}</span><TeamLink ownerId={b.owner_user_id} name={b.name} />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 28, fontWeight: 700 }}>
            <span>{weekScore(a)}</span>
            <span style={{ fontSize: 12, alignSelf: "center" }}>projected from per-game averages</span>
            <span>{weekScore(b)}</span>
          </div>
        </div>
      )}

      {pair && view === "matchup" && (
        <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.04em", borderBottom: "1px solid var(--border)" }}>
              <th style={{ ...cell, textAlign: "left" }}>{a.name}</th><th style={{ ...cell, textAlign: "right" }}>Pts</th>
              <th style={cell}>Slot</th>
              <th style={{ ...cell, textAlign: "left" }}>Pts</th><th style={{ ...cell, textAlign: "right" }}>{b.name}</th>
            </tr>
          </thead>
          <tbody>
            {(() => {
              const left = rosterBySlot(a.roster), right = rosterBySlot(b.roster);
              return left.map(({ slot, entry }, i) => {
                const opp = right[i].entry;
                return (
                  <tr key={i} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                    <td style={cell}>{entry ? <EntityLink id={entry.id} name={entry.name} /> : "Empty"}</td>
                    <td style={{ ...cell, textAlign: "right" }}>{entry?.fantasy_points ?? 0}</td>
                    <td style={{ ...cell, textAlign: "center", fontWeight: 700 }}>{slot}</td>
                    <td style={cell}>{opp?.fantasy_points ?? 0}</td>
                    <td style={{ ...cell, textAlign: "right" }}>{opp ? <EntityLink id={opp.id} name={opp.name} /> : "Empty"}</td>
                  </tr>
                );
              });
            })()}
          </tbody>
        </table>
      )}

      {teams && view === "leaderboard" && (
        <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.04em", borderBottom: "1px solid var(--border)" }}>
              <th style={{ ...cell, textAlign: "left" }}>#</th><th style={{ ...cell, textAlign: "left" }}>Player</th>
              <th style={{ ...cell, textAlign: "left" }}>Fantasy Team</th><th style={{ ...cell, textAlign: "right" }}>Pts</th>
            </tr>
          </thead>
          <tbody>
            {weeklyLeaders.map((e, i) => (
              <tr key={e.id} style={{ borderTop: "1px solid var(--border-subtle)", fontWeight: i === 0 ? 700 : 400 }}>
                <td style={cell}>{i + 1}{i === 0 ? " (prize)" : ""}</td>
                <td style={cell}><EntityLink id={e.id} name={e.name} /></td>
                <td style={cell}><TeamLink ownerId={e.team.owner_user_id} name={e.team.name} /></td>
                <td style={{ ...cell, textAlign: "right" }}>{e.fantasy_points}</td>
              </tr>
            ))}
            {weeklyLeaders.length === 0 && <tr><td colSpan={4} style={cell}>Nobody's rostered yet.</td></tr>}
          </tbody>
        </table>
      )}
    </FantasyShell>
  );
}
