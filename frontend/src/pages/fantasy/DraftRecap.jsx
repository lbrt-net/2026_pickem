import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { EntityLink, TeamLink } from "../../components/fantasy/links";
import { base, SEASON, useFantasyApi } from "../../components/fantasy/data";

const heading = { fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 6 };
const GRADES = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D"];

// Steal/reach = where a pick went vs. its rank in the whole pool by fantasy points.
// Grade = team's total drafted fantasy points, ranked across the league.
export default function DraftRecap() {
  const draft = useFantasyApi("draft");

  if (draft === undefined) {
    return <FantasyShell title="Draft Recap" season={SEASON}><p style={{ fontSize: 13 }}>Loading…</p></FantasyShell>;
  }
  const picks = draft?.picks || [];
  if (picks.length === 0) {
    return (
      <FantasyShell title="Draft Recap" season={SEASON}>
        <p style={{ fontSize: 13 }}>No draft yet. <Link to={`${base()}/draft`}>Go to the Draft Room</Link></p>
      </FantasyShell>
    );
  }

  const withValue = picks.map(p => ({ ...p, value: p.pick - p.pool_rank }));
  const steals = [...withValue].sort((a, b) => b.value - a.value).slice(0, 5);
  const reaches = [...withValue].sort((a, b) => a.value - b.value).slice(0, 5);

  const byTeam = (draft.order || []).map(t => {
    const mine = withValue.filter(p => p.team_id === t.id);
    return { ...t, total: Math.round(mine.reduce((s, p) => s + p.fantasy_points, 0) * 10) / 10, best: [...mine].sort((a, b) => b.value - a.value)[0] };
  }).sort((a, b) => b.total - a.total);
  const grade = i => GRADES[Math.min(Math.floor((i / Math.max(byTeam.length - 1, 1)) * (GRADES.length - 1)), GRADES.length - 1)];

  const pickLine = p => (
    <div key={p.pick} style={{ fontSize: 13, padding: "3px 0" }}>
      <EntityLink id={p.id} name={p.name} /> — pick {p.pick}, ranked #{p.pool_rank} ·{" "}
      <TeamLink ownerId={p.owner_user_id} name={p.team_name} />
    </div>
  );

  return (
    <FantasyShell title="Draft Recap" season={SEASON}>
      <p style={{ fontSize: 13, marginBottom: 10 }}>
        "Ranked" is where the player sits in the whole pool by fantasy points per game.{" "}
        <Link to={`${base()}/draft`}>Every pick</Link>
      </p>
      <div style={{ display: "flex", gap: 14, marginBottom: 14, flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 280, border: "1px solid var(--border)", padding: 12 }}>
          <div style={heading}>Biggest steals</div>
          {steals.map(pickLine)}
        </div>
        <div style={{ flex: 1, minWidth: 280, border: "1px solid var(--border)", padding: 12 }}>
          <div style={heading}>Biggest reaches</div>
          {reaches.map(pickLine)}
        </div>
      </div>
      <div style={heading}>Team grades</div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 8 }}>
        {byTeam.map((t, i) => (
          <div key={t.id} style={{ border: "1px solid var(--border)", padding: 10, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600 }}><TeamLink ownerId={t.owner_user_id} name={t.name} /></div>
              <div style={{ fontSize: 12 }}>{t.total} Fantasy Pts{t.best && <> · best value: <EntityLink id={t.best.id} name={t.best.name} /></>}</div>
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, border: "1px solid var(--border)", padding: "2px 10px" }}>{grade(i)}</div>
          </div>
        ))}
      </div>
    </FantasyShell>
  );
}
