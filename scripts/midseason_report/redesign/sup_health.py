# sup_health.py S KIND -> m_sup_{KIND}.html : Healthiest roster (KIND=healthy) / Most games missed (KIND=hurt), comic look
# Ranked by games missed (ties: less / more MAX value lost). Shows games missed and the MAX value lost to them
# (health_value.py), for the team and for each player who missed games, as tiles.
import base64, json, math, os, sys
def tfs(n):  # a long single word (SilverSephiroth) shrinks to fit beside the big numbers
    L = max(len(x) for x in str(n).split() or ['']); return '' if L <= 9 else f' style="font-size:{max(24, min(40, round(230 / (0.52 * L))))}px"'
S = sys.argv[1]; KIND = sys.argv[2] if len(sys.argv) > 2 else 'hurt'
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
def tpic(tid, cls):
    lg = r['tlogo'].get(tid)
    g = r['glyphs'].get(T.get(tid, {}).get('glyph')) or r['glyphs'].get('basketball', '')
    inner = f'<img src="{lg}">' if lg else f'<svg class="gl" viewBox="0 0 24 24"><path d="{g}" fill="none" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    return f'<span class="{cls}" style="--tc:{tcol(tid)}">{inner}</span>'
neg = lambda v: f'−{v:.1f}' if v > 0 else '0'

lst = r['health_least'] if KIND == 'healthy' else r['health_most']
top = lst[:3]; w = top[0]; tid = w['id']; tn = T.get(tid, {}).get('name', tid)
# the band: a heart monitor per player — one pulse a week (height = his weekly MAX); a week he missed any game
# pulses red. The injured come first (most games missed); the healthiest
# team's monitors are filled out with its other regulars, beating, so both cards hold the same five.
info = {p['id']: p for p in w['players']}
seqs = [q for q in w.get('seq', []) if q['seq'] and info.get(q['id'], {}).get('missed', 0) > 0]  # only players who missed games
seqs.sort(key=lambda q: (-info.get(q['id'], {}).get('missed', 0), -info.get(q['id'], {}).get('lost', 0), -sum((x['max'] or 0) for x in q['seq'])))
MW, MH, BASE = 400, 46, 33
def ekg(seq):  # one pulse a week, height = his weekly MAX; a week he missed any game pulses red (a fully missed week is a red flatline)
    u = MW / max(1, len(seq)); segs = ''
    for i, wk_ in enumerate(seq):
        x0 = i * u; hurt = wk_['k'] < wk_['n']
        if wk_['max'] is None:
            pts = [f'{x0:.1f},{BASE}', f'{x0 + u:.1f},{BASE}']
        else:
            h = 6 + min(wk_['max'], 80) / 80 * (BASE - 6); q = u / 8
            pts = [f'{x0:.1f},{BASE}', f'{x0 + 2*q:.1f},{BASE}', f'{x0 + 3*q:.1f},{BASE + 4}', f'{x0 + 4*q:.1f},{BASE - h:.1f}',
                   f'{x0 + 5*q:.1f},{BASE + 7}', f'{x0 + 6*q:.1f},{BASE}', f'{x0 + u:.1f},{BASE}']
        segs += f'<polyline class="{"hu" if hurt else "ok"}" points="{" ".join(pts)}"/>'
    return f'<svg class="ek" viewBox="0 0 {MW} {MH}" preserveAspectRatio="none">{segs}</svg>'
def last(n):
    parts = n.split(' '); return parts[-2] if parts[-1] in ('Jr.', 'Sr.', 'II', 'III', 'IV') and len(parts) > 2 else parts[-1]
mons = ''
for q in seqs[:3]:
    p = info.get(q['id'], {'missed': 0, 'lost': 0})
    side = (f'<span class="st"><b class="{"bad" if p["missed"] else "ok"}">{p["missed"]} G</b><em>{neg(p["lost"]) if p["missed"] else ""}</em></span>')
    mons += (f'<div class="mon"><span class="fc" style="--tc:{kpanel(q["id"])}"><img src="{hs(q["id"])}"></span>'
             f'<div class="scr"><span class="nm">{last(q["name"])}</span>{ekg(q["seq"])}</div>{side}</div>')
# everyone else who missed games: a two-column list, games and MAX lost
rest = [info[q['id']] for q in seqs[3:]]
lst_ = ''.join(f'<div class="lr"><b>{last(p["name"])}</b><span>{p["missed"]} G</span><em>{neg(p["lost"])}</em></div>' for p in rest)
# both cards in the pair are as tall as the busiest shown team needs (build_cards.py: health_band = [monitors, list rows])
NM, NL = r.get('health_band', [3, 0])
hgt = NM * 68 + (math.ceil(NL / 2) * 30 + 12 if NL else 0) - 10
band = (f'<div class="wk4 mons" style="height:{hgt}px">{mons or "<div class=none>Nobody missed a game</div>"}'
        f'{f"<div class=lst>{lst_}</div>" if lst_ else ""}</div>')
