import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { EntityLink } from "./links";
import { BASE } from "./data";
import { API } from "../../utils/helpers";

// Per-game fantasy points for one player or NBA team unit: actual for games
// played, projected for games still on the schedule, rolled up by fantasy week.
const SEASONS = ["2026-27", "2025-26", "2024-25", "2023-24", "2022-23"];
const heading = { fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 8 };
const cell = { padding: "5px 8px", textAlign: "right", whiteSpace: "nowrap" };
const left = { ...cell, textAlign: "left" };
const box = { border: "1px solid var(--border)", padding: 14, marginBottom: 14, overflowX: "auto" };
const fmtDate = iso => new Date(`${iso}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });

export default function GameLog({ entityId }) {
  const [season, setSeason] = useState(SEASONS[0]);
  const [data, setData] = useState({ key: null, value: undefined });
  const key = `${entityId}|${season}`;

  useEffect(() => {
    let current = true;
    fetch(`${API}${BASE}/entity/${encodeURIComponent(entityId)}/games?season=${season}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null)
      .then(v => { if (current) setData({ key, value: v }); });
    return () => { current = false; };
  }, [key, entityId, season]);

  const d = data.key === key ? data.value : undefined;
  const isTeam = d?.kind === "nba_team";
  const weeks = (d?.weeks || []).filter(w => w.games > 0);

  return (
    <>
      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 10, fontSize: 13 }}>
        <span style={{ ...heading, marginBottom: 0 }}>Game log</span>
        <select value={season} onChange={e => setSeason(e.target.value)} style={{ fontSize: 13 }}>
          {SEASONS.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        {d && <span>Projection: {d.projection_per_game ?? "—"} per game ({d.projection_basis})</span>}
      </div>

      {d === undefined && <p style={{ fontSize: 13 }}>Loading…</p>}
      {d === null && <p style={{ fontSize: 13, marginBottom: 14 }}>No games for {season}.</p>}

      {d && (
        <>
          <div style={box}>
            <div style={heading}>By fantasy week</div>
            <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  <th style={left}>Week</th><th style={left}>Dates</th>
                  <th style={cell} title="Games on the schedule this week">Games</th>
                  <th style={cell} title="Games actually played">Played</th>
                  <th style={cell} title="Fantasy points scored">Fantasy Pts</th>
                  <th style={cell} title="Games still to play">Left</th>
                  <th style={cell} title="Fantasy points scored + projection for games left">Projected</th>
                </tr>
              </thead>
              <tbody>
                {weeks.map(w => (
                  <tr key={w.week} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                    <td style={left}><Link to={`${BASE}/schedule?season=${d.season}&week=${w.week}`}>{w.label}</Link></td>
                    <td style={left}>{fmtDate(w.start)}–{fmtDate(w.end)}</td>
                    <td style={cell}>{w.games}</td><td style={cell}>{w.played}</td>
                    <td style={cell}>{w.actual}</td><td style={cell}>{w.remaining}</td>
                    <td style={{ ...cell, fontWeight: 700 }}>{w.projected_total}</td>
                  </tr>
                ))}
                {weeks.length === 0 && <tr><td colSpan={7} style={left}>No games in fantasy weeks.</td></tr>}
              </tbody>
            </table>
          </div>

          <div style={box}>
            <div style={heading}>Every game</div>
            <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  <th style={left}>Date</th><th style={left}>Opponent</th>
                  {isTeam ? <th style={left}>Result</th> : (
                    <>
                      <th style={cell} title="Minutes">MIN</th><th style={cell} title="Points">PTS</th>
                      <th style={cell} title="Rebounds">REB</th><th style={cell} title="Assists">AST</th>
                      <th style={cell} title="Steals">STL</th><th style={cell} title="Blocks">BLK</th>
                      <th style={cell} title="Turnovers">TO</th>
                    </>
                  )}
                  <th style={cell} title="Fantasy points (projected for games not yet played)">Fantasy Pts</th>
                </tr>
              </thead>
              <tbody>
                {d.games.map(g => (
                  <tr key={g.game_id} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                    <td style={left}>{fmtDate(g.date)}</td>
                    <td style={left}>{g.home ? "vs" : "@"} {g.opponent ? <EntityLink id={g.opponent} name={g.opponent} /> : "TBD"}</td>
                    {isTeam ? <td style={left}>{g.result ?? g.dnp ?? "Scheduled"}</td> : g.dnp || g.minutes === undefined ? (
                      <td colSpan={7} style={left}>{g.dnp ?? "Scheduled"}</td>
                    ) : (
                      <>
                        <td style={cell}>{g.minutes}</td><td style={cell}>{g.pts}</td><td style={cell}>{g.reb}</td>
                        <td style={cell}>{g.ast}</td><td style={cell}>{g.stl}</td><td style={cell}>{g.blk}</td><td style={cell}>{g.tov}</td>
                      </>
                    )}
                    <td style={{ ...cell, fontWeight: 700 }}>
                      {g.fantasy_points ?? (g.projected != null ? `proj ${g.projected}` : "—")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {d && isTeam && <p style={{ fontSize: 13, marginBottom: 14 }}>NBA team scoring is a placeholder (50 for a win + point margin) until it's decided.</p>}
      {d?.team && !isTeam && <p style={{ fontSize: 13, marginBottom: 14 }}>Current team: <EntityLink id={d.team} name={d.team} /></p>}
    </>
  );
}
