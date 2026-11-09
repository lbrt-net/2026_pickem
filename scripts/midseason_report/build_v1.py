import json, pathlib
here = pathlib.Path(__file__).parent
data = json.load(open(here / "report.json"))
html = r"""<title>Mid-Season Report</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&family=Barlow+Condensed:ital,wght@0,600;0,700;0,800;1,800&display=swap">
<style>
/* Layout: one column of sections, league site's dark graphite look; standings loud, info tables plain. */
:root{
  --bg:#0f1117; --surface:#161b22; --surface-2:#1c2333; --border:#30363d; --text:#e6edf3;
  --accent:#ff6a1f; --good:#22c55e; --bad:#ef4444;
  --pos-g:#1d6fd6; --pos-f:#1a8a55; --pos-c:#c2540e;
  --panel-1:#18243c; --panel-2:#0f1728;
  --font-body:"Barlow",-apple-system,"Segoe UI",sans-serif;
  --font-display:"Barlow Condensed","Arial Narrow",sans-serif;
  color-scheme:dark;
}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:var(--font-body);font-size:15px;line-height:1.4}
.wrap{max-width:1080px;margin:0 auto;padding-block:28px 64px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:flex;flex-direction:column;gap:44px}
header h1{font-family:var(--font-display);font-style:italic;font-weight:800;font-size:clamp(40px,8vw,72px);line-height:.9;margin:0;text-transform:uppercase;letter-spacing:.01em}
header h1 span{color:var(--accent)}
header .sub{margin-top:8px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;font-size:13px}
h2{font-family:var(--font-display);font-weight:800;text-transform:uppercase;font-size:28px;margin:0 0 14px;letter-spacing:.02em;text-wrap:balance}
.num{font-variant-numeric:tabular-nums}
.chip{display:inline-block;width:12px;height:12px;border-radius:2px;box-shadow:inset 0 0 0 1px var(--border);margin-right:8px;vertical-align:-1px;flex:none}
.scroll{overflow-x:auto}
/* standings: loud */
table{border-collapse:collapse;width:100%}
.stand th{font-family:var(--font-display);font-weight:700;text-transform:uppercase;letter-spacing:.05em;font-size:14px;text-align:right;padding:8px 10px;border-bottom:2px solid var(--accent)}
.stand th:first-child,.stand td:first-child{text-align:left}
.stand td{padding:9px 10px;text-align:right;font-weight:600;border-bottom:1px solid var(--border)}
.stand tr.cut td{border-bottom:2px solid var(--text)}
.stand td.team{font-weight:700;white-space:nowrap}
.stand td.wl{font-weight:800;font-size:17px}
.luck-pos{color:var(--good)} .luck-neg{color:var(--bad)}
.lbar{display:inline-block;height:8px;vertical-align:middle;margin-left:8px;border-radius:1px}
/* all-fantasy */
.tier{display:flex;flex-direction:column;gap:10px;margin-bottom:22px}
.tier h3{font-family:var(--font-display);font-weight:800;font-size:20px;text-transform:uppercase;margin:0;letter-spacing:.04em}
.five{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}
.pc{background:linear-gradient(160deg,var(--panel-1),var(--panel-2));border:1px solid var(--border);display:flex;flex-direction:column;min-width:0}
.pc .top{padding:12px 12px 10px;display:flex;flex-direction:column;gap:4px;flex:1}
.pos{display:inline-block;font-family:var(--font-display);font-weight:800;font-size:13px;padding:1px 6px;width:max-content}
.pos.G{background:var(--pos-g)} .pos.F{background:var(--pos-f)} .pos.C{background:var(--pos-c)}
.pc .nm{font-weight:700;font-size:16px;line-height:1.15}
.pc .nba{font-size:13px;font-weight:500}
.pc .tot{font-family:var(--font-display);font-weight:800;font-size:30px;line-height:1;margin-top:6px}
.pc .wks{font-size:12px;font-weight:500}
.pc .band{padding:6px 12px;font-weight:700;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
/* award cards */
.two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.aw{background:var(--surface);border:1px solid var(--border);display:flex;flex-direction:column;min-width:0}
.aw .tab{font-family:var(--font-display);font-weight:800;text-transform:uppercase;letter-spacing:.06em;font-size:14px;padding:7px 14px;background:var(--surface-2);border-bottom:1px solid var(--border)}
.aw .body{padding:16px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.aw .big{font-family:var(--font-display);font-weight:800;font-size:44px;line-height:1}
.aw .who{font-weight:700;font-size:19px}
.aw .line{font-weight:500;font-size:14px}
.aw .info{display:flex;flex-direction:column;gap:3px;min-width:0;flex:1}
.wkbars{display:flex;align-items:flex-end;gap:6px;height:84px}
.wkbars div{width:30px;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:3px;height:100%;font-size:12px;font-weight:600}
.wkbars i{display:block;width:100%}
/* plain info tables */
.plain th{text-align:right;font-weight:600;font-size:13px;text-transform:uppercase;letter-spacing:.05em;padding:6px 10px;border-bottom:1px solid var(--border)}
.plain td{text-align:right;padding:7px 10px;border-bottom:1px solid var(--surface-2)}
.plain th:first-child,.plain td:first-child{text-align:left}
.plain td:first-child{white-space:nowrap}
.dollars{display:flex;flex-direction:column;gap:7px}
.drow{display:grid;grid-template-columns:200px 1fr 70px;gap:12px;align-items:center}
.drow .t{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.track{height:16px;background:var(--surface-2);position:relative}
.track .k{position:absolute;inset:0 auto 0 0}
.track .g{position:absolute;top:0;bottom:0;background:repeating-linear-gradient(45deg,var(--border) 0 4px,transparent 4px 8px)}
.drow .v{font-weight:700;text-align:right}
.gone{font-size:13px;font-weight:500;grid-column:2/4;margin-top:-4px}
.split{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:28px}.split>div{min-width:0}
svg text{fill:var(--text);font-family:var(--font-body)}
@media (max-width:900px){.five{grid-template-columns:repeat(2,minmax(0,1fr))}.two,.split{grid-template-columns:1fr}.drow{grid-template-columns:120px 1fr 60px}}
@media (max-width:420px){.five{grid-template-columns:1fr 1fr}.pc .tot{font-size:26px}}
</style>
<div class="wrap">
<header>
  <h1>Mid-Season <span>Report</span></h1>
  <div class="sub">2026-27</div>
</header>

<section><h2>Standings</h2><div class="scroll"><table class="stand" id="stand"></table></div></section>

<section><h2>All-Fantasy Teams</h2><div id="af"></div></section>

<section class="two" id="steady"></section>

<section class="split">
  <div><h2>Most Active</h2><div class="scroll"><table class="plain" id="act"></table></div></div>
  <div><h2>Improbable Wins</h2><div id="imp"></div></div>
</section>

<section><h2>Draft Dollars Still On The Roster</h2><div class="dollars" id="dollars"></div></section>

<section class="two" id="vb"></section>
</div>
<script>
const D = __DATA__;
const T = D.teams, nm = id => T[id] ? T[id].name : "Free agent", col = id => T[id] ? T[id].color : "#30363d";
const chip = id => `<span class="chip" style="background:${col(id)}"></span>`;
const f1 = x => (Math.round(x*10)/10).toFixed(1);
const el = id => document.getElementById(id);

// Standings
{
  const maxL = Math.max(...D.stand.map(s => Math.abs(s.luck)));
  let h = `<tr><th>Team</th><th>W-L</th><th>PF/WK</th><th>PA/WK</th><th>All-play</th><th>Luck</th></tr>`;
  D.stand.forEach((s,i) => {
    const g = s.w+s.l, c = s.luck>=0 ? "luck-pos":"luck-neg";
    h += `<tr><td class="team">${chip(s.id)}${nm(s.id)}</td><td class="wl num">${s.w}-${s.l}</td>
      <td class="num">${f1(s.pf/g)}</td><td class="num">${f1(s.pa/g)}</td><td class="num">${s.apw}-${s.apl}</td>
      <td class="num ${c}">${s.luck>0?"+":""}${s.luck.toFixed(1)} W<span class="lbar" style="width:${Math.abs(s.luck)/maxL*50}px;background:currentColor"></span></td></tr>`;
  });
  el("stand").innerHTML = h;
}

// All-Fantasy
el("af").innerHTML = D.af.map((t,i) => `<div class="tier"><h3>${["1st","2nd","3rd"][i]} Team</h3><div class="five">${
  t.map(p => `<div class="pc"><div class="top"><span class="pos ${p.pos}">${p.pos}</span>
    <div class="nm">${p.name}</div><div class="nba">${p.nba}${p.price ? ` · drafted $${p.price}` : " · undrafted"}</div>
    <div class="tot num">${f1(p.weeks.reduce((a,b)=>a+b,0))}</div>
    <div class="wks num">${p.weeks.map(f1).join(" · ")}</div></div>
    <div class="band" style="background:${col(p.team)}">${nm(p.team)}</div></div>`).join("")}</div></div>`).join("");

// Steadiest / most up-and-down
{
  const by = [...D.stand].sort((a,b)=>a.sd-b.sd);
  const top = Math.max(...D.stand.flatMap(s=>s.scores));
  const card = (lab, s) => `<div class="aw"><div class="tab">${lab}</div><div class="body">
    <div class="wkbars">${s.scores.map((v,i)=>`<div><span class="num">${f1(v)}</span><i style="height:${v/top*60}px;background:${col(s.id)}"></i><span>W${i+1}</span></div>`).join("")}</div>
    <div class="info"><div class="who">${chip(s.id)}${nm(s.id)}</div><div class="line num">${f1(Math.max(...s.scores)-Math.min(...s.scores))} between best and worst week</div><div class="line">${s.w}-${s.l}</div></div></div></div>`;
  el("steady").innerHTML = card("Most consistent", by[0]) + card("Most up-and-down", by[by.length-1]);
}

// Activity
el("act").innerHTML = `<tr><th>Team</th><th>Moves</th><th>Players added</th><th>Trade offers</th></tr>` +
  D.activity.map(a => `<tr><td>${chip(a.id)}${nm(a.id)}</td><td class="num"><b>${a.moves}</b></td><td class="num">${a.adds}</td><td class="num">${a.offers}</td></tr>`).join("");

// Improbable wins (win chance curves)
{
  const W = 300, H = 90;
  el("imp").innerHTML = `<div style="display:flex;flex-direction:column;gap:12px">` + D.imp.map(x => {
    const n = x.curve.length, pts = x.curve.map((p,i)=>`${8+i*(W-16)/(n-1)},${8+(1-p)*(H-16)}`).join(" ");
    const lowI = x.curve.indexOf(Math.min(...x.curve));
    const [lx,ly] = pts.split(" ")[lowI].split(",");
    return `<div class="aw"><div class="tab">Week ${x.week}</div><div class="body">
      <div class="info"><div class="who">${chip(x.winner)}${nm(x.winner)}</div><div class="line">over ${nm(x.loser)}</div>
      <div class="line num">Low ${Math.round(x.low*100)}% → ${x.now ? `${Math.round(x.curve[n-1]*100)}% now` : "won"}</div></div>
      <svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:220px" role="img" aria-label="win chance by day">
        <line x1="8" x2="${W-8}" y1="${H/2}" y2="${H/2}" stroke="#30363d" stroke-dasharray="3 3"/>
        <polyline points="${pts}" fill="none" stroke="${col(x.winner)}" stroke-width="3" stroke-linejoin="round"/>
        <circle cx="${lx}" cy="${ly}" r="4.5" fill="#e6edf3"/></svg></div></div>`;
  }).join("") + `</div>`;
}

// Draft dollars kept
{
  const max = Math.max(...D.draft.map(d=>d.spent));
  el("dollars").innerHTML = D.draft.map(d => `<div class="drow"><div class="t">${chip(d.id)}${nm(d.id)}</div>
    <div class="track"><div class="k" style="width:${d.kept/max*100}%;background:${col(d.id)}"></div><div class="g" style="left:${d.kept/max*100}%;width:${(d.spent-d.kept)/max*100}%"></div></div>
    <div class="v num">$${d.kept}<span style="font-weight:500"> / ${d.spent}</span></div>
    ${d.gone.length ? `<div></div><div class="gone">Gone: ${d.gone.map(g=>`${g[0]} ($${g[1]})`).join(", ")}</div>` : ""}</div>`).join("");
}

// Best value / biggest bust
{
  const card = (lab, p) => `<div class="aw"><div class="tab">${lab}</div><div class="body">
    <div class="big num">$${p.price}</div>
    <div class="info"><div class="who">${p.name}</div><div class="line">${chip(p.team)}${nm(p.team)}</div>
    <div class="line num">#${p.prank} in price of ${D.ndrafted} drafted · #${p.trank} in points</div>
    <div class="line num">${p.weeks.map(w=>w==null?"—":f1(w)).join(" · ")}</div></div></div></div>`;
  el("vb").innerHTML = card("Best draft value", D.value) + card("Biggest bust", D.bust);
}
</script>
"""
(here / "midseason.html").write_text(html.replace("__DATA__", json.dumps(data)))
print("ok")
