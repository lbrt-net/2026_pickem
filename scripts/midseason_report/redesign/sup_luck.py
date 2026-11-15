# sup_luck.py S KIND -> m_sup_{KIND}.html : Unluckiest (KIND=luck) / Stuck with the draft (KIND=stuck), comic look
# Unluckiest: a scoreboard per bad-luck loss — what happened (lost by) and what a normal week said (won by), his guys
# below their usual, their guys above theirs. Stuck with the draft: a pile of cash per drafted player still rostered,
# as tall as his price (one scale for every team), his face on top.
import base64, json, os, sys
def tfs(n):  # a long single word (SilverSephiroth) shrinks to fit beside the big numbers
    L = max(len(x) for x in str(n).split() or ['']); return '' if L <= 9 else f' style="font-size:{max(24, min(40, round(230 / (0.52 * L))))}px"'
S = sys.argv[1]; KIND = sys.argv[2] if len(sys.argv) > 2 else 'luck'
HERE = os.path.dirname(os.path.abspath(__file__)); W2 = f'{S}/work3'
r = json.load(open(f'{W2}/report.json')); T = r['teams']
kit = json.load(open(f'{HERE}/kit/kit.json'))
P = {p['id']: p for p in json.load(open(f'{W2}/players_scenario_live.json'))}
def hx(c): c = c.lstrip('#'); return [int(c[i:i+2], 16) for i in (0, 2, 4)]
def mix(a, b, t): return '#' + ''.join(f'{round(x*(1-t)+y*t):02x}' for x, y in zip(hx(a), hx(b)))
def lum(c): a, b, d = hx(c); return .2126*a + .7152*b + .0722*d
def lift(c): return c if lum(c) >= 45 else mix(c, '#ffffff', .2)
AL = {'GS': 'GSW', 'NY': 'NYK', 'SA': 'SAS', 'NO': 'NOP', 'PHO': 'PHX', 'UTAH': 'UTA', 'WSH': 'WAS', 'BRK': 'BKN'}
def kof(pid):
    ab = P.get(pid, {}).get('nba_team') or P.get(pid, {}).get('team'); return kit.get(AL.get(ab, ab)) or kit['SAS']
hs = lambda pid: f'https://cdn.nba.com/headshots/nba/latest/1040x760/{pid}.png'
tcol = lambda tid: lift(T.get(tid, {}).get('color') or '#52637b')
tname = lambda tid: T.get(tid, {}).get('name', tid)
def tpic(tid, cls):
    lg = r['tlogo'].get(tid)
    g = r['glyphs'].get(T.get(tid, {}).get('glyph')) or r['glyphs'].get('basketball', '')
    inner = f'<img src="{lg}">' if lg else f'<svg class="gl" viewBox="0 0 24 24"><path d="{g}" fill="none" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    return f'<span class="{cls}" style="--tc:{tcol(tid)}">{inner}</span>'
def face(pid, cls='fc'):
    if pid in kit:
        lg = base64.b64encode(open(f'{HERE}/kit/{kit[pid]["logo"]}', 'rb').read()).decode()
        return f'<span class="{cls}" style="--tc:{lift(kit[pid]["field"])}"><img class="lg" src="data:image/svg+xml;base64,{lg}"></span>'
    return f'<span class="{cls}" style="--tc:{lift(kof(pid)["field"])}"><img src="{hs(pid)}"></span>'
def last(n):
    parts = n.split(' '); return parts[-2] if parts[-1] in ('Jr.', 'Sr.', 'II', 'III', 'IV') and len(parts) > 2 else parts[-1]
