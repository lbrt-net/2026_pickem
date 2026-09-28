import { useEffect, useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { BASE, SEASON } from "../../components/fantasy/data";
import { API } from "../../utils/helpers";

// Scoring rules + format explanation + calculator. Rules come from GET /scoring and the
// calculator is scored by POST /scoring/preview — the same server code as real games.

const box = { border: "1px solid var(--border)", padding: 14, marginBottom: 14 };
const heading = { fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 8 };
const cell = { padding: "5px 8px", textAlign: "left" };
const num = { ...cell, textAlign: "right" };

// Raw box score inputs for the calculator (misses are derived from made/attempted server-side).
const INPUTS = [
  ["pts", "Points"], ["fgm", "FG made"], ["fga", "FG attempted"], ["fg3m", "3PT made"],
  ["ftm", "FT made"], ["fta", "FT attempted"], ["oreb", "Off reb"], ["dreb", "Def reb"],
  ["ast", "Assists"], ["stl", "Steals"], ["blk", "Blocks"], ["tov", "Turnovers"], ["blkd", "Own shots blocked"],
];

const EXAMPLES = [
  ["Makes a 3-pointer", { pts: 3, fgm: 1, fga: 1, fg3m: 1 }, "3 points + 0.5 for the 3 = 3.5"],
  ["Makes 2 of 3 free throws", { pts: 2, ftm: 2, fta: 3 }, "2 points − 1 for the miss = 1"],
  ["Misses a layup and gets blocked by Wemby", { fga: 1, blkd: 1 }, "−0.5 missed shot − 0.5 blocked = −1"],
];

const fmt = n => (n > 0 ? `+${n}` : `${n}`);

export default function Scoring() {
  const [rules, setRules] = useState(undefined);
  const [line, setLine] = useState({ pts: 28, fgm: 10, fga: 20, fg3m: 3, ftm: 5, fta: 6, oreb: 2, dreb: 7, ast: 6, stl: 2, blk: 1, tov: 3, blkd: 1 });
  const [result, setResult] = useState(null);

  useEffect(() => {
    fetch(`${API}${BASE}/scoring`).then(r => (r.ok ? r.json() : null)).catch(() => null).then(setRules);
  }, []);

  useEffect(() => {
    let current = true;
    fetch(`${API}${BASE}/scoring/preview`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(line),
    }).then(r => (r.ok ? r.json() : null)).catch(() => null).then(v => { if (current) setResult(v); });
    return () => { current = false; };
  }, [line]);

  const label = key => rules?.rules?.find(r => r.key === key)?.label ?? key;

  return (
    <FantasyShell title="Scoring" season={SEASON}>
      <div style={box}>
        <div style={heading}>How a week is scored</div>
        <ol style={{ fontSize: 14, lineHeight: 1.6, paddingLeft: 20 }}>
          <li>Every game a player (or NBA team) plays gets fantasy points from the box score, using the rules below.</li>
          <li>Their score for the week is their <b>single best game</b> that week — not the total, not the average.</li>
          <li>Your team's week is the sum of your 11 roster spots' best games. Higher total wins the matchup.</li>
        </ol>
        <p style={{ fontSize: 14, marginTop: 8 }}>
          Why: in the load-management era, totals mostly reward whoever plays more games, and averages punish an extra bad game.
          A best game rewards ceiling — every game is a free shot at it, and a quiet night costs nothing.
          Weeks run Monday–Sunday; the All-Star break and the Championship are 2 weeks each.
        </p>
      </div>

      <div style={{ display: "flex", gap: 14, flexWrap: "wrap", alignItems: "flex-start" }}>
        <div style={{ ...box, flex: 1, minWidth: 260 }}>
          <div style={heading}>Points per stat</div>
          {rules === undefined && <p style={{ fontSize: 13 }}>Loading…</p>}
          {rules === null && <p style={{ fontSize: 13 }}>Couldn't load the rules.</p>}
          {rules && (
            <table style={{ width: "100%", fontSize: 14, borderCollapse: "collapse" }}>
              <tbody>
                {rules.rules.map(r => (
                  <tr key={r.key} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                    <td style={{ ...cell, fontWeight: 700 }}>{r.label}</td>
                    <td style={cell}>{r.name}{rules.pending?.[r.key] ? ` (${rules.pending[r.key]})` : ""}</td>
                    <td style={{ ...num, fontWeight: 700 }}>{fmt(r.points)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div style={{ ...box, flex: 1, minWidth: 260 }}>
          <div style={heading}>Examples (one play)</div>
          {EXAMPLES.map(([title, , math]) => (
            <div key={title} style={{ fontSize: 14, padding: "6px 0", borderTop: "1px solid var(--border-subtle)" }}>
              <div style={{ fontWeight: 600 }}>{title}</div>
              <div>{math}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={box}>
        <div style={heading}>Calculator — enter a stat line</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))", gap: 8, marginBottom: 12 }}>
          {INPUTS.map(([key, name]) => (
            <label key={key} style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 3 }}>
              {name}
              <input type="number" min={0} value={line[key] ?? 0}
                onChange={e => setLine(l => ({ ...l, [key]: Math.max(0, Number(e.target.value) || 0) }))}
                style={{ fontSize: 14, width: "100%", boxSizing: "border-box" }} />
            </label>
          ))}
        </div>
        {result && (
          <>
            <table style={{ fontSize: 14, borderCollapse: "collapse", marginBottom: 8 }}>
              <tbody>
                {Object.entries(result.breakdown).filter(([, v]) => v !== 0).map(([k, v]) => (
                  <tr key={k}><td style={{ ...cell, fontWeight: 700 }}>{label(k)}</td><td style={num}>{fmt(v)}</td></tr>
                ))}
              </tbody>
            </table>
            <div style={{ fontSize: 20, fontWeight: 700 }}>= {result.fantasy_points} fantasy points</div>
          </>
        )}
      </div>

      <div style={box}>
        <div style={heading}>Coming later</div>
        <p style={{ fontSize: 14 }}>
          Flagrant fouls and ejections (need play-by-play), and an advanced score built on hustle and tracking stats
          (shown alongside the basic score first, not deciding matchups). Details in FANTASY_SCORING.md.
        </p>
      </div>
    </FantasyShell>
  );
}
