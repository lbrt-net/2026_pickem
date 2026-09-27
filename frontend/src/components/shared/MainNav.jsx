import { Link } from "react-router-dom";
import useCurrentUser from "../../hooks/useCurrentUser";
import UserChip from "../UserChip";

// The one navigation unit shared across the landing page, pickem, fantasy,
// and the account page: home link + season selector (when applicable) +
// user dropdown. Each product embeds this as-is inside its own differently
// shaped chrome — this component itself never changes shape per product.
export default function MainNav({ seasonOptions, currentSeason, onSeasonChange, showHome = true }) {
  const user = useCurrentUser();

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      {showHome && <Link to="/" style={{ fontSize: 11, color: "#666", textDecoration: "none" }}>&larr; lbrt.net</Link>}

      {seasonOptions && seasonOptions.length > 1 && (
        <select value={currentSeason} onChange={e => onSeasonChange(e.target.value)} style={{ fontSize: 12 }}>
          {seasonOptions.map(({ value, label }) => <option key={value} value={value}>{label}</option>)}
        </select>
      )}
      {seasonOptions && seasonOptions.length === 1 && (
        <span style={{ fontSize: 11, color: "#999" }}>{seasonOptions[0].label}</span>
      )}

      <UserChip user={user} extraLinks={[{ label: "Account", to: "/account" }]} />
    </div>
  );
}
