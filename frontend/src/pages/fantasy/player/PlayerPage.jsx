import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import FantasyShell from "../../../components/fantasy/FantasyShell";
import { API_BASE, base, useFantasyApi } from "../../../components/fantasy/data";
import { API } from "../../../utils/helpers";
import * as art from "./art";
import loadFont from "../../../utils/loadFont";

loadFont(art.ART_FONTS);
import "./PlayerPage.css";

// The player page (approved design, 2026-10-14): card front · stats panel · card back, then the sections printed on
// the panel's own frame. Drawing is art.js (the mockup's builders, fed GET /players/{id}/page); this file paints the
// strings, tints the All-NBA chrome, lays the frames on and handles the switches.
const SECTIONS = ["Overview", "Game Log", "Transactions", "Availability", "Extras"];
const TEAM_SECTIONS = ["Overview", "Game Log", "Transactions"]; // NBA teams: no availability or shot chart
// the MVP gold (same stops as the gold cards), as a picture so it can be a border image
const GOLD_SVG = `<svg xmlns='http://www.w3.org/2000/svg' width='1100' height='300'><defs><linearGradient id='g' x1='0' y1='0' x2='0' y2='1'>${[["0", "#fff1c0"], [".12", "#c9952f"], [".3", "#5e3a08"], [".46", "#e8bd5c"], [".58", "#3a2204"], [".74", "#b88428"], [".88", "#fff0bc"], ["1", "#7a5110"]].map(([o, c]) => `<stop offset='${o}' stop-color='${c}'/>`).join("")}</linearGradient><linearGradient id='s' x1='0' y1='0' x2='1' y2='.25'><stop offset='.12' stop-color='#fffae1' stop-opacity='0'/><stop offset='.14' stop-color='#fffae1' stop-opacity='.95'/><stop offset='.17' stop-color='#fffae1' stop-opacity='0'/><stop offset='.52' stop-color='#fff6d2' stop-opacity='0'/><stop offset='.54' stop-color='#fff6d2' stop-opacity='.8'/><stop offset='.57' stop-color='#fff6d2' stop-opacity='0'/></linearGradient></defs><rect width='100%' height='100%' fill='url(#g)'/><rect width='100%' height='100%' fill='url(#s)'/></svg>`;
const GOLD = `url("data:image/svg+xml,${encodeURIComponent(GOLD_SVG)}")`;

