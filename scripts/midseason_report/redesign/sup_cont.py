# sup_cont.py S KIND -> m_sup_{KIND}.html : Same lineup (KIND=same) / Revolving door (KIND=door), in the superlative look
# A team award: the winner's sticker is the team's picture; the band is a packed bubble chart of every starter he used,
# each circle's area proportional to the games that player played in a starting slot. Both cards share one scale.
import base64, json, math, os, sys
S = sys.argv[1]; KIND = sys.argv[2] if len(sys.argv) > 2 else 'same'
HERE = os.path.dirname(os.path.abspath(__file__)); W2 = f'{S}/work3'
r = json.load(open(f'{W2}/report.json')); T = r['teams']
kit = json.load(open(f'{HERE}/kit/kit.json'))
P = {p['id']: p for p in json.load(open(f'{W2}/players_scenario_live.json'))}
def hx(c): c = c.lstrip('#'); return [int(c[i:i+2], 16) for i in (0, 2, 4)]
def mix(a, b, t): return '#' + ''.join(f'{round(x*(1-t)+y*t):02x}' for x, y in zip(hx(a), hx(b)))
def lum(c): a, b, d = hx(c); return .2126*a + .7152*b + .0722*d
def lift(c): return c if lum(c) >= 45 else mix(c, '#ffffff', .2)
AL = {'GS': 'GSW', 'NY': 'NYK', 'SA': 'SAS', 'NO': 'NOP', 'PHO': 'PHX', 'UTAH': 'UTA', 'WSH': 'WAS', 'BRK': 'BKN'}
def kpanel(pid):
    ab = P.get(pid, {}).get('nba_team') or P.get(pid, {}).get('team'); k = kit.get(AL.get(ab, ab)) or kit['SAS']
    return lift(k['field'])
hs = lambda pid: f'https://cdn.nba.com/headshots/nba/latest/1040x760/{pid}.png'
tcol = lambda tid: lift(T.get(tid, {}).get('color') or '#52637b')
def tpic(tid, cls):  # team picture in a round sticker; its glyph on the team color when it has none
    lg = r['tlogo'].get(tid)
    g = r['glyphs'].get(T.get(tid, {}).get('glyph')) or r['glyphs'].get('basketball', '')
    inner = f'<img src="{lg}">' if lg else f'<svg class="gl" viewBox="0 0 24 24"><path d="{g}" fill="none" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    return f'<span class="{cls}" style="--tc:{tcol(tid)}">{inner}</span>'

lst = r.get('cont_same' if KIND == 'same' else 'cont_rev') or (sorted(r['cont'], key=lambda c: (c['n'], -len(c['every']))) if KIND == 'same'
                                                               else sorted(r['cont'], key=lambda c: (-c['n'], len(c['every']))))
top = lst[:3]; w = top[0]; tid = w['id']; tn = T.get(tid, {}).get('name', tid)

# --- packed bubbles: area ~ games started; one scale for every team (the busiest team fills about 60% of the band)
BW, BH = 588, 250
gsum = max(sum(max(u.get('g', 0), 1) for u in c['used']) for c in r['cont'])
K = math.sqrt(.62 * BW * BH / (math.pi * gsum))
items = sorted(({**u, 'r': max(13, K * math.sqrt(max(u.get('g', 0), 1)))} for u in w['used']), key=lambda u: -u['r'])
PAD = 3
def ok(x, y, rr, placed):
    return all(math.hypot(x - p['x'], y - p['y']) >= rr + p['r'] + PAD - 1e-6 for p in placed)
placed = []
for it in items:
    rr = it['r']
    if not placed:
        it['x'], it['y'] = 0.0, 0.0; placed.append(it); continue
    cands = []
    for a in placed:  # touching one circle, at 36 angles
        for k in range(36):
            t = 2 * math.pi * k / 36; d = a['r'] + rr + PAD
            cands.append((a['x'] + d * math.cos(t), a['y'] + d * math.sin(t)))
    for i, a in enumerate(placed):  # touching two circles
        for b in placed[i + 1:]:
            ra, rb = a['r'] + rr + PAD, b['r'] + rr + PAD; dx, dy = b['x'] - a['x'], b['y'] - a['y']; d = math.hypot(dx, dy)
            if d == 0 or d > ra + rb or d < abs(ra - rb): continue
            l = (ra * ra - rb * rb + d * d) / (2 * d); h = math.sqrt(max(0, ra * ra - l * l))
            mx, my = a['x'] + l * dx / d, a['y'] + l * dy / d
            cands += [(mx + h * dy / d, my - h * dx / d), (mx - h * dy / d, my + h * dx / d)]
    # closest to the middle, squashed so the cluster spreads wide like the band
    best = min((c for c in cands if ok(c[0], c[1], rr, placed)), key=lambda c: (c[0] / 2.1) ** 2 + c[1] ** 2)
    it['x'], it['y'] = best; placed.append(it)
