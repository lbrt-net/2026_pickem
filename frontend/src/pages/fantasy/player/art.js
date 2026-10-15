// Player page drawing code, carried over from the approved mockup (2026-10-14): cards (front / back), the stats panel,
// the wheel and the sections. Builders return HTML strings; PlayerPage.jsx feeds them the API payload (load()) and
// puts the strings on the page. Data lives in module variables so the builders read like the mockup did.
import { headshotLarge, logoUrl } from "../../../components/fantasy/media";

const NBA_FIG = "/player-art/nba-fig.png";
const LOGO = code => logoUrl(code) || "";
let MODE = "fp", SECTION = "Overview", GLS = "2026-27", BASE = "";
let PARTS = null, PART_LABELS = [], TEAMW = null; // TEAMW: a team's 6-slice wheel // NBA teams: the 7 TEAM scoring parts (team_page.py)
let SHOTD, SHS = null; // shots by season (undefined = not fetched yet), chosen season
let GLF = { kind: "week", lo: "", hi: "" }; // game log filter: weeks or dates, from / to ("" = open)
let SEASONS = [], RECENT = [], GLOG = {}, TX = { next: [], status: null, hist: [] }, MOVES = [];
let M2 = null, GAMES2 = [], WHEEL4 = [], MITCH = null, P1 = "#52637b", S1 = "#c4ced4", T1 = "#1a1a1a";
const TEAMS = [
 ["ATL","Atlanta Hawks","#c8102e","#ffc72c","#26282a"],["BOS","Boston Celtics","#007a33","#ffffff","#ba9653"],["BKN","Brooklyn Nets","#2a2a2c","#ffffff","#777d84"],
 ["CHA","Charlotte Hornets","#00778b","#211747","#a1a1a4"],["CHI","Chicago Bulls","#ba0c2f","#1a1a1a","#d6d6d6"],["CLE","Cleveland Cavaliers","#6f263d","#b9975b","#041e42"],
 ["DAL","Dallas Mavericks","#0050b5","#0c2340","#b8c4ca"],["DEN","Denver Nuggets","#0c2340","#fec524","#862633"],["DET","Detroit Pistons","#c8102e","#1d4289","#bec0c2"],
 ["GSW","Golden State Warriors","#1d4289","#ffc72c","#26282a"],["HOU","Houston Rockets","#c8102e","#ffcd00","#1a1a1a"],["IND","Indiana Pacers","#0c2340","#ffcd00","#bec0c2"],
 ["LAC","LA Clippers","#0c2340","#c8102e","#bec0c2"],["LAL","Los Angeles Lakers","#552583","#ffc72c","#1a1a1a"],["MEM","Memphis Grizzlies","#0c2340","#7d9cc0","#f5b112"],
 ["MIA","Miami Heat","#98002e","#1a1a1a","#f9a01b"],["MIL","Milwaukee Bucks","#2c5234","#ddcba4","#0077c0"],["MIN","Minnesota Timberwolves","#1d4289","#009a44","#9ea2a2"],
 ["NOP","New Orleans Pelicans","#0c2340","#b9975b","#c8102e"],["NYK","New York Knicks","#1d4289","#ff8200","#bec0c2"],["OKC","Oklahoma City Thunder","#0072ce","#ef3b24","#fdbb30"],
 ["ORL","Orlando Magic","#0050b5","#1a1a1a","#c4ced4"],["PHI","Philadelphia 76ers","#1d4289","#c8102e","#ffffff"],["PHX","Phoenix Suns","#211747","#e56020","#63727a"],
 ["POR","Portland Trail Blazers","#c8102e","#1a1a1a","#ffffff"],["SAC","Sacramento Kings","#582c83","#1a1a1a","#63727a"],["SAS","San Antonio Spurs","#12a594","#e63e6d","#f7901e"],
 ["TOR","Toronto Raptors","#ba0c2f","#1a1a1a","#a1a1a4"],["UTA","Utah Jazz","#4b2a8a","#1a1a1a","#ffffff"],["WAS","Washington Wizards","#c8102e","#0c2340","#c4ced4"],
];
const rgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
const hex = c => "#" + c.map(v => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, "0")).join("");
const mix = (a, b, t) => hex(rgb(a).map((v, i) => v + (rgb(b)[i] - v) * t));
const lumOf = h => { const [r, g, b] = rgb(h); return (.3 * r + .59 * g + .11 * b) / 255; };
const svgUrl = s => `url("data:image/svg+xml,${encodeURIComponent(s)}")`;
let W = 260, H = 364;
const frameAt = (w, h, fn) => { const ow = W, oh = H; W = w; H = h; const r = fn(); W = ow; H = oh; return r; };
// ---- Plain: primary with printed grain; textured hard elbows in the secondary (top-left, bottom-right)
function plain(p, s0, t3) {
  const s = lumOf(s0) < .2 ? t3 : s0;   // a near-black second color disappears on the frame: use the third
  const arm = `M0 0 H46 L37 9 H9 V37 L0 46 Z M52 0 H61 L52 9 H43 Z M0 52 V61 L9 52 V43 Z`;
  const e = `<svg xmlns='http://www.w3.org/2000/svg' width='${W}' height='${H}'><defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='${mix(s, "#ffffff", .45)}'/><stop offset='.5' stop-color='${s}'/><stop offset='1' stop-color='${mix(s, "#000000", .35)}'/></linearGradient>
  <filter id='tx'><feTurbulence type='fractalNoise' baseFrequency='1.1' numOctaves='1' seed='6' result='n'/><feSpecularLighting in='n' surfaceScale='1' specularConstant='.7' specularExponent='20' lighting-color='#ffffff' result='sp'><feDistantLight azimuth='225' elevation='45'/></feSpecularLighting><feComposite in='sp' in2='SourceAlpha' operator='in' result='s2'/><feComposite in='s2' in2='SourceGraphic' operator='arithmetic' k1='0' k2='.18' k3='1' k4='0'/></filter></defs>
  <g ${lumOf(s) > .45 ? "filter='url(#tx)'" : ''}><path d='${arm}' fill='url(#g)'/><path d='${arm}' fill='url(#g)' transform='rotate(180 ${W / 2} ${H / 2})'/></g></svg>`;
  const grain = `<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='1.1' numOctaves='2'/><feColorMatrix values='0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 .09 0'/></filter><rect width='100%' height='100%' filter='url(#n)'/></svg>`;
  return `background:${svgUrl(e)}, ${svgUrl(grain)}, ${p};`;
}
// ---- All-Defense: pebbled leather in the primary with a secondary sheen
function defense(p, s) {
  const v = `<svg xmlns='http://www.w3.org/2000/svg' width='${W}' height='${H}'><defs>
  <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='${mix(p, "#ffffff", .3)}'/><stop offset='.35' stop-color='${p}'/><stop offset='.55' stop-color='${mix(s, p, .25)}'/><stop offset='.7' stop-color='${p}'/><stop offset='1' stop-color='${mix(p, "#000000", .45)}'/></linearGradient>
  <filter id='pb'><feTurbulence type='fractalNoise' baseFrequency='.5' numOctaves='2' seed='9' result='n'/><feSpecularLighting in='n' surfaceScale='2.4' specularConstant='.9' specularExponent='18' lighting-color='#ffffff' result='s'><feDistantLight azimuth='235' elevation='48'/></feSpecularLighting><feComposite in='s' in2='SourceGraphic' operator='arithmetic' k1='0' k2='.4' k3='1' k4='-.04'/></filter></defs>
  <rect width='100%' height='100%' fill='url(#g)' filter='url(#pb)'/></svg>`;
  return `background:${svgUrl(v)};`;
}
// ---- All-Star: team-color marbled swirl
function allstar(p, s) {
  const v = `<svg xmlns='http://www.w3.org/2000/svg' width='${W}' height='${H}'><defs><filter id='sw'><feTurbulence type='fractalNoise' baseFrequency='.01 .019' numOctaves='3' seed='4'/><feDisplacementMap in='SourceGraphic' scale='56'/></filter>
  <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='${mix(p, "#ffffff", .25)}'/><stop offset='.25' stop-color='${mix(s, "#ffffff", .3)}'/><stop offset='.45' stop-color='${p}'/><stop offset='.65' stop-color='${s}'/><stop offset='.85' stop-color='${mix(p, "#000000", .2)}'/><stop offset='1' stop-color='${mix(s, "#ffffff", .3)}'/></linearGradient></defs>
  <rect width='100%' height='100%' fill='url(#g)'/><g filter='url(#sw)' fill='none'>${[...Array(22)].map((_, i) => `<circle cx='${W / 2}' cy='${H / 2}' r='${9 + i * 9}' stroke='${i % 2 ? mix(s, "#ffffff", .6) : mix(p, "#000000", .45)}' stroke-opacity='.55' stroke-width='3.5'/>`).join("")}</g></svg>`;
  return `background:${svgUrl(v)};`;
}
// ---- All-NBA: brushed metal around the frame, 60% primary / 25% secondary / 15% third, long metal-to-metal blends
// Frame art is the same for every visit to a team (colors, size, seed), so it's painted once and kept: in memory for
// this page view, in sessionStorage for the rest of the visit.
const ART = new Map();
function kept(key, make) {
  if (ART.has(key)) return ART.get(key);
  let v = null;
  try { v = sessionStorage.getItem(key); } catch { /* storage off */ }
  if (!v) { v = make(); try { sessionStorage.setItem(key, v); } catch { /* full or off: memory only */ } }
  ART.set(key, v);
  return v;
}
function allnba(p, s, t3, seedN) {
  return kept(`ppg-nba:${p}${s}${t3}:${seedN}:${W}x${H}`, () => paintAllnba(p, s, t3, seedN));
}
function paintAllnba(p, s, t3, seedN) {
  const S = 2, CW = W * S, CH = H * S; let seed = seedN; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const ramp = c => [mix(c, "#000000", .7), mix(c, "#000000", .35), mix(c, "#ffffff", .3), mix(c, "#000000", .35), mix(c, "#000000", .55), mix(c, "#000000", .3), mix(c, "#ffffff", .25), mix(c, "#000000", .3), mix(c, "#000000", .7)];
  const brushed = stops => { const c = document.createElement("canvas"); c.width = CW; c.height = CH; const x = c.getContext("2d"), cx = CW / 2, cy = CH / 2, R = Math.hypot(cx, cy);
    const g = x.createConicGradient(rnd() * 6.28, cx, cy); for (let k = 0; k <= 3 * (stops.length - 1); k++) g.addColorStop(k / (3 * (stops.length - 1)), stops[k % (stops.length - 1)]);
    x.fillStyle = g; x.fillRect(0, 0, CW, CH);
    for (let r = 2; r < R; r += 1.3) { x.strokeStyle = rnd() < .5 ? `rgba(255,255,255,${(rnd() * .08).toFixed(3)})` : `rgba(0,0,0,${(rnd() * .1).toFixed(3)})`; const a0 = rnd() * 6.28; x.beginPath(); x.arc(cx, cy, r, a0, a0 + 1.5 + rnd() * 4.5); x.stroke(); }
    return x.getImageData(0, 0, CW, CH).data; };
  const L = { b: brushed(ramp(p)), g: brushed(ramp(s)), n: brushed(ramp(t3)) };
  const P = 2 * (CW + CH), layout = [["b", 70], ["g", 40], ["b", 55], ["n", 30], ["b", 50], ["g", 50], ["b", 41], ["n", 24]];
  const segs = []; let acc = P * .04; for (const [k, w] of layout) { const len = w / 360 * P; segs.push([k, acc, acc + len]); acc += len; }
  const hw = 46 * S, sm = v => v * v * (3 - 2 * v), out = document.createElement("canvas"); out.width = CW; out.height = CH;
  const o = out.getContext("2d"), img = o.createImageData(CW, CH), D = img.data, ins = 7 * S, IW = CW - 2 * ins, IH = CH - 2 * ins;
  for (let y = 0; y < CH; y++) for (let x = 0; x < CW; x++) {
    const cx = Math.min(Math.max(x - ins, 0), IW), cy = Math.min(Math.max(y - ins, 0), IH), m = Math.min(cx, IW - cx, cy, IH - cy);
    let q = (m === cy ? cx : m === IW - cx ? IW + cy : m === IH - cy ? IW + IH + (IW - cx) : 2 * IW + IH + (IH - cy)) * P / (2 * (IW + IH));
    q = ((q - segs[0][1]) % P + P) % P + segs[0][1]; let si = segs.findIndex(sg => q >= sg[1] && q < sg[2]); if (si < 0) si = segs.length - 1;
    const [k, s0, s1] = segs[si], i = (y * CW + x) * 4, A = L[k]; let B = A, wb = 0;
    if (q - s0 < hw) { B = L[segs[(si - 1 + segs.length) % segs.length][0]]; wb = .5 * (1 - sm((q - s0) / hw)); }
    else if (s1 - q < hw) { B = L[segs[(si + 1) % segs.length][0]]; wb = .5 * (1 - sm((s1 - q) / hw)); }
    D[i] = A[i] * (1 - wb) + B[i] * wb; D[i + 1] = A[i + 1] * (1 - wb) + B[i + 1] * wb; D[i + 2] = A[i + 2] * (1 - wb) + B[i + 2] * wb; D[i + 3] = 255;
  }
  o.putImageData(img, 0, 0);
  return `background:url("${out.toDataURL()}") center/100% 100% no-repeat;`;
}

