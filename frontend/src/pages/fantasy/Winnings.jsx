import { useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { API_BASE, SEASON, useFantasyApi } from "../../components/fantasy/data";
import { TeamLink } from "../../components/fantasy/links";
import { dateRange as range } from "../../components/fantasy/format";
import { textOnColor } from "../../components/fantasy/teamColors";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";
import "./Winnings.css";

// Winnings (redone 2026-11-25): the pot as a bar of every prize (won ones in the winner's color), a tracker of what each
// team has won against its buy-in, the week-by-week prizes as tiles, then the playoff prizes. Numbers from GET /winnings
// (winnings.py). The commissioner marks who's in and the extras in a Commissioner panel at the bottom.

const $ = v => `$${Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
// net is a difference, so it keeps its sign
const net = v => (v > 0 ? `+$${v}` : v < 0 ? `−$${-v}` : "$0");
const PLACES = ["Champion", "Runner-up", "3rd place"];
const plain = { color: "inherit", textDecoration: "none" };

const SHIELD = (
  <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
    <path d="M9 1.8 3 4.2v4.3c0 3.7 2.6 6.7 6 7.7 3.4-1 6-4 6-7.7V4.2z" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinejoin="round" />
    <path d="M6.3 9.1 8.2 11l3.6-3.8" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

// the whole pot, one block per prize sized by its dollars: won = the winner's color, this week = lit edge
function PotBar({ rows, byId, pool }) {
  return (
    <div className="wn-pot" role="img" aria-label="Prize pool">
      {rows.map((r, i) => {
        const t = r.winner && byId[r.winner.team];
        return (
          <span key={i} className={`wn-seg ${r.kind} ${r.status}${t ? " won" : ""}`}
            style={{ flexGrow: r.amount / pool, ...(t ? { "--tc": t.color } : {}) }}
            title={`${r.kind === "week" ? r.label : PLACES[i - rows.filter(x => x.kind === "week").length]} · ${$(r.amount)}${t ? ` · ${t.name}` : ""}`} />
        );
      })}
    </div>
  );
}

function Tracker({ teams, rows, buyIn }) {
  const wins = {};
  rows.forEach(r => { if (r.winner) (wins[r.winner.team] ||= []).push(r); });
  const list = teams.map(t => {
    const won = (wins[t.id] || []).reduce((s, r) => s + r.amount, 0);
    return { t, won, n: t.paid ? won - buyIn : null, rows: wins[t.id] || [] };
  }).sort((a, b) => b.won - a.won || a.t.name.localeCompare(b.t.name));
  const top = Math.max(buyIn, ...list.map(x => x.won));
  return (
    <table className="wn-track">
      <thead><tr><th className="l">Team</th><th className="l wn-bar-h" aria-label="Won so far" /><th className="r">Won</th><th className="r">Net</th></tr></thead>
      <tbody>
        {list.map(({ t, won, n, rows: rs }) => (
          <tr key={t.id} style={{ "--tc": t.color, "--ti": textOnColor(t.color) }}>
            <td className="l">
              <span className="wn-who">
                <span className="wn-rk">{won > 0 ? 1 + list.filter(x => x.won > won).length : ""}</span>
                <TeamIcon team={t} size={30} />
                <span className="wn-nm"><b><TeamLink ownerId={t.owner_user_id} name={t.name} style={plain} /></b><small>{t.owner_name}{!t.paid ? " · not in" : ""}</small></span>
              </span>
            </td>
            <td className="l wn-bar-c">
              <span className="wn-bar">
                <span className="wn-fill" style={{ width: `${(won / top) * 100}%` }}>
                  {rs.map((r, k) => <span key={k} className="wn-chunk" style={{ flexGrow: r.amount }} title={r.label}>{r.kind === "week" ? r.week : ""}</span>)}
                </span>
                <span className="wn-even" style={{ left: `${(buyIn / top) * 100}%` }} />
              </span>
            </td>
            <td className="r wn-won">{$(won)}</td>
            <td className={`r wn-net${n > 0 ? " up" : ""}`}>{n == null ? "" : net(n)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Weeks({ rows, byId }) {
  return (
    <div className="wn-weeks">
      {rows.filter(r => r.kind === "week").map(r => {
        const t = r.winner && byId[r.winner.team];
        return (
          <div key={r.week} className={`wn-wk ${r.status}${t ? " won" : ""}`} style={t ? { "--tc": t.color, "--ti": textOnColor(t.color) } : undefined}>
            <div className="wn-wk-top"><b>Wk {r.week}</b><span className="wn-wk-amt">{$(r.amount)}</span></div>
            <span className="wn-wk-dt">{range(r.start, r.end)}</span>
            {t
              ? <div className="wn-wk-win"><TeamIcon team={t} size={24} /><span className="wn-wk-nm">{t.name}<small>{r.winner.score.toFixed(1)}</small></span></div>
              : <div className="wn-wk-win open">{r.status === "in_progress" ? "This week" : r.status === "final" ? "No paid team" : ""}</div>}
          </div>
        );
      })}
    </div>
  );
}

function Podium({ rows, byId }) {
  const po = rows.filter(r => r.kind === "playoff");
  return (
    <div className="wn-podium">
      {po.map((r, i) => {
        const t = r.winner && byId[r.winner.team];
        return (
          <div key={i} className={`wn-pl p${i + 1}${t ? " won" : ""}`} style={t ? { "--tc": t.color } : undefined}>
            <span className="wn-pl-place">{PLACES[i] || r.label}</span>
            <b className="wn-pl-amt">{$(r.amount)}</b>
            {t ? <span className="wn-pl-team"><TeamIcon team={t} size={22} />{t.name}</span> : <span className="wn-pl-team open">Playoffs</span>}
          </div>
        );
      })}
    </div>
  );
}

export default function Winnings() {
  const [scenario] = useFantasyScenario();
  const user = useCurrentUser();
  const fetched = useFantasyApi("winnings");
  const [fresh, setFresh] = useState(null);  // after a commissioner save
  const w = fresh?.scenario === scenario ? fresh.data : fetched;
  const [busy, setBusy] = useState(false);
  const [extraName, setExtraName] = useState(""), [extraAmt, setExtraAmt] = useState("");
  const admin = !!user?.isAdmin;

  async function save(changes) {
    setBusy(true);
    try {
      await fetch(`${API}${API_BASE}/admin/finance?scenario=${scenario}`, {
        method: "PUT", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(changes),
      });
      const r = await fetch(`${API}${API_BASE}/winnings?scenario=${scenario}`, { credentials: "include" });
      if (r.ok) setFresh({ scenario, data: await r.json() });
    } finally { setBusy(false); }
  }

  if (w === undefined) return <FantasyShell title="Winnings" season={SEASON}><p className="wn-note">Loading…</p></FantasyShell>;
  if (!w) return <FantasyShell title="Winnings" season={SEASON}><p className="wn-note">Couldn't load the prize pool.</p></FantasyShell>;
  const s = w.settings, a = w.actual;
  const byId = Object.fromEntries(w.teams.map(t => [t.id, t]));
  const paid = w.teams.filter(t => t.paid);
  const togglePaid = t => save({ paid: t.paid ? s.paid.filter(x => x !== t.owner_user_id) : [...s.paid, t.owner_user_id] });
  const won = a.rows.filter(r => r.winner).reduce((x, r) => x + r.amount, 0);
  const weeksDone = a.rows.filter(r => r.kind === "week" && r.status === "final").length;

  return (
    <FantasyShell title="Winnings" season={SEASON}>
      <div className="wn">
        <section className="wn-hero">
          <div className="wn-hero-nums">
            <div className="wn-big"><span>Pot</span><b>{$(a.pool)}</b></div>
            <div className="wn-big"><span>Won</span><b>{$(won)}</b></div>
            <div className="wn-big"><span>Left</span><b>{$(a.pool - won)}</b></div>
            <div className="wn-hero-meta">
              <span>{paid.length} teams × {$(s.buy_in)}{w.extras.length ? ` + ${$(w.extras.reduce((x, e) => x + e.amount, 0))} extra` : ""}</span>
              <span>{$(s.weekly)} a week · {weeksDone} of {w.regular_weeks} weeks</span>
              <span>Playoffs {s.split.join(" / ")}</span>
            </div>
          </div>
          <PotBar rows={a.rows} byId={byId} pool={a.pool} />
        </section>

        <section className="wn-card">
          <h3 className="wn-h">Tracker</h3>
          <div className="wn-scroll"><Tracker teams={w.teams} rows={a.rows} buyIn={s.buy_in} /></div>
        </section>

        <section className="wn-card">
          <h3 className="wn-h">Top score each week</h3>
          <Weeks rows={a.rows} byId={byId} />
        </section>

        <section className="wn-card">
          <h3 className="wn-h">Playoffs</h3>
          <Podium rows={a.rows} byId={byId} />
        </section>

        {admin && (
          <section className="wn-commish" aria-label="Commissioner">
            <span className="wn-commish-h">{SHIELD}Commissioner</span>
            <ul className="wn-members">
              {w.teams.map(t => (
                <li key={t.id}>
                  <TeamIcon team={t} size={20} /><span className="wn-name">{t.name}</span>
                  <button type="button" className={`wn-chip${t.paid ? " on" : ""}`} disabled={busy} onClick={() => togglePaid(t)}>{t.paid ? "Paid" : "Not paid"}</button>
                </li>
              ))}
            </ul>
            <div className="wn-extras">
              {w.extras.map((x, i) => (
                <span key={i} className="wn-extra">{x.name} {$(x.amount)}
                  <button type="button" className="wn-chip" disabled={busy} onClick={() => save({ extras: s.extras.filter((_, k) => k !== i) })}>Remove</button></span>
              ))}
              <form className="wn-add" onSubmit={e => { e.preventDefault(); if (extraName.trim() && Number(extraAmt) > 0) { save({ extras: [...s.extras, { name: extraName.trim(), amount: Number(extraAmt) }] }); setExtraName(""); setExtraAmt(""); } }}>
                <input placeholder="Extra money from" value={extraName} onChange={e => setExtraName(e.target.value)} />
                <input placeholder="$" inputMode="decimal" value={extraAmt} onChange={e => setExtraAmt(e.target.value)} />
                <button type="submit" className="wn-chip" disabled={busy}>Add</button>
              </form>
            </div>
          </section>
        )}
      </div>
    </FantasyShell>
  );
}
