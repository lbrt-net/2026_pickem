import TeamIcon from "./TeamIcon";
import { NbaTeamSquare, PositionBadge } from "./RosterBits";
import { EntityLink, TeamLink } from "./links";
import { nameLines } from "./nbaTeams";
import { base, useFantasyApi } from "./data";
import { Link } from "react-router-dom";
import "./LeagueActivity.css";

// Home's League activity (design: canvas "Home — League activity"): GET /activity — the most impactful real moves,
// one line per team per week (its net change), plus the draft as one line with its three biggest picks; newest
// first. Denser than the Transaction Log on purpose: one row per entry (a line per player under the team), small
// position squares instead of headshots, initial + last name. The ranking (impact) is the server's and never shown.

const day = iso => new Date(iso).toLocaleDateString(undefined, { weekday: "short" });
const md = s => new Date(`${s.slice(0, 10)}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });
const short = e => (e.kind === "nba_team" ? nameLines({ kind: "nba_team", id: e.id, name: e.name })[1] || e.name
  : (() => { const i = (e.name || "").indexOf(" "); return i === -1 ? e.name : `${e.name[0]}. ${e.name.slice(i + 1)}`; })());

function Square({ e }) {
  return e.kind === "nba_team" ? <NbaTeamSquare tricode={e.id} size={18} /> : <PositionBadge entry={e} size={18} />;
}

function Move({ e, sign, claim }) {
  return (
    <span className="la-mv">
      <i className={`la-sign ${sign === "+" ? "add" : "drop"}`} aria-label={sign === "+" ? "added" : "dropped"}>{sign === "+" ? "+" : "−"}</i>
      <Square e={e} />
      <EntityLink id={e.id} name={short(e)} style={{ color: "inherit", textDecoration: "none" }} />
      {claim && <small className="la-via">via waivers</small>}
    </span>
  );
}

export default function LeagueActivity({ teams }) {
  const data = useFantasyApi("activity");
  const teamById = Object.fromEntries((teams || []).map(t => [t.id, t]));
  const entries = data?.entries || [];
  const when = e => (e.kind === "draft" ? md(e.at) : e.week && e.week === data.current_week ? day(e.at) : e.week ? `Wk ${e.week}` : md(e.asof));
  return (
    <section className="hm-panel la" aria-label="League activity">
      <div className="hm-head"><span className="hm-tick" aria-hidden="true" />League activity<Link className="hm-head-aside" to={`${base()}/transactions`}>Transaction Log →</Link></div>
      {data === undefined && <p className="la-msg">Loading…</p>}
      {data && entries.length === 0 && <p className="la-msg">No moves yet.</p>}
      {entries.map(e => {
        if (e.kind === "draft") {
          return (
            <div key="draft" className="la-ev draft">
              <span className="la-ti" aria-hidden="true"><svg width="12" height="12" viewBox="0 0 16 16"><path d="M3 13l7-7M9 3l4 4-2 2-4-4zM2 14h6" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg></span>
              <Link className="la-who" to={`${base()}/draft/results`}>Draft</Link>
              <span className="la-moves">
                {e.top.map(p => (
                  <span key={p.id} className="la-mv">
                    <span className="la-by">{teamById[p.team_id] && <TeamIcon team={teamById[p.team_id]} size={16} />}{p.team_name}</span>
                    {p.price != null && <b className="la-price">${p.price}</b>}
                    <Square e={p} />
                    <EntityLink id={p.id} name={short(p)} style={{ color: "inherit", textDecoration: "none" }} />
                  </span>
                ))}
              </span>
              <span className="la-when">{when(e)}</span>
            </div>
          );
        }
        const t = teamById[e.team_id];
        return (
          <div key={`${e.team_id}-${e.week ?? 0}`} className="la-ev">
            {t ? <TeamIcon team={t} size={22} /> : <span />}
            <span className="la-who"><TeamLink ownerId={t?.owner_user_id} name={e.team_name} style={{ color: "inherit", textDecoration: "none" }} /></span>
            <span className="la-moves">
              {e.adds.map(p => <Move key={`a${p.id}`} e={p} sign="+" claim={e.via === "waivers"} />)}
              {e.drops.map(p => <Move key={`d${p.id}`} e={p} sign="-" />)}
            </span>
            <span className="la-when">{when(e)}</span>
          </div>
        );
      })}
    </section>
  );
}