const ORDER = ["mvp", "fmvp", "champ", "finals", "dpoy", "allnba", "allstar", "alldef"];
const METAL = { g: ["#f3dc9c", "#c99a44", "#8a6420"], s: ["#f1f3f6", "#b4bac2", "#6f7680"] };
// monoline glyphs (stroke only, consistent 1.6 weight) on a 24 grid
const G = {
  mvp: '<path d="M15.7 1.9l.8.45v.9l-.8.45-.8-.45v-.9Z"/><path d="M15.4 3.8 13.3 8.9" stroke-width="1.5"/><g fill="url(#ID)" stroke="none"><circle cx="12.1" cy="9.7" r="1.25"/><path d="M12.9 8.6l1.6 1.5-.6 3.2-.7 1.9-.3 3.4h-1.6l.2-3.6-.4-2.2-.8 1.2-.9-.4 1.4-2.5Z"/></g><path d="M8.4 18.9l1-1.1h5.2l1 1.1Z M7.6 19.3h8.8l-.9 2H8.5Z"/>',
  fmvp: '<circle cx="12" cy="8.3" r="3.8"/><path d="M8.4 7.5c2.4 1.1 4.8 1.1 7.2 0 M12 4.5v7.6"/><path d="M7.2 12.2h9.6v.8H7.2Z"/><path d="M7.4 13c1.2 2.2 2.8 3.6 3.4 5h2.4c.6-1.4 2.2-2.8 3.4-5"/><path d="M9 18h6v1.3H9Z M8.2 19.7h7.6v1.4H8.2Z"/>',
  // a team's Finals trips (conference titles): a rafters banner — hanging bar, notched cloth, a ball on it
  finals: '<path d="M4.5 3.5h15"/><path d="M7 3.5v16l5-3.2 5 3.2v-16"/><circle cx="12" cy="9.6" r="2.6"/><path d="M9.4 9.6h5.2 M10.7 7.4c.9 1.4.9 3 0 4.4 M13.3 7.4c-.9 1.4-.9 3 0 4.4"/>',
  champ: '<g transform="translate(.6 0)"><circle cx="14.1" cy="5.7" r="4.5"/><path d="M9.7 4.9c2.9 1.4 5.9 1.3 8.8-.3 M13 1.4c1.8 2.9 2 6.3.6 9.4"/><path d="M13.7 10.2v.4"/><path d="M8.8 10.6H15.4 M8.8 10.6V18 M15.4 10.6 11.4 18"/><path d="M8.8 12.6l4.5 2.2 M14.4 12.5l-5.6 3.4"/><path d="M5.6 18h9v1.3h-9Z M4.1 19.7h12v1.4h-12Z"/></g>',
  dpoy: '<g fill="url(#ID)" stroke="none"><circle cx="12" cy="4.1" r="1.75"/><path d="M9.1 6.6h5.8l.3 1.2-.6 3.6h-5.2l-.6-3.6Z"/></g><path d="M9.4 7 7.2 9.4 5.4 12.4 M14.6 7l2.2 2.4 1.8 3" stroke-width="1.9"/><path d="M10.1 11.3 8 13.9l.5 3.5 M13.9 11.3 16 13.9l-.5 3.5" stroke-width="2.1"/><path d="M7.3 17.8h2.2 M14.5 17.8h2.2" stroke-width="1.6"/><path d="M5.6 19.2h12.8v2H5.6Z"/>',
  allnba: '',
  allstar:'<path d="M12 4.5l2.2 4.6 5 .7-3.6 3.5.9 5-4.5-2.4-4.5 2.4.9-5L4.8 9.8l5-.7Z"/>',
  alldef: '<path d="M12 4l7 2.5V12c0 4-3 6.5-7 8-4-1.5-7-4-7-8V6.5Z"/>',
};
const B = { finals: ["Finals", "s"], mvp: ["MVP", "g"], fmvp: ["Finals MVP", "g"], champ: ["Champion", "g"], dpoy: ["DPOY", "g"], allnba: ["All-NBA", "s"], allstar: ["All-Star", "s"], alldef: ["All-Defense", "s"] };
let u = 0;
const badge = (k, n) => {
  const [label, m] = B[k], [hi, mid, lo] = METAL[m], id = "m" + u++;
  return `<div class="bd" title="${label}"><svg viewBox="0 0 40 40"><defs><linearGradient id="${id}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${hi}"/><stop offset=".55" stop-color="${mid}"/><stop offset="1" stop-color="${lo}"/></linearGradient></defs>
    <circle cx="20" cy="20" r="19" fill="url(#${id})"/><circle cx="20" cy="20" r="16.5" fill="#15171c"/><circle cx="20" cy="20" r="16.5" fill="none" stroke="rgba(255,255,255,.08)"/>
    ${k === "allnba" ? `<mask id="k${id}"><image href="${NBA_FIG}" x="14.4" y="7.4" width="11.2" height="25.2" preserveAspectRatio="xMidYMid meet"/></mask><rect x="14.6" y="7.6" width="10.8" height="24.8" rx="3.4" fill="none" stroke="url(#${id})" stroke-width="1.1"/><rect x="0" y="0" width="40" height="40" fill="url(#${id})" mask="url(#k${id})"/>` : ""}<g transform="translate(5.6 5.6) scale(1.2)" fill="none" stroke="url(#${id})" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">${G[k].replace(/url\(#ID\)/g, `url(#${id})`)}</g></svg>
    <div class="t"><span>${label}</span>${n > 1 ? `<b>×${n}</b>` : ""}</div></div>`;
};

const tc = code => TEAMS.find(t => t[0] === code);
let TP = '#a8475f', TS = '#e6cf98';
const CATCOL = { Scoring: "#ff8a3d", Boards: "#4ea3ff", Playmaking: "#42d39b", Steals: "#c48bff", Blocks: "#ff5f8f", Stocks: "#c48bff" };
function overview() {
  const G = [["Scoring", [["pts", "PTS"], ["fg3m", "3PTM"], ["clutch_pts", "Clutch"], ["fgx", "FG-"], ["ftx", "FT-"], ["blkd", "BLKD"]]], ["Playmaking", [["ast", "AST"], ["tov", "TO"]]], ["Boards", [["oreb", "OREB"], ["dreb", "DREB"]]], ["Stocks", [["stl", "STL"], ["blk", "BLK"]]]];
  const fp = MODE === "fp", f = v => v == null ? "" : Number(v).toFixed(1);
  const sg = (v, whole) => v == null ? "" : (v < 0 ? "−" : "") + (whole && !fp ? Math.abs(v).toFixed(0) : Math.abs(v).toFixed(1));
  const pc = p => p == null ? "" : `<small class="pc">${p}</small>`;
  const catCells = (src, whole, pcs) => G.map(([, cs]) => cs.map(([k], i) => `<td class="${i ? "" : "g"}">${sg(src ? src[k] : null, whole)}${pcs ? pc(pcs[k]) : ""}</td>`).join("") + (fp ? `<td class="tc">${src ? sg(cs.reduce((n, [k]) => n + (src[k] || 0), 0)) : ""}${pcs ? pc(pcs["t_" + G.find(x => x[1] === cs)[0].toLowerCase()]) : ""}</td>` : "")).join("");
  const head = first => `<colgroup><col style="width:104px"><col style="width:62px"><col style="width:52px"><col style="width:58px"><col style="width:52px"></colgroup><thead><tr><th colspan="5"></th>${G.map(([g, cs]) => `<th class="g" colspan="${cs.length + (fp ? 1 : 0)}">${g}</th>`).join("")}</tr>
    <tr><th class="l">${first[0]}</th><th>${first[1]}</th><th>${first[2]}</th><th>${first[3]}</th><th>${first[4]}</th>${G.map(([, cs]) => cs.map(([, l], i) => `<th class="${i ? "" : "g"}">${l}</th>`).join("") + (fp ? `<th class="tc">Total</th>` : "")).join("")}</tr></thead>`;
  let h = `<div class="ov"><div class="mode">${[["fp", "Fantasy points"], ["raw", "Box score"]].map(([k, l]) => `<span class="${MODE === k ? "on" : ""}" data-act="mode" data-v="${k}">${l}</span>`).join("")}</div>`;
  h += `<div class="ovh">Seasons</div><table>${head(["Season · Age", "GP", "MPG", "MAX", "AVG"])}<tbody>`;
  for (const r of SEASONS) h += `<tr class="${r.proj ? "proj" : ""}"><td class="l">${r.season}${r.age ? ` · ${r.age}` : ""}<small>${r.team || ""} · ${MITCH.pos}</small></td><td>${r.gp ?? ""}</td><td>${f(r.mpg)}</td><td class="acc">${f(r.max)}${pc(r.pct?.max)}</td><td>${f(r.avg)}${pc(r.pct?.avg)}</td>${catCells(fp ? r.cat : r.raw, false, r.proj ? null : r.pct)}</tr>`;
  h += `</tbody></table>`;
  // last 10 games, newest first, a divider row per Mon–Sun week (fantasy week numbers carry the All-Star exception)
  const md = d => new Date(d + "T12:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" });
  const monday = d => { const x = new Date(d + "T12:00:00"); x.setDate(x.getDate() - (x.getDay() + 6) % 7); return x; };
  if (RECENT.length) h += `<div class="ovh">Last 10 games</div><table>${head(["Date", "Opp", "MIN", "FPTS", ""])}<tbody>`;
  let cur = null;
  for (const g of [...RECENT].reverse()) {
    const key = g.week ?? monday(g.date).toDateString();
    if (key !== cur) { cur = key; const m = monday(g.date), e = new Date(m); e.setDate(m.getDate() + 6);
      h += `<tr class="wk"><td colspan="${fp ? 21 : 17}">${g.week != null ? `Week ${g.week}` : "After the fantasy season"} · ${md(m.toISOString().slice(0, 10))} – ${md(e.toISOString().slice(0, 10))}</td></tr>`; }
    h += `<tr><td class="l">${md(g.date)}</td><td class="l">${g.home ? "" : "@"}${g.opp}</td><td>${g.min}</td><td class="acc ${g.best ? "best" : ""}">${g.fp.toFixed(1)}</td><td></td>${catCells(fp ? g.cat : g.raw, true)}</tr>`;
  }
  if (RECENT.length) h += `</tbody></table>`;
  if (TX.next.length) h += `<div class="ovh">Next 10 games</div><table class="sch"><colgroup><col style="width:104px"><col style="width:90px"><col></colgroup><tbody>`;
  let wk = null;
  for (const g of TX.next) {
    if (g.week !== wk) { wk = g.week; const m = monday(g.date), e = new Date(m); e.setDate(m.getDate() + 6);
      h += `<tr class="wk"><td colspan="3">Week ${g.week} · ${md(m.toISOString().slice(0, 10))} – ${md(e.toISOString().slice(0, 10))} · ${g.wn} games</td></tr>`; }
    const day = new Date(g.date + "T12:00:00").toLocaleDateString(undefined, { weekday: "short" });
    h += `<tr><td class="l">${md(g.date)}<small>${day}</small></td><td class="l">${g.home ? "" : "@"}${g.opp}</td><td></td></tr>`;
  }
  return h + (TX.next.length ? `</tbody></table>` : "") + `</div>`;
}
function transactions() {
  const md = d => new Date(d + "T12:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" });
  let h = `<div class="ov">`;
  // sample moves (fake): newest first. A drop puts him on waivers; if nobody claims him he clears to free agency.

  const chip = ([ab, c]) => `<span class="tm" style="--c:${c}">${ab}</span>`;
  h += `<div class="ovh">Fantasy moves<a class="full" href="${BASE}/transactions?player=${MITCH.id}">Full transaction log →</a></div><div class="moves">` + (MOVES.length ? "" : `<div class="stat">No fantasy moves yet.</div>`) + MOVES.map(m => `<div class="mv ${m.k}"><span class="dt">${md(m.d)}</span><span class="dot"></span><span class="what"><b>${m.txt}</b>${m.a ? (m.k === "trade" ? ` ${chip(m.a)} → ${chip(m.b)}` : ` ${m.k === "drop" ? "by" : "by"} ${chip(m.a)}`) : ""}${m.note ? `<small>${m.note}</small>` : ""}</span></div>`).join("") + `</div>`;
  return h + `</div>`;
}
function availability() {
  const md = d => new Date(d + "T12:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" });
  let h = `<div class="ov"><div class="ovh">Status</div><div class="stat">${TX.status ? `${TX.status.status} · ${TX.status.injury}` : "Healthy"}</div>`;
  // one strip per season: a tick per team game in order, filled = played, gap = missed; month marks underneath
  h += `<div class="ovh">Availability · regular season</div>`;
  for (const s of TX.hist) {
    const G = s.games, n = G.length;
    h += `<div class="tlrow"><div class="tls"><b>'${s.season.slice(-2)}</b><span>${n - s.missed} of ${n}</span></div><div class="tlbar">`;
    h += G.map(g => `<i class="${g.p ? "on" : "off"}" title="${md(g.d)} ${g.p ? "vs " + g.o + " · " + g.fp.toFixed(1) : "· " + g.r}"></i>`).join("");
    h += `</div></div><div class="tlm">`;
    let last = "";
    G.forEach((g, i) => { const m = new Date(g.d + "T12:00:00").toLocaleDateString(undefined, { month: "short" }); if (m !== last) { last = m; h += `<span style="left:${(i / n * 100).toFixed(2)}%">${m}</span>`; } });
    h += `</div>`;
  }
  return h + `</div>`;
}
function gamelog() {
  const G = [["Scoring", [["pts", "PTS"], ["fg3m", "3PTM"], ["clutch_pts", "Clutch"], ["fgx", "FG-"], ["ftx", "FT-"], ["blkd", "BLKD"]]], ["Playmaking", [["ast", "AST"], ["tov", "TO"]]], ["Boards", [["oreb", "OREB"], ["dreb", "DREB"]]], ["Stocks", [["stl", "STL"], ["blk", "BLK"]]]];
  const fp = MODE === "fp", n = fp ? 21 : 17;
  const md = d => new Date(d + "T12:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" });
  const monday = d => { const x = new Date(d + "T12:00:00"); x.setDate(x.getDate() - (x.getDay() + 6) % 7); return x; };
  const sg = v => (v < 0 ? "−" : "") + (fp ? Math.abs(v).toFixed(1) : Math.abs(v).toFixed(0));
  const cells = g => G.map(([, cs]) => cs.map(([k], i) => `<td class="${i ? "" : "g"}">${sg((fp ? g.cat : g.raw)[k] || 0)}</td>`).join("") + (fp ? `<td class="tc">${sg(cs.reduce((s, [k]) => s + (g.cat[k] || 0), 0))}</td>` : "")).join("");
  let h = `<div class="ov"><div class="mode">${[["fp", "Fantasy points"], ["raw", "Box score"]].map(([k, l]) => `<span class="${MODE === k ? "on" : ""}" data-act="mode" data-v="${k}">${l}</span>`).join("")}</div>`;
  h += `<div class="mode seas">${Object.keys(GLOG).map(s => `<span class="${GLS === s ? "on" : ""}" data-act="season" data-v="${s}">'${s.slice(-2)}</span>`).join("")}</div>`;
  h += `<div class="ovh">Game log</div><table><colgroup><col style="width:92px"><col style="width:66px"><col style="width:84px"><col style="width:44px"><col style="width:58px"></colgroup>`;
  h += `<thead><tr><th colspan="5"></th>${G.map(([g, cs]) => `<th class="g" colspan="${cs.length + (fp ? 1 : 0)}">${g}</th>`).join("")}</tr>`;
  h += `<tr><th class="l">Date</th><th class="l">Opp</th><th class="l">Result</th><th>MIN</th><th>FPTS</th>${G.map(([, cs]) => cs.map(([, l], i) => `<th class="${i ? "" : "g"}">${l}</th>`).join("") + (fp ? `<th class="tc">Total</th>` : "")).join("")}</tr></thead><tbody>`;
  let cur = null;
  const all = GLOG[GLS] || [], wks = [...new Set(all.map(g => g.week).filter(w => w != null))];
  const pick = (k, v) => GLF.kind === "week"
    ? `<select data-act="gl${k}"><option value="">${k === "lo" ? "First" : "Last"} week</option>${wks.map(w => `<option value="${w}" ${String(w) === v ? "selected" : ""}>Week ${w}</option>`).join("")}</select>`
    : `<input type="date" data-act="gl${k}" value="${v}" min="${all[0]?.date || ""}" max="${all.at(-1)?.date || ""}">`;
  h += `<div class="glf"><div class="mode">${[["week", "Weeks"], ["date", "Dates"]].map(([k, l]) => `<span class="${GLF.kind === k ? "on" : ""}" data-act="glk" data-v="${k}">${l}</span>`).join("")}</div>${pick("lo", GLF.lo)}<span>to</span>${pick("hi", GLF.hi)}</div>`;
  const inRange = g => GLF.kind === "week"
    ? (!GLF.lo || (g.week != null && g.week >= +GLF.lo)) && (!GLF.hi || (g.week != null && g.week <= +GLF.hi))
    : (!GLF.lo || g.date >= GLF.lo) && (!GLF.hi || g.date <= GLF.hi);
  for (const g of all.filter(inRange)) {
    const key = g.week ?? "x" + monday(g.date).toDateString();
    if (key !== cur) { cur = key; const m = monday(g.date), e = new Date(m); e.setDate(m.getDate() + 6);
      h += `<tr class="wk"><td colspan="${n}">${g.week != null ? `Week ${g.week}` : "Outside the fantasy season"} · ${md(m.toISOString().slice(0, 10))} – ${md(e.toISOString().slice(0, 10))}</td></tr>`; }
    const opp = `${g.home ? "" : "@"}${g.opp}`, res = g.res || "";
    if (g.up) { h += `<tr class="out"><td class="l">${md(g.date)}</td><td class="l">${opp}</td><td class="l"></td><td colspan="${n - 3}"></td></tr>`; continue; }
    if (g.out) { h += `<tr class="out"><td class="l">${md(g.date)}</td><td class="l">${opp}</td><td class="l">${res}</td><td colspan="${n - 3}" class="l">OUT · ${g.out}</td></tr>`; continue; }
    h += `<tr><td class="l">${md(g.date)}</td><td class="l">${opp}</td><td class="l">${res}</td><td>${g.min}</td><td class="acc ${g.best ? "best" : ""}">${g.fp.toFixed(1)}</td>${cells(g)}</tr>`;
  }
  return h + `</tbody></table></div>`;
}
function extras() {
  // LED board (approved 2026-10-14). Bulbs on rings around the hoop, never touching a line. The lit area, the five
  // brightness layers (95 / 80 / 60 / 40 / 20% of his shots) and the colors (points per shot vs the league from that
  // spot) come precomputed per season (scripts/build_shot_fields.py = the pipeline chart's method).
  if (SHOTD === undefined) return `<div class="ov"><div class="stat">Loading…</div></div>`;
  const seasons = Object.keys(SHOTD || {});
  if (seasons.length && !SHOTD[SHS]) SHS = seasons[0];
  const FD = seasons.length ? SHOTD[SHS] : null; // none built: the empty board
  const W = 500, H = 382, X = x => x + 250, Y = y => y + 52;
  const R = 3.3, CLR = R + 1.5;
  const zone = (x, y) => { const d = Math.hypot(x, y); if (Math.abs(x) >= 220 && y <= 92.5) return "c3"; if (d >= 237.5) return "a3"; if (d <= 40 && y >= -47.5) return "rim"; if (Math.abs(x) <= 80 && y <= 142.5) return "paint"; return "mid"; };
  const dSeg = (x, y, x0, y0, x1, y1) => { const dx = x1 - x0, dy = y1 - y0, u = Math.max(0, Math.min(1, ((x - x0) * dx + (y - y0) * dy) / (dx * dx + dy * dy))); return Math.hypot(x - x0 - u * dx, y - y0 - u * dy); };
  const dArc = (x, y, cx, cy, r, ymin) => y - cy >= ymin ? Math.abs(Math.hypot(x - cx, y - cy) - r) : 99;
  const clear = (x, y) => Math.min(
    Math.abs(y + 47.5), dSeg(x, y, -80, -47.5, -80, 142.5), dSeg(x, y, 80, -47.5, 80, 142.5), dSeg(x, y, -80, 142.5, 80, 142.5),
    dArc(x, y, 0, 142.5, 60, 0), dArc(x, y, 0, 0, 40, 0), dSeg(x, y, -220, -47.5, -220, 92.5), dSeg(x, y, 220, -47.5, 220, 92.5),
    dArc(x, y, 0, 0, 237.5, 92.5), Math.hypot(x, y) - 7.5, dSeg(x, y, -30, -7.5, 30, -7.5)) >= CLR;
  const P = [], keep = (x, y, z) => { if (y > -47.5 && X(x) > R + 2 && X(x) < W - R - 2 && Y(y) < H - R - 2 && zone(x, y) === z && clear(x, y)) P.push([x, y]); };
  const rings = (r0, r1, z, s = 9.9) => { const a0 = r0 + CLR + .01, a1 = r1 - CLR - .01, n = Math.max(1, Math.round((a1 - a0) / s)); for (let k = 0; k <= n; k++) { const r = a0 + k * (a1 - a0) / n, m = Math.round(Math.PI * 2 * r / s); for (let i = 0; i < m; i++) { const a = (i + .5) * 2 * Math.PI / m; keep(r * Math.cos(a), r * Math.sin(a), z); } } };
  rings(7.5, 40, "rim", 8.2); rings(40, 237.5, "paint"); rings(40, 237.5 + 9.9 * 20, "c3");
  rings(40, 237.5, "mid"); rings(237.5, 237.5 + 9.9 * 20, "a3");
  const STRENGTH = [.127, .291, .62, 1.05, 1.3]; // outer → inner layer; past 1 = the same hue, stronger (never toward white)
  const dAt = new Map();
  if (FD) { let k = 0; for (let c = 0; c < FD.lvl.length; c++) if (FD.lvl[c] !== "0") dAt.set(c, FD.d[k++]); }
  const cell = (x, y) => { const i = Math.round((x - FD.x0) / FD.step), j = Math.round((y - FD.y0) / FD.step); return i < 0 || j < 0 || i >= FD.nx || j >= FD.ny ? -1 : j * FD.nx + i; };
  const ramp = d => { const t = Math.max(-1, Math.min(1, d / .22)), u = Math.abs(t) ** .8, mid = [196, 186, 170], end = t < 0 ? [34, 96, 205] : [218, 52, 28];
    return mid.map((m, i) => m + (end[i] - m) * u); };
  const hx = a => "#" + a.map(q => Math.round(Math.max(0, Math.min(255, q))).toString(16).padStart(2, "0")).join("");
  const bulb = ([x, y]) => {
    const cx = X(x).toFixed(1), cy = Y(y).toFixed(1), c0 = FD ? cell(x, y) : -1, lv = c0 < 0 ? 0 : +FD.lvl[c0];
    if (!lv) return `<circle cx="${cx}" cy="${cy}" r="${R}" class="bo"/>`;
    const c = ramp(dAt.get(c0) / 100), f = STRENGTH[lv - 1], mx = Math.max(...c), k = f <= 1 ? f : 1 + (255 / mx - 1) * Math.min(1, (f - 1) / .6);
    return `<circle cx="${cx}" cy="${cy}" r="${R}" fill="${hx(c.map(q => q * k))}"/>` + (f > .7 ? `<circle cx="${cx}" cy="${cy}" r="${(R * .5).toFixed(1)}" fill="${hx(c.map(q => q * Math.min(255 / mx, k * 1.12)))}"/>` : "");
  };
  const L = `<g fill="none" stroke="rgba(230,237,243,.5)" stroke-width="1.3">
    <path d="M${X(-250)},${Y(-47.5)} H${X(250)}"/><path d="M${X(-80)},${Y(-47.5)} V${Y(142.5)} H${X(80)} V${Y(-47.5)}"/><path d="M${X(-60)},${Y(142.5)} A60,60 0 0 0 ${X(60)},${Y(142.5)}"/>
    <path d="M${X(-40)},${Y(0)} A40,40 0 0 0 ${X(40)},${Y(0)}"/><path d="M${X(-220)},${Y(-47.5)} V${Y(92.5)} A237.5,237.5 0 0 0 ${X(220)},${Y(92.5)} V${Y(-47.5)}"/>
    <line x1="${X(-30)}" x2="${X(30)}" y1="${Y(-7.5)}" y2="${Y(-7.5)}" stroke-width="2.5"/><circle cx="${X(0)}" cy="${Y(0)}" r="7.5"/></g>`;
  return `<div class="ov">
    <div class="ovh">Shot chart${FD ? ` · ${FD.n} shots` : ""}</div>
    <div class="shw"><svg class="led" viewBox="0 0 ${W} ${H}"><rect width="${W}" height="${H}" fill="#000"/>${P.map(bulb).join("")}${L}</svg></div></div>`;
}
function dial(col, data = WHEEL4, multi = false, rot = 0) {
  // 5 slices, wedge length = his percentile; label + percentile outside each wedge
  const n = data.length, R = 50, r0 = 12, cx = 110, cy = 80;
  const pt = (rad, a) => `${(cx + rad * Math.cos(a)).toFixed(1)},${(cy + rad * Math.sin(a)).toFixed(1)}`;
  const w = (rad, a0, a1) => `M${pt(r0, a0)} L${pt(rad, a0)} A${rad},${rad} 0 0 1 ${pt(rad, a1)} L${pt(r0, a1)} A${r0},${r0} 0 0 0 ${pt(r0, a0)}Z`;
  let s = `<svg viewBox="0 6 220 156">`;
  data.forEach((q, i) => {
    const c2 = multi === "team" ? TP : multi ? CATCOL[q.k] : col;
    const a0 = i / n * 6.283 - 1.571 + rot, a1 = (i + 1) / n * 6.283 - 1.571 + rot, am = (a0 + a1) / 2;
    s += `<path d="${w(R, a0, a1)}" fill="#34363c"/>${q.p == null ? "" : `<path d="${w(r0 + (R - r0) * q.p / 100, a0, a1)}" stroke="${multi === "team" ? TS : "none"}" stroke-width="1.3" stroke-opacity=".9" fill="${c2}" fill-opacity="${multi === "team" ? (.1 + .9 * q.p / 100).toFixed(2) : (.35 + .65 * q.p / 100).toFixed(2)}"/>`}`;
    const bot = Math.sin(am) > 0, lx = cx + (R + 30) * Math.cos(am), ly = cy + (R + 12) * Math.sin(am);
    const nameY = bot ? ly + 18 : ly - 2, numY = bot ? ly + 5 : ly + 11;
    s += `<text x="${lx.toFixed(1)}" y="${nameY.toFixed(1)}" text-anchor="middle" style="font:700 9.5px Barlow;letter-spacing:.08em;fill:#e6edf3">${q.k.toUpperCase()}</text>`;
    s += `<text x="${lx.toFixed(1)}" y="${numY.toFixed(1)}" text-anchor="middle" style="font:600 14px Teko;fill:#f2f4f7">${q.p ?? ""}</text>`;
  });
  for (let i = 0; i < n; i++) { const a = i / n * 6.283 - 1.571 + rot; s += `<line x1="${pt(0, a).split(",")[0]}" y1="${pt(0, a).split(",")[1]}" x2="${pt(R + 1, a).split(",")[0]}" y2="${pt(R + 1, a).split(",")[1]}" stroke="#140b10" stroke-width="2"/>`; }
  return s + `<circle cx="${cx}" cy="${cy}" r="${r0}" fill="#140b10"/></svg>`;
}
const back = (d, wheel = WHEEL4, multi = "team", rot = 0) => {
  const code = d.team, p = P1, s = S1, t3 = T1;
  const rich = h => { const c = rgb(h), m = Math.max(...c) || 1; return m >= 170 ? h : hex(c.map(v => v * 185 / m)); };
  TP = rich(p); TS = rich(s);
  const ks = ORDER.filter(k => d.c[k]);
  const inner = d.tier === "mvp"
    ? "background:radial-gradient(70% 50% at 50% 30%, #3a2c14, #120d07 75%), #0c0905;"
    : `background:radial-gradient(80% 55% at 50% 28%, ${mix(p, "#000000", .45)}, ${mix(p, "#000000", .82)} 75%), #08080b;`;
  const frame = frameFor(d.tier, p, s, t3, 7);
  return `<div class="card ${d.tier === "mvp" ? "mvp3" : ""}" data-frame="${encodeURIComponent(frame)}"><div class="in backside" style="${inner}">
    <div class="tophalf"><div class="top">${code ? `<img src="${LOGO(code)}" alt="">` : ""}<b>${d.name}</b></div>
    <div class="dial">${dial(d.tier === "mvp" ? "#e8bd5c" : mix(p, "#ffffff", .25), d.kind === "team" ? TEAMW : wheel, multi, rot)}</div></div>
    <div class="bothalf">${ks.length ? `<div class="case"><div class="grid">${ks.map(k => badge(k, d.c[k])).join("")}</div></div>` : ""}</div>
  </div></div>`;
};
const spot = "radial-gradient(1.2px 1.2px at 40% 26%, rgba(255,255,255,.6), transparent), radial-gradient(1px 1px at 60% 36%, rgba(255,255,255,.55), transparent), radial-gradient(70% 12% at 50% 73%, rgba(255,248,236,.45), rgba(255,248,236,.12) 55%, transparent 80%), conic-gradient(from 0deg at 50% -18%, transparent 0deg 145deg, rgba(255,248,236,.07) 149deg, rgba(255,248,236,.2) 157deg, rgba(255,248,236,.26) 180deg, rgba(255,248,236,.2) 203deg, rgba(255,248,236,.07) 211deg, transparent 215deg 360deg), linear-gradient(180deg, #050507, #0b0b0e 60%, #050507)";
const RINGS = [
  "radial-gradient(closest-side, transparent 80%, rgba(255,226,150,0) 81%, #f6d07a 83%, #fff3c8 84.5%, #a87420 87%, transparent 90%) 50% 36%/250px 250px no-repeat",
  "radial-gradient(closest-side, transparent 91.6%, rgba(233,191,98,.35) 92.6%, rgba(255,246,214,.85) 93.6%, rgba(233,191,98,.6) 94.6%, rgba(233,191,98,.2) 95.6%, transparent 96.6%) 50% 36%/276px 276px no-repeat",
  "radial-gradient(closest-side, transparent 90.6%, rgba(168,116,32,.5) 91.6%, rgba(246,208,122,.8) 92.8%, rgba(255,243,200,.9) 93.4%, rgba(168,116,32,.45) 94.6%, transparent 95.6%) 50% 36%/316px 316px no-repeat",
  "radial-gradient(closest-side, transparent 94.2%, rgba(232,189,92,.18) 95%, rgba(246,208,122,.55) 95.8%, rgba(232,189,92,.18) 96.6%, transparent 97.6%) 50% 36%/372px 372px no-repeat",
];
const front = (d, bgUrl) => {
  const code = d.team;
  const frame = frameFor(d.tier, P1, S1, T1, 7);
  const bg = d.tier === "plain" ? "background:#0b0b0e" : d.tier === "allnba" ? `background:url(${bgUrl}) center/100% 100%` : d.tier === "mvp"
    ? `background:${RINGS.slice(0, d.c.mvp || 1).join(", ")}, linear-gradient(115deg, transparent 30%, rgba(255,230,160,.10) 45%, transparent 60%), radial-gradient(60% 40% at 50% 38%, #2a2015, #0c0a08 70%, #050404)` : `background:${spot}`;
  return `<div class="card ${d.tier === "mvp" ? "mvp3" : ""}" data-frame="${encodeURIComponent(frame)}"><div class="in front"><div class="bg" style="${bg}"></div>
    <span class="tag">${d.pos}</span>${code && d.kind !== "team" ? `<img class="lgc" src="${LOGO(code)}" alt="">` : ""}${d.kind === "team" ? `<img class="tlogo" src="${LOGO(code)}" alt="">` : `<img class="hs" src="${d.hs}" alt="">`}
    <div class="tx"><div class="nm">${d.name}</div><div class="bio">${d.kind === "team" ? "NBA team" : [d.age ? `Age ${d.age}` : "", d.ht && d.wt ? `${d.ht}, ${d.wt} lb` : d.ht || ""].filter(Boolean).join(" · ")}</div><div class="st"><div><b>${d.gp}</b><i>GP</i></div>${d.kind === "team" ? "" : `<div><b>${d.mpg != null ? d.mpg.toFixed(1) : "—"}</b><i>MPG</i></div>`}</div></div></div>
    <div class="ribw"><div class="rib">${d.ribbon}</div></div></div>`;
};
// All-NBA background: the chrome template, flows tinted with the team primary
function chromeTint(hex, cb, edge = 18, post = 0, sty = 0, k = 7, src = null, seed = 0) {
  const key = `ppg-chrome:${hex}:${src}:${seed}:${edge}:${post}`;
  if (ART.has(key)) return cb(ART.get(key));
  try { const v = sessionStorage.getItem(key); if (v) { ART.set(key, v); return cb(v); } } catch { /* storage off */ }
  paintChrome(hex, url => { ART.set(key, url); try { sessionStorage.setItem(key, url); } catch { /* full */ } cb(url); }, edge, post, sty, k, src, seed);
}
function paintChrome(hex, cb, edge = 18, post = 0, sty = 0, k = 7, src = null, seed = 0) {
  const img = new Image(); img.onload = () => {
    const c = document.createElement("canvas"); c.width = img.width; c.height = img.height; const x = c.getContext("2d");
    if (sty) { x.filter = `blur(${sty}px)`; x.drawImage(img, 0, 0); x.filter = "none";
      const s = x.getImageData(0, 0, c.width, c.height), Q = s.data;
      for (let i = 0; i < Q.length; i += 4) { const v = Q[i] / 255, y = 1 / (1 + Math.exp(-k * (v - .5))), lo = 1 / (1 + Math.exp(k * .5)), hi = 1 / (1 + Math.exp(-k * .5)); Q[i] = Q[i + 1] = Q[i + 2] = 255 * (y - lo) / (hi - lo); }
      x.putImageData(s, 0, 0); } else x.drawImage(img, 0, 0);
    const d = x.getImageData(0, 0, c.width, c.height), D = d.data, [pr, pg, pb] = rgb(hex);
    const bl = document.createElement("canvas"); bl.width = c.width; bl.height = c.height; const bx = bl.getContext("2d"); bx.filter = "blur(18px)"; bx.drawImage(img, 0, 0); const B = bx.getImageData(0, 0, c.width, c.height).data; bx.filter = "none";
    const vals = []; for (let i = 0; i < B.length; i += 40) vals.push(B[i]); vals.sort((a, b) => a - b); let sd = seed || 1; const rnd = () => (sd = (sd * 16807) % 2147483647) / 2147483647; const share = seed ? .35 + rnd() * .25 : .5, high = seed ? rnd() < .5 : false; const q = vals[Math.floor(vals.length * (high ? 1 - share : share))];
    for (let i = 0; i < D.length; i += 4) { const L = D[i] / 255; let m = Math.min(1, Math.max(0, ((high ? B[i] - q : q - B[i]) + edge / 2) / edge)); m = m * m * (3 - 2 * m);
      const col = L < .5 ? [pr * (.3 + 1.4 * L), pg * (.3 + 1.4 * L), pb * (.3 + 1.4 * L)] : [pr + (255 - pr) * (L - .5) * 1.7, pg + (255 - pg) * (L - .5) * 1.7, pb + (255 - pb) * (L - .5) * 1.7];
      for (let k = 0; k < 3; k++) D[i + k] = D[i] * (1 - m) + Math.min(255, col[k]) * m; }
    x.putImageData(d, 0, 0);
    if (post) { const o = document.createElement("canvas"); o.width = c.width; o.height = c.height; const ox = o.getContext("2d"); ox.filter = `blur(${post}px)`; ox.drawImage(c, 0, 0); cb(o.toDataURL()); }
    else cb(c.toDataURL()); }; img.crossOrigin = "anonymous"; img.src = src;
}
const ord = n => n + (n % 100 >= 11 && n % 100 <= 13 ? "th" : ["th", "st", "nd", "rd"][n % 10] || "th");
const pc = n => `<span class="pc">${n}<sup>${ord(n).slice(-2)}</sup></span>`;
// Before games: a violin of his expected games (gray) with the simulated weekly bests (team colors) over it, on the
// cloud's axis — the projection's shape instead of dots.
function projViolin(w, h, acc) {
  const L = 8, R = 8, B = 18, dist = M2.dist || [], sim = M2.sim || [];
  const hi = Math.max(70, Math.ceil(Math.max(0, ...dist, ...sim) / 10) * 10), X = v => L + v / hi * (w - L - R), mid = (h - B) / 2 + 2;
  const kde = (vals, bw) => { const xs = []; for (let v = 0; v <= hi; v += hi / 140) xs.push(v);
    const d = xs.map(v => vals.reduce((s, x) => s + Math.exp(-0.5 * ((v - x) / bw) ** 2), 0)); const m = Math.max(...d) || 1; return xs.map((v, i) => [v, d[i] / m]); };
  const shape = (vals, half, fill, stroke, op) => { if (!vals.length) return ""; const k = kde(vals, Math.max(1.5, hi / 45));
    const top = k.map(([v, d]) => `${X(v).toFixed(1)},${(mid - d * half).toFixed(1)}`), bot = k.map(([v, d]) => `${X(v).toFixed(1)},${(mid + d * half).toFixed(1)}`).reverse();
    return `<polygon points="${top.join(" ")} ${bot.join(" ")}" fill="${fill}" fill-opacity="${op}" stroke="${stroke}" stroke-width="1.4"/>`; };
  let s = `<svg viewBox="0 0 ${w} ${h + 16}">`;
  s += `<line x1="${L}" x2="${w - R}" y1="${h - B}" y2="${h - B}" stroke="rgba(255,255,255,.25)"/>`;
  for (let v = 0; v <= hi; v += hi > 80 ? 20 : 10) s += `<text x="${X(v)}" y="${h - 4}" text-anchor="middle" style="opacity:.75">${v}</text>`;
  s += `<text x="${(L + w - R) / 2}" y="${h + 12}" text-anchor="middle" style="font:700 11px Barlow;letter-spacing:.14em;fill:${acc}">FANTASY POINTS PER GAME</text>`;
  s += shape(dist, mid - 14, "#5f636b", "#8b9099", .55);
  s += shape(sim, (mid - 14) * .8, mix(S1, "#ffffff", .3), mix(P1, "#ffffff", .15), .6);
  if (M2.max != null) s += `<line x1="${X(M2.max)}" x2="${X(M2.max)}" y1="${mid - (mid - 10)}" y2="${mid + (mid - 10)}" stroke="${acc}" stroke-width="2"/>`;
  return s + `</svg>`;
}
function ridge(w, h, acc) {
  if (M2 && M2.proj) return projViolin(w, h, acc);
  // SHAP beeswarm: narrow x bins, dots overlap, each bin stacked symmetrically -> one smooth dense blob
  const L = 8, R = 8, B = 18, lo = 0, hi = Math.max(70, Math.ceil(Math.max(0, ...GAMES2.map(g => g[0])) / 10) * 10), X = v => L + (v - lo) / (hi - lo) * (w - L - R), mid = (h - B) / 2 + 2, r = 3.6;
  // loose cloud: each dot jiggled a little left/right and spread up/down by how crowded its neighborhood is
  let sd = 7; const rnd = () => (sd = (sd * 16807) % 2147483647) / 2147483647;
  const all = GAMES2.map(g => g[0]), dots = [], minGap = r * 2 + 1;
  for (const [v, isBest] of [...GAMES2].sort((a, b) => a[0] - b[0])) {
    const near = all.filter(u => Math.abs(u - v) < 4).length, spread = Math.min(mid - 16, 3 + near * 3.2);
    let best = null;
    for (let tries = 0; tries < 40; tries++) {
      const x = X(v) + (rnd() * 2 - 1) * 3, y = mid + (rnd() * 2 - 1) * spread;
      const clear = dots.every(p => (p.x - x) ** 2 + (p.y - y) ** 2 >= minGap * minGap);
      if (clear) { best = { x, y }; break; }
      if (!best) best = { x, y };
    }
    dots.push({ ...best, isBest });
  }
  let s = `<svg viewBox="0 0 ${w} ${h + 16}">`;
  s += `<line x1="${L}" x2="${w - R}" y1="${h - B}" y2="${h - B}" stroke="rgba(255,255,255,.25)"/>`;
  for (let v = 0; v <= hi; v += hi > 80 ? 20 : 10) s += `<text x="${X(v)}" y="${h - 4}" text-anchor="middle" style="opacity:.75">${v}</text>`;
  s += `<text x="${(L + w - R) / 2}" y="${h + 12}" text-anchor="middle" style="font:700 11px Barlow;letter-spacing:.14em;fill:${acc}">FANTASY POINTS PER GAME</text>`;
  s += dots.filter(p => !p.isBest).map(p => `<circle cx="${p.x}" cy="${p.y}" r="${r}" fill="#5f636b"/>`).join("");
  s += dots.filter(p => p.isBest).map(p => `<circle cx="${p.x}" cy="${p.y}" r="${r}" fill="${mix(S1, "#ffffff", .3)}" stroke="${mix(P1, "#ffffff", .15)}" stroke-width="1.8"/>`).join("");
  return s + `</svg>`;
}
// blank (no games this season): invisible stand-ins keep the panel spaced exactly as when it has numbers
const num = (v, d = 1) => (v == null ? `<span style="visibility:hidden">00.0</span>` : Number(v).toFixed(d));
// MAX and AVG as a matched pair: label, number + percentile, bar — the same blocks, MAX the larger
const duo = (k, l, v, q) => `<div class="duo-s ${k}"><div class="l">${l}</div><div class="v"><b>${v}</b>${pcOr(q)}</div><div class="bar"><i style="width:${q || 0}%"></i></div></div>`;
const pcOr = p => (p ? pc(p) : `<span class="pc" style="visibility:hidden">99<sup>th</sup></span>`);
function midPanel(w) {
  const f = frameAt(w, 364, () => frameFor(MITCH.tier, P1, S1, T1, 7)), acc = "#e6cf98", P = M2 ? M2.pct : {};
  return `<div class="mid ${MITCH.tier === "mvp" ? "mvp3" : ""}" data-frame="${encodeURIComponent(f + 'padding:9px;border-radius:14px;box-shadow:0 22px 44px rgba(0,0,0,.6);')}"><div style="position:relative;height:100%;border-radius:6px;overflow:hidden;--acc:${acc};background:radial-gradient(80% 90% at 25% 15%, ${mix(P1, "#000000", .45)}, ${mix(P1, "#000000", .86)} 75%)">
    <div class="m2${M2 && M2.proj ? " proj" : ""}"><div class="topband">
      <div class="duo">${duo("max", "Max", num(M2?.max), P.max)}${duo("avg", "Avg", num(M2?.avg), P.avg)}</div>
      </div>
      <div class="chart"><div class="sl">${M2 && M2.proj ? "Projected games · weekly bests" : "Season performance"}</div>${ridge(410, 104, acc)}</div>
    </div></div></div>`;
}

