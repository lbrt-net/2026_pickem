import { Link } from "react-router-dom";
import { entityPath, teamPath } from "./data";
import { openEntityCard } from "./cardEvents";

// Every fantasy team name links to that team's page.
export function TeamLink({ ownerId, name, style }) {
  if (!ownerId) return <span style={style}>{name}</span>;
  return <Link to={teamPath(ownerId)} style={style}>{name}</Link>;
}

// Player / NBA team names open a pop-up card over the page (PlayerCard.jsx) instead of leaving it —
// it should be hard to tap out of a page by accident (LINKS.md). The link keeps its real address,
// so open-in-new-tab / middle-click still go to the full page.

export function EntityLink({ id, name, style }) {
  if (!id) return <span style={style}>{name}</span>;
  return (
    <Link to={entityPath(id)} style={style} onClick={e => {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return; // new tab / window: let it go
      e.preventDefault();
      openEntityCard(id);
    }}>{name}</Link>
  );
}