// A frame style (background:url(...) [, more layers]) → the panel's border image. The brushed-metal (All-NBA) frame is
// painted at 2× so its slices are in doubled pixels; plain frames keep their grain + team color underneath.
function borderFrame(tier, f) {
  const urls = [...f.matchAll(/url\("([^"]+)"\)/g)].map(m => m[1]);
  const img = tier === "mvp" ? GOLD : `url("${urls[0]}")`;
  const k = tier === "allnba" ? 2 : 1;
  const under = tier === "plain" ? f.replace(/^background:url\("[^"]+"\),\s*/, "background:") : "";
  return `border-image:${img} ${38 * k} ${10 * k} ${10 * k} fill stretch;${under}`;
}

// The accent (headings, totals, percentiles) is the team's second color, lifted toward white until it reads on the dark
// panel (no dim text): navy or black second colors come out light.
function accent(hex) {
  const lum = h => { const n = parseInt(h.slice(1), 16); return (0.3 * (n >> 16) + 0.59 * ((n >> 8) & 255) + 0.11 * (n & 255)) / 255; };
  let t = 0.3, c = art.mix(hex, "#ffffff", t);
  while (lum(c) < 0.6 && t < 0.9) { t += 0.1; c = art.mix(hex, "#ffffff", t); }
  return c;
}

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
  const teams = useFantasyApi("teams");
  const nav = useNavigate();
  const hdr = useRef(null), inner = useRef(null), panel = useRef(null), shotsFor = useRef(null); // the payload whose shots were fetched
  const [tinted, setTinted] = useState(null); // {data, url}: the All-NBA background made for this payload
  const [tick, setTick] = useState(0); // bumped by a switch (mode / season / section) to re-draw the panel

  // load the payload into the builders (before anything reads them), then reset the switches for a new player
  useMemo(() => {
    if (!data) return;
    art.load(data, base());
    art.set("section", "Overview");
    art.set("mode", "fp");
  }, [data]);
  useMemo(() => { if (data && teams) art.setTeams(teams); }, [data, teams]);
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

  // Phone (2026-10-15): the card front and back sit side by side, shrunk to fit; the stats panel goes underneath at
  // its desktop width (552px), scaled to the screen. --cz / --mz are those scales (CSS uses them under 760px).
  useLayoutEffect(() => {
    const el = hdr.current;
    if (!el) return undefined;
    const fit = () => {
      const w = el.clientWidth;
      el.style.setProperty("--cz", String(Math.min(1, (w - 10) / 2 / 260)));
      el.style.setProperty("--mz", String(Math.min(1, w / 552)));
    };
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(el);
    return () => ro.disconnect();
  }, [data]);

  // the section panel's frame (same tier art as the cards)
  useLayoutEffect(() => {
    if (!data || !panel.current) return;
    const { P1, S1, T1 } = art.colors();
    const tier = data.player.tier;
    const f = tier === "mvp" ? "" : art.frameAt(1100, 300, () => art.frameFor(tier, P1, S1, T1, 11));
    panel.current.setAttribute("style", borderFrame(tier, f));
  }, [data]);

  // the open section
  useLayoutEffect(() => {
    if (!data || !inner.current) return;
    inner.current.innerHTML = art.sectionHtml();
  }, [data, tick, teams]);

  // the game log's week / date pickers live in the painted HTML, which React's onChange doesn't see: a plain listener
  useEffect(() => {
    const el = inner.current;
    if (!el) return;
    const onChange = e => {
      const t = e.target.closest("[data-act]");
      if (!t || !["gllo", "glhi"].includes(t.dataset.act)) return;
      art.set(t.dataset.act, t.value);
      setTick(n => n + 1);
    };
    el.addEventListener("change", onChange);
    return () => el.removeEventListener("change", onChange);
  }, [data]);

  function onClick(e) {
    const a = e.target.closest("a[data-nav]");  // a team chip in Fantasy moves: go there in-app
    if (a && !(e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0)) { e.preventDefault(); nav(a.getAttribute("href")); return; }
    const el = e.target.closest("[data-act]");
    if (!el || el.tagName === "SELECT" || el.tagName === "INPUT") return;
    art.set(el.dataset.act, el.dataset.v);
    setTick(n => n + 1);
    if (el.dataset.act === "section" && el.dataset.v === "Extras" && shotsFor.current !== data) {  // shots load on first open
      shotsFor.current = data;
      fetch(`${API}${API_BASE}/players/${id}/shots`).then(r => (r.ok ? r.json() : {})).catch(() => ({}))
        .then(d => { art.setShots(d); setTick(n => n + 1); });
    }
  }

  if (data === undefined) return <FantasyShell title="Player"><p className="ppg-msg">Loading…</p></FantasyShell>;
  if (!data) return <FantasyShell title="Player"><p className="ppg-msg">No such player.</p></FantasyShell>;

  const { P1, S1 } = art.colors();
  const vars = {
    "--p": P1, "--p-hi": art.mix(P1, "#ffffff", 0.25), "--p-lo": art.mix(P1, "#000000", 0.55), "--s-hi": accent(S1),
  };
  return (
    <FantasyShell title={data.player.kind === "team" ? "Team" : "Player"}>
      <div className={`ppg tier-${data.player.tier}`} style={vars}>
        <div className="hdr" ref={hdr} />
        <div className="fpw"><div className="fp tcg" ref={panel}>
          <div className="band">
            {SECTIONS.filter(s => data.player.kind !== "team" || TEAM_SECTIONS.includes(s)).map(s => (
              <span key={s} className={view?.SECTION === s ? "on" : ""} data-act="section" data-v={s} onClick={onClick}>{s}</span>
            ))}
          </div>
          <div className="inner" ref={inner} style={{ display: "block" }} onClick={onClick} />
        </div></div>
      </div>
    </FantasyShell>
  );
}
