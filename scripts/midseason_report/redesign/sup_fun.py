# sup_fun.py S KIND -> m_sup_{KIND}.html : Just for fun (KIND=fun) / Best pickup (KIND=pick), in the superlative look
# Just for fun: the team's adds who never started for it, sitting on a cartoon bench (tag = the week he was added).
# Best pickup: his running total over replacement as a stock chart, week by week from the add (dashed line = replacement).
import json, os, sys
def tfs(n):  # a long single word (SilverSephiroth) shrinks to fit beside the big numbers
    L = max(len(x) for x in str(n).split() or ['']); return '' if L <= 9 else f' style="font-size:{max(24, min(40, round(230 / (0.52 * L))))}px"'
S = sys.argv[1]; KIND = sys.argv[2] if len(sys.argv) > 2 else 'fun'
HERE = os.path.dirname(os.path.abspath(__file__)); W2 = f'{S}/work3'
r = json.load(open(f'{W2}/report.json')); T = r['teams']; BY = r['byname']

# a team with no uploaded picture: its glyph on its color, like the site's TeamIcon (2026-11-21: plain color squares
# read as nothing)
def gli(tid, cls=''):
    t = T.get(tid, {}); c = t.get('color') or '#30363d'
    g = r.get('glyphs', {}).get(t.get('glyph')) or r.get('glyphs', {}).get('basketball', '')
    h = c.lstrip('#'); L = .2126 * int(h[0:2], 16) + .7152 * int(h[2:4], 16) + .0722 * int(h[4:6], 16)
    ink = '#0d1117' if L > 150 else '#f2f4f7'; ca = f' class="{cls}"' if cls else ''
    return (f'<i{ca} style="background:{c};display:inline-flex;align-items:center;justify-content:center">'
            f'<svg viewBox="0 0 24 24" style="width:76%;height:76%"><path d="{g}" fill="none" stroke="{ink}" stroke-width="2.2" '
            f'stroke-linecap="round" stroke-linejoin="round"/></svg></i>')
kit = json.load(open(f'{HERE}/kit/kit.json'))
P = {p['id']: p for p in json.load(open(f'{W2}/players_scenario_live.json'))}
def hx(c): c = c.lstrip('#'); return [int(c[i:i+2], 16) for i in (0, 2, 4)]
def mix(a, b, t): return '#' + ''.join(f'{round(x*(1-t)+y*t):02x}' for x, y in zip(hx(a), hx(b)))
def lum(c): a, b, d = hx(c); return .2126*a + .7152*b + .0722*d
def lift(c): return c if lum(c) >= 45 else mix(c, '#ffffff', .2)
AL = {'GS': 'GSW', 'NY': 'NYK', 'SA': 'SAS', 'NO': 'NOP', 'PHO': 'PHX', 'UTAH': 'UTA', 'WSH': 'WAS', 'BRK': 'BKN'}
def kof(pid):
    ab = P.get(pid, {}).get('nba_team') or P.get(pid, {}).get('team'); return kit.get(AL.get(ab, ab)) or kit['SAS']
kpanel = lambda pid: lift(kof(pid)['field'])
hs = lambda pid: f'https://cdn.nba.com/headshots/nba/latest/1040x760/{pid}.png'
tcol = lambda tid: lift(T.get(tid, {}).get('color') or '#52637b')
def tpic(tid, cls):
    lg = r['tlogo'].get(tid)
    g = r['glyphs'].get(T.get(tid, {}).get('glyph')) or r['glyphs'].get('basketball', '')
    inner = f'<img src="{lg}">' if lg else f'<svg class="gl" viewBox="0 0 24 24"><path d="{g}" fill="none" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    return f'<span class="{cls}" style="--tc:{tcol(tid)}">{inner}</span>'
def own(tid):
    t = T.get(tid)
    if not t: return '<span class="own">Free agent</span>'
    lg = r['tlogo'].get(tid); ic = f'<img src="{lg}">' if lg else gli(tid)
    return f'<span class="own">{ic}{t["name"]}</span>'
