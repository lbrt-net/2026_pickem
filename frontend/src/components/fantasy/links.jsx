import { Link } from "react-router-dom";
import { entityPath, teamPath } from "./data";
import { openEntityCard } from "./cardEvents";

// Every fantasy team name links to that team's page.
export function TeamLink({ ownerId, name, style }) {
  if (!ownerId) return <span style={style}>{name}</span>;
  return <Link to={teamPath(ownerId)} style={style}>{name}</Link>;
}

// Player / NBA team names open a pop-up card over the page (PlayerCard.jsx) instead of leaving it — it should be
// hard to tap out of a page by accident (LINKS.md). Players' links keep their real address (the player page, back
// 2026-10-14), so open-in-new-tab / middle-click go there; NBA teams have no page, the pop-up only.
export function EntityLink({ id, name, style }) {
  if (!id) return <span style={style}>{name}</span>;
  if (!/^\d+$/.test(id)) {
    return <a href="#" role="button" style={style} onClick={e => { e.preventDefault(); openEntityCard(id); }}>{name}</a>;
  }
  return (
    <Link to={entityPath(id)} style={style} onClick={e => {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return; // new tab / window: let it go
      e.preventDefault();
      openEntityCard(id);
    }}>{name}</Link>
  );
}