// The frame for a tier (cards, the stats panel and the section panel all wear it). MVP = the gold class, no style.
export function frameFor(tier, p, s, t3, seed = 7) {
  return tier === "mvp" ? "" : tier === "allnba" ? allnba(p, s, t3, seed) : tier === "allstar" ? allstar(p, s) : tier === "alldef" ? defense(p, s) : plain(p, s, t3);
}
export { frameAt, mix, tc, chromeTint };

// ---- feeding the builders
export function load(d, base) {
  BASE = base;
  const pl = d.player, h = d.header;
  const team = tc(pl.team) || ["", "", "#52637b", "#c4ced4", "#1a1a1a"];
  [P1, S1, T1] = team.slice(2);
  MITCH = { ...pl, team: tc(pl.team) ? pl.team : null, gp: h ? h.gp : 0, mpg: h ? h.mpg : null, hs: headshotLarge(pl.id) };
  PARTS = d.parts || null; PART_LABELS = d.part_labels || [];
  TEAMW = d.wheel || ["Points allowed", "SCV", "Fast break", "Paint", "Turnovers", "Glass"].map(k => ({ k, v: null, p: null }));
  M2 = h || { max: null, avg: null, floor: null, ceil: null, pct: {} }; // this season only: blank until he plays
  GAMES2 = h ? h.games : [];
  WHEEL4 = h && h.wheel ? h.wheel : ["Playmaking", "Stocks", "Boards", "Scoring"].map(k => ({ k, v: null, p: null }));
  SEASONS = d.seasons; RECENT = d.recent; GLOG = d.glog; MOVES = movesFor(d.moves);
  TX = { next: d.next, status: d.status, hist: d.hist };
  GLS = Object.keys(GLOG)[0] || "2026-27";
  SHOTD = undefined; SHS = null; GLF = { kind: "week", lo: "", hi: "" };
}
export function setShots(d) { SHOTD = d || {}; }
function movesFor(ms) {
  const what = { draft: "Drafted", add: "Added from free agency", claim: "Claimed off waivers", drop: "Dropped" };
  return ms.filter(m => m.d).map(m => ({ d: m.d, k: m.k, txt: what[m.k] || m.k, a: m.team,
    note: m.k === "draft" ? (m.price != null ? `$${m.price}` : m.pick ? `pick ${m.pick}` : "") : "" }));
}
export const state = () => ({ MODE, SECTION, GLS });
export function set(k, v) {
  if (k === "glk") { GLF = { kind: v, lo: "", hi: "" }; return; }
  if (k === "gllo" || k === "glhi") { GLF = { ...GLF, [k.slice(2)]: v }; return; }
  if (k === "season") GLF = { ...GLF, lo: "", hi: "" };
  if (k === "shots") SHS = v; else if (k === "mode") MODE = v; else if (k === "season") GLS = v; else if (k === "section") SECTION = v; }