def face(pid, cls='fc'):
    if pid in kit:
        import base64
        lg = base64.b64encode(open(f'{HERE}/kit/{kit[pid]["logo"]}', 'rb').read()).decode()
        return f'<span class="{cls}" style="--tc:{lift(kit[pid]["field"])}"><img class="lg" src="data:image/svg+xml;base64,{lg}"></span>'
    return f'<span class="{cls}" style="--tc:{kpanel(pid)}"><img src="{hs(pid)}"></span>'
def last(n):
    parts = n.split(' '); return parts[-2] if parts[-1] in ('Jr.', 'Sr.', 'II', 'III', 'IV') and len(parts) > 2 else parts[-1]
sg = lambda v: ('+' if v >= 0 else '−') + f'{abs(v):.1f}'
BLOB = '<svg viewBox="0 0 300 70" preserveAspectRatio="none"><path d="M14 18 C30 0 90 6 150 4 C210 2 270 -2 290 16 C304 30 300 50 286 62 C260 74 200 66 150 68 C96 70 36 76 14 62 C-2 50 0 30 14 18Z" fill="var(--tc)" stroke="#fff" stroke-width="6"/></svg>'

if KIND == 'fun':
    lst = r.get('forfun') or []
    top = lst[:3]; w = top[0]; tid = w['id']; TC = tcol(tid)
    # tag = how many weekly locks he sat on the bench (some sat since the draft, some for weeks), longest first
    ps = sorted(w['players'], key=lambda p: -p.get('bw', 1))[:7]
    seats = ''.join(f'<div class="seat">{face(p["id"])}<span class="tag">{p.get("bw", 1)} wk{"s" if p.get("bw", 1) != 1 else ""}</span><span class="pn">{last(p["name"])}</span></div>' for p in ps)
    band = (f'<div class="wk4 benchb"><div class="seats">{seats}</div>'
            '<svg class="bench" viewBox="0 0 588 70" preserveAspectRatio="none">'
            '<rect x="10" y="40" width="20" height="28" fill="#8a5a2b" stroke="#16181d" stroke-width="2.5"/><rect x="558" y="40" width="20" height="28" fill="#8a5a2b" stroke="#16181d" stroke-width="2.5"/>'
            '<rect x="2" y="8" width="584" height="16" rx="3" fill="#c98a4b" stroke="#16181d" stroke-width="2.5"/>'
            '<rect x="2" y="26" width="584" height="16" rx="3" fill="#b77a3f" stroke="#16181d" stroke-width="2.5"/>'
            '<path d="M40 16 H120 M200 14 H260 M330 17 H420 M470 15 H540 M70 34 H150 M250 33 H330 M400 35 H500" stroke="#8a5a2b" stroke-width="1.5"/></svg></div>')
    runners = ''.join(
        f'<div class="ru"><span class="rk">{x.get("_rk", i)}</span>{tpic(x["id"], "tsk sm")}'
        f'<span class="rn"><b>{T.get(x["id"], {}).get("name", x["id"])}</b></span><span class="rv">{x["n"]}</span></div>'
        for i, x in ((2, top[1] if len(top) > 1 else None), (3, top[2] if len(top) > 2 else None)) if x)
    ic = ('<svg class="ic" viewBox="0 0 36 30"><rect x="3" y="10" width="30" height="6" rx="2" fill="#ffd23f" stroke="#16181d" stroke-width="2.2"/>'
          '<rect x="3" y="17" width="30" height="6" rx="2" fill="#ffd23f" stroke="#16181d" stroke-width="2.2"/><path d="M7 23 V29 M29 23 V29" stroke="#16181d" stroke-width="3"/></svg>')
    title = f'<div class="ttl"><span class="blb">{BLOB}<span class="w">{ic}<i>JUST FOR</i> <b>FUN</b></span></span></div>'
    hero = f'{tpic(tid, "tsk")}<div><div class="tn"{tfs(T.get(tid, {}).get("name", tid))}>{T.get(tid, {}).get("name", tid)}</div></div>'
    big = f'<div class="big"><b>{w["n"]}</b><span class="note">adds who never started</span></div>'
