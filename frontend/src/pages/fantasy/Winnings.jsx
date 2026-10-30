import { useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { API_BASE, SEASON, useFantasyApi } from "../../components/fantasy/data";
import { TeamLink } from "../../components/fantasy/links";
import { dateRange as range } from "../../components/fantasy/format";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";
import "./Winnings.css";

// Winnings (commissioner, 2026-10-13): who's in the pool, extra money, the pool and its split, who collects when, and
// — collapsed — who would have if everyone had paid in. Numbers from GET /winnings (winnings.py). The commissioner
// marks who's paid and the extras right here.

const $ = v => `$${Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;

const PLACES = ["Champion", "Runner-up", "3rd place"];

function Payouts({ plan, byId }) {
  const plain = { color: "inherit", textDecoration: "none" };
  const name = id => (byId[id] ? <TeamLink ownerId={byId[id].owner_user_id} name={byId[id].name} style={plain} /> : "—");
  const weeks = plan.rows.filter(r => r.kind === "week").length;
  return (
    <table className="wn-table">
      <thead><tr><th className="l">Prize</th><th className="r">Amount</th><th className="l">Collects</th></tr></thead>
      <tbody>
        {plan.rows.map((r, i) => (
          <tr key={i} className={r.kind}>
            <td className="l">{r.kind === "week" ? <>{r.label}<small>{range(r.start, r.end)}</small></> : PLACES[i - weeks] || r.label}</td>
            <td className="r">{$(r.amount)}</td>
            <td className="l">{r.winner
              ? <span className="wn-team"><TeamIcon team={byId[r.winner.team]} size={20} />{name(r.winner.team)}{r.winner.score != null && <small>{r.winner.score.toFixed(1)}</small>}</span>
              : <span className="wn-tbd">{r.status === "final" ? "No paid team" : "TBD"}</span>}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function Winnings() {
  const [scenario] = useFantasyScenario();
  const user = useCurrentUser();
  const fetched = useFantasyApi("winnings");
  const [fresh, setFresh] = useState(null);  // after a commissioner save
  const w = fresh?.scenario === scenario ? fresh.data : fetched;
  const [showWould, setShowWould] = useState(false);
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

  return (
    <FantasyShell title="Winnings" season={SEASON}>
      <div className="wn">
        <section className="wn-card">
          <h3 className="wn-h">In the pool · {paid.length} of {w.teams.length} teams · {$(s.buy_in)} each</h3>
          <ul className="wn-members">
            {w.teams.map(t => (
              <li key={t.id} className={t.paid ? "paid" : ""}>
                <TeamIcon team={t} size={22} /><span className="wn-name"><TeamLink ownerId={t.owner_user_id} name={t.name} style={{ color: "inherit", textDecoration: "none" }} /></span>
                {admin
                  ? <button type="button" className="wn-chip" disabled={busy} onClick={() => togglePaid(t)}>{t.paid ? "Paid" : "Not paid"}</button>
                  : <span className="wn-chip static">{t.paid ? "Paid" : "Not in"}</span>}
              </li>
            ))}
          </ul>
        </section>

        <section className="wn-card">
          <h3 className="wn-h">Extra</h3>
          {w.extras.length === 0 && <p className="wn-note">None.</p>}
          <ul className="wn-members">
            {w.extras.map((x, i) => (
              <li key={i}><span className="wn-name">{x.name}</span><span className="wn-amt">{$(x.amount)}</span>
                {admin && <button type="button" className="wn-chip" disabled={busy} onClick={() => save({ extras: s.extras.filter((_, k) => k !== i) })}>Remove</button>}</li>
            ))}
          </ul>
          {admin && (
            <form className="wn-add" onSubmit={e => { e.preventDefault(); if (extraName.trim() && Number(extraAmt) > 0) { save({ extras: [...s.extras, { name: extraName.trim(), amount: Number(extraAmt) }] }); setExtraName(""); setExtraAmt(""); } }}>
              <input placeholder="Name" value={extraName} onChange={e => setExtraName(e.target.value)} />
              <input placeholder="$" inputMode="decimal" value={extraAmt} onChange={e => setExtraAmt(e.target.value)} />
              <button type="submit" className="wn-chip" disabled={busy}>Add</button>
            </form>
          )}
        </section>

        <section className="wn-card wn-pool">
          <div><span>Total pool</span><b>{$(a.pool)}</b></div>
          <div><span>Regular season · {$(s.weekly)} × {w.regular_weeks} weeks</span><b>{$(a.regular)}</b></div>
          <div><span>Playoffs · {s.split.join(" / ")}</span><b>{$(a.playoff)}</b></div>
        </section>

        <section className="wn-card">
          <h3 className="wn-h">Who collects · top score each week, then the playoffs</h3>
          <Payouts plan={a} byId={byId} />
        </section>

        {/* hidden once everyone's in (full participation, 2026-10-17): it would just repeat the plan above */}
        {w.would.pool > a.pool && <section className="wn-card">
          <button type="button" className="wn-fold" aria-expanded={showWould} onClick={() => setShowWould(o => !o)}>
            If everyone had paid in · {$(w.would.pool)} pool {showWould ? "▾" : "▸"}
          </button>
          {showWould && <Payouts plan={w.would} byId={byId} />}
        </section>}
      </div>
    </FantasyShell>
  );
}
