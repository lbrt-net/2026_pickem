// Easter egg: the moment LaMelo Ball is drafted, a small YouTube player pops up in the corner and plays
// "Tweaker" by GELO (his brother) from 0:27 — the official video on GELO's own channel, through YouTube's embedded
// player (allowed for any site; it has to stay visible and at least 200×200, YouTube's rule).
// Only fires for a pick made while the page is open, never for a LaMelo already on the board when it loaded.
// Loading: YouTube's script loads with the draft room; the player itself loads (see-through) as soon as he's on
// the auction block, so it can start the instant he's won.
import { useEffect, useRef, useState } from "react";
import "./GeloDrop.css";
import { shake, shockwave } from "./shockwave";

const ID = "1630163";
const NAME = "LaMelo Ball";
const VIDEO = "2Mk7VTUwbck"; // GELO - Tweaker (Official Video), youtube.com/@GeloMusicOfficial
const START_S = 27;          // "I might swerve, bend that corner, woah"

let apiPromise = null;
function youtubeApi() {
  apiPromise ??= new Promise(resolve => {
    if (window.YT?.Player) { resolve(window.YT); return; }
    const prev = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => { prev?.(); resolve(window.YT); };
    const s = document.createElement("script");
    s.src = "https://www.youtube.com/iframe_api";
    s.async = true;
    document.body.appendChild(s);
  });
  return apiPromise;
}

export default function GeloDrop({ picks, onBlock, onDrop, colorOf }) {
  const [last, setLast] = useState(picks); // the board as of the last render; a new LaMelo pick opens the pop-up
  const [drop, setDrop] = useState(null); // {team}: the pop-up is open
  const [playing, setPlaying] = useState(false);
  const host = useRef(null);
  const card = useRef(null);
  const ctl = useRef(null); // {p: YT.Player, ready}
  const show = useRef(false); // play as soon as the player is ready
  const isPlaying = useRef(false);

  if (picks !== last) {
    setLast(picks);
    const before = new Set((last || []).map(p => p.pick));
    const hit = (picks || []).find(p => !before.has(p.pick) && (p.id === ID || p.name === NAME));
    if (hit) setDrop({ team: hit.team_name, pick: hit });
  }
  const armed = !!drop || onBlock === ID;

  useEffect(() => { youtubeApi(); }, []);
  // the same moment slams his cell on the draft board (DraftRoom)
  const onDropRef = useRef(onDrop);
  useEffect(() => { onDropRef.current = onDrop; });
  const colorRef = useRef(colorOf);
  useEffect(() => { colorRef.current = colorOf; });
  useEffect(() => {
    if (!drop) return undefined;
    onDropRef.current?.({ pick: drop.pick.pick, id: drop.pick.id });
    const t = setTimeout(() => { shockwave(card.current, colorRef.current?.(drop.pick.id)); shake(); }, 280); // as the card lands
    return () => clearTimeout(t);
  }, [drop]);

  // the player: built (see-through) once armed, torn down when disarmed or closed
  useEffect(() => {
    if (!armed) return undefined;
    let gone = false;
    const box = host.current;
    youtubeApi().then(YT => {
      if (gone || !box) return;
      const el = document.createElement("div");
      box.appendChild(el);
      const p = new YT.Player(el, {
        videoId: VIDEO, width: "100%", height: "100%",
        playerVars: { start: START_S, playsinline: 1, rel: 0, modestbranding: 1 },
        events: {
          onReady: () => {
            if (gone) return;
            ctl.current = { p, ready: true };
            p.setVolume(100);
            if (show.current) p.playVideo(); // browsers that block autoplay just show the play button
          },
          onStateChange: e => {
            const on = e.data === YT.PlayerState.PLAYING;
            isPlaying.current = on;
            setPlaying(on);
          },
        },
      });
      ctl.current = { p, ready: false };
    });
    return () => {
      gone = true;
      const p = ctl.current?.p;
      ctl.current = null;
      isPlaying.current = false;
      if (p) { try { p.stopVideo(); p.destroy(); } catch { /* already gone */ } }
      if (box) box.innerHTML = "";
    };
  }, [armed]);

  // he's won: show it and play (now if the player is loaded, else on its ready), asking again over the next
  // second if it still isn't playing — a player that was loaded out of sight can miss the first ask
  useEffect(() => {
    show.current = !!drop;
    if (!drop) return undefined;
    const ask = () => { if (ctl.current?.ready && !isPlaying.current) ctl.current.p.playVideo(); };
    ask();
    const t1 = setTimeout(ask, 400), t2 = setTimeout(ask, 1200);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [drop]);

  const close = () => {
    try { ctl.current?.p.pauseVideo(); } catch { /* not ready */ }
    isPlaying.current = false;
    setDrop(null);
    setPlaying(false);
  };

  if (!armed) return null;
  return (
    <aside ref={card} className={`gd${drop ? " show" : " pre"}`} aria-label="Now playing" aria-hidden={!drop}>
      <div className="gd-top">
        <span className={`gd-bars${playing ? " on" : ""}`} aria-hidden="true"><i /><i /><i /><i /></span>
        <span className="gd-line"><b>{NAME}</b>{drop && <> to {drop.team}</>}</span>
        <button type="button" className="gd-x" aria-label="Close" onClick={close}>✕</button>
      </div>
      <div className="gd-embed" ref={host} />
    </aside>
  );
}
