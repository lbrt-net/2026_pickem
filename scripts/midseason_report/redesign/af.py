# af.py S -> m_af.html : All-Fantasy teams in the card look (team panel + knockout mark, stacked name, two-color strip)
import json, sys, urllib.parse, os
S = sys.argv[1]; K = __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), 'kit')
r = json.load(open(f'{S}/work3/report.json')); T = r['teams']
kit = json.load(open(f'{K}/kit.json'))
def hx(c): c = c.lstrip('#'); return [int(c[i:i+2], 16) for i in (0, 2, 4)]
def mix(a, b, t): return '#' + ''.join(f'{round(x*(1-t)+y*t):02x}' for x, y in zip(hx(a), hx(b)))
def lum(c): r_, g, b = hx(c); return .2126*r_ + .7152*g + .0722*b
for k in kit.values():
    k['panel'] = k['field'] if lum(k['field']) >= 45 else mix(k['field'], '#ffffff', .16)
    k['accent'] = next((c for c in (k['secondary'], k['tertiary'], '#ffffff') if lum(c) >= 60), '#ffffff')
enc = lambda s: "url('data:image/svg+xml," + urllib.parse.quote(s) + "')"
AL = {'GS': 'GSW', 'NY': 'NYK', 'SA': 'SAS', 'NO': 'NOP', 'PHO': 'PHX', 'UTAH': 'UTA', 'WSH': 'WAS', 'BRK': 'BKN'}
def kt(ab): return kit[AL.get(ab, ab)]
def chip(tid):
    t = T.get(tid)
    if not t: return '<span class="own">Free agent</span>'
    lg = r['tlogo'].get(tid)
    ic = f'<img class="ti" src="{lg}">' if lg else f'<i class="ti" style="background:{t["color"]}"></i>'
    return f'<span class="own">{ic}{t["name"]}</span>'
WA = [json.load(open(f'{S}/work3/f3/wa{w}.json')) for w in __import__('json').loads(__import__('os').environ.get('MS_WEEKS', '[1, 2, 3, 4]'))]
def weeks_on(e):  # weeks he spent on this fantasy team's roster
    return sum(1 for wa in WA if any(x['id'] == e['id'] for x in (wa.get(e['team']) or {}).get('entries', [])))
def tile(e):
    k = kt(e['nba']); mk = enc(open(f'{K}/{k["knock"]}').read())
    pos = {'TM': 'TEAM'}.get(e['pos'], e['pos'])
    if e['pos'] == 'TM':
        city, _, nick = e['name'].rpartition(' ')
        art = '<img class="lg" src="data:image/svg+xml;base64,' + __import__('base64').b64encode(open(f'{K}/{k["logo"]}', 'rb').read()).decode() + '">'; fn, ln, sub = city, nick, e['how']
        bg = f'radial-gradient(circle at 60% 38%,{mix(k["panel"],"#ffffff",.12)},{k["panel"]} 70%)'
    else:
        w = e['name'].split(' '); kk = 2 if len(w) > 2 and w[-1].rstrip('.').lower() in ('jr', 'sr', 'ii', 'iii', 'iv') else 1
        fn, ln = ' '.join(w[:-kk]), ' '.join(w[-kk:])
        art = f'<img class="hs" src="https://cdn.nba.com/headshots/nba/latest/1040x760/{e["id"]}.png">'; sub = e['how']
        bg = f'{mk} -70px -40px/380px auto no-repeat,{k["panel"]}'
    o = T.get(e['team'], {}); lng = ' class="lng"' if len(o.get('name', '')) > 14 else ''  # (3.11: no same-quote nesting)
    oc = o.get('color') or '#30363d'; lg = r['tlogo'].get(e['team'])
    ink = '#0d1117' if lum(oc) > 150 else '#f2f4f7'
    ic = f'<img class="ti" src="{lg}">' if lg else f'<i class="ti" style="background:{mix(oc,"#000000",.3)}"></i>'
    aink = '#0d1117' if lum(k['accent']) > 150 else '#f2f4f7'
    deep = mix(k['panel'], '#000000', .5)
    return (f'<div class="t" style="--pc:{k["panel"]};--ac:{k["accent"]};--aink:{aink};--deep:{deep};--oc:{oc};--ink:{ink}">'
            f'<div class="art" style="background:{bg}"><span class="pos">{pos}</span>{art}</div>'
            f'<div class="nm"><div class="fn">{fn}</div><div class="ln" style="font-size:{min(30, int(30 * 11 / max(11, len(ln))))}px!important">{ln}</div><div class="tot"><b>{e["tot"]:.1f}</b><i>pts</i></div></div>'
            f'<div class="own"><span class="who">{ic}<b{lng}>{o.get("name","Free agent")}</b></span><span class="how">{sub} · {weeks_on(e)} week{"s" if weeks_on(e) != 1 else ""}</span></div></div>')