else:
    lst = r.get('pick2') or []
    top = lst[:3]; w = top[0]; pid = BY.get(w['name']); TC = kpanel(pid) if pid else '#52637b'
    tot = w.get('tot', round(sum(w['vor'].values()), 1))
    wks = sorted(w['vor'], key=int)
    # the stock chart: running total over replacement, a point per week started, starting at 0 when he was added
    CW, CH, PADX, PADT, PADB = 588, 190, 46, 34, 34
    run, pts = 0.0, [0.0]
    for k in wks: run += w['vor'][k]; pts.append(run)
    lo, hi = min(pts + [0]), max(pts + [0]); span = (hi - lo) or 1
    X = lambda i: PADX + i * (CW - 2 * PADX) / max(1, len(pts) - 1)
    Y = lambda v: PADT + (hi - v) / span * (CH - PADT - PADB)
    path = ' '.join(f'{X(i):.1f},{Y(v):.1f}' for i, v in enumerate(pts))
    area = f'{X(0):.1f},{Y(0):.1f} ' + path + f' {X(len(pts) - 1):.1f},{Y(0):.1f}'
    marks = ''
    for i, v in enumerate(pts):
        lab = 'Added' if i == 0 else f'Wk {wks[i - 1]}'
        marks += f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="6.5" class="pt"/><text x="{X(i):.1f}" y="{CH - 8}" class="wl">{lab}</text>'
        if i:
            d = w['vor'][wks[i - 1]]
            marks += f'<text x="{X(i):.1f}" y="{Y(v) - 14:.1f}" class="dv {"up" if d >= 0 else "dn"}">{sg(d)}</text>'
    chart = (f'<svg class="stk" viewBox="0 0 {CW} {CH}"><line x1="{PADX - 20}" x2="{CW - PADX + 20}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" class="zero"/>'
             f'<text x="{CW - PADX + 20}" y="{Y(0) + 16:.1f}" class="zl">replacement</text>'
             f'<polygon points="{area}" class="ar"/><polyline points="{path}" class="ln0"/><polyline points="{path}" class="ln"/>{marks}</svg>')
    band = f'<div class="wk4">{chart}</div>'
    runners = ''.join(
        f'<div class="ru"><span class="rk">{x.get("_rk", i)}</span>{face(BY.get(x["name"], ""), "fc sm") if BY.get(x["name"]) else "<span></span>"}'
        f'<span class="rn"><b>{x["name"]}</b>{own(x["team"])}</span><span class="rv">{sg(x.get("tot", 0))}</span></div>'
        for i, x in ((2, top[1] if len(top) > 1 else None), (3, top[2] if len(top) > 2 else None)) if x)
    ic = ('<svg class="ic" viewBox="0 0 36 30"><path d="M3 25 L13 15 L19 20 L31 6" fill="none" stroke="#16181d" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>'
          '<path d="M3 25 L13 15 L19 20 L31 6" fill="none" stroke="#ffd23f" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
          '<path d="M23 5 L33 4 L32 14 Z" fill="#ffd23f" stroke="#16181d" stroke-width="2" stroke-linejoin="round"/></svg>')
    title = f'<div class="ttl"><span class="blb">{BLOB}<span class="w">{ic}<b>BEST PICKUP</b></span></span></div>'
    fn, _, ln = w['name'].rpartition(' ')
    hero = f'{face(pid, "tsk hd") if pid else ""}<div><div class="fn">{fn}</div><div class="ln">{ln}</div>{own(w["team"])}</div>'
    big = (f'<div class="big"><b>{sg(tot)}</b><span class="note">over replacement</span>'
           f'<span class="mx">{len(wks)} wks <i>·</i> {sg(w["per"])}/wk</span></div>')

