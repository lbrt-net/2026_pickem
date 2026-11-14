import sys, json, urllib.parse, os, re
S = sys.argv[1]; K = __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), 'kit')
def hx(c): c=c.lstrip('#'); return [int(c[i:i+2],16) for i in (0,2,4)]
def mix(a,b,t): return '#'+''.join(f'{round(x*(1-t)+y*t):02x}' for x,y in zip(hx(a),hx(b)))
kit = json.load(open(f'{K}/kit.json'))
def _lum(c): c=c.lstrip('#'); r,g,b=(int(c[i:i+2],16) for i in (0,2,4)); return .2126*r+.7152*g+.0722*b
for _k in kit.values():
    # panel = field, lifted when the team's main color is too dark to show a logo on a dark page (DEN, NOP, IND, WAS...)
    _k['panel'] = _k['field'] if _lum(_k['field']) >= 45 else mix(_k['field'], '#ffffff', .16)
    # accent = second color, or the next usable one when it's black/near-black (CHI, ORL, TOR, POR...)
    _k['accent'] = next((c for c in (_k['secondary'], _k['tertiary'], '#ffffff') if _lum(c) >= 60), '#ffffff')
src = open(f'{S}/m_flair4.html').read()
import re as _re
_h = open(f'{S}/m_flair4.html').read()
ROW = {c: t for c in dict.fromkeys(_re.findall(r'--nc:(#[0-9a-f]{6})', _h)) for t, k in kit.items() if k['field'].lower() == c}
enc = lambda s: "url('data:image/svg+xml," + urllib.parse.quote(s) + "')"
def sky(t, f):
    p = f'{K}/sky/{t}.svg'
    if not os.path.exists(p): return None
    s = open(p).read().replace('<path class="b"', f'<path class="b" fill="{mix(f,"#000000",.45)}"').replace('<path class="f"', f'<path class="f" fill="{mix(f,"#000000",.7)}"')
    return enc(s.replace(' fill-opacity=".55"', ''))
css = ''
for nc, t in ROW.items():
    k = kit[t]; f = k["panel"]; sel = f'[style*="--nc:{nc}"]'
    mk = enc(open(f'{K}/{k["knock"]}').read()); sk = sky(t, f)
    lay = f'{mk} 30px -150px/440px auto no-repeat,'
    lay2 = f'{mk} -40px -70px/210px auto no-repeat,'
    glow = ''
    css += (f'.r.win{sel} .slab{{background:{lay}{glow}{f}!important}}'
            f'.r:not(.win){sel} .ph{{background:{lay2}{glow}{f}!important}}')
FL = css + '''
.r.win .slab:before,.r.win .slab:after,.r.win .ech{display:none!important}
.r.win .slab{clip-path:polygon(0 0,100% 0,calc(100% - 22px) 100%,0 100%)!important;width:250px!important}
.r.win:after{display:none!important}
.r:not(.win) .ph{clip-path:polygon(0 0,100% 0,calc(100% - 10px) 100%,0 100%)!important}
'''
open(f'{S}/m_card.html','w').write(src.replace('</style>', FL + '</style>', 1))
# two-color strips: team primary + secondary (2026-11-12, "why one color")
h = open(f'{S}/m_card.html').read()
add = ''
for nc, t in ROW.items():
    k = kit[t]; sel = f'[style*="--nc:{nc}"]'
    strip = f'linear-gradient(100deg,{k["panel"]} 0 62%,transparent 62% 64%,{k["accent"]} 64%)'
    add += (f'.r.win{sel} .v span{{border-top:0!important;background:{strip} 0 0/100% 4px no-repeat;padding-top:9px!important}}'
            f'.r.win{sel}{{box-shadow:inset 0 3px 0 {k["accent"]}!important}}'
            f'.ctx[style*="--nc:{nc}"]:before{{background:linear-gradient(180deg,{k["panel"]} 0 60%,{k["accent"]} 60%)!important}}'
            f'.r:not(.win){sel} .rk{{box-shadow:inset 0 -4px 0 {k["accent"]}}}')
open(f'{S}/m_card.html','w').write(h.replace('</style>', add + '</style>', 1))
