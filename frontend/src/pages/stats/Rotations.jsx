import { useEffect, useMemo, useRef, useState } from "react";
import MainNav from "../../components/shared/MainNav";
import StatsNav from "./StatsNav";
import { TeamChip } from "./StatsControls";
import { useLeague } from "./statsLeague";
import "./Rebounding.css";
import "./Rotations.css";

// /stats/lineups and /wnba/stats/lineups (2026-10-20): the lineup visualizer — a team's rotation pattern. Rows = every
// player who played for the team in the chosen games; columns = the game clock in four quarter panels (30-second
// slices); color = how often he was on the floor at that moment across those games. Games narrowed by a date range and
// conditions on players: played / played his normal minutes / missed. Static files from nba-pipeline/models/rotations.py
// (public/rotations/<season>/). Stats never link into fantasy.
const SEASONS = { nba: "2025-26", wnba: "2026" };
const base = league => `/rotations/${league === "wnba" ? "wnba-" : ""}${SEASONS[league]}`;
const MODES = [["played", "played"], ["normal", "played normal minutes"], ["missed", "missed"]];

// a player's normal minutes: inside the box-plot fences (1.5 × IQR beyond the quartiles) of all his games for this team
function fences(mins) {
  const v = mins.filter(x => x != null).sort((a, b) => a - b);
  if (v.length < 4) return [-Infinity, Infinity];
  const q = p => { const k = (v.length - 1) * p, lo = Math.floor(k), hi = Math.ceil(k); return v[lo] + (v[hi] - v[lo]) * (k - lo); };
  const q1 = q(0.25), q3 = q(0.75), iqr = q3 - q1;
  return [q1 - 1.5 * iqr, q3 + 1.5 * iqr];
}

function Heat({ rows, slices, quarter, bin, nGames }) {
  const ref = useRef(null), wrap = useRef(null);
  const [w, setW] = useState(900);
  const [tip, setTip] = useState(null);
  useEffect(() => {
    const ro = new ResizeObserver(e => setW(Math.max(560, Math.floor(e[0].contentRect.width))));
    if (wrap.current) ro.observe(wrap.current);
    return () => ro.disconnect();
  }, []);
  const LAB = 230, GAP = 10, RH = 22, TOP = 26, perQ = slices / 4;
  const pw = (w - LAB - 3 * GAP) / 4, cw = pw / perQ, H = TOP + rows.length * RH + 6;
  useEffect(() => {
    const xOf = j => LAB + Math.floor(j / perQ) * (pw + GAP) + (j % perQ) * cw;
    const c = ref.current; if (!c) return;
    const dpr = window.devicePixelRatio || 1; c.width = w * dpr; c.height = H * dpr; c.style.width = `${w}px`; c.style.height = `${H}px`;
    const g = c.getContext("2d"); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, w, H);
    const css = getComputedStyle(c), text = css.getPropertyValue("--text").trim() || "#eee", acc = css.getPropertyValue("--accent").trim() || "#f60", bg = css.getPropertyValue("--surface-2").trim() || "#222";
    const rgbOf = s => { const c = document.createElement("canvas").getContext("2d"); c.fillStyle = s; const h = c.fillStyle.replace("#", ""); return h.length === 6 ? [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16)) : [40, 40, 40]; };
    const A = rgbOf(acc), Bg = rgbOf(bg);
    g.font = "700 13px " + (css.getPropertyValue("--font-body") || "sans-serif"); g.fillStyle = text; g.textBaseline = "middle"; g.textAlign = "center";
    ["1st", "2nd", "3rd", "4th"].forEach((l, q) => g.fillText(l, LAB + q * (pw + GAP) + pw / 2, 12));
    rows.forEach((r, y) => {
      const yy = TOP + y * RH;
      g.textAlign = "left"; g.font = "700 13px " + css.getPropertyValue("--font-body"); g.fillStyle = text; g.fillText(r.name, 0, yy + RH / 2);
      g.textAlign = "right"; g.font = "500 12px " + css.getPropertyValue("--font-body"); g.fillText(`${r.gp} g · ${r.mpg.toFixed(1)} min`, LAB - 10, yy + RH / 2);
      for (let q = 0; q < 4; q++) { g.fillStyle = bg; g.fillRect(LAB + q * (pw + GAP), yy + 1, pw, RH - 2); }
      // solid colors mixed from the panel to the accent (no transparency: overlapping slices would stripe)
      r.share.forEach((v, j) => {
        if (v < 0.01) return; const k = 0.12 + 0.88 * v;
        g.fillStyle = `rgb(${A.map((x, n) => Math.round(Bg[n] + (x - Bg[n]) * k)).join(",")})`;
        g.fillRect(Math.floor(xOf(j)), yy + 1, Math.ceil(cw) + 1, RH - 2);
      });
    });
  }, [rows, w, H, pw, cw, perQ]);
  const onMove = e => {
    const r = ref.current.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
    const row = Math.floor((y - TOP) / RH), q = Math.floor((x - LAB) / (pw + GAP)), inq = x - LAB - q * (pw + GAP);
    if (row < 0 || row >= rows.length || q < 0 || q > 3 || inq < 0 || inq > pw) { setTip(null); return; }
    const j = q * perQ + Math.floor(inq / cw), sec = (j % perQ) * bin, clock = quarter * 60 - sec;
    const mm = Math.floor(clock / 60), ss = String(clock % 60).padStart(2, "0");
    setTip({ x: e.clientX, y: e.clientY, t: `${rows[row].name} · Q${q + 1} ${mm}:${ss}: on the floor in ${Math.round(100 * rows[row].share[j])}% of the ${nGames} games` });
  };
  return (
    <div ref={wrap} className="rt-wrap">
      <canvas ref={ref} onMouseMove={onMove} onMouseLeave={() => setTip(null)} />
      {tip && <div className="rt-tip" style={{ left: Math.min(tip.x + 14, window.innerWidth - 320), top: tip.y + 14 }}>{tip.t}</div>}
    </div>
  );
}