export const headerHtml = bgUrl => `${front(MITCH, bgUrl)}${midPanel(1100 - 520 - 28)}${back(MITCH)}`;
function teamOverview() {
  const f = v => v == null ? "" : Number(v).toFixed(1), pc = p => p == null ? "" : `<small class="pc">${p}</small>`;
  const md = d => new Date(d + "T12:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" });
  // box score = how often each event happened, per game (SCV forced per game; the bonuses as the share of games they hit)
  const fp = MODE === "fp", pv = r => (fp ? r.parts : r.counts && r.gp ? Object.fromEntries(Object.entries(r.counts).map(([k, v]) => [k, v / r.gp])) : null);
  const fc = (v, raw) => v == null ? "" : raw ? Number(v).toFixed(2) : Number(v).toFixed(1);
  let h = `<div class="ov"><div class="mode">${[["fp", "Fantasy points"], ["raw", "Box score"]].map(([k, l]) => `<span class="${MODE === k ? "on" : ""}" data-act="mode" data-v="${k}">${l}</span>`).join("")}</div><div class="ovh">Seasons</div><table><thead><tr><th colspan="4"></th><th class="g" colspan="${PART_LABELS.length}">Scoring parts</th></tr><tr><th class="l">Season</th><th>GP</th><th>MAX</th><th>AVG</th>${PART_LABELS.map(([, l], i) => `<th class="${i ? "" : "g"}">${l}</th>`).join("")}</tr></thead><tbody>`;
  for (const r of SEASONS) h += `<tr class="${r.proj ? "proj" : ""}"><td class="l">${r.season}</td><td>${r.gp ?? ""}</td><td class="acc">${f(r.max)}${pc(r.pct?.max)}</td><td>${f(r.avg)}${pc(r.pct?.avg)}</td>${PART_LABELS.map(([k], i) => `<td class="${i ? "" : "g"}">${pv(r) ? fc(pv(r)[k], !fp) : ""}${pc(r.pct?.[k])}</td>`).join("")}</tr>`;
  h += `</tbody></table>`;
  if (TX.next.length) {
    h += `<div class="ovh">Next 10 games</div><table class="sch"><colgroup><col style="width:104px"><col style="width:90px"><col></colgroup><tbody>`;
    let wk = null;
    for (const g of TX.next) {
      if (g.week !== wk) { wk = g.week; h += `<tr class="wk"><td colspan="3">Week ${g.week ?? ""}${g.wn ? ` · ${g.wn} games` : ""}</td></tr>`; }
      h += `<tr><td class="l">${md(g.date)}</td><td class="l">${g.home ? "" : "@"}${g.opp}</td><td></td></tr>`;
    }
    h += `</tbody></table>`;
  }
  return h + `</div>`;
}
function teamGamelog() {
  const md = d => new Date(d + "T12:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" });
  const f = v => (v == null ? "" : Number(v).toFixed(1));
  const fp = MODE === "fp";
  let h = `<div class="ov"><div class="mode">${[["fp", "Fantasy points"], ["raw", "Box score"]].map(([k, l]) => `<span class="${MODE === k ? "on" : ""}" data-act="mode" data-v="${k}">${l}</span>`).join("")}</div>`;
  h += `<div class="mode seas">${Object.keys(GLOG).map(s => `<span class="${GLS === s ? "on" : ""}" data-act="season" data-v="${s}">'${s.slice(-2)}</span>`).join("")}</div>`;
  h += `<div class="ovh">Game log</div><table><thead><tr><th colspan="4"></th><th class="g" colspan="${PART_LABELS.length}">Scoring parts</th></tr><tr><th class="l">Date</th><th class="l">Opp</th><th class="l">Result</th><th>FPTS</th>${PART_LABELS.map(([, l], i) => `<th class="${i ? "" : "g"}">${l}</th>`).join("")}</tr></thead><tbody>`;
  let cur = null;
  for (const g of GLOG[GLS] || []) {
    if (g.week !== cur) { cur = g.week; h += `<tr class="wk"><td colspan="${4 + PART_LABELS.length}">${g.week != null ? `Week ${g.week}` : "Outside the fantasy season"}</td></tr>`; }
    const opp = `${g.home ? "" : "@"}${g.opp}`;
    if (g.up) { h += `<tr class="out"><td class="l">${md(g.date)}</td><td class="l">${opp}</td><td colspan="${2 + PART_LABELS.length}"></td></tr>`; continue; }
    h += `<tr><td class="l">${md(g.date)}</td><td class="l">${opp}</td><td class="l">${g.res}</td><td class="acc ${g.best ? "best" : ""}">${f(g.fp)}</td>${PART_LABELS.map(([k], i) => `<td class="${i ? "" : "g"}">${fp ? f(g.parts?.[k]) : (g.counts?.[k] ?? "")}</td>`).join("")}</tr>`;
  }
  return h + `</tbody></table></div>`;
}
const isTeam = () => MITCH?.kind === "team";
export const sectionHtml = () => isTeam() ? (SECTION === "Game Log" ? teamGamelog() : SECTION === "Transactions" ? transactions() : teamOverview())
  : SECTION === "Overview" ? overview() : SECTION === "Transactions" ? transactions()
  : SECTION === "Availability" ? availability() : SECTION === "Game Log" ? gamelog() : extras();