x0 = min(p['x'] - p['r'] for p in placed); x1 = max(p['x'] + p['r'] for p in placed)
y0 = min(p['y'] - p['r'] for p in placed); y1 = max(p['y'] + p['r'] for p in placed)
sc = min(1, (BW - 8) / (x1 - x0), (BH - 8) / (y1 - y0))
cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
bub = ''
for p in placed:
    d = 2 * p['r'] * sc; L = BW / 2 + (p['x'] - cx) * sc - d / 2; Tp = BH / 2 + (p['y'] - cy) * sc - d / 2
    pid = p['id']
    if pid in kit:  # an NBA team slot: its logo
        lg = base64.b64encode(open(f'{HERE}/kit/{kit[pid]["logo"]}', 'rb').read()).decode()
        inner = f'<img class="lg" src="data:image/svg+xml;base64,{lg}">'; col = lift(kit[pid]['field'])
    else:
        inner = f'<img class="hd" src="{hs(pid)}">'; col = kpanel(pid)
    fs = max(10, min(22, round(d * .2)))
    bub += (f'<div class="bub" style="left:{L:.0f}px;top:{Tp:.0f}px;width:{d:.0f}px;height:{d:.0f}px;--tc:{col}" data-n="{p["name"]}" data-s="{p.get("g", 0)} games · {p.get("w", 0)} week{"" if p.get("w", 0) == 1 else "s"}">'
            f'{inner}<b style="font-size:{fs}px">{p.get("g", 0)}</b></div>')
band = f'<div class="wk4"><div class="bubs" style="height:{BH}px">{bub}<div class="tip" hidden><b></b><span></span></div></div></div>'
runners = ''.join(
    f'<div class="ru"><span class="rk">{x.get("_rk", i)}</span>{tpic(x["id"], "tsk sm")}'
    f'<span class="rn"><b>{T.get(x["id"], {}).get("name", x["id"])}</b></span><span class="rv">{x["n"]}</span></div>'
    for i, x in ((2, top[1]), (3, top[2])) if x)

