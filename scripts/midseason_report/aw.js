// Awards: winner up top (picture, name, labeled numbers), 2nd and 3rd as small rows
{
  const day = d => new Date(d + "T12:00").toLocaleDateString("en-US", {weekday: "short", month: "numeric", day: "numeric"});
  const last = n => { const w = n.split(" ").filter(x => !/^(Jr\.?|Sr\.?|II|III|IV)$/.test(x)); return w[w.length - 1]; };
  const top = (xs, key, dir = -1) => [...xs].sort((a,b) => dir * (key(a) - key(b)));
  const sg = (v, neg) => (v >= 0 ? (neg ? "−" : "+") : (neg ? "+" : "−")) + f1(Math.abs(v));
  const pimg = name => { const id = D.byname[name]; return id && D.icons[id] ? D.icons[id] : null; };
  // a fantasy team's icon: its picture, else its glyph on its color (the site's TeamIcon)
  const glyph = (tid, cls) => { const g = D.glyphs[(T[tid] || {}).glyph] || D.glyphs.basketball;
    return `<span class="${cls} gl" style="background:${col(tid)}"><svg viewBox="0 0 24 24"><path d="${g}" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></span>`; };
  const tic = (tid, cls) => D.tlogo[tid] ? `<img class="${cls}" src="${D.tlogo[tid]}" alt="">` : glyph(tid, cls);
  const pic = (src, cls, tid, isTeam) => isTeam ? tic(tid, cls) : src ? `<img class="${cls}" src="${src}" alt="">` : `<span class="${cls}"></span>`;
  const strip = xs => `<div class="strip">${xs.map(([src, cap]) => `<figure>${src ? `<img src="${src}" alt="">` : ""}${cap ? `<figcaption>${cap}</figcaption>` : ""}</figure>`).join("")}</div>`;
  const tchip = tid => T[tid] ? `${tic(tid, "ti")}${nm(tid)}` : "Free agent";

  // one award: f(x) → {name, team (fantasy team id), img, stats: [[value, label], …], extra}
  // all three places in rank order; one is open (the winner first), click a closed one to open it
  const award = (title, xs, f) => {
    const es = xs.slice(0, 3).map(f);
    if (!es.length) return "";
    const ent = (e, i) => {
      const isTeam = e.name === nm(e.team);
      return `<div class="ent${i ? "" : " open"}" style="--tc:${col(e.team)}">
        <button type="button" class="ru-row"><span class="rk">${i + 1}</span>${pic(e.img, isTeam ? "tl-s" : "hs-s", e.team, isTeam)}
          <span class="ru-name">${e.name}${isTeam ? "" : `<small>${tchip(e.team)}</small>`}</span><b class="num">${e.stats[0][0]}</b></button>
        <div class="det"><div class="hero">
          ${pic(e.img, isTeam ? "tl" : "hs", e.team, isTeam)}
          <div class="hero-who">${i ? `<div class="place">${["","2nd","3rd"][i]} place</div>` : ""}<div class="hero-name">${e.name}</div>${isTeam ? "" : `<div class="hero-team">${tchip(e.team)}</div>`}</div>
          <div class="stats">${e.stats.map(([v, l], j) => `<div class="st${j ? " sm" : ""}"><b class="num">${v}</b><span>${l}</span></div>`).join("")}</div>
        </div>${e.extra || ""}</div>
      </div>`;
    };
    return `<div class="aw2" style="--tc:${col(es[0].team)}"><div class="aw2-h">${title}</div>${es.map(ent).join("")}</div>`;
  };
  // redesigned cards (redesign/build_cards.py, 2026-11-14): sealed frames scaled to the column; old look otherwise
  const NC = D.cards || {};
  const nc = k => `<div class="nc" data-k="${k}"></div>`;
  const pick = (k, old) => NC[k] ? nc(k) : old();
  const mount = root => root.querySelectorAll(".nc").forEach(box => {
    const f = document.createElement("iframe");
    f.setAttribute("title", box.dataset.k); f.setAttribute("scrolling", "no");
    f.style.cssText = "display:block;width:100%;border:0;height:400px;background:transparent";
    f.addEventListener("load", () => {
      const d = f.contentDocument, html = d.documentElement;
      const fit = () => {  // measure at full size, then scale the card down to the column
        html.style.zoom = 1;
        const w = Math.max(d.body.scrollWidth, ...[...d.body.children].map(c => c.scrollWidth)), h = d.body.scrollHeight;
        const z = Math.min(1, f.clientWidth / w);
        html.style.zoom = z;
        f.style.height = Math.ceil(h * z) + 4 + "px";
      };
      fit(); (d.fonts ? d.fonts.ready : Promise.resolve()).then(fit); setTimeout(fit, 800);
      new ResizeObserver(fit).observe(box);
    });
    f.srcdoc = NC[box.dataset.k];
    box.appendChild(f);
  });
  const team = (x, stats, extra) => ({name: nm(x.id), team: x.id, stats, extra});
  const plyr = (name, tid, stats, extra, id) => ({name, team: tid, img: (id && D.icons[id]) || pimg(name), stats, extra});
  const PL = {};
  const pv = v => (Math.abs(v) % 1 ? Math.abs(v).toFixed(1) : Math.abs(v));
  const sline = l => l ? `<div class="sline"><div class="box">${l.box || ""}</div><div class="pills">${[...l.parts.filter(p => p[1] > 0), ...l.parts.filter(p => p[1] < 0)].map(([k, v]) => `<span class="${v > 0 ? "up" : "dn"}"><i>${PL[k] || k}</i><b>${v > 0 ? "+" : "−"}${pv(v)}</b></span>`).join("")}</div></div>` : "";
  const used = x => strip(x.used.map(p => [D.icons[p.id], ""]));
  const wks = ws => ws.map(v => v == null ? "—" : f1(v)).join(" · ");

  // MVP by wheel group (the player page's wheel): points from that group in his weekly best games, all season
  el("mvp").innerHTML = ["Scoring", "Playmaking", "Boards", "Stocks"].map(g => pick(g, () =>
    award(g, D.mvp[g], x => plyr(x.name, x.team, [[f1(x.tot), "points from " + g.toLowerCase()]], "", x.id)))).join("") + [
    NC["Most improved"] ? nc("Most improved") : award("Most improved", D.mip, x => plyr(x.name, x.team, [["+" + f1(x.gain), "a week vs last season"], [f1(x.then), "last season"], [f1(x.now), "this season"]], "", x.id)),
    NC["Top rookie"] ? nc("Top rookie") : award("Top rookie", D.rookie, x => plyr(x.name, x.team, [[f1(x.tot), "weekly bests, total"], [f1(x.avg), "a week"]], "", x.id)),
    NC["Sixth man"] ? nc("Sixth man") : award("Sixth man", D.sixth, x => plyr(x.name, x.team, [[f1(x.tot), "points on the bench"], [Object.keys(x.weeks).length, "weeks benched"]], "", x.id)),
  ].join("");

  // All-Fantasy: picture, position, name, total; the owner's icon and color along the bottom
  el("af").innerHTML = NC["All-Fantasy"] ? nc("All-Fantasy") : D.af.map((t, i) => `<div class="tier"><h3>${["1st", "2nd", "3rd"][i]} Team</h3><div class="five">${
    t.map(p => `<div class="afc" style="--tc:${col(p.team)}">
      <div class="afc-img">${p.pos === "TM" ? `<img class="lg" src="${D.icons[p.id] || ""}" alt="">` : D.icons[p.id] ? `<img src="${D.icons[p.id]}" alt="">` : ""}<span class="pos ${p.pos}">${p.pos === "TM" ? "TEAM" : p.pos}</span></div>
      <div class="afc-body"><div class="afc-nm">${p.name}</div><div class="afc-meta">${p.pos === "TM" ? "" : p.nba + " · "}${p.how}</div>
        <b class="afc-tot num">${f1(p.tot)}</b></div>
      <div class="afc-own">${tchip(p.team)}</div></div>`).join("")}</div></div>`).join("");

  el("aw").innerHTML = [
    NC["Biggest game"] ? nc("Biggest game") : award("Biggest game", D.pops, x => plyr(x.name, x.team, [[f1(x.pts), "points"], [`Wk ${x.week} · ${day(x.date)}`, "the game"]], sline(x.line))),
    NC["Best game on the bench"] ? nc("Best game on the bench") : award("Best game on the bench", D.bench, x => plyr(x.bench, x.team, [["+" + f1(x.gain), "over his starter"], [f1(x.bpts), "on the bench"], [f1(x.spts), last(x.start) + " started"]], sline(x.line))),
    NC["Steadiest player"] ? nc("Steadiest player") : award("Steadiest player", D.cons.steady, x => plyr(x.name, x.team, [["±" + f1(x.sd), "week to week"]])),
    NC["Most up-and-down"] ? nc("Most up-and-down") : award("Most up-and-down", D.cons.swing, x => plyr(x.name, x.team, [["±" + f1(x.sd), "week to week"]])),
    award("Same lineup", top(D.cont, x => x.n, 1), x => team(x, [[x.n, "starters used"]], used(x))),
    award("Revolving door", top(D.cont, x => x.n), x => team(x, [[x.n, "starters used"]], used(x))),
    award("Most balanced", D.balance, x => team(x, [[x.pct + "%", "top scorer's share"]], strip(x.weeks.map(w => [pimg(w.name), `Wk ${w.week} ${w.share}%`])))),
    award("One-man team", [...D.balance].reverse(), x => team(x, [[x.pct + "%", "top scorer's share"]], strip(x.weeks.map(w => [pimg(w.name), `Wk ${w.week} ${w.share}%`])))),
    award("Healthiest roster", top(D.health, x => x.games - x.played, 1), x => team(x, [[x.games - x.played, "games missed"], [x.games, "games"]],
      Object.keys(x.miss).length ? strip(Object.entries(x.miss).sort((a,b) => b[1]-a[1]).map(([n,k]) => [pimg(n), `${last(n)} ${k}`])) : "")),
    award("Most games missed", top(D.health, x => x.games - x.played), x => team(x, [[x.games - x.played, "games missed"], [x.games, "games"]],
      strip(Object.entries(x.miss).sort((a,b) => b[1]-a[1]).slice(0,3).map(([n,k]) => [pimg(n), `${last(n)} ${k}`])))),
    award("Just for fun", D.forfun, x => team(x, [[x.n, "adds who never started"]], strip(x.players.map(p => [D.icons[p.id] || pimg(p.name), last(p.name)])))),
    award("Best pickup", D.pick2, x => plyr(x.name, x.team, [[sg(x.per), "a week over replacement"], [Object.keys(x.weeks).length, "weeks started"]])),
    award("Unluckiest", D.unlucky, x => team(x, [[x.n, "bad-luck losses"], [sg(x.under, true), "his guys, a loss"], [sg(x.over), "their guys, a loss"]])),
    award("Stuck with the draft", top(D.draft, x => x.kept), x => team(x, [["$" + x.kept, "drafted, still rostered"], ["$" + x.spent, "spent"]], strip(x.still.map(([id, n, p]) => [D.icons[id], `${last(n)} $${p}`])))),
  ].join("");
  for (const box of [el("mvp"), el("af"), el("aw")]) mount(box);
  for (const box of [el("mvp"), el("aw")]) box.addEventListener("click", e => {
    const row = e.target.closest(".ru-row"); if (!row) return;
    const ent = row.parentElement, card = ent.parentElement;
    card.querySelectorAll(".ent").forEach(x => x.classList.toggle("open", x === ent));
    card.style.setProperty("--tc", getComputedStyle(ent).getPropertyValue("--tc"));
  });
}
