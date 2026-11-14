# sup.py S -> m_sup_bench.html : Best game on the bench, in the superlative look
import json, sys
S = sys.argv[1]; K = __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), 'kit'); W2 = f'{S}/work3'
r = json.load(open(f'{W2}/report.json')); T = r['teams']; BY = r['byname']
kit = json.load(open(f'{K}/kit.json'))
P = {p['id']: p for p in json.load(open(f'{W2}/players_scenario_live.json'))}
def hx(c): c = c.lstrip('#'); return [int(c[i:i+2], 16) for i in (0, 2, 4)]
def mix(a, b, t): return '#' + ''.join(f'{round(x*(1-t)+y*t):02x}' for x, y in zip(hx(a), hx(b)))
def lum(c): a, b, d = hx(c); return .2126*a + .7152*b + .0722*d
for k in kit.values():
    k['panel'] = k['field'] if lum(k['field']) >= 45 else mix(k['field'], '#ffffff', .16)
    k['accent'] = next((c for c in (k['secondary'], k['tertiary'], '#ffffff') if lum(c) >= 60), '#ffffff')
AL = {'GS': 'GSW', 'NY': 'NYK', 'SA': 'SAS', 'NO': 'NOP', 'PHO': 'PHX', 'UTAH': 'UTA', 'WSH': 'WAS', 'BRK': 'BKN'}
def kof(pid):
    ab = P.get(pid, {}).get('nba_team') or P.get(pid, {}).get('team'); return kit.get(AL.get(ab, ab)) or kit['SAS']
def own(tid, cls='own'):
    t = T.get(tid)
    if not t: return f'<span class="{cls}">Free agent</span>'
    lg = r['tlogo'].get(tid); ic = f'<img src="{lg}">' if lg else f'<i style="background:{t["color"]}"></i>'
    return f'<span class="{cls}">{ic}{t["name"]}</span>'
hs = lambda pid: f'https://cdn.nba.com/headshots/nba/latest/1040x760/{pid}.png'
import datetime
top = r['pops'][:3]; w = top[0]; bid = BY[w['name']]; kb = kof(bid)
G = None
for t in json.load(open(f"{W2}/f3/wa{w['week']}.json")).values():
    for e in t['entries']:
        if e.get('name') == w['name']:
            G = next(g for g in e['games'] if g['date'] == w['date']); BOX = e.get('box_line')
fn, _, ln = w['name'].rpartition(' ')
day = datetime.date.fromisoformat(w['date']).strftime('%a %-m/%-d')
pos = sorted([p for p in G['parts'] if p['points'] > 0], key=lambda p: -p['points']); neg = sum(p['points'] for p in G['parts'] if p['points'] < 0)
tot = sum(p['points'] for p in pos)
big = [p for p in pos if p['points'] >= 8][:4]; small = [p for p in pos if p not in big]
shades = [kb['panel'], kb['accent'], mix(kb['panel'], '#ffffff', .35), mix(kb['accent'], '#000000', .35), mix(kb['panel'], '#000000', .35)]
terms = [(p['points'], p['label']) for p in big] + ([(sum(p['points'] for p in small), 'other')] if small else [])
import math
fills = [kb['panel'], kb['accent'], mix(kb['panel'], '#ffffff', .3), mix(kb['accent'], '#000000', .3), '#3a3f4b']
SH = {  # die-cut sticker outlines (100x100 box)
 'badge': ''.join(f"{'M' if k == 0 else 'L'}{50 + (46 if k % 2 == 0 else 40) * math.cos(math.pi * k / 12):.1f} {50 + (46 if k % 2 == 0 else 40) * math.sin(math.pi * k / 12):.1f} " for k in range(24)) + 'Z',
 'blob': 'M50 4 C74 2 96 20 95 46 C94 72 80 97 50 95 C22 93 3 76 5 48 C7 22 27 6 50 4Z',
 'squircle': 'M50 5 C88 5 95 12 95 50 C95 88 88 95 50 95 C12 95 5 88 5 50 C5 12 12 5 50 5Z',
 'hex': 'M30 8 L70 8 Q78 8 82 15 L96 43 Q99 50 96 57 L82 85 Q78 92 70 92 L30 92 Q22 92 18 85 L4 57 Q1 50 4 43 L18 15 Q22 8 30 8Z',
 'cloud': 'M' + f"{50 + 40 * math.cos(0):.1f} {50 + 40 * math.sin(0):.1f} " + ''.join(f"A14 14 0 0 1 {50 + 40 * math.cos(2 * math.pi * (k + 1) / 9):.1f} {50 + 40 * math.sin(2 * math.pi * (k + 1) / 9):.1f} " for k in range(9)) + 'Z',
 'burst': ''.join(f"{'M' if k == 0 else 'L'}{50 + (47 if k % 2 == 0 else 30) * math.cos(math.pi * k / 9 - 1.4):.1f} {50 + (47 if k % 2 == 0 else 30) * math.sin(math.pi * k / 9 - 1.4):.1f} " for k in range(18)) + 'Z'}
