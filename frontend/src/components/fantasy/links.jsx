import { Link } from "react-router-dom";
import { teamPath } from "./data";
import { openEntityCard } from "./cardEvents";

// Every fantasy team name links to that team's page.
export function TeamLink({ ownerId, name, style }) {
  if (!ownerId) return <span style={style}>{name}</span>;
  return <Link to={teamPath(ownerId)} style={style}>{name}</Link>;
}

// Player / NBA team names open a pop-up card over the page (PlayerCard.jsx). There is no player page
// (commissioner, 2026-10-11): the pop-up is the only place, so this isn't a link to an address.
export function EntityLink({ id, name, style }) {
  if (!id) return <span style={style}>{name}</span>;
  return (
    <a href="#" role="button" style={style} onClick={e => { e.preventDefault(); openEntityCard(id); }}>{name}</a>
  );
}