runners = ''.join(
    f'<div class="ru"><span class="rk">{x.get("_rk", i)}</span>{tpic(x["id"], "tsk sm")}'
    f'<span class="rn"><b>{T.get(x["id"], {}).get("name", x["id"])}</b></span><span class="rv">{x["missed"]}<em>{neg(x["lost"])}</em></span></div>'
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
.tn{font:800 40px/1 "Bricolage Grotesque";letter-spacing:-.02em;text-wrap:balance}.win>div{min-width:0}
.big{display:flex;flex-direction:column;align-items:flex-end}
.big b{text-shadow:4px 4px 0 color-mix(in srgb,var(--tc) 85%,#000)}
.note{display:block;margin-top:8px!important;background:none!important;padding:0!important;color:var(--text)!important;
  font:700 12px Inter!important;letter-spacing:.08em!important;text-transform:uppercase!important}
.big .mx{background:none!important;padding:0!important;border-radius:0!important;margin-top:12px;font:800 28px/1 "Bricolage Grotesque";color:#f87171;letter-spacing:-.01em}
.wk4{margin:22px 0 12px;padding:16px 18px 6px;background:var(--bg);border-radius:20px}
.fc{position:relative;display:block;width:72px;height:72px;border-radius:50%;background:var(--tc);overflow:hidden;box-sizing:border-box;
  border:2.5px solid #16181d;box-shadow:3px 3px 0 0 #16181d}
.fc img{position:absolute;left:50%;top:-6%;width:200%;transform:translateX(-50%)}
.mons{display:flex;flex-direction:column;gap:10px;padding:14px 16px}
.mons{box-sizing:content-box}.mons .none{margin:auto;font:400 26px "Permanent Marker"}
.lst{display:grid;grid-template-columns:1fr 1fr;gap:0 26px;margin-top:2px;padding-top:8px;border-top:1px dashed var(--line)}
.lr{display:grid;grid-template-columns:minmax(0,1fr) auto 56px;gap:10px;align-items:baseline;height:30px;line-height:30px}
.lr b{font:700 14px Inter;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.lr span{font:800 16px "Bricolage Grotesque";color:#ff6b6b}
.lr em{font:800 15px "Bricolage Grotesque";font-style:normal;color:#f87171;text-align:right}
.mon{display:grid;grid-template-columns:58px minmax(0,1fr) 78px;gap:12px;align-items:center;height:58px}
.mon .fc{width:58px;height:58px}
.scr{position:relative;height:54px;border-radius:8px;border:2.5px solid #16181d;box-shadow:3px 3px 0 0 #16181d;overflow:hidden;
  background:linear-gradient(rgba(57,255,136,.07) 1px,transparent 1px) 0 0/12px 12px,linear-gradient(90deg,rgba(57,255,136,.07) 1px,transparent 1px) 0 0/12px 12px,#07150d}
.scr .nm{position:absolute;left:8px;top:4px;font:800 10px Inter;letter-spacing:.08em;text-transform:uppercase;color:#7dffb2}
.ek{position:absolute;left:0;right:0;bottom:2px;width:100%;height:46px;overflow:visible}
.ek polyline{fill:none;stroke:#39ff88;stroke-width:2;stroke-linejoin:round;filter:drop-shadow(0 0 3px rgba(57,255,136,.8))}
.ek polyline.hu{stroke:#ff4d4d;stroke-width:2.5;filter:drop-shadow(0 0 4px rgba(255,77,77,.9))}
.st{display:flex;flex-direction:column;align-items:flex-end;line-height:1.1}
.st b{font:800 24px "Bricolage Grotesque"}.st b.bad{color:#ff6b6b}.st b.ok{color:#7dffb2}
.st em{font:800 15px "Bricolage Grotesque";font-style:normal;color:#f87171}
.none{grid-column:1/-1;align-self:center;text-align:center;font:400 26px "Permanent Marker";padding-top:60px}
.ru{grid-template-columns:28px 46px 1fr auto}.rv em{font-style:normal;font-size:18px;color:#f87171;margin-left:12px}
</style>''')
BLOB = '<svg viewBox="0 0 300 70" preserveAspectRatio="none"><path d="M14 18 C30 0 90 6 150 4 C210 2 270 -2 290 16 C304 30 300 50 286 62 C260 74 200 66 150 68 C96 70 36 76 14 62 C-2 50 0 30 14 18Z" fill="var(--tc)" stroke="#fff" stroke-width="6"/></svg>'
if KIND == 'healthy':  # a heart
    ic = '<svg class="ic" viewBox="0 0 36 30"><path d="M18 27 C6 19 3 13 3 9 a7 7 0 0 1 15 -2 a7 7 0 0 1 15 2 c0 4 -3 10 -15 18Z" fill="#ffd23f" stroke="#16181d" stroke-width="2.5" stroke-linejoin="round"/></svg>'
    title = f'<div class="ttl"><span class="blb">{BLOB}<span class="w">{ic}<b>HEALTHIEST ROSTER</b></span></span></div>'
else:  # a bandage
    ic = ('<svg class="ic" viewBox="0 0 36 30"><g transform="rotate(-30 18 15)"><rect x="2" y="9" width="32" height="12" rx="6" fill="#ffd23f" stroke="#16181d" stroke-width="2.5"/>'
          '<rect x="12" y="9" width="12" height="12" fill="#f6e3a8" stroke="#16181d" stroke-width="2"/><circle cx="16" cy="13" r="1" fill="#16181d"/><circle cx="20" cy="17" r="1" fill="#16181d"/></g></svg>')
    title = f'<div class="ttl"><span class="blb">{BLOB}<span class="w">{ic}<i>MOST</i> <b>GAMES MISSED</b></span></span></div>'
big = f'<div class="big"><b>{w["missed"]}</b><span class="note">games missed</span><span class="mx">{neg(w["lost"])}</span><span class="note">max lost</span></div>'
html = (f'<title>sup {KIND}</title>{css}<div class="card">{title}'
        f'<div class="win">{tpic(tid, "tsk")}<div><div class="tn"{tfs(tn)}>{tn}</div></div>{big}</div>{band}{runners}</div>')
open(f'{S}/m_sup_{KIND}.html', 'w').write(html)