f1 = lambda v: f'{abs(v):.1f}'
sg = lambda v: ('+' if v >= 0 else '−') + f1(v)
em = lambda v: f'<em class="{"dn" if v < 0 else "up"}">{sg(v)}</em>'  # red only when the number is negative
BLOB = '<svg viewBox="0 0 300 70" preserveAspectRatio="none"><path d="M14 18 C30 0 90 6 150 4 C210 2 270 -2 290 16 C304 30 300 50 286 62 C260 74 200 66 150 68 C96 70 36 76 14 62 C-2 50 0 30 14 18Z" fill="var(--tc)" stroke="#fff" stroke-width="6"/></svg>'

if KIND == 'luck':
    lst = r.get('unlucky') or []
    top = lst[:3]; w = top[0]; tid = w['id']
    # a busted bet slip per bad-luck loss: the normal-week line (both teams' usual scores — a win), torn off, then the
    # final (both teams' real scores, each with how far it moved), stamped with the real loss
    rows = ''
    # the 3 worst (biggest gap between projection and result), worst first
    worst = sorted(w['games'], key=lambda g: -(g['usual_margin'] - g['margin']))[:3]
    for g in worst:
        mu, ou = g.get('me_usual'), g.get('op_usual'); mt, ot = g.get('me_tot'), g.get('op_tot')
        if mu is None: mt, ot = 0, -g['margin']; mu, ou = g.get('under', 0), g['usual_margin'] - g.get('under', 0)  # old data
        dl = lambda v: f'<em class="dl{" dn" if v < 0 else ""}">{sg(v)}</em>'
        line = lambda t, v, d='': f'<div class="ln">{tpic(t, "tsk ci")}<b>{v:.1f}</b>{d}</div>'
        rows += (f'<div class="slip"><div class="sh2"><span class="wk">WK {g["week"]}</span></div>'
                 f'<i class="lb">projection</i>{line(tid, mu)}{line(g["opp"], ou)}'
                 f'<div class="pk">WIN by {f1(g["usual_margin"])}</div><div class="tear"></div>'
                 f'{line(tid, mt)}{line(g["opp"], ot)}'
                 f'<div class="lk"><span>own luck</span>{dl(mt - mu)}</div><div class="lk"><span>opp luck</span>{dl(ou - ot)}</div>'
                 f'<div class="stp">LOST by {f1(g["margin"])}</div></div>')
    band = f'<div class="wk4 slips">{rows}</div>'
    runners = ''.join(
        f'<div class="ru"><span class="rk">{x.get("_rk", i)}</span>{tpic(x["id"], "tsk sm")}'
        f'<span class="rn"><b>{tname(x["id"])}</b></span><span class="rv">{x["n"]}</span></div>'
        for i, x in ((2, top[1] if len(top) > 1 else None), (3, top[2] if len(top) > 2 else None)) if x)
    ic = ('<svg class="ic" viewBox="0 0 36 30"><rect x="6" y="3" width="24" height="24" rx="5" fill="#ffd23f" stroke="#16181d" stroke-width="2.5"/>'
          '<circle cx="12.5" cy="9.5" r="2.6" fill="#16181d"/><circle cx="23.5" cy="20.5" r="2.6" fill="#16181d"/></svg>')
    title = f'<div class="ttl"><span class="blb">{BLOB}<span class="w">{ic}<b>UNLUCKIEST</b></span></span></div>'
    big = (f'<div class="big"><b>{w["n"]}</b><span class="note">bad-luck losses</span>'
           f'<span class="mx">{sum(g["usual_margin"] - g["margin"] for g in worst):.0f}</span><span class="note">points of bad luck</span></div>')