ORDER = ['badge', 'blob', 'squircle', 'hex']
import sys; sys.path.insert(0, S); from stickers import sticker, CSS as STK_CSS
LBL = {'3PTM': '3PTM', 'CLUTCH': 'CLUTCH', 'FG-': 'FG-', 'FT-': 'FT-', 'TO': 'TO', 'BLKD': 'BLKD'}
srt = sorted(G['parts'], key=lambda p: -abs(p['points']))
top5 = srt if len(srt) <= 5 else srt[:4] + [{'label': 'OTHER', 'points': round(sum(p['points'] for p in srt[4:]), 1)}]  # 5 or fewer categories: show them all
eq = ''.join(sticker(p['label'], p['points'], round(max(84, 52 + 6 * math.sqrt(abs(p['points'])))), k) for k, p in enumerate(top5))
band = (f'<div class="gm"><div class="gl"><span class="wk">Week {w["week"]}</span><div class="gd">{"vs" if G["home"] else "at"} {G["opp"]} · {day}<br>{G["min"]} minutes</div></div>'
        f'<div class="gr"><div class="eq">{eq}</div></div></div>'
        '')
runners = ''.join(
    f'<div class="ru"><span class="rk">{i}</span><span class="sk sm" style="--tc:{kof(BY[x["name"]])["panel"]}"><img src="{hs(BY[x["name"]])}"></span>'
    f'<span class="rn"><b>{x["name"]}</b>{own(x["team"], "own s")}</span><span class="rv">{x["pts"]:.1f}</span></div>' for i, x in ((2, top[1]), (3, top[2])))
