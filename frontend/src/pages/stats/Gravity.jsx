import { useEffect, useMemo, useRef, useState } from "react";
import MainNav from "../../components/shared/MainNav";
import StatsNav from "./StatsNav";
import { TeamChip } from "./StatsControls";
import "./Rebounding.css";
import "./Gravity.css";

// /stats/gravity (2026-10-19): every rotation player's on/off effect on where his teammates shoot (offense) or where
// opponents shoot against his team (defense), and how well they make them there. Table numbers are points per 75 of the
// shooters' own field-goal attempts: distribution = (share on − share off) × 75 × points per shot off, shooting = share
// on × 75 × (points per shot on − off), per zone, adding to the total. Click a row for his court: the 3D surface (how
// much more / less often from each spot), the flat map (points per shot there) and the zone table.
// Data: static files from nba-pipeline/analysis/onoff_gravity_batch.py in public/gravity/<season>/ — index.json and one
// grid file per team and side (signed bytes: shot-share change %, then points-per-shot change %). Stats never link into fantasy.
const SEASON = "2025-26";
const BASE = `/gravity/${SEASON}`;

// colors match the reviewed relief pages: teal → blue → indigo for less often, beige = same, yellow → orange → red more
const LAND = [236, 230, 216];
const VALE = [[0.03, LAND], [0.06, [170, 215, 205]], [0.12, [70, 172, 170]], [0.22, [22, 112, 152]], [0.4, [34, 58, 132]], [1, [44, 18, 82]]];
const PEAK = [[0.03, LAND], [0.06, [248, 216, 118]], [0.12, [242, 160, 38]], [0.22, [216, 88, 22]], [0.4, [172, 30, 40]], [1, [112, 8, 62]]];
function hcol(r) {
  const a = Math.min(1, Math.abs(r)); if (a < 0.03) return LAND; const S = r > 0 ? PEAK : VALE;
  for (let n = 1; n < S.length; n++) if (a <= S[n][0]) { const [x0, c0] = S[n - 1], [x1, c1] = S[n], t = (a - x0) / (x1 - x0); return c0.map((e, k) => Math.round(e + (c1[k] - e) * t)); }
  return S[S.length - 1][1];
}
const HOT = [207, 74, 44], COLD = [47, 109, 184], CREAM = [246, 241, 230];
function rgb(v) { const a = Math.abs(v); if (a < 0.04) return CREAM; const t = Math.min(1, (a - 0.04) / 0.26) ** 0.8, c = v > 0 ? HOT : COLD; return CREAM.map((e, k) => Math.round(e + (c[k] - e) * t)); }
const css = c => `rgb(${c})`;
const pct = v => `${(100 * v).toFixed(1)}%`;
const f1 = v => (Math.abs(v) < 0.05 ? "0.0" : (v > 0 ? "+" : "−") + Math.abs(v).toFixed(1));
const YC = Math.sqrt(23.75 ** 2 - 22 ** 2), A0 = Math.atan2(YC, 22);

const COLS = [
  { key: "name", label: "Player", left: true, v: r => r.name },
  { key: "team", label: "Team", left: true, v: r => r.team },
  { key: "shots", label: "Shots on", grp: true, v: r => r.on.shots, f: r => r.on.shots.toLocaleString() },
  { key: "efg", label: "eFG off → on", v: r => r.on.efg - r.off.efg, f: r => `${pct(r.off.efg)} → ${pct(r.on.efg)}` },
  { key: "distribution", label: "Distribution", grp: true, v: r => r.distribution, f: r => f1(r.distribution) },
  { key: "shooting", label: "Shooting", v: r => r.shooting, f: r => f1(r.shooting) },
  { key: "total", label: "Total", big: true, v: r => r.total, f: r => f1(r.total) },
];
const LEDE = {
  o: "His teammates' shots with him on the floor vs off. Distribution, shooting and total: points per 75 of the teammates' own field-goal attempts — where they shoot from, how well they make them there, and both.",
  d: "Opponents' shots against his team with him on the floor vs off. Distribution, shooting and total: points per 75 of the opponents' field-goal attempts (negative = fewer points for opponents).",
};

