// A team's icon: its uploaded logo, or a solid block of the team's color.
// The color comes from the API (defaults to a hash of the owner's username; owners can change it).
export default function TeamIcon({ team, size = 24 }) {
  const box = { width: size, height: size, borderRadius: Math.round(size / 6), flexShrink: 0, display: "inline-block", verticalAlign: "middle" };
  if (team?.logo_url) return <img src={team.logo_url} alt="" style={{ ...box, objectFit: "cover" }} />;
  return <span aria-hidden="true" style={{ ...box, background: team?.color || "var(--surface-2)" }} />;
}
