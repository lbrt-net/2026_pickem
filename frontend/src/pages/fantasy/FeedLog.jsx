import { useEffect, useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { SEASON } from "../../components/fantasy/data";
import { API } from "../../utils/helpers";

// Feed Log (commissioner, 2026-10-22): can our server reach the NBA's live feed? Every 10 minutes it tries the main
// feed (cdn.nba.com) and the NBA's storage copy (backup); every live pull records which one answered. Kept 60 days —
// the record for moving to our own box.
const cell = { padding: "5px 8px", textAlign: "left", whiteSpace: "nowrap" };
const when = iso => new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", second: "2-digit" });

export default function FeedLog() {
  const [d, setD] = useState(undefined);
  useEffect(() => {
    let on = true;
    const go = () => fetch(`${API}/nba/admin/feed-log?limit=400`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null).then(x => { if (on) setD(x); });
    go();
    const t = setInterval(go, 60000);
    return () => { on = false; clearInterval(t); };
  }, []);
  const day = d?.last_24h || {};
  const rate = s => (day[s]?.checks ? `${Math.round((day[s].ok / day[s].checks) * 100)}% of ${day[s].checks} worked${day[s].avg_ms ? ` · ${day[s].avg_ms} ms` : ""}` : "no checks yet");
  return (
    <FantasyShell title="Feed Log" season={SEASON}>
      <p style={{ fontSize: 13, marginBottom: 10 }}>Whether our server can reach the NBA's live feed. Checked every 10 minutes, and on every live pull.</p>
      {d === undefined ? <p style={{ fontSize: 13 }}>Loading…</p> : !d ? <p style={{ fontSize: 13 }}>Commissioner only.</p> : (
        <>
          <table style={{ fontSize: 13, borderCollapse: "collapse", marginBottom: 16 }}>
            <tbody>
              <tr><td style={cell}>Main feed (cdn.nba.com), last 24 h</td><td style={cell}><b>{rate("cdn")}</b></td></tr>
              <tr><td style={cell}>Backup (NBA storage copy), last 24 h</td><td style={cell}><b>{rate("backup")}</b></td></tr>
            </tbody>
          </table>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.04em", borderBottom: "1px solid var(--border)" }}>
                  <th style={cell}>When</th><th style={cell}>Check</th><th style={cell}>Source</th><th style={cell}>Result</th><th style={cell}>Time</th><th style={cell}>Error</th>
                </tr>
              </thead>
              <tbody>
                {d.rows.map((r, i) => (
                  <tr key={i} style={{ borderTop: "1px solid var(--border-subtle)", boxShadow: r.status === 200 ? undefined : "inset 3px 0 0 var(--accent-red)" }}>
                    <td style={cell}>{when(r.at)}</td>
                    <td style={cell}>{r.kind === "probe" ? "10-minute check" : "live pull"}</td>
                    <td style={cell}>{r.source === "cdn" ? "Main feed" : "Backup"}</td>
                    <td style={cell}>{r.status === 200 ? "OK" : r.status ? `Refused (${r.status})` : "No answer"}</td>
                    <td style={cell}>{r.ms != null ? `${r.ms} ms` : ""}</td>
                    <td style={{ ...cell, whiteSpace: "normal" }}>{r.error || ""}</td>
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