export default function Gravity() {
  const [D, setD] = useState(null);
  const [err, setErr] = useState(false);
  const [side, setSide] = useState("o");
  const [sort, setSort] = useState({ key: "total", dir: -1 });
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(null);
  useEffect(() => {
    fetch(`${BASE}/index.json`).then(r => r.json()).then(setD).catch(() => setErr(true));
  }, []);
  const rows = useMemo(() => {
    if (!D) return [];
    const col = COLS.find(c => c.key === sort.key), s = q.trim().toLowerCase();
    return D.rows.filter(r => r.side === side && (!s || r.name.toLowerCase().includes(s) || r.team.toLowerCase().includes(s)))
      .sort((a, b) => { const x = col.v(a), y = col.v(b); return (typeof x === "string" ? x.localeCompare(y) : x - y) * sort.dir; });
  }, [D, side, sort, q]);
  const pickSide = s => { setSide(s); setSort({ key: "total", dir: s === "o" ? -1 : 1 }); };
  const clickHead = k => setSort(p => (p.key === k ? { key: k, dir: -p.dir } : { key: k, dir: k === "name" || k === "team" ? 1 : -1 }));
  return (
    <div className="site-ui stats-ui" style={{ minHeight: "100vh" }}>
      <MainNav />
      <div style={{ padding: "24px clamp(16px, 4vw, 24px)", maxWidth: 1240, boxSizing: "border-box", minWidth: 0 }}>
        <StatsNav />
        <div className="rb-head">
          <h1 className="rb-title">Gravity</h1>
          <span className="rb-meta">{SEASON} regular season · on vs off</span>
        </div>
        <p className="gv-lede">{LEDE[side]} Click a player for his court.</p>
        <div className="rb-bar">
          <div className="rb-seg" role="radiogroup" aria-label="Side">
            {[["o", "Offense"], ["d", "Defense"]].map(([v, l]) => <button key={v} role="radio" aria-checked={side === v} onClick={() => pickSide(v)}>{l}</button>)}
          </div>
          <input className="gv-q" type="search" placeholder="Player or team" value={q} onChange={e => setQ(e.target.value)} aria-label="Filter by player or team" />
        </div>
        <div className="rb-card">
          <table className="rb-table">
            <thead><tr>{COLS.map(c => (
              <th key={c.key} className={`${c.left ? "l " : ""}${c.grp ? "g " : ""}${sort.key === c.key ? "on" : ""}`} onClick={() => clickHead(c.key)}
                aria-sort={sort.key === c.key ? (sort.dir > 0 ? "ascending" : "descending") : undefined}>{c.label}</th>))}</tr></thead>
            <tbody>
              {err && <tr><td className="l rb-empty" colSpan={COLS.length}>Couldn't load the data.</td></tr>}
              {!D && !err && <tr><td className="l rb-empty" colSpan={COLS.length}>Loading…</td></tr>}
              {rows.map(r => (
                <tr key={`${r.pid}|${r.team}|${r.side}`} className={sel === r ? "sel" : ""} onClick={() => setSel(r)}>
                  {COLS.map(c => c.key === "name" ? <td key={c.key} className="name l">{r.name}</td>
                    : c.key === "team" ? <td key={c.key} className="team l"><TeamChip team={r.team} /></td>
                    : <td key={c.key} className={`${c.grp ? "g " : ""}${c.big ? "big" : ""}`}>{c.f(r)}</td>)}
                </tr>))}
            </tbody>
          </table>
        </div>
      </div>
      {sel && D && <Side key={`${sel.pid}|${sel.team}|${sel.side}`} r={sel} grid={D.grid} zmax={D.zmax} onClose={() => setSel(null)} />}
    </div>
  );
}

const bins = {};
function loadGrids(r, grid) {
  const key = `${r.team}_${r.side}`;
  if (!bins[key]) bins[key] = fetch(`${BASE}/g/${key}.bin`).then(x => x.arrayBuffer()).then(b => new Int8Array(b));
  const n = grid.nx * grid.ny;
  return bins[key].then(all => ({ h: all.subarray(r.offset, r.offset + n), rel: all.subarray(r.offset + n, r.offset + 2 * n) }));
}

function Side({ r, grid, zmax, onClose }) {
  const [g, setG] = useState(null);
  useEffect(() => {
    let live = true;   // a new player remounts Side (keyed), so g starts empty
    loadGrids(r, grid).then(x => { if (live) setG(x); });
    return () => { live = false; };
  }, [r, grid]);
  useEffect(() => {
    const k = e => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k);
  }, [onClose]);
  const sum = k => r.zones.reduce((s, z) => s + z[k], 0);
  const who = r.side === "o" ? "Teammates'" : "Opponents'";
  return (
    <aside className="gv-side" aria-label={`${r.name} court`}>
      <div className="gv-side-head">
        <div><h2>{r.name}</h2><p>{r.team} · {r.side === "o" ? "offense" : "defense"} · {r.off.shots.toLocaleString()} shots with him off, {r.on.shots.toLocaleString()} on</p></div>
        <button type="button" className="gv-close" onClick={onClose}>Close</button>
      </div>
      <section className="gv-card">
        <h3>Where the shots moved</h3>
        <Surface g={g} grid={grid} zmax={zmax} />
        <div className="gv-leg"><span className="gv-ramp">{[-1, -0.4, -0.22, -0.12, -0.06, 0, 0.06, 0.12, 0.22, 0.4, 1].map(v => <i key={v} style={{ background: css(hcol(v)) }} />)}</span> fewer · same · more shots here per 75 of their attempts, him on vs off (one scale for every player)</div>
        <div className="gv-zt-wrap">
          <table className="gv-zt">
            <caption>{who} points per 75 of their field-goal attempts, him on vs off</caption>
            <thead><tr><th>Zone</th><th>Share of shots</th><th>Points per shot</th><th>Distribution</th><th>Shooting</th><th>Total</th></tr></thead>
            <tbody>
              {r.zones.map(z => (
                <tr key={z.zone}><td>{z.zone}</td><td>{(100 * z.share_off).toFixed(1)}% → {(100 * z.share_on).toFixed(1)}%</td>
                  <td>{z.pps_off.toFixed(2)} → {z.pps_on.toFixed(2)}</td><td>{f1(z.distribution)}</td><td>{f1(z.shooting)}</td><td className="tot">{f1(z.total)}</td></tr>))}
              <tr className="all"><td>All</td><td></td><td></td><td>{f1(sum("distribution"))}</td><td>{f1(sum("shooting"))}</td><td>{f1(sum("total"))}</td></tr>
            </tbody>
          </table>
        </div>
      </section>
      <section className="gv-card">
        <h3>How well they shot there</h3>
        <Flat g={g} grid={grid} />
        <div className="gv-leg"><span className="gv-ramp">{[-0.3, -0.2, -0.12, -0.04, 0, 0.04, 0.12, 0.2, 0.3].map(v => <i key={v} style={{ background: css(rgb(v)) }} />)}</span> −30% · even · +30% points per shot, on vs off</div>
      </section>
    </aside>
  );
}

