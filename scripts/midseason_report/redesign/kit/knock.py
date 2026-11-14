"""One-color knockout marks: dark/saturated logo colors = solid ink, light colors (white, gold, cream) = negative space.
Done with an SVG mask so later light shapes really cut through earlier dark ones."""
import re, json
kit = json.load(open('kit.json'))
def hx(c): c=c.lstrip('#'); c=''.join(x*2 for x in c) if len(c)==3 else c; return [int(c[i:i+2],16) for i in (0,2,4)]
def mix(a,b,t): return '#'+''.join(f'{round(x*(1-t)+y*t):02x}' for x,y in zip(hx(a),hx(b)))
def lum(c): r,g,b=hx(c); return .2126*r+.7152*g+.0722*b
NAMED = {"white": "#ffffff", "black": "#000000"}
def auto_cut(svg):
    cs = sorted({lum(NAMED.get(c.lower(), c)) for c in re.findall(r'(?:fill|stroke)\s*[:=]\s*"?(#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b|white\b|black\b)', svg)})
    if len(cs) < 2: return 140
    gaps = [(cs[i+1]-cs[i], (cs[i]+cs[i+1])/2) for i in range(len(cs)-1)]
    return max(gaps)[1]
def knock(svg, ink, cut=None, inv=False):
    svg = re.sub(r'<\?xml.*?\?>|<!--.*?-->', '', svg, flags=re.S).strip()
    cut = auto_cut(svg) if cut is None else cut
    head = re.match(r'<svg\b[^>]*>', svg).group(0); body = svg[len(head):svg.rindex('</svg>')]
    def m(mo):
        c = NAMED.get(mo.group(2).lower(), mo.group(2)); return mo.group(1) + (('#000000' if lum(c) > cut else '#ffffff') if not inv else ('#ffffff' if lum(c) > cut else '#000000'))
    body = re.sub(r'((?:fill|stroke)\s*[:=]\s*"?)(#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b|white\b|black\b)', m, body)
    vb = re.search(r'viewBox="([^"]+)"', head).group(1)
    head2 = re.sub(r'\sfill="[^"]*"', '', head)
    return (f'{head2}<defs><mask id="k" maskUnits="userSpaceOnUse" x="-10%" y="-10%" width="120%" height="120%">'
            f'<g fill="#ffffff">{body}</g></mask></defs>'
            f'<rect x="-50%" y="-50%" width="200%" height="200%" fill="{ink}" mask="url(#k)"/></svg>')
MODE = {"MEM": dict(cut=None), **{t: dict(cut=140, inv=True) for t in "ATL CHI CLE HOU MIA POR PHX LAL MIL CHA LAC SAC DAL".split()}}  # picked by eye from both sheets
import sys
INV = len(sys.argv) > 1 and sys.argv[1] == "inv"
for t, k in kit.items():
    opt = dict(cut=140, inv=True) if INV else MODE.get(t, dict(cut=140))
    name = f'logo/{t}_knock{"_inv" if INV else ""}.svg'
    open(name, 'w').write(knock(open(f'logo/{t}.svg').read(), mix(k["field"], "#000000", .5), **opt))
    if not INV: k["knock"] = name
json.dump(kit, open('kit.json', 'w'), indent=1)
