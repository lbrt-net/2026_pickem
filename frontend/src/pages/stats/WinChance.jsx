import { useEffect, useRef, useState } from "react";
import MainNav from "../../components/shared/MainNav";
import { API } from "../../utils/helpers";
import StatsNav, { GamesTabs } from "./StatsNav";
import { TeamChip } from "./StatsControls";
import { winChance, minutesLeft, clockSecs, pctText, clockText } from "./winChance";
import "./Rebounding.css";
import "./Games.css";
import "./WinChance.css";

// /stats/nba/games/live (2026-11-18, commissioner: "move the win prob / game is over indicator to my website stats …
// I have to request a live game that's happening that day and then it checks whether it's actually live or not").
// Today's games come from the Games page's predictions (the pre-game expected margin drives the math). Nothing loads
// until a game is asked for; then the server says whether it's live (/nba/live-game/<id>, from the 30-second live
// pull) and, while it is, the numbers follow it every 30 seconds. Final or not started: says so and stops.
const tipTime = iso => (iso ? new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }) : "TBD");
const POLL_MS = 30000;

export default function WinChance() {
  const [games, setGames] = useState(null);
  const [pick, setPick] = useState(null);     // the game asked for (from today's predictions)
  const [live, setLive] = useState(null);     // the server's answer for it
  const [busy, setBusy] = useState(false);
  const timer = useRef(null);

  useEffect(() => {
    fetch(`${API}/nba/stats/standings`, { credentials: "include" }).then(r => r.json())
      .then(d => {
        const today = new Date().toLocaleDateString("en-CA", { timeZone: "America/Chicago" });
        const day = (d.dates || []).map(x => x.next).find(x => x && x.date === today);
        setGames(day?.games || []);
      })
      .catch(() => setGames([]));
    return () => clearTimeout(timer.current);
  }, []);

  const ask = g => {
    clearTimeout(timer.current);
    setPick(g); setLive(null); setBusy(true);
    const check = () => fetch(`${API}/nba/live-game/${g.game_id}`, { credentials: "include" }).then(r => r.json())
      .then(x => {
        setLive(x); setBusy(false);
        if (x.state === "live") timer.current = setTimeout(check, POLL_MS);   // follow it while it's on
      })
      .catch(() => { setLive({ state: "error" }); setBusy(false); });
    check();
  };

  let body = null;
  if (pick && busy && !live) body = <p className="wc-msg">Checking…</p>;
  else if (pick && live) {
    const away = pick.away, home = pick.home;
    if (live.state === "scheduled") body = <p className="wc-msg">Not live yet: {away} at {home} tips at {tipTime(live.tipoff_utc || pick.tip)}.</p>;
    else if (live.state === "final") body = <p className="wc-msg">Final: {away} {live.away_score}, {home} {live.home_score}.</p>;
    else if (live.state === "not_today") body = <p className="wc-msg">That game isn't on today's slate.</p>;
    else if (live.state !== "live") body = <p className="wc-msg">Couldn't tell whether that game is live. Try again in a minute.</p>;
    else {
      const secs = clockSecs(live.clock), per = live.period || 1, tm = minutesLeft(per, secs);
      const lead = (live.home_score ?? 0) - (live.away_score ?? 0);
      const exp = (pick.home_pred ?? 0) - (pick.away_pred ?? 0);
      const w = winChance(lead, tm, exp);
      const favTeam = w.homeFav ? home : away, trail = lead > 0 ? away : home;
      const r = v => (v === "already" ? "already" : pctText(v));
      body = <>
        <div className="wc-board">
          <span className="wc-side"><TeamChip team={away} /><b>{live.away_score}</b></span>
          <span className="wc-clock">{per === 2 && secs === 0 ? "Halftime" : clockText(per, secs)}</span>
          <span className="wc-side"><b>{live.home_score}</b><TeamChip team={home} /></span>
        </div>
        <div className="wc-nums">
          <div><span><TeamChip team={favTeam} bare /> favored</span><b>{pctText(w.fav)}</b></div>
          <div><span><TeamChip team={favTeam} bare /> stays favored to the end</span><b>{pctText(w.stays)}</b></div>
        </div>
        {lead !== 0 && <div className="wc-reach">
          <div><span>{trail} gets within 6</span><b>{r(w.within6)}</b></div>
          <div><span>{trail} gets within 3</span><b>{r(w.within3)}</b></div>
          <div><span>{trail} ties it</span><b>{r(w.ties)}</b></div>
        </div>}
        <p className="wc-msg">Updates every 30 seconds while the game is live{live.stale_s > 120 ? ` — last update ${Math.round(live.stale_s / 60)} min ago` : ""}.</p>
      </>;
    }
  }

  return (
    <div className="site-ui stats-ui" style={{ minHeight: "100vh" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1100, boxSizing: "border-box", minWidth: 0 }}>
        <StatsNav />
        <div className="rb-head">
          <h1 className="rb-title">Games</h1>
          <span className="rb-meta">live win chance</span>
        </div>
        <GamesTabs />
        {games === null && <p style={{ fontSize: 14 }}>Loading…</p>}
        {games && !games.length && <p className="rb-empty">No games today.</p>}
        {games && games.length > 0 && <div className="wc-list">
          {games.map(g => (
            <button key={g.game_id} className={`wc-game${pick?.game_id === g.game_id ? " on" : ""}`} onClick={() => ask(g)}>
              <span className="wc-tip">{tipTime(g.tip)}</span>
              <TeamChip team={g.away} /><span className="wc-at">@</span><TeamChip team={g.home} />
            </button>))}
        </div>}
        {body}
      </div>
    </div>
  );
}