css = open(f'{HERE}/sup_base.css').read().replace('family=Bricolage', 'family=Kalam:wght@700&family=Permanent+Marker&family=Caveat+Brush&family=Bricolage', 1)
css = css.replace('--tc:', '--tc:' + TC + ';--x:', 1).replace('--ac:', '--ac:#f2f4f7;--y:', 1)
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
.tsk.hd img{position:absolute;left:50%;top:-4%;width:190%;height:auto;transform:translateX(-50%)}
.tsk.sm{width:46px;height:46px;box-shadow:0 0 0 3px var(--card),0 0 0 5px var(--tc)}
.tn{font:800 40px/1 "Bricolage Grotesque";letter-spacing:-.02em;text-wrap:balance}.win>div{min-width:0}
.own{display:inline-flex!important;align-items:center;gap:8px;margin-top:10px;padding:0!important;background:none!important;border-radius:0!important;font:700 15px Inter!important}
.own img,.own i{width:26px!important;height:26px!important;border-radius:4px!important;border:2px solid #16181d}
.win{height:168px}
.big{display:flex;flex-direction:column;align-items:flex-end}
.big b{text-shadow:4px 4px 0 color-mix(in srgb,var(--tc) 85%,#000)}
.note{display:block;margin-top:8px!important;background:none!important;padding:0!important;color:var(--text)!important;
  font:700 12px Inter!important;letter-spacing:.08em!important;text-transform:uppercase!important}
.big .mx{background:none!important;padding:0!important;border-radius:0!important;margin-top:10px;font:800 20px "Bricolage Grotesque";color:var(--text)}
.big .mx i{font-style:normal;margin:0 4px}
.wk4{margin:22px 0 12px;padding:14px 16px;background:var(--bg);border-radius:20px}
.fc{position:relative;display:block;width:74px;height:74px;border-radius:50%;background:var(--tc);overflow:hidden;box-sizing:border-box;
  border:2.5px solid #16181d;box-shadow:3px 3px 0 0 #16181d}
.fc img{position:absolute;left:50%;top:-6%;width:200%;transform:translateX(-50%)}.fc img.lg{left:14%;top:14%;width:72%;transform:none}
.fc.sm{width:46px;height:46px}
/* the bench */
.benchb{position:relative;padding:14px 16px 0}
.wk4{box-sizing:border-box;height:218px}
.seats{position:relative;z-index:1;display:flex;justify-content:center;gap:14px;height:150px;align-items:flex-end}
.seat{position:relative;display:flex;flex-direction:column;align-items:center;margin-bottom:-26px}
.seat .tag{position:absolute;bottom:-4px;right:-12px;font:800 12px "Bricolage Grotesque";background:#ffd23f;color:#16181d;border:2px solid #16181d;
  box-shadow:2px 2px 0 0 #16181d;padding:2px 6px}
.seat .pn{order:-1;font:700 12px Inter;margin-bottom:6px;white-space:nowrap}
.bench{position:absolute;left:16px;right:16px;bottom:10px;width:calc(100% - 32px);height:70px}
/* the stock chart */
.stk{display:block;width:100%;height:190px;overflow:visible}
.stk .zero{stroke:#ffd23f;stroke-width:2;stroke-dasharray:6 6}.stk .zl{fill:#ffd23f;font:800 11px Inter;letter-spacing:.06em;text-anchor:end;text-transform:uppercase}
.stk .ar{fill:color-mix(in srgb,#4ade80 22%,transparent)}
.stk .ln0{fill:none;stroke:#16181d;stroke-width:9;stroke-linejoin:round;stroke-linecap:round}
.stk .ln{fill:none;stroke:#4ade80;stroke-width:4.5;stroke-linejoin:round;stroke-linecap:round}
.stk .pt{fill:#4ade80;stroke:#16181d;stroke-width:2.5}
.stk .wl{fill:var(--text);font:700 11px Inter;letter-spacing:.08em;text-anchor:middle;text-transform:uppercase}
.stk .dv{font:800 17px "Bricolage Grotesque";text-anchor:middle;paint-order:stroke;stroke:#0e1015;stroke-width:4px}.stk .up{fill:#4ade80}.stk .dn{fill:#f87171}
.ru{grid-template-columns:28px 46px 1fr auto;height:72px;padding-top:0;padding-bottom:0;box-sizing:border-box}.ru .own{margin-top:3px;font-size:13px!important}.ru .own img,.ru .own i{width:20px!important;height:20px!important}
</style>''')
html = (f'<title>sup {KIND}</title>{css}<div class="card">{title}'
        f'<div class="win">{hero}{big}</div>{band}{runners}</div>')
open(f'{S}/m_sup_{KIND}.html', 'w').write(html)