// the 3D surface: x, y on the court, height = shots gained / lost per 75 of the shooters' FGA per 100 sq ft, him on vs off,
// on one fixed scale for every player (index zmax) — absolute, so a spot that goes from no shots to a few stays small
function Surface({ g, grid, zmax }) {
  const host = useRef(null), tip = useRef(null);
  useEffect(() => {
    if (!g || !host.current) return;
    let dead = false, P = null;
    import("plotly.js-gl3d-dist-min").then(mod => {
      if (dead) return; P = mod.default || mod;
      const { x0, y0, dx, nx, ny } = grid, xs = [], ys = [], z = [];
      for (let i = 0; i < nx; i++) xs.push(x0 + i * dx);
      for (let j = 0; j < ny; j++) { ys.push(y0 + j * dx); const row = []; for (let i = 0; i < nx; i++) row.push(g.h[j * nx + i] / 100 * zmax); z.push(row); }
      const at = (x, y) => g.h[Math.max(0, Math.min(ny - 1, Math.round((y - y0) / dx))) * nx + Math.max(0, Math.min(nx - 1, Math.round((x - x0) / dx)))] / 100 * zmax + zmax * 0.008;
      const lines = [], seg = pts => lines.push({ type: "scatter3d", mode: "lines", x: pts.map(p => p[0]), y: pts.map(p => p[1]), z: pts.map(p => at(p[0], p[1])), line: { color: "#3f3a32", width: 3 }, hoverinfo: "skip", showlegend: false });
      const dense = (pts, n = 40) => { const o = []; for (let s = 0; s < pts.length - 1; s++) for (let t = 0; t <= n; t++) o.push([pts[s][0] + (pts[s + 1][0] - pts[s][0]) * t / n, pts[s][1] + (pts[s + 1][1] - pts[s][1]) * t / n]); return o; };
      const ring = (cx, cy, rr, b0, b1, n = 96) => { const o = []; for (let k = 0; k <= n; k++) { const a = b0 + (b1 - b0) * k / n; o.push([cx + rr * Math.cos(a), cy + rr * Math.sin(a)]); } return o; };
      seg(dense([[-8, -5.25], [-8, 13.75], [8, 13.75], [8, -5.25]])); seg(ring(0, 13.75, 6, 0, 2 * Math.PI)); seg(ring(0, 0, 4, 0, Math.PI, 32)); seg(ring(0, 0, 0.75, 0, 2 * Math.PI, 24));
      seg(dense([[-22, -5.25], [-22, YC]])); seg(dense([[22, -5.25], [22, YC]])); seg(ring(0, 0, 23.75, A0, Math.PI - A0, 160));
      const cs = []; for (let n = 0; n <= 40; n++) cs.push([n / 40, css(hcol(-1 + n / 20))]);
      const tk = [-1, -0.5, 0, 0.5, 1].map(f => f * zmax), sg = v => (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(1);
      const surf = { type: "surface", x: xs, y: ys, z, colorscale: cs, cmin: -zmax, cmax: zmax,
        colorbar: { title: { text: "shots / 75, per 100 sq ft", side: "right", font: { color: "#efe8da" } }, tickfont: { color: "#efe8da" }, tickvals: tk, ticktext: tk.map(v => (v === 0 ? "same" : sg(v))), len: 0.75, thickness: 12 },
        lighting: { ambient: 1, diffuse: 0, specular: 0, roughness: 1, fresnel: 0 },
        contours: { x: { highlight: true, highlightcolor: "#2b2722", highlightwidth: 2 }, y: { highlight: true, highlightcolor: "#2b2722", highlightwidth: 2 }, z: { highlight: false } },
        hoverinfo: "none" };
      P.react(host.current, [surf, ...lines], { margin: { l: 0, r: 0, t: 0, b: 0 }, paper_bgcolor: "rgba(0,0,0,0)",
        scene: { aspectmode: "manual", aspectratio: { x: 1, y: 0.94, z: 0.9 },
          xaxis: { visible: false, showspikes: false, range: [25, -25] }, yaxis: { visible: false, showspikes: false, range: [-5.25, 41.75] },
          zaxis: { visible: false, showspikes: false, range: [-zmax, zmax] }, camera: { eye: { x: 0.55, y: -0.95, z: 0.6 } } } },
        { displayModeBar: false, responsive: true });
      const el = host.current, t = tip.current;
      let last = null; el.onpointermove = e => { last = e; };
      el.removeAllListeners?.("plotly_hover"); el.removeAllListeners?.("plotly_unhover");
      el.on("plotly_hover", ev => {
        const pt = ev.points[0]; if (!pt || pt.data.type !== "surface") return;
        const x = pt.x, y = pt.y, v = pt.z, e = ev.event || last;   // during a drag Plotly sends hovers with no mouse event
        const sd = Math.abs(x) < 0.5 ? "straight on" : `${Math.round(Math.abs(x))} ft ${x < 0 ? "left" : "right"}`;
        const dp = y < -0.25 ? `${Math.round(-y)} ft behind the basket` : `${Math.round(y)} ft out`;
        t.innerHTML = `<b>${sd}, ${dp}</b><br>${sg(v)} shots per 75 per 100 sq ft here, him on vs off`;
        if (!e) return;
        t.hidden = false; t.style.left = `${Math.min(e.clientX + 14, window.innerWidth - 290)}px`; t.style.top = `${Math.min(e.clientY + 14, window.innerHeight - 90)}px`;
      });
      el.on("plotly_unhover", () => { t.hidden = true; });
    });
    return () => { dead = true; };
  }, [g, grid, zmax]);
  useEffect(() => () => { import("plotly.js-gl3d-dist-min").then(m => { const P = m.default || m; if (host.current) P.purge(host.current); }); }, []);
  return (<>
    <div ref={host} className="gv-3d">{!g && <div className="gv-wait">Loading…</div>}</div>
    <div ref={tip} className="gv-tip" hidden />
  </>);
}

// the flat map: change in points per shot there, him on vs off
function Flat({ g, grid }) {
  const ref = useRef(null);
  useEffect(() => {
    const cv = ref.current; if (!g || !cv) return;
    const { x0, y0, dx, nx, ny } = grid, cx = cv.getContext("2d");
    const sm = document.createElement("canvas"); sm.width = nx; sm.height = ny; const sx = sm.getContext("2d"), im = sx.createImageData(nx, ny);
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) { const c = rgb(g.rel[j * nx + i] / 100), o = 4 * ((ny - 1 - j) * nx + i); im.data[o] = c[0]; im.data[o + 1] = c[1]; im.data[o + 2] = c[2]; im.data[o + 3] = 255; }
    sx.putImageData(im, 0, 0); cx.imageSmoothingEnabled = true; cx.imageSmoothingQuality = "high"; cx.drawImage(sm, 0, 0, cv.width, cv.height);
    const P = cv.width / nx, X = x => (x - x0) / dx * P + P / 2, Y = y => (ny - 1 - (y - y0) / dx) * P + P / 2;
    cx.strokeStyle = "#3f3a32"; cx.lineWidth = 1.6;
    const L = pts => { cx.beginPath(); pts.forEach(([x, y], n) => (n ? cx.lineTo(X(x), Y(y)) : cx.moveTo(X(x), Y(y)))); cx.stroke(); };
    const A = (x, y, rr, b0, b1) => { const p = []; for (let k = 0; k <= 96; k++) { const a = b0 + (b1 - b0) * k / 96; p.push([x + rr * Math.cos(a), y + rr * Math.sin(a)]); } L(p); };
    L([[-25, -5.25], [25, -5.25], [25, 41.75], [-25, 41.75], [-25, -5.25]]); L([[-8, -5.25], [-8, 13.75], [8, 13.75], [8, -5.25]]);
    A(0, 13.75, 6, 0, 2 * Math.PI); A(0, 0, 0.75, 0, 2 * Math.PI); A(0, 0, 4, 0, Math.PI); L([[-3, -1.25], [3, -1.25]]);
    L([[-22, -5.25], [-22, YC]]); L([[22, -5.25], [22, YC]]); A(0, 0, 23.75, A0, Math.PI - A0); A(0, 41.75, 6, Math.PI, 2 * Math.PI);
  }, [g, grid]);
  return <canvas ref={ref} className="gv-flat" width={505} height={475} aria-label="Flat map of the change in points per shot" />;
}
