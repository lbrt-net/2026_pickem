import { Link } from "react-router-dom";
import { entityPath, teamPath } from "./data";

// Every fantasy team name links to that team's page.
export function TeamLink({ ownerId, name, style }) {
  if (!ownerId) return <span style={style}>{name}</span>;
  return <Link to={teamPath(ownerId)} style={style}>{name}</Link>;
}

// Every player / NBA-team-unit name links to its detail page.
export function EntityLink({ id, name, style }) {
  if (!id) return <span style={style}>{name}</span>;
  return <Link to={entityPath(id)} style={style}>{name}</Link>;
}