export default function Rotations() {
  const league = useLeague(), B = base(league);
  const [idx, setIdx] = useState(null);
  const [team, setTeam] = useState("");
  const [T, setT] = useState(null);
  const [conds, setConds] = useState([]);
  const [range, setRange] = useState(["", ""]);
  useEffect(() => { fetch(`${B}/index.json`).then(r => r.json()).then(d => { setIdx(d); setTeam(t => (d.teams.includes(t) ? t : d.teams[0])); }).catch(() => setIdx({ teams: [] })); }, [B]);
  useEffect(() => {
    if (!team) return;
    let live = true;
    fetch(`${B}/${team}.json`).then(r => r.json()).then(d => {
      if (!live) return;
      setT(d); setConds([]); setRange([d.games[0]?.d || "", d.games[d.games.length - 1]?.d || ""]);
    });
    return () => { live = false; };
  }, [B, team]);

  const view = useMemo(() => {
    if (!T || !idx) return null;
    const G = T.games, n = T.players.length, S = idx.slices, bin = idx.bin;
    const info = T.players.map((p, i) => {
      const played = G.map((g, k) => (g.m[i] != null ? k : -1)).filter(k => k >= 0);
      return { first: played[0] ?? -1, last: played[played.length - 1] ?? -1, fence: fences(G.map(g => g.m[i])) };
    });
    const ok = (g, k, c) => {
      const m = g.m[c.p];
      if (c.mode === "played") return m != null;
      if (c.mode === "normal") return m != null && m >= info[c.p].fence[0] && m <= info[c.p].fence[1];
      return m == null && k >= info[c.p].first && k <= info[c.p].last;   // missed: a game inside his stretch with the team
    };
    const games = G.filter((g, k) => (!range[0] || g.d >= range[0]) && (!range[1] || g.d <= range[1]) && conds.every(c => ok(g, k, c)));
    const rows = [];
    for (let i = 0; i < n; i++) {
      const on = new Array(S).fill(0); let gp = 0, mins = 0;
      for (const g of games) {
        if (g.m[i] == null) continue;
        gp++; mins += g.m[i];
        const s = g.s[i]; if (s) for (let j = 0; j < S; j++) on[j] += s[j] / bin;
      }
      if (gp === 0) continue;
      rows.push({ name: T.players[i].name, gp, mpg: mins / gp, avg: mins / games.length, share: on.map(v => v / games.length) });
    }
    rows.sort((a, b) => b.avg - a.avg);
    const w = games.filter(g => g.pts > g.opts).length;
    return { games, rows, w, l: games.length - w };
  }, [T, idx, conds, range]);

  return (
    <div className="site-ui stats-ui" style={{ minHeight: "100vh" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1320, boxSizing: "border-box", minWidth: 0 }}>
        <StatsNav />
        <div className="rb-head">
          <h1 className="rb-title">Lineups</h1>
          <span className="rb-meta">{league === "wnba" ? "WNBA " : ""}{idx?.season || SEASONS[league]} · rotation patterns · how often each player was on the floor, moment by moment</span>
        </div>
        <div className="rt-bar">
          <select value={team} onChange={e => setTeam(e.target.value)} aria-label="Team">{(idx?.teams || []).map(t => <option key={t} value={t}>{t}</option>)}</select>
          {T && <>
            <label className="rt-dates">from <input type="date" value={range[0]} min={T.games[0]?.d} max={range[1]} onChange={e => setRange([e.target.value, range[1]])} /></label>
            <label className="rt-dates">to <input type="date" value={range[1]} min={range[0]} max={T.games[T.games.length - 1]?.d} onChange={e => setRange([range[0], e.target.value])} /></label>
          </>}
        </div>
        {T && <div className="rt-bar">
          {conds.map((c, k) => (
            <span key={k} className="rt-cond">
              <select value={c.p} onChange={e => setConds(cs => cs.map((x, j) => (j === k ? { ...x, p: +e.target.value } : x)))} aria-label="Player">
                {T.players.map((p, i) => <option key={p.pid} value={i}>{p.name}</option>)}
              </select>
              <select value={c.mode} onChange={e => setConds(cs => cs.map((x, j) => (j === k ? { ...x, mode: e.target.value } : x)))} aria-label="Condition">
                {MODES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
              <button type="button" onClick={() => setConds(cs => cs.filter((_, j) => j !== k))} aria-label="Remove condition">×</button>
            </span>))}
          <button type="button" className="rt-add" onClick={() => setConds(cs => [...cs, { p: 0, mode: "played" }])}>+ Only games when…</button>
        </div>}
        {view && <div className="rt-head">
          <TeamChip team={team} bare />
          <b>{view.w}-{view.l}</b>
          <span>{view.games.length} of {T.games.length} games</span>
          <span className="rt-legend"><i /> on the floor in 0% … 100% of these games</span>
        </div>}
        {view && (view.games.length === 0 ? <p className="rb-empty">No games match.</p>
          : <Heat rows={view.rows} slices={idx.slices} quarter={idx.quarter} bin={idx.bin} nGames={view.games.length} />)}
      </div>
    </div>
  );
}
