# sup_bal.py S KIND -> m_sup_{KIND}.html : One-man team (KIND=one) / Most balanced (KIND=bal), in the superlative look
# A team award: the winner's sticker is the team's picture; the band shows each week's top scorer and his share.
import json, os, sys
S = sys.argv[1]; KIND = sys.argv[2] if len(sys.argv) > 2 else 'one'
HERE = os.path.dirname(os.path.abspath(__file__)); W2 = f'{S}/work3'
r = json.load(open(f'{W2}/report.json')); T = r['teams']; BY = r['byname']
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
def tpic(tid, cls):  # team picture in a round sticker; the team color when it has none
    lg = r['tlogo'].get(tid); nm = T.get(tid, {}).get('name', '?')
    g = r['glyphs'].get(T.get(tid, {}).get('glyph')) or r['glyphs'].get('basketball', '')  # no picture: its glyph (the site's TeamIcon)
    inner = f'<img src="{lg}">' if lg else f'<svg class="gl" viewBox="0 0 24 24"><path d="{g}" fill="none" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    return f'<span class="{cls}" style="--tc:{tcol(tid)}">{inner}</span>'

lst = r['balance'] if KIND == 'bal' else (r.get('oneman') or r['balance'][::-1])
top = lst[:3]; w = top[0]; tid = w['id']; tn = T.get(tid, {}).get('name', tid)
STYLE = os.environ.get('SB_STYLE', 'pie')  # 2026-11-14: pie picked over bar and ring
def bright(c, need=125):  # dull (grayish) or very dark team colors get lifted toward white so the slice stands out on the dark pie;
    v = hx(c); sat = (max(v) - min(v)) / max(1, max(v))  # strong colors (a real red, green, blue) stay as they are
    if sat >= .45 and lum(c) >= 50: return c
    t = 0
    while lum(mix(c, '#ffffff', t)) < need and t < .7: t += .05
    return mix(c, '#ffffff', t)
SLICE = bright(tcol(tid))
cols = ''
for x in w['weeks']:
    pid = BY.get(x['name']); last = x['name'].rpartition(' ')[2] or x['name']
    if pid in kit:  # an NBA team slot: its logo
        import base64
        lg = base64.b64encode(open(f'{HERE}/kit/{kit[pid]["logo"]}', 'rb').read()).decode()
        face = f'<span class="tsk xs" style="--tc:{lift(kit[pid]["field"])}"><img class="lg" src="data:image/svg+xml;base64,{lg}"></span>'
        last = x['name'].rpartition(' ')[2]
    else:
        face = f'<span class="sk xs" style="--tc:{kpanel(pid)}"><img src="{hs(pid)}"></span>' if pid else '<span class="sk xs"></span>'
    sh = x['share']
    if STYLE == 'pie':  # his slice of the week's starters' points, cut out of the pie
        mid = sh * 1.8; import math
        dx, dy = 4 * math.sin(math.radians(mid)), -4 * math.cos(math.radians(mid))
        ang = sh * 3.6; lg_ = 1 if ang > 180 else 0
        ex, ey = 30 + 26 * math.sin(math.radians(ang)), 30 - 26 * math.cos(math.radians(ang))
        pie = (f'<svg class="pie" viewBox="-4 -4 68 68"><circle cx="30" cy="30" r="26" fill="#262a33" stroke="#16181d" stroke-width="2.5"/>'
               f'<path transform="translate({dx:.1f} {dy:.1f})" d="M30 30 L30 4 A26 26 0 {lg_} 1 {ex:.1f} {ey:.1f} Z" fill="{SLICE}" stroke="#16181d" stroke-width="2.5" stroke-linejoin="round"/></svg>')
        cols += (f'<div class="wc">{face}<span class="pn">{last}</span>{pie}'
                 f'<span class="wv">{sh}%</span><span class="wl">Wk {x["week"]}</span></div>')
    else:  # ring: a ring around his face fills to his share
        cols += (f'<div class="wc"><span class="rg" style="--p:{sh}">{face}</span><span class="pn">{last}</span>'
                 f'<span class="wv">{sh}%</span><span class="wl">Wk {x["week"]}</span></div>')
