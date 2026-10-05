import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CARD_EVENT } from "./cardEvents";
import { entityPath, useFantasyApi } from "./data";
import { Headshot, NbaTeamSquare } from "./RosterBits";
import { NBA_TEAMS, nameLines } from "./nbaTeams";
import "./PlayerCard.css";

// The pop-up a player / NBA team name opens (one per page, mounted by FantasyShell). Bottom sheet on
// phones. Mostly empty for now — stats, this week, game log come later. Esc / tap outside closes.
export default function PlayerCardHost() {
  const [id, setId] = useState(null);
  const players = useFantasyApi("players");
  const nbaTeams = useFantasyApi("nba-teams");

  useEffect(() => {
    const open = e => setId(e.detail.id);
    const esc = e => { if (e.key === "Escape") setId(null); };
    window.addEventListener(CARD_EVENT, open);
    window.addEventListener("keydown", esc);
    return () => { window.removeEventListener(CARD_EVENT, open); window.removeEventListener("keydown", esc); };
  }, []);
  if (!id) return null;

  const p = (players || []).find(x => x.id === id);
  const t = !p && (nbaTeams || []).find(x => x.id === id);
  const e = p ? { ...p, kind: "player" } : t ? { ...t, kind: "nba_team" } : null;
  const [first, last] = e ? nameLines(e) : ["", id];
  const team = e && (e.kind === "player" ? NBA_TEAMS[e.nba_team] : NBA_TEAMS[e.id]);

  return (
    <div className="pc-overlay" onClick={() => setId(null)}>
      <div className="pc-card" role="dialog" aria-modal="true" aria-label={e ? e.name : "Player"} onClick={ev => ev.stopPropagation()}>
        <div className="pc-head" style={{ "--team": team?.primary || "var(--surface-3)" }}>
          {e?.kind === "player" ? <Headshot playerId={e.id} tricode={e.nba_team} width={120} height={88} />
            : e ? <span className="pc-logo"><NbaTeamSquare tricode={e.id} size={72} /></span> : null}
          <div className="pc-name">
            <span>{first}</span>
            <b>{last}</b>
            {e?.kind === "player" && <span>{[e.position, team && `${team.city} ${team.nickname}`].filter(Boolean).join(" · ")}</span>}
          </div>
          <button type="button" className="pc-close" aria-label="Close" onClick={() => setId(null)}>×</button>
        </div>
        <div className="pc-body">
          <p>More here soon — this week, season stats, recent games.</p>
        </div>
        <div className="pc-foot">
          <Link className="pc-full" to={entityPath(id)} onClick={() => setId(null)}>Full page →</Link>
        </div>
      </div>
    </div>
  );
}