css = open(f'{HERE}/sup_base.css').read().replace('family=Bricolage', 'family=Kalam:wght@700&family=Permanent+Marker&family=Caveat+Brush&family=Bricolage', 1)
css = css.replace('--tc:', '--tc:' + tcol(tid) + ';--x:', 1).replace('--ac:', '--ac:#f2f4f7;--y:', 1)
css = css.replace('</style>', '''
.card{background:var(--card)!important;box-shadow:7px 7px 0 0 color-mix(in srgb,var(--tc) 80%,#000)}
.card:before{right:-40px!important;top:-40px!important;width:420px!important;height:360px!important;border-radius:0!important;opacity:1!important;
  background:radial-gradient(circle,color-mix(in srgb,var(--tc) 85%,#fff) 2.2px,transparent 2.6px) 0 0/11px 11px!important;
  -webkit-mask:radial-gradient(ellipse at 100% 0,#000 0,rgba(0,0,0,.55) 35%,transparent 70%)}
.ttl{position:relative;display:inline-flex;align-items:center;margin:0 0 20px}
.blb{position:relative;display:inline-grid;place-items:center;padding:20px 30px 22px}
.blb svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible;filter:drop-shadow(0 5px 6px rgba(0,0,0,.45))}
.blb .w{position:relative;white-space:nowrap;color:#fff;line-height:1;word-spacing:-.02em}
.blb b{font:400 26px "Permanent Marker"}.blb i{font:400 20px "Caveat Brush";font-style:normal}
.blb .ic{position:relative;width:34px;height:30px;margin-right:8px;vertical-align:-6px}
.tsk{position:relative;display:grid;place-items:center;width:150px;height:150px;border-radius:50%;background:var(--tc);overflow:hidden;
  box-shadow:0 0 0 5px var(--card),0 0 0 8px var(--ac),8px 8px 0 5px #16181d}
.tsk img{width:100%;height:100%;object-fit:cover}.tsk .gl{width:56%;height:56%}
.tsk.sm{width:46px;height:46px;box-shadow:0 0 0 3px var(--card),0 0 0 5px var(--tc)}
.tn{font:800 40px/1 "Bricolage Grotesque";letter-spacing:-.02em;text-wrap:balance}
.big{display:flex;flex-direction:column;align-items:flex-end}
.big b{text-shadow:4px 4px 0 color-mix(in srgb,var(--tc) 85%,#000)}
.note{display:block;margin-top:8px!important;background:none!important;padding:0!important;color:var(--text)!important;
  font:700 12px Inter!important;letter-spacing:.08em!important;text-transform:uppercase!important}
.wk4{margin:22px 0 12px;padding:14px 0 10px;background:var(--bg);border-radius:20px}
.bubs{position:relative;width:588px;margin:0 auto}
.bub{position:absolute;border-radius:50%;background:var(--tc);overflow:hidden;box-sizing:border-box;border:2.5px solid #16181d;
  box-shadow:3px 3px 0 0 #16181d;background-image:radial-gradient(rgba(0,0,0,.16) 1.2px,transparent 1.5px);background-size:6px 6px}
.bub img.hd{position:absolute;left:50%;bottom:-4%;width:128%;transform:translateX(-50%)}
.bub img.lg{position:absolute;inset:16%;width:68%;height:68%;object-fit:contain}
.bub b{position:absolute;left:50%;bottom:6%;transform:translateX(-50%);font-family:"Bricolage Grotesque";font-weight:800;line-height:1;color:#fff;
  -webkit-text-stroke:4px #16181d;paint-order:stroke fill}
.key{margin-top:8px;text-align:center;font:700 11px Inter;letter-spacing:.08em;text-transform:uppercase}
.ru{grid-template-columns:28px 46px 1fr auto}
.bub{cursor:default}.bub:hover{z-index:2;outline:3px solid #ffd23f;outline-offset:1px}
.tip{position:absolute;z-index:5;transform:translate(-50%,calc(-100% - 12px));pointer-events:none;white-space:nowrap;text-align:center;
  background:#fff;color:#16181d;border:2.5px solid #16181d;border-radius:10px;box-shadow:4px 4px 0 0 #16181d;padding:7px 12px 6px}
.tip:after{content:"";position:absolute;left:50%;bottom:-9px;width:14px;height:14px;background:#fff;border-right:2.5px solid #16181d;border-bottom:2.5px solid #16181d;transform:translateX(-50%) rotate(45deg)}
.tip b{display:block;font:800 17px/1.1 "Bricolage Grotesque"}.tip span{display:block;font:700 12px Inter;margin-top:2px}
</style>''')
BLOB = '<svg viewBox="0 0 300 70" preserveAspectRatio="none"><path d="M14 18 C30 0 90 6 150 4 C210 2 270 -2 290 16 C304 30 300 50 286 62 C260 74 200 66 150 68 C96 70 36 76 14 62 C-2 50 0 30 14 18Z" fill="var(--tc)" stroke="#fff" stroke-width="6"/></svg>'
if KIND == 'same':  # a padlock
    ic = ('<svg class="ic" viewBox="0 0 36 30"><path d="M11 13 V9 a7 7 0 0 1 14 0 V13" fill="none" stroke="#16181d" stroke-width="6"/>'
          '<path d="M11 13 V9 a7 7 0 0 1 14 0 V13" fill="none" stroke="#ffd23f" stroke-width="3"/>'
          '<rect x="7" y="13" width="22" height="15" rx="3" fill="#ffd23f" stroke="#16181d" stroke-width="2.5"/><circle cx="18" cy="20" r="2.4" fill="#16181d"/></svg>')
    title = f'<div class="ttl"><span class="blb">{BLOB}<span class="w">{ic}<b>SAME</b> <i>lineup</i></span></span></div>'
else:  # two arrows chasing each other
    ic = ('<svg class="ic" viewBox="0 0 36 30"><g fill="none" stroke-linecap="round"><path d="M8 13 A10 10 0 0 1 27 10" stroke="#16181d" stroke-width="6"/><path d="M28 17 A10 10 0 0 1 9 20" stroke="#16181d" stroke-width="6"/>'
          '<path d="M8 13 A10 10 0 0 1 27 10" stroke="#ffd23f" stroke-width="3"/><path d="M28 17 A10 10 0 0 1 9 20" stroke="#ffd23f" stroke-width="3"/></g>'
          '<path d="M23 5 L30 9 L24 14 Z M13 25 L6 21 L12 16 Z" fill="#ffd23f" stroke="#16181d" stroke-width="2" stroke-linejoin="round"/></svg>')
    title = f'<div class="ttl"><span class="blb">{BLOB}<span class="w">{ic}<b>REVOLVING</b> <i>door</i></span></span></div>'
big = f'<div class="big"><b>{w["n"]}</b><span class="note">starters used</span></div>'
html = (f'<title>sup {KIND}</title>{css}<div class="card">{title}'
        f'<div class="win">{tpic(tid, "tsk")}<div><div class="tn">{tn}</div></div>{big}</div>{band}{runners}</div>')
# hover a bubble: its name, games and weeks in a comic label above it
html += '''<script>document.addEventListener("mouseover", e => {
  const b = e.target.closest(".bub"); document.querySelectorAll(".tip").forEach(t => t.hidden = true); if (!b) return;
  const t = b.parentNode.querySelector(".tip"); t.querySelector("b").textContent = b.dataset.n; t.querySelector("span").textContent = b.dataset.s;
  t.style.left = (b.offsetLeft + b.offsetWidth / 2) + "px"; t.style.top = b.offsetTop + "px"; t.hidden = false;
});</script>'''
open(f'{S}/m_sup_{KIND}.html', 'w').write(html)