css = open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), 'sup_base.css')).read().replace('family=Bricolage','family=Kalam:wght@700&family=Permanent+Marker&family=Caveat+Brush&family=Bricolage',1)
css = css.replace('--tc:', '--tc:' + kb['panel'] + ';--x:', 1).replace('--ac:', '--ac:' + kb['accent'] + ';--y:', 1)
css = css.replace('</style>', STK_CSS + '''
.gm{display:grid;grid-template-columns:auto 1fr;gap:22px;align-items:center;margin:22px 0 16px;padding:28px 18px;background:var(--bg);border-radius:20px}
.gl{display:flex;flex-direction:column;gap:10px;align-items:flex-start}.gd{font:600 13px/1.4 Inter;white-space:nowrap}
.gbox{font:800 24px/1.05 "Bricolage Grotesque";letter-spacing:-.01em;text-align:right}
.gr{display:flex;flex-direction:column;align-items:stretch;gap:14px}.eq .stk{margin:0 -6px}.eq{display:flex;align-items:center;justify-content:flex-end;gap:0;flex:1;margin:0 2px 2px 0}
.dt{display:grid;place-items:center;align-content:center;margin:0 -7px;margin:0 -2px;position:relative}
.dt svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible;filter:drop-shadow(2px 3px 2px rgba(0,0,0,.45));z-index:0}.dt b,.dt i{position:relative;z-index:1}
.dt b{font-family:"Bricolage Grotesque";font-weight:800;line-height:1;letter-spacing:-.02em;color:#fff;-webkit-text-stroke:5px #16181d;paint-order:stroke fill;text-shadow:3px 3px 0 #16181d}.dt.dk b{color:#e8434a}.dt.bub b,.dt.bub i{transform:translateY(-9%)}.dt i{color:#fff;-webkit-text-stroke:2.5px #16181d;paint-order:stroke fill;font:800 10px Inter;letter-spacing:.05em;font-style:normal;letter-spacing:.08em;text-transform:uppercase;margin-top:2px}
.tm{display:flex;flex-direction:column;align-items:center}.tm b{font:800 30px/1 "Bricolage Grotesque";letter-spacing:-.02em}
.tm i{font:700 10px Inter;font-style:normal;letter-spacing:.1em;text-transform:uppercase;margin-top:5px}
.tm.neg b{color:#f87171}.op{font:800 26px/1.1 "Bricolage Grotesque";color:var(--ac)}
.tm.tot b{background:#ffcf4a;color:#16181d;padding:2px 10px 4px;border:2.5px solid #16181d;box-shadow:4px 4px 0 0 #16181d;margin-top:-4px}
.bar{margin:0 0 14px}.bt{display:flex;height:44px;border:2.5px solid #16181d;box-shadow:4px 4px 0 0 #16181d;border-radius:4px;overflow:hidden}
.sg{display:flex;flex-direction:column;justify-content:center;padding:0 8px;min-width:0;color:#fff;text-shadow:0 1px 2px rgba(0,0,0,.6);border-right:2px solid #16181d}
.sg:last-child{border-right:0}.sg b{font:800 11px Inter;letter-spacing:.06em;white-space:nowrap;overflow:hidden}.sg i{font:800 16px "Bricolage Grotesque";font-style:normal}
.bneg{margin-top:10px;font:800 16px "Bricolage Grotesque";color:#f87171}.bneg span{font:700 11px Inter;letter-spacing:.08em;text-transform:uppercase;color:var(--text);margin-left:6px}
.ttl.tb .blb{padding:16px 30px 16px!important}.ttl.tb .w{display:flex;align-items:center;gap:8px;transform:translateY(9px)}.ttl.tb b.huge{font-size:64px;line-height:.5;display:block;margin:0 0 0 -8px;transform:translateY(-6px);-webkit-text-stroke:5px #16181d;paint-order:stroke fill;text-shadow:4px 4px 0 #16181d}.ttl.tb{margin-top:10px!important}

.h2h{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:14px;margin:24px 0 14px;padding:18px 20px;background:var(--bg);border-radius:20px}
.side{display:flex;align-items:center;gap:14px}.side.r{justify-content:flex-end;text-align:right}
.side .v{font:800 34px/1 "Bricolage Grotesque";letter-spacing:-.02em}.side .l{font:600 12px/1.35 Inter;margin-top:4px}
.sk.md{width:64px;height:64px;box-shadow:0 0 0 3px var(--bg),0 0 0 5px var(--ac)}
.sk.md img{width:76px;filter:drop-shadow(2px 0 0 #fff) drop-shadow(-2px 0 0 #fff) drop-shadow(0 -2px 0 #fff);
  -webkit-mask:radial-gradient(circle 32px at 50% calc(100% - 32px),#000 99%,transparent 100%) bottom/100% 100% no-repeat,linear-gradient(#000,#000) top/100% 50% no-repeat}
.mid{display:flex;flex-direction:column;align-items:center;gap:6px}
.wk{font:800 13px "Bricolage Grotesque";background:var(--line);padding:4px 10px;border-radius:999px}
.res{font:700 12px Inter;background:#f87171;color:#0d1117;padding:4px 10px;border-radius:999px;white-space:nowrap}

.card{background:var(--card)!important;box-shadow:7px 7px 0 0 color-mix(in srgb,var(--tc) 80%,#000)}
.card:before{right:-40px!important;top:-40px!important;width:420px!important;height:360px!important;border-radius:0!important;opacity:1!important;
  background:radial-gradient(circle,color-mix(in srgb,var(--tc) 85%,#fff) 2.2px,transparent 2.6px) 0 0/11px 11px!important;
  -webkit-mask:radial-gradient(ellipse at 100% 0,#000 0,rgba(0,0,0,.55) 35%,transparent 70%)}
.own,.own.s{position:relative;display:inline-flex;align-items:center;gap:8px!important;margin-top:12px;padding:0!important;background:none!important;color:var(--text)!important;
  border-radius:0!important;box-shadow:none!important;font:700 15px Inter!important}
.own.s{margin-top:4px;font-size:13px!important}
.own img,.own i{width:28px!important;height:28px!important;border-radius:4px!important;border:2px solid #16181d;box-shadow:3px 3px 0 0 var(--tc)!important}
.own.s img,.own.s i{width:22px!important;height:22px!important;box-shadow:2px 2px 0 0 var(--line)!important}
.big{display:flex;flex-direction:column;align-items:flex-end}
.big b{text-shadow:4px 4px 0 color-mix(in srgb,var(--tc) 85%,#000)}
.note{display:flex!important;align-items:flex-end;gap:4px;margin-top:6px!important;background:none!important;padding:0!important;color:var(--text)!important;
  font:700 12px Inter!important;letter-spacing:.08em!important;text-transform:uppercase!important}
.note svg{width:30px;height:22px;transform:translateY(-8px)}
.bn{width:64px;height:44px;flex:none}
.wk{font:800 18px "Bricolage Grotesque"!important;background:#ffcf4a!important;color:#16181d!important;-webkit-mask:none!important;border-radius:0!important;
  padding:4px 12px 5px!important;border:2.5px solid #16181d;box-shadow:4px 4px 0 0 #16181d;text-transform:uppercase;letter-spacing:.02em}
.res{position:relative;display:flex;flex-direction:column;align-items:center;background:none!important;-webkit-mask:none!important;padding:8px 0 0!important;color:var(--text)!important}
.res i{font:700 11px Inter;font-style:normal;letter-spacing:.1em;text-transform:uppercase;margin-bottom:2px}
.res b{position:relative;font:800 38px/1 "Bricolage Grotesque";color:#ff4d4d;-webkit-text-stroke:6px #16181d;paint-order:stroke fill;text-shadow:4px 4px 0 #16181d;letter-spacing:-.02em}

.mid{position:relative;z-index:0}

.ttl{position:relative;display:inline-flex;align-items:center;margin:0 0 20px}
.sbst{width:72px;height:72px;flex:none;position:absolute;left:14px;top:50%;transform:translateY(-50%);z-index:2;filter:drop-shadow(0 4px 5px rgba(0,0,0,.45))}
.blb{position:relative;display:inline-grid;place-items:center;margin-left:0;padding:18px 26px 20px 97px}
.blb svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible;filter:drop-shadow(0 5px 6px rgba(0,0,0,.45))}
.blb svg.sbst{inset:auto!important;left:8px!important;top:50%!important;width:86px!important;height:86px!important;transform:translateY(-50%)}
.blb .w{position:relative;white-space:nowrap;color:#fff;line-height:1;word-spacing:-.02em}
.blb b{font:400 24px "Permanent Marker";font-weight:400}.blb i{font:400 18px "Caveat Brush";font-style:normal;margin:0}

.bchd{position:relative;display:grid;place-items:center;flex:none}
.bchd .sk{filter:grayscale(1) contrast(1.15) brightness(.95)}
.bchd .sk:after{content:"";position:absolute;inset:0;border-radius:50%;
  background:radial-gradient(circle,transparent 45%,rgba(0,0,0,.55) 100%),
  url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80'%3E%3Cfilter id='n'%3E%3CfeTurbulence baseFrequency='1.2' numOctaves='2'/%3E%3CfeColorMatrix values='0 0 0 0 .5 0 0 0 0 .5 0 0 0 0 .5 0 0 0 .35 0'/%3E%3C/filter%3E%3Crect width='80' height='80' filter='url(%23n)'/%3E%3C/svg%3E")}
.bchd b{position:absolute;left:50%;top:54%;transform:translate(-50%,-50%);z-index:3;white-space:nowrap;
  font:800 15px "Bricolage Grotesque";letter-spacing:-.01em;color:#d8262b;-webkit-text-stroke:2px #111;paint-order:stroke fill;text-shadow:0 2px 3px rgba(0,0,0,.5)}
</style>''')
ink = '#0d1117' if lum(kb['accent']) > 150 else '#f2f4f7'
title = ('<div class="ttl tb"><span class="blb"><svg viewBox="0 0 300 70" preserveAspectRatio="none"><path d="M14 18 C30 0 90 6 150 4 C210 2 270 -2 290 16 C304 30 300 50 286 62 C260 74 200 66 150 68 C96 70 36 76 14 62 C-2 50 0 30 14 18Z" fill="var(--tc)" stroke="#fff" stroke-width="6"/></svg>'
         '<span class="w"><b class="huge">BIGGEST</b> <b>GAME</b></span></span></div>')
html = (f'<title>sup biggest</title>{css}<div class="card">{title}'
        f'<div class="win"><span class="sk"><img src="{hs(bid)}"></span><div><div class="fn">{fn}</div><div class="ln">{ln}</div>{own(w["team"])}</div>'
        f'<div class="big"><b>{w["pts"]:.1f}</b><span class="note">fantasy points</span></div></div>{band}{runners}</div>')
open(f'{S}/m_sup_biggest.html', 'w').write(html)
