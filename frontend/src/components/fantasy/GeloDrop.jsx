// Easter egg: the moment LaMelo Ball is drafted, a tiny Spotify player pops up in the corner and plays
// "Tweaker" by G3 GELO (his brother) from 0:22. Uses Spotify's official embed (iFrame API): someone logged in to
// Spotify in this browser hears the real track from 0:22; anyone else gets Spotify's own 30-second preview.
// Only fires for a pick made while the page is open, never for a LaMelo already on the board when it loaded.
import { useEffect, useRef, useState } from "react";
import "./GeloDrop.css";

const NAME = "LaMelo Ball";
const URI = "spotify:track:5nk6BxN9bM5rLNkA3pMOzn"; // Tweaker — G3 GELO (original single)
const START_S = 22;

let apiPromise = null;
function spotifyApi() {
  apiPromise ??= new Promise(resolve => {
    window.onSpotifyIframeApiReady = resolve;
    const s = document.createElement("script");
    s.src = "https://open.spotify.com/embed/iframe-api/v1";
    s.async = true;
    document.body.appendChild(s);
  });
  return apiPromise;
}

export default function GeloDrop({ picks }) {
  const [last, setLast] = useState(picks); // the board as of the last render; a new LaMelo pick opens the pop-up
  const [drop, setDrop] = useState(null); // {team}: the pop-up is open
  const [playing, setPlaying] = useState(false);
  const host = useRef(null);
  const ctl = useRef(null);

  if (picks !== last) {
    setLast(picks);
    const before = new Set((last || []).map(p => p.pick));
    const hit = (picks || []).find(p => !before.has(p.pick) && p.name === NAME);
    if (hit) setDrop({ team: hit.team_name });
  }

  useEffect(() => {
    if (!drop) return undefined;
    let gone = false, jumped = false;
    spotifyApi().then(api => {
      if (gone || !host.current) return;
      const el = document.createElement("div");
      host.current.appendChild(el);
      api.createController(el, { uri: URI, width: "100%", height: 80, theme: "dark" }, c => {
        if (gone) { c.destroy(); return; }
        ctl.current = c;
        c.addListener("ready", () => c.play()); // browsers that block autoplay just show the play button
        c.addListener("playback_update", e => {
          const { isPaused, position, duration } = e.data;
          setPlaying(!isPaused);
          // the full track (logged-in listener) starts at 0:22; a 30-second preview plays as Spotify gives it
          if (!jumped && !isPaused && duration > 31000 && position < START_S * 1000) { jumped = true; c.seek(START_S); }
        });
      });
    });
    return () => { gone = true; ctl.current?.destroy(); ctl.current = null; };
  }, [drop]);

  if (!drop) return null;
  return (
    <aside className="gd" aria-label="Now playing">
      <div className="gd-top">
        <span className={`gd-bars${playing ? " on" : ""}`} aria-hidden="true"><i /><i /><i /><i /></span>
        <span className="gd-line"><b>{NAME}</b> to {drop.team}</span>
        <button type="button" className="gd-x" aria-label="Close" onClick={() => { setDrop(null); setPlaying(false); }}>✕</button>
      </div>
      <div className="gd-embed" ref={host} />
    </aside>
  );
}