head = open(f'{S}/m_ballot.html').read(); head = head[:head.index('<div class="grid">')]
CSS = '''
.af{display:flex;flex-direction:column;gap:34px;max-width:1080px}
.af h2{font:800 26px var(--fd);letter-spacing:.06em;text-transform:uppercase;margin:0 0 12px;display:flex;align-items:center;gap:12px}
.af h2:before{content:"";width:14px;height:24px;background:var(--accent,#ff6b1a);transform:skewX(-14deg)}
.row{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}
.t{position:relative;display:flex;flex-direction:column;min-width:0;background:var(--pc);overflow:hidden;
   clip-path:polygon(0 0,calc(100% - 18px) 0,100% 18px,100% 100%,0 100%)}
.art{position:relative;height:178px;overflow:hidden}
.art .hs{position:absolute;right:-6px;bottom:0;height:168px}
.art .lg{position:absolute;right:10px;top:50%;width:118px;height:118px;transform:translateY(-50%);object-fit:contain;filter:drop-shadow(0 4px 10px rgba(0,0,0,.35))}
.pos{position:absolute;left:10px;top:10px;z-index:2;font:800 15px/1 var(--fd);letter-spacing:.1em;text-transform:uppercase;padding:5px 8px 4px;background:#0d1117;box-shadow:inset 3px 0 0 var(--ac)}
.art .lg{left:50%!important;right:auto!important;top:56%!important;width:140px!important;height:140px!important;transform:translate(-50%,-50%)!important}
.who b.lng{font-size:12px!important;white-space:normal!important;line-height:1.1}
.nm{position:relative;padding:0 12px 12px;background:
  repeating-linear-gradient(135deg,transparent 0 9px,rgba(255,255,255,.035) 9px 10px),linear-gradient(180deg,var(--deep),var(--deep));
  border-top:4px solid var(--ac)}
.nm .fn{margin-top:10px;position:relative;z-index:3;font-size:14px;text-shadow:0 1px 3px rgba(0,0,0,.6)}
.nm .ln{position:relative;z-index:3;font-size:30px!important;text-shadow:0 2px 0 rgba(0,0,0,.35)}
.nm .tot{display:inline-flex;align-items:baseline;gap:5px;margin-top:10px;padding:6px 10px 4px;background:var(--ac);color:var(--aink);
  clip-path:polygon(0 0,100% 0,calc(100% - 10px) 100%,0 100%);padding-right:18px}
.nm .tot b{font:800 36px/.9 var(--fd)}.nm .tot i{font:800 14px var(--fd);font-style:normal;letter-spacing:.06em;text-transform:uppercase}
.art{height:190px!important}.art:after{content:"";position:absolute;left:0;right:0;bottom:0;height:30px;background:linear-gradient(180deg,transparent,var(--deep));z-index:2}
.fn{font-size:13px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ln{font:800 25px/1 var(--fd);text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.how{font-size:15px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.own{position:relative;display:flex;flex-direction:column;gap:6px;padding:10px 12px 11px;margin-top:auto;background:var(--oc);color:var(--ink);
     }
.tot{font:800 40px/.9 var(--fd);margin-top:8px}
.who{display:flex;align-items:center;gap:7px;min-width:0}
.who b{font-size:15px;font-weight:800;letter-spacing:.04em;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.who .ti{width:26px;height:26px;border-radius:3px;flex:none;object-fit:cover;box-shadow:0 0 0 2px var(--ink)}
'''
body = '<div class="af">' + ''.join(f'<section><h2>{n} Team</h2><div class="row">' + ''.join(tile(e) for e in team) + '</div></section>'
                                   for n, team in zip(("1st", "2nd", "3rd"), r['af'])) + '</div>'
open(f'{S}/m_af.html', 'w').write(head.replace('</style>', CSS + '</style>', 1) + body)
