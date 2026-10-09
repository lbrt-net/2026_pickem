import { useMemo, useState } from "react";
import FantasyShell from "../../components/fantasy/FantasyShell";
import TeamIcon from "../../components/fantasy/TeamIcon";
import { Headshot, NbaTeamSquare } from "../../components/fantasy/RosterBits";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { SEASON, useFantasyApi } from "../../components/fantasy/data";
import "./DraftRoom.css";
import "./Transactions.css";

// Transaction Log: every real add / drop (one entry per checkout), waiver claims won, and the draft — newest first,
// grouped by fantasy week. Adds that were dropped again before they ever locked in aren't real moves and never
// show (the server erases them). Draft picks come from GET /draft.

const TYPES = [["all", "All"], ["moves", "Adds & drops"], ["waivers", "Waiver claims"], ["draft", "Draft"]];
const SPOT = { G: "G", F: "F", C: "C", TEAM: "TM", FLEX: "Flex", BENCH: "Bench" };
const sub = e => (e.kind === "nba_team" ? `TM · ${e.id}` : [e.position || "—", e.nba_team].filter(Boolean).join(" · "));
const when = iso => new Date(iso).toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
const day = d => new Date(`${d}T00:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });

function Who({ e, sign }) {
  return (
    <span className="tx-who">
      <i className="tx-sign" aria-label={sign === "+" ? "added" : "dropped"}>{sign === "+" ? "+" : "−"}</i>
      {e.kind === "player" ? <Headshot playerId={e.id} tricode={e.nba_team} width={30} height={34} /> : <NbaTeamSquare tricode={e.id} size={28} />}
      <span className="tx-name"><EntityLink id={e.id} name={e.name} style={{ color: "inherit", textDecoration: "none" }} /><small>{sub(e)}</small></span>
    </span>
  );
}

function Seg({ options, value, onChange }) {
  return (
    <span className="dr-seg" role="radiogroup">
      {options.map(([k, label]) => <button key={k} type="button" role="radio" aria-checked={value === k} onClick={() => onChange(k)}>{label}</button>)}
    </span>
  );
}

export default function Transactions() {
  const log = useFantasyApi("transactions");
  const draft = useFantasyApi("draft");
  const teams = useFantasyApi("teams");
  const [type, setType] = useState("all");
  const [team, setTeam] = useState("");
  const [showDraft, setShowDraft] = useState(false);

  const teamById = useMemo(() => Object.fromEntries((teams || []).map(t => [t.id, t])), [teams]);
  const items = useMemo(() => (log?.items || []).filter(g =>
    (!team || g.team_id === team) && (type === "all" || (type === "moves" && g.via !== "waivers") || (type === "waivers" && g.via === "waivers"))),
  [log, type, team]);
  // Newest week first; each week's entries newest first (the server's order).
  const byWeek = useMemo(() => {
    const out = [];
    for (const g of items) {
      const k = g.week ?? "pre";
      let w = out.find(x => x.key === k);
      if (!w) { w = { key: k, week: g.week, label: g.week_label, items: [] }; out.push(w); }
      w.items.push(g);
    }
    return out;
  }, [items]);
  const weekInfo = Object.fromEntries((log?.weeks || []).map(w => [w.week, w]));
  const picks = (draft?.picks || []).filter(p => !team || p.team_id === team);
  const auction = draft?.draft_type === "auction";
  const claimsWon = (log?.items || []).filter(g => g.via === "waivers").length;
  const loading = log === undefined || draft === undefined;

  return (
    <FantasyShell title="Transaction Log" season={SEASON}>
      <section className="tx-sum" aria-label="Summary">
        <div><b>{log?.adds ?? "—"}</b><span>Adds</span></div>
        <div><b>{log?.drops ?? "—"}</b><span>Drops</span></div>
        <div><b>{log ? claimsWon : "—"}</b><span>Waiver claims won</span></div>
        <div><b>{draft?.picks?.length ?? "—"}</b><span>Draft picks</span></div>
      </section>

      <section className="dr-panel tx-panel" aria-label="Transactions">
        <div className="tx-tools">
          <Seg options={TYPES} value={type} onChange={setType} />
          <select className="tx-team" value={team} onChange={e => setTeam(e.target.value)} aria-label="Team">
            <option value="">All teams</option>
            {(teams || []).map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </div>

        {loading && <p className="tx-msg">Loading…</p>}
        {!loading && type !== "draft" && byWeek.length === 0 && <p className="tx-msg">No adds or drops yet.</p>}

        {type !== "draft" && byWeek.map(w => (
          <div key={w.key} className="tx-week">
            <div className="tx-week-h">
              <b>{w.week ? (w.label || `Week ${w.week}`) : "Before the season"}</b>
              {w.week && weekInfo[w.week] && <span>{day(weekInfo[w.week].start)} – {day(weekInfo[w.week].end)}</span>}
            </div>
            {w.items.map(g => {
              const t = teamById[g.team_id];
              return (
                <div key={`${g.team_id}-${g.at}`} className="tx-row">
                  <span className="tx-time">{when(g.at)}</span>
                  <span className="tx-team-cell">{t && <TeamIcon team={t} size={24} />}<TeamLink ownerId={t?.owner_user_id} name={g.team_name} style={{ color: "inherit", textDecoration: "none" }} /></span>
                  <span className="tx-moves">
                    {g.adds.map(e => <Who key={`a${e.id}`} e={e} sign="+" />)}
                    {g.drops.map(e => <Who key={`d${e.id}`} e={e} sign="-" />)}
                  </span>
                  <span className="tx-tags">
                    {g.via === "waivers" && <span className="dr-tag">Waiver claim</span>}
                    {g.drops.length > 0 && <span className="tx-note">{g.drops.length === 1 ? "Dropped player" : "Dropped players"} → waivers</span>}
                    {g.by === "commissioner" && <span className="dr-tag">commissioner</span>}
                  </span>
                </div>
              );
            })}
          </div>
        ))}

        {(type === "all" || type === "draft") && picks.length > 0 && (
          <div className="tx-week">
            <button type="button" className="tx-week-h tx-fold" aria-expanded={showDraft || type === "draft"} onClick={() => setShowDraft(v => !v)}>
              <b>{type === "draft" || showDraft ? "▾" : "▸"} Draft</b><span>{picks.length} {auction ? "buys" : "picks"}</span>
            </button>
            {(showDraft || type === "draft") && picks.map(p => {
              const t = teamById[p.team_id];
              const e = { id: p.id, kind: p.kind, name: p.name, position: p.position, nba_team: p.kind === "nba_team" ? p.id : null };
              return (
                <div key={p.pick} className="tx-row">
                  <span className="tx-time">{auction ? `$${p.price ?? 0}` : `R${p.round} · #${p.pick}`}</span>
                  <span className="tx-team-cell">{t && <TeamIcon team={t} size={24} />}<span>{p.team_name}</span></span>
                  <span className="tx-moves"><span className="tx-who"><i className="tx-sign">+</i><span className="tx-name"><EntityLink id={e.id} name={e.name} style={{ color: "inherit", textDecoration: "none" }} /><small>{p.kind === "nba_team" ? "TM" : p.position} · {SPOT[p.slot] || p.slot}</small></span></span></span>
                  <span className="tx-tags">{p.auto && <span className="dr-tag">auto</span>}</span>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </FantasyShell>
  );
}