export const player = () => MITCH;
export const colors = () => ({ P1, S1, T1 });

// ---- the player pop-up (PlayerCard.jsx) borrows the header's pieces without touching the open player page: swap the
// module data in, build, put it back (synchronous).
function withData(d, fn) {
  const saved = [MITCH, M2, GAMES2, WHEEL4, P1, S1, T1, TP, TS];
  try {
    const t = tc(d.player.team) || ["", "", "#52637b", "#c4ced4", "#1a1a1a"];
    [P1, S1, T1] = t.slice(2);
    MITCH = { ...d.player };
    M2 = d.header || { max: null, avg: null, floor: null, ceil: null, pct: {} };
    GAMES2 = d.header ? d.header.games : [];
    WHEEL4 = d.header ? d.header.wheel : ["Playmaking", "Stocks", "Boards", "Scoring"].map(k => ({ k, v: null, p: null }));
    const rich = h => { const c = rgb(h), m = Math.max(...c) || 1; return m >= 170 ? h : hex(c.map(v => v * 185 / m)); };
    TP = rich(P1); TS = rich(S1);
    return fn();
  } finally {
    [MITCH, M2, GAMES2, WHEEL4, P1, S1, T1, TP, TS] = saved;
  }
}

// The stats panel's pieces (MAX + AVG / FLOOR / CEILING with percentile bars, the season cloud) and the wheel.
export function popupStats(d) {
  return withData(d, () => {
    const acc = "#e6cf98", P = M2.pct || {};
    return `<div class="pc-ppg-stats" style="--acc:${acc}"><div class="m2${M2 && M2.proj ? " proj" : ""}"><div class="topband">
        <div class="duo">${duo("max", "Max", num(M2.max), P.max)}${duo("avg", "Avg", num(M2.avg), P.avg)}</div>
        </div>
        <div class="chart"><div class="sl">${M2 && M2.proj ? "Projected games · weekly bests" : "Season performance"}</div>${ridge(410, 104, acc)}</div></div>
      <div class="pc-ppg-dial">${dial(d.player.tier === "mvp" ? "#e8bd5c" : mix(P1, "#ffffff", .25), d.player.kind === "team" ? (d.wheel || []) : WHEEL4, "team", 0)}</div></div>`;
  });
}

// The pop-up's thin tier border (look A): border-image of the tier's frame art; plain = the team's color.
export function popupBorder(d, w = 860, h = 600, bw = 5) {
  return withData(d, () => {
    if (d.player.tier === "mvp") return `border:${bw}px solid #c9952f;border-image:linear-gradient(180deg,#fff1c0 0%,#c9952f 12%,#5e3a08 30%,#e8bd5c 46%,#3a2204 58%,#b88428 74%,#fff0bc 88%,#7a5110 100%) 1;`;
    if (d.player.tier === "plain") return `border:${bw}px solid ${P1};`;
    const f = frameAt(w, h, () => frameFor(d.player.tier, P1, S1, T1, 9));
    const url = (f.match(/url\("([^"]+)"\)/) || [])[1];
    const k = d.player.tier === "allnba" ? 2 : 1;
    return url ? `border:${bw}px solid ${P1};border-image:url("${url}") ${bw * k * 3} stretch;` : `border:${bw}px solid ${P1};`;
  });
}
