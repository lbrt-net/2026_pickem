import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { Headshot, NbaTeamSquare } from "../../components/fantasy/RosterBits";
import { EntityLink } from "../../components/fantasy/links";
import { API_BASE, SEASON } from "../../components/fantasy/data";
import { accent } from "../../components/fantasy/standings";
import useCurrentUser from "../../hooks/useCurrentUser";
import useFantasyScenario from "../../hooks/useFantasyScenario";
import { API } from "../../utils/helpers";
import "./Trades.css";

// Trades (2026-10-17; backend trades.py): the only way players move between two teams. Propose → the other team
// accepts (with any drops it needs), declines or counters → the commissioner approves. Both rosters must end up legal
// at every step (the server checks). Everyone sees every trade.
// Layout: the deal builder is two rosters face to face (yours | theirs); tapping a player puts him in the deal strip
// under them. Offers read the same way: one side | ⇄ | the other.

const STATUS = { proposed: "Waiting for an answer", accepted: "Waiting for the commissioner", approved: "Done",
  declined: "Declined", countered: "Countered", cancelled: "Cancelled", rejected: "Rejected by the commissioner" };
const SLOT = { BENCH: "Bench", TEAM: "TM", FLEX: "FLX", IR: "IR" };

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

function Face({ e, size = 34 }) {
  return e.kind === "nba_team" ? <NbaTeamSquare tricode={e.id} size={size - 4} /> : <Headshot playerId={e.id} tricode={e.nba_team} width={size + 10} height={size} />;
}

function Plate({ team, label }) {
  return (
    <div className="tr-plate" style={{ "--tc": accent(team?.color) }}>
      <TeamIcon team={team} size={30} />
      <div><span className="tr-plate-l">{label}</span><b>{team?.name}</b></div>
    </div>
  );
}

// One roster, every player a button: tap to put him in (or take him out of) the deal.
function Roster({ roster, chosen, onToggle, mark, locked = [] }) {
  if (!roster?.length) return <p className="tr-empty">No players.</p>;
  return (
    <div className="tr-roster">
      {roster.map(e => {
        const on = chosen.includes(e.id), off = locked.includes(e.id);
        return (
          <button key={e.id} type="button" className={`tr-row${on ? " on" : ""}`} disabled={off} aria-pressed={on} onClick={() => onToggle(e.id)}>
            <span className="tr-slot">{SLOT[e.slot] || e.slot}</span>
            <Face e={e} />
            <span className="tr-who"><b>{e.name}</b><span>{e.kind === "nba_team" ? "NBA team" : [e.position, e.nba_team].filter(Boolean).join(" · ")}</span></span>
            <span className="tr-mark">{on ? mark : ""}</span>
          </button>
        );
      })}
    </div>
  );
}

function Names({ list }) {
  if (!list?.length) return <p className="tr-none">Nobody</p>;
  return (
    <ul className="tr-names">
      {list.map(e => <li key={e.id}><Face e={e} size={28} /><EntityLink id={e.id} name={e.name} /></li>)}
    </ul>
  );
}

