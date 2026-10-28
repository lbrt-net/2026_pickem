import { useLayoutEffect, useRef, useState } from "react";
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

export default function LeagueActivity({ teams, preDraft }) {
  const data = useFantasyApi("activity");
  const teamById = Object.fromEntries((teams || []).map(t => [t.id, t]));
  const entries = data?.entries || [];  // most important first (activity.py)
  // when it was made: the weekday within the last 6 days (by the league's date), else the date
  const today = data?.as_of ? new Date(`${data.as_of}T12:00:00`) : null;
  const when = e => (e.kind !== "draft" && today && today - new Date(e.at) < 6 * 86400000 ? day(e.at) : md(e.at));
  const keyOf = e => (e.kind === "draft" ? "draft" : e.key || `${e.team_id}-${e.week ?? 0}`);
  const render = e => {
        if (e.kind === "draft") {
          return (
            <div key="draft" data-k="draft" className="la-ev draft">
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
          <div key={keyOf(e)} data-k={keyOf(e)} className="la-ev">
            {t ? <TeamIcon team={t} size={22} /> : <span />}
            <span className="la-who"><TeamLink ownerId={t?.owner_user_id} name={e.team_name} style={{ color: "inherit", textDecoration: "none" }} /></span>
            <span className="la-moves">
              {e.adds.map(p => <Move key={`a${p.id}`} e={p} sign="+" claim={p.via === "waivers"} />)}
              {e.drops.map(p => <Move key={`d${p.id}`} e={p} sign="-" />)}
            </span>
            <span className="la-when">{when(e)}</span>
          </div>
        );
  };

  // Fill the box by importance (2026-10-23): take moves most important first, each using its own measured height, until
  // the room runs out (the last one taken may run past the bottom, 2026-10-24); then show them newest first — whatever
  // ends up at the bottom fades out past the edge.
  const boxRef = useRef(null), measureRef = useRef(null);
  const [picked, setPicked] = useState(null);
  const [over, setOver] = useState(false);
  const sig = entries.map(keyOf).join("|");
  useLayoutEffect(() => {
    const box = boxRef.current, m = measureRef.current;
    if (!box || !m) return undefined;
    const fit = () => {
      const head = box.querySelector(".hm-head");
      let room = box.clientHeight - (head ? head.offsetHeight : 0);
      const take = [];
      for (const el of m.children) {
        const h = el.getBoundingClientRect().height;
        if (room <= 0) break;
        take.push(el.dataset.k);         // the one that runs past the bottom is kept too: the box's bottom fades it out
        room -= h;
      }
      setPicked(take.join("|"));
      setOver(room < 0);
    };
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(box);
    return () => ro.disconnect();
  }, [sig]);
  const chosen = new Set((picked || "").split("|"));
  const shown = entries.filter(e => chosen.has(keyOf(e))).sort((x, y) => String(y.at).localeCompare(String(x.at)));

  return (
    <section ref={boxRef} className={`hm-panel la${over ? " over" : ""}`} aria-label="League activity">
      <div className="hm-head"><span className="hm-tick" aria-hidden="true" />League activity<Link className="hm-head-aside" to={`${base()}/transactions`}>Transaction Log →</Link></div>
      {preDraft && <p className="hm-empty">League activity — draft picks, adds and drops — will show here after the draft.</p>}
      {data === undefined && !preDraft && <p className="la-msg">Loading…</p>}
      {/* the same moves, invisible, most important first — only to measure each one's height */}
      <div ref={measureRef} className="la-measure" aria-hidden="true">{entries.map(render)}</div>
      {shown.map(render)}
    </section>
  );
}