else:
    lst = r.get('stuck') or sorted(r.get('draft') or [], key=lambda x: (-x['kept'], -x['kept'] / max(1, x['spent'])))
    top = lst[:3]; w = top[0]; tid = w['id']
    MAXP = max((p[2] for x in r.get('draft', []) for p in x['still'] + x.get('gone', [])), default=1)
    piles = ''
    # every pick, priciest first; one he no longer has is faded, with where he is now (that team's logo, or FA)
    allp = [(x[0], x[1], x[2], False, None) for x in w['still']] + [(x[0], x[1], x[2], True, x[3]) for x in w.get('gone', [])]
    for pid, nm, price, gone, now in sorted(allp, key=lambda p: -p[2])[:7]:
        if price <= 5:  # a coin per dollar
            stack = '<span class="coins">' + '<i class="coin"></i>' * price + '</span>'
        else:
            stack = f'<span class="cash" style="height:{max(14, round(165 * price / MAXP))}px"></span>'
        where = (f'<span class="now">now {tpic(now, "tsk xs") if now else "<b>FA</b>"}</span>' if gone else '')
        piles += f'<div class="pile{" gone" if gone else ""}">{face(pid)}{stack}<b class="pr">${price}</b><span class="pn">{last(nm)}</span>{where}</div>'
    band = f'<div class="wk4 piles">{piles}</div>'
    runners = ''.join(
        f'<div class="ru"><span class="rk">{x.get("_rk", i)}</span>{tpic(x["id"], "tsk sm")}'
        f'<span class="rn"><b>{tname(x["id"])}</b></span><span class="rv">${x["kept"]}</span></div>'
        for i, x in ((2, top[1] if len(top) > 1 else None), (3, top[2] if len(top) > 2 else None)) if x)
    ic = ('<svg class="ic" viewBox="0 0 36 30"><rect x="3" y="7" width="30" height="16" rx="2" fill="#4ade80" stroke="#16181d" stroke-width="2.5"/>'
          '<circle cx="18" cy="15" r="4.5" fill="#16181d"/><text x="18" y="18" font-size="7" font-weight="800" text-anchor="middle" fill="#4ade80" font-family="Inter">$</text></svg>')
    title = f'<div class="ttl"><span class="blb">{BLOB}<span class="w">{ic}<i>STUCK WITH THE</i> <b>DRAFT</b></span></span></div>'
    big = (f'<div class="big"><b>${w["kept"]}</b><span class="note">still rostered</span>'
           f'<span class="mx">${w["spent"]}</span><span class="note">spent</span></div>')
hero = f'{tpic(tid, "tsk")}<div><div class="tn"{tfs(tname(tid))}>{tname(tid)}</div></div>'

