"""stickers.py: one comic sticker per scoring category (shape + colors fixed per category)."""
import math, random
def cloud(cx, cy, rx, ry, n, bump, seed):
    R = random.Random(seed); pts = []
    for k in range(n + 1):
        a = 2 * math.pi * k / n; j = 1 + R.uniform(-.06, .06)
        pts.append((cx + rx * j * math.cos(a), cy + ry * j * math.sin(a)))
    d = f'M{pts[0][0]:.1f} {pts[0][1]:.1f} '
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        r = math.hypot(x2 - x1, y2 - y1) / 2 * bump; d += f'A{r:.1f} {r:.1f} 0 0 1 {x2:.1f} {y2:.1f} '
    return d + 'Z'
def burst(cx, cy, ro, ri, n, seed, rot=-.3):
    R = random.Random(seed + 7)
    return 'M' + ' L'.join(f'{cx + (ro * R.uniform(.88, 1.06) if k % 2 == 0 else ri) * math.cos(math.pi * k / n + rot):.1f} {cy + (ro * R.uniform(.88, 1.06) if k % 2 == 0 else ri) * math.sin(math.pi * k / n + rot):.1f}' for k in range(2 * n)) + 'Z'
BUB = 'M14 14 Q14 4 28 4 L100 4 Q114 4 114 16 L114 66 Q114 78 100 78 L56 78 L34 98 L40 78 L28 78 Q14 78 14 66Z'
RED, YEL, TEAL, CREAM, NAVY, PURP, MINT, ORNG = '#e8434a', '#ffd23f', '#2f9e8f', '#f7efe0', '#3a4f8f', '#7b4fb0', '#8ed6c1', '#f28c28'
# cat: (label, shape, fill, inner burst or None, text box = fraction of width usable, text y offset %)
CAT = {
    'PTS':    ('PTS',       'cloudburst', RED,  YEL,  .52, 0),
    '3PTM':   ('3PM',       'burst',      YEL,  None, .48, 0),
    'CLUTCH': ('CLUTCH',    'cloudburst', NAVY, YEL,  .52, 0),
    'OREB':   ('OFF REB',   'cloud',      TEAL, None, .56, 0),
    'DREB':   ('DEF REB',   'bubble',     TEAL, None, .72, -9),
    'AST':    ('AST',       'bubble',     PURP, None, .72, -9),
    'STL':    ('STL',       'burst',      ORNG, None, .48, 0),
    'BLK':    ('BLK',       'jag',        NAVY, None, .50, 0),
    'OTHER':  ('OTHER',     'cloud',      '#4a5160', None, .56, 0),
    'FG-':    ('MISSED FG', 'cloud',      CREAM, None, .54, 0),
    'FT-':    ('MISSED FT', 'bubble',     CREAM, None, .62, -9),
    'TO':     ('TURNOVERS', 'jag',        CREAM, None, .44, 0),
    'BLKD':   ('BLOCKED',   'burst',      CREAM, None, .42, 0),
}
def path(shape, seed):
    if shape in ('cloud', 'cloudburst'): return cloud(64, 50, 54, 40, 9, 1.25, seed)
    if shape == 'burst': return burst(64, 50, 54, 32, 11, seed)
    if shape == 'jag': return burst(64, 50, 52, 36, 8, seed, .2)
    return BUB
def sticker(cat, v, w, uid):
    lab, shape, fill, inner, box, dy = CAT[cat]
    neg = v < 0; h = round(w * .8); seed = sum(map(ord, cat))
    p = path(shape, seed); ink = '#16181d'
    num = f'{"−" if neg else ""}{abs(v):g}'; tw = w * box
    nf = min(w * .3, tw / (len(num) * .58)); lf = min(11, tw / (len(lab) * .8))
    ly = (f'<path d="{p}" fill="#fff" stroke="#fff" stroke-width="16" stroke-linejoin="round"/>'
          f'<path d="{p}" fill="none" stroke="{ink}" stroke-width="1.4" stroke-dasharray="4 3" stroke-linejoin="round" transform="translate(64 50) scale(1.12) translate(-64 -50)"/>'
          f'<path d="{p}" fill="{fill}" stroke="{ink}" stroke-width="3.5" stroke-linejoin="round"/>'
          f'<path d="{p}" fill="url(#ht{uid})"/>')
    if inner: ly += f'<path d="{burst(64, 50, 40, 22, 9, seed)}" fill="{inner}" stroke="{ink}" stroke-width="2.5" stroke-linejoin="round"/>'
    svg = (f'<svg viewBox="-12 -12 152 124"><defs><pattern id="ht{uid}" width="6" height="6" patternUnits="userSpaceOnUse">'
           f'<circle cx="3" cy="3" r="1.3" fill="rgba(0,0,0,.16)"/></pattern></defs>{ly}</svg>')
    return (f'<span class="stk{" neg" if neg else ""}" style="width:{w}px;height:{h}px">{svg}'
            f'<span class="tx" style="transform:translateY({dy}%)"><b style="font-size:{nf:.1f}px">{num}</b><i style="font-size:{lf:.1f}px">{lab}</i></span></span>')
CSS = '''
.stk{position:relative;display:inline-grid;place-items:center;flex:none}
.stk svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible;filter:drop-shadow(2px 3px 2px rgba(0,0,0,.45))}
.stk .tx{position:relative;display:flex;flex-direction:column;align-items:center;line-height:1}
.stk b{font-family:"Bricolage Grotesque";font-weight:800;letter-spacing:-.02em;color:#fff;-webkit-text-stroke:5px #16181d;paint-order:stroke fill;text-shadow:2px 2px 0 #16181d}
.stk i{font-family:Inter;font-weight:800;font-style:normal;letter-spacing:.04em;margin-top:2px;color:#fff;-webkit-text-stroke:2.5px #16181d;paint-order:stroke fill;white-space:nowrap}
.stk.neg b{color:#e8434a}
'''
