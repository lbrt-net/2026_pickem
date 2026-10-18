import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { EntityLink } from "../../components/fantasy/links";
import { API_BASE, SEASON } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";
import "./Trades.css";

// Trades (2026-10-17; backend trades.py): the only way players move between two teams. Propose → the other team
// accepts (with any drops it needs) or declines → the commissioner approves. Both rosters must end up legal at every
// step (the server checks). Everyone sees every trade.

const STATUS = { proposed: "Waiting for their answer", accepted: "Waiting for the commissioner", approved: "Done",
  declined: "Declined", cancelled: "Cancelled", rejected: "Rejected by the commissioner" };

function useJson(path, scenario, version) {
  const [data, setData] = useState(undefined);
  useEffect(() => {
    let live = true;
    fetch(`${API}${API_BASE}/${path}?scenario=${scenario}`, { credentials: "include" })
      .then(r => (r.ok ? r.json() : null)).catch(() => null)
      .then(d => { if (live) setData(d); });
    return () => { live = false; };
  }, [path, scenario, version]);
  return data;
}

function Pick({ roster, chosen, onToggle, disabled = [] }) {
  if (!roster?.length) return <p className="tr-empty">No players.</p>;
  return (
    <div className="tr-pick">
      {roster.map(e => (
        <label key={e.id} className={`tr-opt${chosen.includes(e.id) ? " on" : ""}${disabled.includes(e.id) ? " off" : ""}`}>
          <input type="checkbox" checked={chosen.includes(e.id)} disabled={disabled.includes(e.id)} onChange={() => onToggle(e.id)} />
          <span className="tr-pos">{e.kind === "nba_team" ? "TM" : e.position}</span>
          <EntityLink id={e.id} name={e.name} />
        </label>
      ))}
    </div>
  );
}

function Names({ list }) {
  if (!list?.length) return <span>nobody</span>;
  return list.map((e, i) => <span key={e.id}>{i ? ", " : ""}<EntityLink id={e.id} name={e.name} /></span>);
}

function TradeCard({ t, children }) {
  return (
    <div className="tr-card">
      <div className="tr-sides">
        <div><span className="tr-team"><TeamIcon team={t.from} size={20} /><b>{t.from?.name}</b> gives</span><Names list={t.give} /></div>
        <div><span className="tr-team"><TeamIcon team={t.to} size={20} /><b>{t.to?.name}</b> gives</span><Names list={t.get} /></div>
      </div>
      {(t.from_drops.length > 0 || t.to_drops.length > 0) && (
        <div className="tr-drops">
          {t.from_drops.length > 0 && <span>{t.from?.name} drops <Names list={t.from_drops} /></span>}
          {t.to_drops.length > 0 && <span>{t.to?.name} drops <Names list={t.to_drops} /></span>}
        </div>
      )}
      <div className="tr-foot"><span className="tr-status">{STATUS[t.status] || t.status}</span>{children}</div>
    </div>
  );
}