css = open(f'{HERE}/sup_base.css').read().replace('family=Bricolage', 'family=Kalam:wght@700&family=Courier+Prime:wght@700&family=Permanent+Marker&family=Caveat+Brush&family=Bricolage', 1)
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
.tsk.xs{display:inline-grid;width:24px;height:24px;box-shadow:0 0 0 2px #16181d;vertical-align:middle;margin:0 6px}
.tn{font:800 40px/1 "Bricolage Grotesque";letter-spacing:-.02em;text-wrap:balance}.win>div{min-width:0}
.win{height:168px}
.big{display:flex;flex-direction:column;align-items:flex-end}
.big b{text-shadow:4px 4px 0 color-mix(in srgb,var(--tc) 85%,#000)}
.note{display:block;white-space:nowrap;margin-top:6px!important;background:none!important;padding:0!important;color:var(--text)!important;
  font:700 12px Inter!important;letter-spacing:.08em!important;text-transform:uppercase!important}
.big .mx{background:none!important;padding:0!important;border-radius:0!important;margin-top:10px;font:800 26px/1 "Bricolage Grotesque";color:var(--text)}
.big .mx i{font-style:normal;margin:0 8px}.big .mx{display:flex;align-items:center;gap:4px}.big .mx .ci{width:26px;height:26px}
em.dn{font-style:normal;color:#f87171}em.up{font-style:normal;color:#4ade80}
.big .note{white-space:nowrap}
.wk4{box-sizing:border-box;height:318px;margin:22px 0 12px;padding:14px 16px;background:var(--bg);border-radius:20px}
.fc{position:relative;display:block;width:62px;height:62px;border-radius:50%;background:var(--tc);overflow:hidden;box-sizing:border-box;
  border:2.5px solid #16181d;box-shadow:3px 3px 0 0 #16181d;z-index:1}
.fc img{position:absolute;left:50%;top:-6%;width:200%;transform:translateX(-50%)}.fc img.lg{left:14%;top:14%;width:72%;transform:none}
/* busted bet slips */
.slips{display:flex;justify-content:center;gap:14px;padding:12px 14px;align-items:stretch}
.slip{position:relative;flex:1;max-width:172px;display:flex;flex-direction:column;padding:10px 12px 12px;background:#f3ecd8;color:#16181d;
  box-shadow:4px 4px 0 0 #16181d;font-family:"Courier Prime",ui-monospace,monospace;
  -webkit-mask:conic-gradient(from -45deg at bottom,#0000,#000 1deg 89deg,#0000 90deg) 50%/12px 100%}
.sh2{display:flex;justify-content:center;margin-bottom:6px}
.slip .wk{font:800 14px "Bricolage Grotesque";background:#ffd23f;border:2px solid #16181d;padding:1px 8px}
.slip .lb{font:700 12px "Courier Prime",monospace;font-style:normal;letter-spacing:.06em;text-transform:uppercase;text-align:center;margin:2px 0 3px}
.ln{display:flex;align-items:center;gap:8px;height:28px}
.ln b{font:700 22px "Courier Prime",monospace}
.tsk.ci{flex:none;width:26px;height:26px;box-shadow:0 0 0 2px #16181d}
.lk{display:flex;align-items:baseline;justify-content:space-between;font:700 12px "Courier Prime",monospace;text-transform:uppercase;letter-spacing:.04em;margin-top:3px}
.dl{margin-left:auto;font:700 14px "Courier Prime",monospace;font-style:normal;color:#16181d}.dl.dn{color:#c81e1e}
.pk{text-align:center;font:800 16px "Bricolage Grotesque";color:#15803d;margin-top:2px}
.tear{height:0;border-top:2.5px dashed #16181d;margin:8px -12px 4px}
.stp{align-self:center;margin-top:8px;padding:3px 10px;border:3px solid #c81e1e;color:#c81e1e;font:800 20px "Bricolage Grotesque";white-space:nowrap;
  box-shadow:inset 0 0 0 2px #f3ecd8,inset 0 0 0 4px #c81e1e}
/* piles of cash */
.piles{display:flex;justify-content:center;align-items:flex-end;gap:16px}
.pile{display:flex;flex-direction:column;align-items:center;min-width:0}
.cash{display:block;width:58px;margin-top:-8px;border:2.5px solid #16181d;border-radius:3px;box-shadow:3px 3px 0 0 #16181d;
  background:repeating-linear-gradient(180deg,#6fcf7a 0 7px,#3e9a4c 7px 9px,#16181d 9px 10.5px)}
.coins{display:flex;flex-direction:column-reverse;align-items:center;margin-top:8px}
.coin{display:block;width:44px;height:13px;margin-top:-5px;border-radius:50%;background:#ffd23f;border:2px solid #16181d}
.pile.gone .fc,.pile.gone .cash,.pile.gone .coins,.pile.gone .pr,.pile.gone .pn{opacity:.35}
.pile.gone .cash{filter:grayscale(1)}
.now{display:flex;align-items:center;gap:4px;margin-top:3px;font:800 11px Inter;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}.now .tsk.xs{width:20px;height:20px;margin:0}
.pr{margin-top:8px;font:800 20px "Bricolage Grotesque"}.pn{font:700 12px Inter;white-space:nowrap}
.ru{grid-template-columns:28px 46px 1fr auto;height:72px;padding-top:0;padding-bottom:0;box-sizing:border-box}
</style>''')
html = (f'<title>sup {KIND}</title>{css}<div class="card">{title}'
        f'<div class="win">{hero}{big}</div>{band}{runners}</div>')
open(f'{S}/m_sup_{KIND}.html', 'w').write(html)