N = len(w['weeks'])  # up to 9 weeks a row; 18 weeks wrap to two rows of 9
band = f'<div class="wk4"><div class="cols" style="--n:{min(N, 9)}">{cols}</div></div>'
runners = ''.join(
    f'<div class="ru"><span class="rk">{x.get("_rk", i)}</span>{tpic(x["id"], "tsk sm")}'
    f'<span class="rn"><b>{T.get(x["id"], {}).get("name", x["id"])}</b></span><span class="rv">{x["pct"]}%</span></div>'
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
.tsk img{width:100%;height:100%;object-fit:cover}.tsk b{font:800 64px "Bricolage Grotesque";color:#fff}
.tsk .gl{width:56%;height:56%}.tsk.xs{width:44px;height:44px;box-shadow:0 0 0 3px var(--bg),0 0 0 5px var(--tc)}.tsk img.lg{width:74%;height:74%;object-fit:contain}
.tsk.sm{width:46px;height:46px;box-shadow:0 0 0 3px var(--card),0 0 0 5px var(--tc)}.tsk.sm b{font-size:22px}
.tn{font:800 40px/1 "Bricolage Grotesque";letter-spacing:-.02em;text-wrap:balance}
.big{display:flex;flex-direction:column;align-items:flex-end}
.big b{text-shadow:4px 4px 0 color-mix(in srgb,var(--tc) 85%,#000)}
.note{display:block;margin-top:8px!important;background:none!important;padding:0!important;color:var(--text)!important;
  font:700 12px Inter!important;letter-spacing:.08em!important;text-transform:uppercase!important}
.wk4{margin:22px 0 12px;padding:16px 22px 12px;background:var(--bg);border-radius:20px}
.cols{display:grid;grid-template-columns:repeat(var(--n),minmax(0,1fr));gap:16px 10px}
.wc{display:flex;flex-direction:column;align-items:center}
.sk.xs{width:44px;height:44px;box-shadow:0 0 0 3px var(--bg),0 0 0 5px var(--tc)}
.sk.xs img{width:52px;filter:drop-shadow(1.5px 0 0 #fff) drop-shadow(-1.5px 0 0 #fff) drop-shadow(0 -1.5px 0 #fff);
  -webkit-mask:radial-gradient(circle 22px at 50% calc(100% - 22px),#000 99%,transparent 100%) bottom/100% 100% no-repeat,linear-gradient(#000,#000) top/100% 50% no-repeat}
.pn{font:700 11px Inter;margin:7px 0 7px;white-space:nowrap;max-width:100%;overflow:hidden;text-overflow:ellipsis}
.rg{display:grid;place-items:center;width:64px;height:64px;border-radius:50%;
  background:conic-gradient(var(--ac) calc(var(--p)*1%),#2b303b 0);box-shadow:0 0 0 2.5px #16181d,3px 3px 0 2.5px #16181d}
.rg .sk.xs,.rg .tsk.xs{box-shadow:0 0 0 4px var(--bg)!important}
.pie{width:52px;height:52px;margin:2px 0 0;overflow:visible;filter:drop-shadow(3px 3px 0 #16181d)}
.wv{font:800 17px "Bricolage Grotesque";margin-top:10px}.wl{font:700 11px Inter;letter-spacing:.08em;text-transform:uppercase;margin-top:2px}
.ru{grid-template-columns:28px 46px 1fr auto}
</style>''')
BLOB = '<svg viewBox="0 0 300 70" preserveAspectRatio="none"><path d="M14 18 C30 0 90 6 150 4 C210 2 270 -2 290 16 C304 30 300 50 286 62 C260 74 200 66 150 68 C96 70 36 76 14 62 C-2 50 0 30 14 18Z" fill="var(--tc)" stroke="#fff" stroke-width="6"/></svg>'
if KIND == 'bal':  # a balance scale, level
    ic = ('<svg class="ic" viewBox="0 0 36 30"><path d="M18 4 V25 M7 9 H29" stroke="#16181d" stroke-width="5" stroke-linecap="round"/>'
          '<path d="M18 4 V25 M7 9 H29" stroke="#ffd23f" stroke-width="2.5" stroke-linecap="round"/>'
          '<path d="M2 18 L7 9 L12 18 Z M24 18 L29 9 L34 18 Z" fill="#ffd23f" stroke="#16181d" stroke-width="2"/><rect x="11" y="24" width="14" height="4" rx="1" fill="#ffd23f" stroke="#16181d" stroke-width="2"/></svg>')
    title = f'<div class="ttl"><span class="blb">{BLOB}<span class="w">{ic}<i>MOST</i> <b>BALANCED</b></span></span></div>'
else:  # one player, alone
    ic = ('<svg class="ic" viewBox="0 0 36 30"><circle cx="18" cy="8" r="6" fill="#ffd23f" stroke="#16181d" stroke-width="2.5"/>'
          '<path d="M7 29 C7 19 11 15.5 18 15.5 C25 15.5 29 19 29 29 Z" fill="#ffd23f" stroke="#16181d" stroke-width="2.5" stroke-linejoin="round"/></svg>')
    title = f'<div class="ttl"><span class="blb">{BLOB}<span class="w">{ic}<b>ONE-MAN</b> <i>team</i></span></span></div>'
big = f'<div class="big"><b>{w["pct"]}%</b><span class="note">top scorer\'s share</span></div>'
html = (f'<title>sup {KIND}</title>{css}<div class="card">{title}'
        f'<div class="win">{tpic(tid, "tsk")}<div><div class="tn">{tn}</div></div>{big}</div>{band}{runners}</div>')
open(f'{S}/m_sup_{KIND}.html', 'w').write(html)