function TradeCard({ t, children }) {
  return (
    <article className={`tr-card st-${t.status}`}>
      <div className="tr-card-sides">
        <div><Plate team={t.from} label="Sends" /><Names list={t.give} />
          {t.from_drops.length > 0 && <p className="tr-dropnote">Drops {t.from_drops.map(e => e.name).join(", ")}</p>}</div>
        <span className="tr-swap" aria-hidden="true">⇄</span>
        <div><Plate team={t.to} label="Sends" /><Names list={t.get} />
          {t.to_drops.length > 0 && <p className="tr-dropnote">Drops {t.to_drops.map(e => e.name).join(", ")}</p>}</div>
      </div>
      <footer className="tr-card-foot">
        <span className="tr-status">{STATUS[t.status] || t.status}</span>
        <span className="tr-when">{new Date(t.updated_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}</span>
        {children}
      </footer>
    </article>
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
  const [showDrops, setShowDrops] = useState(false);
  const [legal, setLegal] = useState(null);
  const [answerDrops, setAnswerDrops] = useState({});
  const [msg, setMsg] = useState(null);
  const [counterOf, setCounterOf] = useState(null);
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

  // live check of the deal being built (kept with the offer it was for)
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

  const clear = () => { setGive([]); setGet([]); setDrops([]); setCounterOf(null); setShowDrops(false); };
  const send = async () => {
    const d = await post("trades", { from_team: mine.id, to_team: partner.id, give, get, drops });
    if (!d) return;
    if (counterOf) await post(`trades/${counterOf}/counter`, {});
    const was = counterOf; clear();
    setMsg({ text: was ? "Counteroffer sent." : "Offer sent." }); setVersion(v => v + 1);
  };
  const counter = t => {
    setPartnerId(t.from.id); setGive(t.get.map(e => e.id)); setGet(t.give.map(e => e.id)); setDrops([]); setCounterOf(t.id);
    setMsg({ text: `Countering ${t.from.name}. Change the deal, then send it back.` });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const act = async (t, action, body) => { if (await post(`trades/${t.id}/${action}`, body)) setVersion(v => v + 1); };

  const trades = list?.trades || [];
  const incoming = trades.filter(t => t.status === "proposed" && mine && t.to?.id === mine.id);
  const outgoing = trades.filter(t => t.status === "proposed" && mine && t.from?.id === mine.id);
  const waiting = trades.filter(t => t.status === "accepted");
  const history = trades.filter(t => !incoming.includes(t) && !outgoing.includes(t) && !waiting.includes(t));
  const byId = Object.fromEntries([...(mine?.roster || []), ...(partner?.roster || [])].map(e => [e.id, e]));

  return (
    <FantasyShell title="Trades" season={SEASON}>
      <div className="tr">
        {msg && <div className={`tr-msg${msg.error ? " error" : ""}`} role="status">{msg.text}</div>}

        {incoming.length > 0 && (
          <section className="tr-sec">
            <h2 className="tr-h">Offers for you <span className="tr-count">{incoming.length}</span></h2>
            {incoming.map(t => {
              const ds = answerDrops[t.id] || [];
              const keep = (mine?.roster || []).filter(e => !t.get.some(g => g.id === e.id));
              return (
                <TradeCard key={t.id} t={t}>
                  <span className="tr-acts">
                    <button type="button" className="tr-btn" onClick={() => act(t, "decline")}>Decline</button>
                    <button type="button" className="tr-btn" onClick={() => counter(t)}>Counter</button>
                    <button type="button" className="tr-btn primary" onClick={() => act(t, "accept", { drops: ds })}>Accept</button>
                  </span>
                  <details className="tr-answerdrops"><summary>Need room? Pick who you'd drop</summary>
                    <Roster roster={keep} chosen={ds} mark="Drop" onToggle={id => setAnswerDrops(a => ({ ...a, [t.id]: ds.includes(id) ? ds.filter(x => x !== id) : [...ds, id] }))} />
                  </details>
                </TradeCard>
              );
            })}
          </section>
        )}

        {mine && (
          <section className="tr-sec tr-builder">
            <h2 className="tr-h">{counterOf ? "Counteroffer" : "Make a trade"}</h2>
            <div className="tr-partners" role="radiogroup" aria-label="Trade with">
              {all.filter(t => t !== mine).map(t => (
                <button key={t.id} type="button" role="radio" aria-checked={partner === t} className={`tr-chip${partner === t ? " on" : ""}`}
                  style={{ "--tc": accent(t.color) }} onClick={() => { setPartnerId(t.id); setGet([]); }}>
                  <TeamIcon team={t} size={18} />{t.name}
                </button>
              ))}
            </div>

            {!partner ? <p className="tr-empty">Pick a team to trade with.</p> : (
              <>
                <div className="tr-face">
                  <div className="tr-side">
                    <Plate team={mine} label="You" />
                    <Roster roster={mine.roster} chosen={showDrops ? drops : give} mark={showDrops ? "Drop" : "Sending"}
                      onToggle={showDrops ? toggle(setDrops) : toggle(setGive)} locked={showDrops ? give : drops} />
                    <button type="button" className={`tr-link${showDrops ? " on" : ""}`} onClick={() => setShowDrops(s => !s)}>
                      {showDrops ? "Done picking drops" : drops.length ? `Dropping ${drops.length} · change` : "Need room? Pick who you'd drop"}
                    </button>
                  </div>
                  <div className="tr-side">
                    <Plate team={partner} label="Them" />
                    <Roster roster={partner.roster} chosen={get} mark="Getting" onToggle={toggle(setGet)} />
                  </div>
                </div>

                <div className="tr-deal">
                  <div className="tr-deal-col"><span className="tr-deal-l">You send</span>
                    <span>{give.length ? give.map(i => byId[i]?.name).join(", ") : "Nobody yet"}</span></div>
                  <span className="tr-swap" aria-hidden="true">⇄</span>
                  <div className="tr-deal-col"><span className="tr-deal-l">You get</span>
                    <span>{get.length ? get.map(i => byId[i]?.name).join(", ") : "Nobody yet"}</span></div>
                  <div className="tr-deal-go">
                    {legalNow && (
                      <span className="tr-legal">
                        <span className={legalNow.from.ok ? "" : "bad"}>{legalNow.from.ok ? "Your roster works" : `Your roster: ${legalNow.from.error} Pick someone to drop.`}</span>
                        <span>{legalNow.to.ok ? `${partner.name}'s roster works` : `${partner.name} would need to drop someone`}</span>
                      </span>
                    )}
                    {(give.length > 0 || get.length > 0 || counterOf) && <button type="button" className="tr-btn" onClick={() => { clear(); setMsg(null); }}>Clear</button>}
                    <button type="button" className="tr-btn primary" disabled={!legalNow?.from?.ok} onClick={send}>{counterOf ? "Send counteroffer" : "Send offer"}</button>
                  </div>
                </div>
              </>
            )}
          </section>
        )}

        {waiting.length > 0 && (
          <section className="tr-sec">
            <h2 className="tr-h">Waiting for the commissioner <span className="tr-count">{waiting.length}</span></h2>
            {waiting.map(t => (
              <TradeCard key={t.id} t={t}>
                <span className="tr-acts">
                  {user?.isAdmin && <><button type="button" className="tr-btn" onClick={() => act(t, "reject")}>Reject</button>
                    <button type="button" className="tr-btn primary" onClick={() => act(t, "approve")}>Approve</button></>}
                  {!user?.isAdmin && mine && t.from?.id === mine.id && <button type="button" className="tr-btn" onClick={() => act(t, "cancel")}>Cancel</button>}
                </span>
              </TradeCard>
            ))}
          </section>
        )}

        {outgoing.length > 0 && (
          <section className="tr-sec">
            <h2 className="tr-h">Your offers <span className="tr-count">{outgoing.length}</span></h2>
            {outgoing.map(t => <TradeCard key={t.id} t={t}><span className="tr-acts"><button type="button" className="tr-btn" onClick={() => act(t, "cancel")}>Cancel</button></span></TradeCard>)}
          </section>
        )}

        <section className="tr-sec">
          <h2 className="tr-h">League trades</h2>
          {list === undefined ? <p className="tr-empty">Loading…</p>
            : history.length === 0 ? <p className="tr-empty">No trades yet this season.</p>
              : history.map(t => <TradeCard key={t.id} t={t} />)}
        </section>
      </div>
    </FantasyShell>
  );
}
