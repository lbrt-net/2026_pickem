import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import FantasyShell from "../../../components/fantasy/FantasyShell";
import { base, useFantasyApi } from "../../../components/fantasy/data";
import * as art from "./art";
import "./PlayerPage.css";

// The player page (approved design, 2026-10-14): card front · stats panel · card back, then the sections printed on
// the panel's own frame. Drawing is art.js (the mockup's builders, fed GET /players/{id}/page); this file paints the
// strings, tints the All-NBA chrome, lays the frames on and handles the switches.
const SECTIONS = ["Overview", "Game Log", "Transactions", "Availability", "Extras"];
const GOLD = "padding:6px;background:linear-gradient(100deg, transparent 0 12%, rgba(255,250,225,.95) 14%, transparent 17% 52%, rgba(255,246,210,.8) 54%, transparent 57%), linear-gradient(180deg, #fff1c0 0%, #c9952f 12%, #5e3a08 30%, #e8bd5c 46%, #3a2204 58%, #b88428 74%, #fff0bc 88%, #7a5110 100%);";

function applyFrames(root) {
  root.querySelectorAll("[data-frame]").forEach(el => {
    const f = decodeURIComponent(el.dataset.frame);
    if (f) el.setAttribute("style", f);
  });
  root.querySelectorAll(".front .tx .nm").forEach(n => {
    n.style.overflow = "hidden";
    let fs = 25;
    while (n.scrollWidth > n.clientWidth && fs > 13) { fs -= 0.5; n.style.fontSize = fs + "px"; }
  });
}

export default function PlayerPage() {
  const { id } = useParams();
  const data = useFantasyApi(`players/${id}/page`);
  const hdr = useRef(null), inner = useRef(null), panel = useRef(null);
  const [tinted, setTinted] = useState(null); // {data, url}: the All-NBA background made for this payload
  const [tick, setTick] = useState(0); // bumped by a switch (mode / season / section) to re-draw the panel

  // load the payload into the builders (before anything reads them), then reset the switches for a new player
  useMemo(() => {
    if (!data) return;
    art.load(data, base());
    art.set("section", "Overview");
    art.set("mode", "fp");
  }, [data]);
  const bg = tinted && tinted.data === data ? tinted.url : null;
  const view = data ? { ...art.state(), tick } : null;

  // All-NBA cards: the chrome template (picked by player id), tinted with the team's primary
  useEffect(() => {
    if (!data || data.player.tier !== "allnba") return;
    const n = Number(id) || 0;
    art.chromeTint(art.colors().P1, url => setTinted({ data, url }), 18, 1.5, 0, 7, `/player-art/chrome-${n % 8}.png`, (n % 2147483646) + 1);
  }, [data, id]);

  // header: card front · stats panel · card back
  useLayoutEffect(() => {
    if (!data || !hdr.current) return;
    hdr.current.innerHTML = art.headerHtml(bg || "");
    applyFrames(hdr.current);
  }, [data, bg]);

  // the section panel's frame (same tier art as the cards)
  useLayoutEffect(() => {
    if (!data || !panel.current) return;
    const { P1, S1, T1 } = art.colors();
    const tier = data.player.tier;
    const f = tier === "mvp" ? GOLD : art.frameAt(1100, 300, () => art.frameFor(tier, P1, S1, T1, 11));
    panel.current.setAttribute("style", f);
  }, [data]);

  // the open section
  useLayoutEffect(() => {
    if (!data || !inner.current) return;
    inner.current.innerHTML = art.sectionHtml();
  }, [data, tick]);

  function onClick(e) {
    const el = e.target.closest("[data-act]");
    if (!el) return;
    art.set(el.dataset.act, el.dataset.v);
    setTick(n => n + 1);
  }

  if (data === undefined) return <FantasyShell title="Player"><p className="ppg-msg">Loading…</p></FantasyShell>;
  if (!data) return <FantasyShell title="Player"><p className="ppg-msg">No such player.</p></FantasyShell>;

  const { P1, S1 } = art.colors();
  const vars = {
    "--p": P1, "--p-hi": art.mix(P1, "#ffffff", 0.25), "--p-lo": art.mix(P1, "#000000", 0.55), "--s-hi": art.mix(S1, "#ffffff", 0.3),
  };
  return (
    <FantasyShell title="Player">
      <div className="ppg" style={vars}>
        <div className="hdr" ref={hdr} />
        <div className="fp tcg" ref={panel}>
          <div className="band">
            {SECTIONS.map(s => (
              <span key={s} className={view?.SECTION === s ? "on" : ""} data-act="section" data-v={s} onClick={onClick}>{s}</span>
            ))}
          </div>
          <div className="inner" ref={inner} style={{ display: "block" }} onClick={onClick} />
        </div>
      </div>
    </FantasyShell>
  );
}
