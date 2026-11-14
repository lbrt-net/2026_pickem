import sys, re
S = sys.argv[1]
src = open(f'{S}/m_flair2.html').read()
import json as _j
_kit = _j.load(open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), 'kit', 'kit.json'))); _pl = {p['name']: p['nba_team'] for p in _j.load(open(f'{S}/work3/players_scenario_live.json'))}
_rows = re.findall(r'<div class=fn>([^<]+)</div><div class="ln">([^<]+)</div>', src)
NBA = {f'>{fn}</div><div class="ln">{ln}<': _kit[_pl[f"{fn} {ln}"]]['field'].lower() for fn, ln in _rows if _pl.get(f"{fn} {ln}") in _kit}
# tag each row with its NBA color (--nc)
def tag(m):
    row = m.group(0)
    for fn, c in NBA.items():
        if fn in row: return row.replace('class="r', f'style="--nc:{c}" class="r', 1) if 'style=' not in row[:40] else row.replace('style="', f'style="--nc:{c};', 1)
    return row
src = re.sub(r'<div class="r[^"]*"[^>]*>.*?(?=<div class="r|<div class="ctx|</section>)', tag, src, flags=re.S)
FL = '''
:root{--ink:#0b0c0f}
.r.win:before{display:none!important}
/* winner: solid NBA-color slab behind the headshot, slanted right edge, fades to ink */
.r.win{background:linear-gradient(100deg,var(--nc) 0 236px,color-mix(in srgb,var(--nc) 55%,var(--ink)) 236px 252px,var(--ink) 252px)!important}
.r.win .ph{filter:saturate(1.1) contrast(1.05)}
.r.win:after{background:#fff!important;height:4px!important;left:0!important;width:232px!important}
.r.win .rk{color:#fff;opacity:.95}
.r.win .v span{border-top-color:var(--nc)!important;border-top-width:3px!important}
/* band: plain ink, no tint */
.ctx{background:#14161b!important;border-bottom:0!important}
.ctx:before{background:var(--nc,#552583)!important}
/* runners-up: headshot on its own NBA-color slab with a slant */
.r:not(.win){background:var(--ink)!important}
.r:not(.win):before{display:none}
.r:not(.win) .ph{background:linear-gradient(100deg,var(--nc) 0 82%,transparent 82%)!important;filter:none}
.r:not(.win) .rk{background:#fff;color:var(--ink);font-weight:800}
'''
src = src.replace('class="ctx" style="--tc:', 'class="ctx" style="--nc:' + list(NBA.values())[0] + ';--tc:', 1)
open(f'{S}/m_flair3.html','w').write(src.replace('</style>', FL + '</style>', 1))
