import { useNavigate, useSearchParams } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { base, SEASON, useFantasyApi } from "../../components/fantasy/data";
import useCurrentUser from "../../hooks/useCurrentUser";

const cell = { padding: "6px 8px", textAlign: "left" };
const day = iso => (iso ? new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "");

// ?team=<ownerId>, defaults to your own team. Every player who's been on the roster: how he joined (the locked draft
// record, or an add / claim / trade from the transaction log) and whether he's still there (today's roster) — a
// drafted player who was dropped shows "Dropped <date>", not "Current" (2026-10-17).
export default function Tenure() {
  const user = useCurrentUser();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const draft = useFantasyApi("draft");
  const teams = useFantasyApi("teams");
  const log = useFantasyApi("transactions");

  const order = draft?.order || [];
  const owner = params.get("team") || user?.discordId || order[0]?.owner_user_id;
  const team = order.find(t => t.owner_user_id === owner);
  const auction = draft?.draft_type === "auction";
  const now = new Map(((teams || []).find(t => t.owner_user_id === owner)?.roster || []).map(e => [e.id, e]));
  const moves = (log?.items || []).filter(g => g.team_id === team?.id);

  const rows = new Map();
  for (const p of (draft?.picks || []).filter(p => p.owner_user_id === owner)) {
    rows.set(p.id, { id: p.id, name: p.name, pos: p.position, joined: auction ? `Drafted · $${p.price ?? 0}` : `Drafted · round ${p.round}, pick ${p.pick}`, at: p.picked_at });
  }
  for (const g of [...moves].reverse()) {  // oldest first, so a later re-add replaces the earlier stint's line
    for (const a of g.adds) rows.set(a.id, { id: a.id, name: a.name, pos: a.position, joined: `${g.via === "trade" ? "Traded for" : g.via === "waivers" ? "Claimed" : "Added"} · ${day(g.at)}`, at: g.at });
    for (const x of g.drops) if (rows.has(x.id)) rows.get(x.id).left = `${g.via === "trade" ? "Traded away" : "Dropped"} ${day(g.at)}`;
  }
  const list = [...rows.values()].map(r => ({ ...r, status: now.has(r.id) ? `Current (${now.get(r.id).slot})` : r.left || "Gone" }))
    .sort((a, b) => (now.has(b.id) - now.has(a.id)) || String(a.at).localeCompare(String(b.at)));

  return (
    <FantasyShell title="Team History" season={SEASON}>
      <p style={{ fontSize: 13, marginBottom: 10 }}>
        Every player who has ever been on a team's roster, and when. Grows across future seasons.
      </p>
      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 14, fontSize: 13 }}>
        <span>Team</span>
        <select value={owner ?? ""} onChange={e => navigate(`${base()}/tenure?team=${e.target.value}`)} style={{ fontSize: 13 }}>
          {order.map(t => <option key={t.id} value={t.owner_user_id}>{t.name}</option>)}
        </select>
        {team && <TeamLink ownerId={team.owner_user_id} name="Current roster →" />}
      </div>

      {draft === undefined || teams === undefined || log === undefined ? <p style={{ fontSize: 13 }}>Loading…</p> : (
        <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.04em", borderBottom: "1px solid var(--border)" }}>
              <th style={cell}>Player</th><th style={cell} title="Position">Pos</th><th style={cell}>Joined</th><th style={cell}>Status</th>
            </tr>
          </thead>
          <tbody>
            {list.map(r => (
              <tr key={r.id} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                <td style={cell}><EntityLink id={r.id} name={r.name} /></td>
                <td style={cell}>{r.pos}</td>
                <td style={cell}>{r.joined}</td>
                <td style={cell}>{r.status}</td>
              </tr>
            ))}
            {list.length === 0 && <tr><td colSpan={4} style={cell}>Nobody has been on this roster yet.</td></tr>}
          </tbody>
        </table>
      )}
    </FantasyShell>
  );
}