export default function Trades() {
  const user = useCurrentUser();
  const [scenario] = useFantasyScenario();
  const [version, setVersion] = useState(0);
  const teams = useJson("teams", scenario, version);
  const list = useJson("trades", scenario, version);
  const [params] = useSearchParams();
  const all = useMemo(() => teams || [], [teams]);
  const mine = user ? all.find(t => t.owner_user_id === user.discordId) : null;
  const [partnerId, setPartnerId] = useState(params.get("with") || "");
  const partner = all.find(t => (t.owner_user_id === partnerId || t.id === partnerId) && t !== mine);
  const [give, setGive] = useState([]);
  const [get, setGet] = useState([]);
  const [drops, setDrops] = useState([]);
  const [legal, setLegal] = useState(null);
  const [answerDrops, setAnswerDrops] = useState({});
  const [msg, setMsg] = useState(null);
  const toggle = setter => id => setter(xs => (xs.includes(id) ? xs.filter(x => x !== id) : [...xs, id]));

  const post = useCallback(async (path, body) => {
    setMsg(null);
    const r = await fetch(`${API}${API_BASE}/${path}?scenario=${scenario}`, {
      method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}),
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) { setMsg({ error: true, text: d.detail || "That didn't work." }); return null; }
    return d;
  }, [scenario]);

  // live check of the offer being built: is my roster legal after it? (kept with the offer it was for)
  const offer = mine && partner && (give.length || get.length)
    ? JSON.stringify({ from_team: mine.id, to_team: partner.id, give, get, from_drops: drops }) : null;
  useEffect(() => {
    if (!offer) return undefined;
    let live = true;
    fetch(`${API}${API_BASE}/trades/check?scenario=${scenario}`, {
      method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: offer,
    }).then(r => (r.ok ? r.json() : null)).then(d => { if (live) setLegal({ offer, d }); });
    return () => { live = false; };
  }, [offer, scenario]);
  const legalNow = legal && legal.offer === offer ? legal.d : null;

  const send = async () => {
    const d = await post("trades", { from_team: mine.id, to_team: partner.id, give, get, drops });
    if (d) { setGive([]); setGet([]); setDrops([]); setMsg({ text: "Offer sent." }); setVersion(v => v + 1); }
  };
  const act = async (t, action, body) => {
    const d = await post(`trades/${t.id}/${action}`, body);
    if (d) setVersion(v => v + 1);
  };

  const trades = list?.trades || [];
  const incoming = trades.filter(t => t.status === "proposed" && mine && t.to?.id === mine.id);
  const outgoing = trades.filter(t => ["proposed", "accepted"].includes(t.status) && mine && t.from?.id === mine.id);
  const waiting = trades.filter(t => t.status === "accepted");
  const rest = trades.filter(t => !incoming.includes(t) && !outgoing.includes(t) && !waiting.includes(t));

  return (
    <FantasyShell title="Trades" season={SEASON}>
      <div className="tr">
        {msg && <div className={`tr-msg${msg.error ? " error" : ""}`} role="status">{msg.text}</div>}

        {mine && (
          <section className="tr-panel">
            <h2 className="tr-h">Make an offer</h2>
            <div className="tr-partners">
              {all.filter(t => t !== mine).map(t => (
                <button key={t.id} type="button" className={`tr-chip${partner === t ? " on" : ""}`}
                  onClick={() => { setPartnerId(t.id); setGet([]); }}><TeamIcon team={t} size={18} />{t.name}</button>
              ))}
            </div>
            {partner && (
              <>
                <div className="tr-two">
                  <div><h3 className="tr-sub">You give</h3><Pick roster={mine.roster} chosen={give} onToggle={toggle(setGive)} disabled={drops} /></div>
                  <div><h3 className="tr-sub">You get from {partner.name}</h3><Pick roster={partner.roster} chosen={get} onToggle={toggle(setGet)} /></div>
                </div>
                <details className="tr-dropbox" open={drops.length > 0 || (legalNow && !legalNow.from.ok)}>
                  <summary className="tr-sub">Drop to make room (only if you need to){drops.length ? ` · ${drops.length} picked` : ""}</summary>
                  <Pick roster={mine.roster.filter(e => !give.includes(e.id))} chosen={drops} onToggle={toggle(setDrops)} />
                </details>
                <div className="tr-send">
                  {legalNow && <span className={legalNow.from.ok ? "tr-ok" : "tr-bad"}>{legalNow.from.ok ? "Your roster works after this trade." : legalNow.from.error}</span>}
                  <button type="button" className="tr-btn primary" disabled={!legalNow?.from?.ok} onClick={send}>Send offer</button>
                </div>
              </>
            )}
          </section>
        )}

        {incoming.length > 0 && (
          <section className="tr-panel">
            <h2 className="tr-h">Needs your answer</h2>
            {incoming.map(t => {
              const ds = answerDrops[t.id] || [];
              const keep = mine.roster.filter(e => !t.get.some(g => g.id === e.id));
              return (
                <TradeCard key={t.id} t={t}>
                  <span className="tr-acts">
                    <button type="button" className="tr-btn" onClick={() => act(t, "decline")}>Decline</button>
                    <button type="button" className="tr-btn primary" onClick={() => act(t, "accept", { drops: ds })}>Accept</button>
                  </span>
                  <details className="tr-answerdrops"><summary>Drop to make room (only if you need to)</summary>
                    <Pick roster={keep} chosen={ds} onToggle={id => setAnswerDrops(a => ({ ...a, [t.id]: ds.includes(id) ? ds.filter(x => x !== id) : [...ds, id] }))} />
                  </details>
                </TradeCard>
              );
            })}
          </section>
        )}

        {waiting.length > 0 && (
          <section className="tr-panel">
            <h2 className="tr-h">Waiting for the commissioner</h2>
            {waiting.map(t => (
              <TradeCard key={t.id} t={t}>
                {user?.isAdmin && (
                  <span className="tr-acts">
                    <button type="button" className="tr-btn" onClick={() => act(t, "reject")}>Reject</button>
                    <button type="button" className="tr-btn primary" onClick={() => act(t, "approve")}>Approve</button>
                  </span>
                )}
                {!user?.isAdmin && mine && t.from?.id === mine.id && <span className="tr-acts"><button type="button" className="tr-btn" onClick={() => act(t, "cancel")}>Cancel</button></span>}
              </TradeCard>
            ))}
          </section>
        )}

        {outgoing.filter(t => t.status === "proposed").length > 0 && (
          <section className="tr-panel">
            <h2 className="tr-h">Your offers</h2>
            {outgoing.filter(t => t.status === "proposed").map(t => (
              <TradeCard key={t.id} t={t}><span className="tr-acts"><button type="button" className="tr-btn" onClick={() => act(t, "cancel")}>Cancel</button></span></TradeCard>
            ))}
          </section>
        )}

        <section className="tr-panel">
          <h2 className="tr-h">All trades</h2>
          {list === undefined ? <p className="tr-empty">Loading…</p>
            : rest.length === 0 ? <p className="tr-empty">No trades yet.</p>
              : rest.map(t => <TradeCard key={t.id} t={t} />)}
        </section>
      </div>
    </FantasyShell>
  );
}
